import tomllib
from pathlib import Path


class AppConfig:
    """Carga las opciones generales de config.toml."""

    def __init__(self, config_path: Path):
        settings = self._leer_configuracion(config_path)
        self.default_provider = self._leer_texto(settings, "LLM_PROVIDER").lower()
        prompt_file = self._leer_texto(settings, "PROMPT_FILE")
        self.prompt_path = (config_path.resolve().parent / prompt_file).resolve()

    def _leer_configuracion(self, config_path: Path) -> dict:
        try:
            with config_path.open("rb") as file:
                return tomllib.load(file)
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise ValueError(f"No se pudo cargar la configuración {config_path}: {error}") from error

    def _leer_texto(self, settings: dict, name: str) -> str:
        value = settings.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} debe ser un texto no vacío en config.toml.")
        return value.strip()
