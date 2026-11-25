from openai import OpenAI

from .base import Provider


class OpenAIProvider(Provider):
    """Envía mensajes a OpenAI y conserva el consumo de la última llamada."""

    def ask(self, messages, parameters) -> str:
        self.last_usage = None
        response = self._consultar_api(messages, parameters)
        self.last_usage = response.usage
        return self._obtener_texto(response)

    def _crear_cliente(self):
        api_key = self.leer_variable_entorno("OPENAI_API_KEY")
        self.model = self.leer_variable_entorno("OPENAI_MODEL_ID")
        return OpenAI(api_key=api_key, max_retries=0)

    def _consultar_api(self, messages: list[dict[str, str]], parameters: dict):
        with self._crear_cliente() as client:
            return client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=parameters["max_output_tokens"],
                temperature=parameters["temperature"],
                top_p=parameters["top_p"],
            )

    def _obtener_texto(self, response) -> str:
        text = response.choices[0].message.content if response.choices else None
        if not text:
            raise RuntimeError("OpenAI no devolvió texto para este prompt.")
        return text
