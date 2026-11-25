from google import genai
from google.genai import types

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

    def ask(self, messages, parameters) -> str:
        self.last_usage = None
        response = self._consultar_api(messages, parameters)
        self.last_usage = response.usage_metadata
        return self._obtener_texto(response)

    def _crear_cliente(self):
        api_key = self.leer_variable_entorno("GEMINI_API_KEY")
        self.model = self.leer_variable_entorno("GEMINI_MODEL_ID")
        # attempts=1 desactiva los reintentos internos del SDK.
        http_options = types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1))
        return genai.Client(api_key=api_key, http_options=http_options)

    def _consultar_api(self, messages: list[dict[str, str]], parameters: dict):
        instrucciones, contenidos = adaptar_mensajes_gemini(messages)
        with self._crear_cliente() as client:
            return client.models.generate_content(
                model=self.model,
                contents=contenidos,
                config=types.GenerateContentConfig(
                    system_instruction=instrucciones or None,
                    max_output_tokens=parameters["max_output_tokens"],
                    temperature=parameters["temperature"],
                    top_p=parameters["top_p"],
                ),
            )

    def _obtener_texto(self, response) -> str:
        if not response.text:
            raise RuntimeError("Gemini no devolvió texto para este prompt.")

        return response.text
