from google import genai
from google.genai import types

from prompt_builder import PromptBuilder

from .base import Provider


def adaptar_mensajes_gemini(messages: list[dict[str, str]]) -> tuple[str, list[types.Content]]:
    """Separa las instrucciones de sistema y traduce los roles para Gemini."""
    instrucciones = []
    contenidos = []

    for message in messages:
        role = message["role"]
        if role == "system":
            instrucciones.append(message["content"])
            continue

        if role not in ("user", "assistant"):
            raise ValueError(f"Rol no soportado por el adaptador de Gemini: {role}")

        # Gemini llama model al rol que OpenAI llama assistant.
        contenidos.append(types.Content(
            role="model" if role == "assistant" else "user",
            parts=[types.Part.from_text(text=message["content"])],
        ))

    return "\n\n".join(instrucciones), contenidos


class GeminiProvider(Provider):
    """Contiene la llamada específica a la API de Gemini."""

    def ask(self, prompt: str) -> str:
        self.last_usage = None
        builder = PromptBuilder(prompt, self.config.prompt_path)
        messages = builder.build_messages()
        instrucciones, contenidos = adaptar_mensajes_gemini(messages)
        api_key = self.leer_variable_entorno("GEMINI_API_KEY")
        self.model = self.leer_variable_entorno("GEMINI_MODEL_ID")

        # attempts=1 significa una sola llamada, sin reintentos internos del SDK.
        http_options = types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1))
        with genai.Client(api_key=api_key, http_options=http_options) as client:
            response = client.models.generate_content(
                model=self.model,
                contents=contenidos,
                config=types.GenerateContentConfig(
                    system_instruction=instrucciones or None,
                    max_output_tokens=builder.parameters["max_output_tokens"],
                    temperature=builder.parameters["temperature"],
                    top_p=builder.parameters["top_p"],
                ),
            )

        self.registrar_usage(response.usage_metadata)
        if not response.text:
            raise RuntimeError("Gemini no devolvió texto para este prompt.")

        return response.text
