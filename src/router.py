from backoff import call_with_backoff
from config import AppConfig
from providers import GeminiProvider, OpenAIProvider


class Router:
    """Elige un proveedor y le delega la consulta."""

    def __init__(self, config: AppConfig):
        self.config = config
        print("====================================================================")
        print(f"Configuraciones cargadas: {self.config.__dict__}")
        print("====================================================================")

        # Cada nombre del diccionario apunta al objeto que sabe llamar a su API.
        self.adapters = {
            "gemini": GeminiProvider(config, model="gemini-3.5-flash-lite"),
            "openai": OpenAIProvider(config, model="gpt-4.1-mini"),
            # "openai": OpenAIProvider(config, model="gpt-6-luna"), # no acepta temperatura 0.2
        }
        self.primary = config.default_provider

        if self.primary not in self.adapters:
            raise ValueError(f"El proveedor '{self.primary}' todavía no está implementado.")

    def ask(self, prompt: str) -> str:
        # Esta función guarda la consulta para poder volver a ejecutarla.
        print(f"Enrutando la consulta '{self.primary}'... '{prompt}'")
        def consulta():
            return self.adapters[self.primary].ask(prompt)

        return call_with_backoff(consulta)
