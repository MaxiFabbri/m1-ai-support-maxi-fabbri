from openai import OpenAI

from .base import Provider


class NvidiaProvider(Provider):
    """Consulta el endpoint NVIDIA compatible con Chat Completions."""

    def ask(self, messages, parameters) -> str:
        self.last_usage = None
        response = self._consultar_api(messages, parameters)
        self.last_usage = response.usage
        return self._obtener_texto(response)

    def _crear_cliente(self):
        api_key = self.leer_variable_entorno("NVIDIA_API_KEY")
        self.model = self.leer_variable_entorno("NVIDIA_MODEL_ID")
        base_url = self.leer_variable_entorno("NVIDIA_BASE_URL")
        return OpenAI(api_key=api_key, base_url=base_url, max_retries=0)

    def _consultar_api(self, messages: list[dict[str, str]], parameters: dict):
        with self._crear_cliente() as client:
            return client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=parameters["max_output_tokens"],
                temperature=parameters["temperature"],
                top_p=parameters["top_p"],
            )

    def _obtener_texto(self, response) -> str:
        text = response.choices[0].message.content if response.choices else None
        if not text:
            raise RuntimeError("NVIDIA no devolvió texto para este prompt.")
        return text
