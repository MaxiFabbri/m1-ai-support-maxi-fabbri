from config import AppConfig
from providers import GeminiProvider, NvidiaProvider, OpenAIProvider


class Router:
    """Selecciona un proveedor y le delega los mensajes ya preparados."""

    def __init__(self, config: AppConfig, provider=None):
        self.adapters = self._crear_adaptadores()
        self.primary = config.default_provider
        if provider is not None:
            self.primary = provider.strip().lower()
        self._validar_proveedor()

    def _crear_adaptadores(self) -> dict:
        return {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "nvidia": NvidiaProvider(),
        }

    def _validar_proveedor(self) -> None:
        if self.primary not in self.adapters:
            raise ValueError(f"El proveedor '{self.primary}' todavía no está implementado.")

    def ask(self, messages, parameters) -> str:
        return self.adapters[self.primary].ask(messages, parameters)

    def obtener_usage(self):
        return self.adapters[self.primary].last_usage
