import tomllib
from pathlib import Path


class AppConfig:
    """Reúne la configuración que necesita la aplicación."""

    def __init__(self, config_path: Path):
        # Leemos las opciones generales desde el archivo recibido.
        with config_path.open("rb") as file:
            settings = tomllib.load(file)

        # Guardamos esas opciones en este objeto, sin valores duplicados.
        self.default_provider = settings["LLM_PROVIDER"].strip().lower()
        self.max_output_tokens = settings["LLM_MAX_OUTPUT_TOKENS"]
        self.temperature = settings["LLM_TEMPERATURE"]
        self.top_p = settings["LLM_TOP_P"]
