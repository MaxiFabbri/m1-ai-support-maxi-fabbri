from openai import OpenAI

from prompt_builder import PromptBuilder

from .base import Provider


class OpenAIProvider(Provider):
    """Contiene la llamada específica a la API de OpenAI."""

    def ask(self, prompt: str) -> str:
        self.last_usage = None
        builder = PromptBuilder(prompt, self.config.prompt_path)
        messages = builder.build_messages()
        api_key = self.leer_variable_entorno("OPENAI_API_KEY")
        self.model = self.leer_variable_entorno("OPENAI_MODEL_ID")

        # Los reintentos se controlan desde call_with_backoff en el router.
        with OpenAI(api_key=api_key, max_retries=0) as client:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=builder.parameters["max_output_tokens"],
                temperature=builder.parameters["temperature"],
                top_p=builder.parameters["top_p"],
            )

        self.registrar_usage(response.usage)
        text = response.choices[0].message.content
        if not text:
            raise RuntimeError("OpenAI no devolvió texto para este prompt.")

        return text
