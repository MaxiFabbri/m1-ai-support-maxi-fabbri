import os
from pathlib import Path

from dotenv import load_dotenv

from config import AppConfig
from usage import mostrar_usage


class Provider:
    """Define la interfaz común y conserva el consumo original de la última llamada."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.model = None
        self.last_usage = None

    def leer_variable_entorno(self, nombre: str) -> str:
        """Lee una variable requerida sin guardar credenciales en AppConfig."""
        project_dir = Path(__file__).resolve().parents[2]
        load_dotenv(project_dir / ".env")
        valor = os.getenv(nombre, "").strip()
        if not valor:
            raise ValueError(f"Completá {nombre} en el archivo .env.")
        return valor

    def registrar_usage(self, usage) -> None:
        self.last_usage = usage
        mostrar_usage(usage)

    def ask(self, prompt: str) -> str:
        raise NotImplementedError("Cada proveedor debe implementar el método ask.")
