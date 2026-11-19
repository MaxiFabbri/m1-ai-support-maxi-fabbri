import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI

from config import AppConfig


# USD por un millón de tokens, tarifa estándar paga para texto.
# Verificadas el 2026-11-18. No incluyen herramientas ni almacenamiento de caché.
# https://developers.openai.com/api/docs/models/gpt-6-luna
# https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite
TARIFAS_USD_POR_MILLON = {
    ("openai", "gpt-6-luna"): {"input": 0.40, "cached": 0.10, "output": 1.60},
    ("gemini", "gemini-3.5-flash-lite"): {"input": 0.30, "cached": 0.03, "output": 2.50},
}


@dataclass(frozen=True)
class Usage:
    """Consumo de una llamada, con los mismos nombres para ambos proveedores.

    None significa que la API no informó ese dato, no que consumió cero.
    Los tokens de caché están incluidos en input_tokens; los de razonamiento,
    en output_tokens. No deben sumarse otra vez al calcular el costo.
    """

    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cached_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def estimated_cost_usd(self) -> float | None:
        return calcular_costo(self)


def calcular_costo(usage: Usage) -> float | None:
    """Estima el costo de los tokens a tarifa paga; no consulta la facturación."""
    tarifas = TARIFAS_USD_POR_MILLON.get((usage.provider, usage.model))
    if tarifas is None or usage.input_tokens is None or usage.output_tokens is None:
        return None

    entrada_sin_cache = usage.input_tokens - usage.cached_tokens
    return (
        entrada_sin_cache * tarifas["input"]
        + usage.cached_tokens * tarifas["cached"]
        + usage.output_tokens * tarifas["output"]
    ) / 1_000_000


def normalizar_usage_openai(metadata, model: str) -> Usage:
    """Acepta el usage completo de una respuesta, también el final de un futuro stream."""
    entrada = getattr(metadata, "prompt_tokens_details", None)
    salida = getattr(metadata, "completion_tokens_details", None)
    return Usage(
        provider="openai",
        model=model,
        input_tokens=getattr(metadata, "prompt_tokens", None),
        output_tokens=getattr(metadata, "completion_tokens", None),
        total_tokens=getattr(metadata, "total_tokens", None),
        cached_tokens=getattr(entrada, "cached_tokens", None) or 0,
        reasoning_tokens=getattr(salida, "reasoning_tokens", None) or 0,
    )


def normalizar_usage_gemini(metadata, model: str) -> Usage:
    """Incluye el razonamiento en la salida facturable, además del texto visible."""
    entrada = getattr(metadata, "prompt_token_count", None)
    salida = getattr(metadata, "candidates_token_count", None)
    razonamiento = getattr(metadata, "thoughts_token_count", None) or 0
    entrada_herramientas = getattr(metadata, "tool_use_prompt_token_count", None) or 0
    return Usage(
        provider="gemini",
        model=model,
        input_tokens=None if entrada is None else entrada + entrada_herramientas,
        output_tokens=None if salida is None else salida + razonamiento,
        total_tokens=getattr(metadata, "total_token_count", None),
        cached_tokens=getattr(metadata, "cached_content_token_count", None) or 0,
        reasoning_tokens=razonamiento,
    )


def mostrar_usage(usage: Usage) -> None:
    """Muestra las métricas por stderr, separado del texto de la respuesta."""
    entrada = usage.input_tokens if usage.input_tokens is not None else "no disponible"
    salida = usage.output_tokens if usage.output_tokens is not None else "no disponible"
    total = usage.total_tokens if usage.total_tokens is not None else "no disponible"
    costo = usage.estimated_cost_usd
    importe = f"USD {costo:.8f}" if costo is not None else "no disponible"
    print(
        f"Usage [{usage.provider} / {usage.model}]\n"
        f"Tokens: entrada={entrada}, salida={salida}, total={total}\n"
        f"Incluidos: cache={usage.cached_tokens}, razonamiento={usage.reasoning_tokens}\n"
        f"Costo estimado (tarifa paga estándar de texto): {importe}",
        file=sys.stderr,
    )


class Provider:
    """Cada proveedor debe recibir un prompt y devolver texto mediante ask."""

    last_usage: Usage | None = None

    def registrar_usage(self, usage: Usage) -> None:
        """Guarda y muestra una vez el consumo final de la llamada."""
        self.last_usage = usage
        mostrar_usage(usage)

    def ask(self, prompt: str) -> str:
        raise NotImplementedError("Cada proveedor debe implementar el método ask.")


class OpenAIProvider(Provider):
    """Contiene la llamada específica a la API de OpenAI."""

    def __init__(self, config: AppConfig, model: str):
        self.config = config
        self.model = model

    def ask(self, prompt: str) -> str:
        self.last_usage = None
        project_dir = Path(__file__).resolve().parent.parent
        load_dotenv(project_dir / ".env")
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("Completá OPENAI_API_KEY en el archivo .env.")

        # Los reintentos se controlan desde call_with_backoff en el router.
        with OpenAI(api_key=api_key, max_retries=0) as client:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=self.config.max_output_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
            )

        self.registrar_usage(normalizar_usage_openai(response.usage, self.model))
        text = response.choices[0].message.content
        if not text:
            raise RuntimeError("OpenAI no devolvió texto para este prompt.")

        return text


class GeminiProvider(Provider):
    """Contiene la llamada específica a la API de Gemini."""

    def __init__(self, config: AppConfig, model: str):
        self.config = config
        self.model = model

    def ask(self, prompt: str) -> str:
        self.last_usage = None
        # La clave se carga cuando se utiliza este proveedor.
        project_dir = Path(__file__).resolve().parent.parent
        load_dotenv(project_dir / ".env")
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("Completá GEMINI_API_KEY en el archivo .env.")

        # attempts=1 significa una sola llamada, sin reintentos internos del SDK.
        http_options = types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1))
        with genai.Client(api_key=api_key, http_options=http_options) as client:
            response = client.models.generate_content(
                model=self.model,
                contents=types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
                config=types.GenerateContentConfig(
                    max_output_tokens=self.config.max_output_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                ),
            )

        self.registrar_usage(normalizar_usage_gemini(response.usage_metadata, self.model))
        if not response.text:
            raise RuntimeError("Gemini no devolvió texto para este prompt.")

        return response.text
