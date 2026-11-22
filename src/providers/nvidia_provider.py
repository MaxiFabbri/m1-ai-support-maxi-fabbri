from openai import OpenAI

from prompt_builder import PromptBuilder

from .base import Provider


class NvidiaProvider(Provider):
    """Consulta un endpoint NVIDIA compatible con Chat Completions."""

    def ask(self, prompt: str) -> str:
        self.last_usage = None
        builder = PromptBuilder(prompt, self.config.prompt_path)
        messages = builder.build_messages()
        api_key = self.leer_variable_entorno("NVIDIA_API_KEY")
        self.model = self.leer_variable_entorno("NVIDIA_MODEL_ID")
        base_url = self.leer_variable_entorno("NVIDIA_BASE_URL")

        # Usa el SDK de OpenAI, pero la solicitud se dirige a la URL de NVIDIA.
        with OpenAI(api_key=api_key, base_url=base_url, max_retries=0) as client:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                # NVIDIA utiliza max_tokens para el límite de generación.
                max_tokens=builder.parameters["max_output_tokens"],
                temperature=builder.parameters["temperature"],
                top_p=builder.parameters["top_p"],
            )

        self.registrar_usage(response.usage)
        text = response.choices[0].message.content
        if not text:
            raise RuntimeError("NVIDIA no devolvió texto para este prompt.")

        return text
