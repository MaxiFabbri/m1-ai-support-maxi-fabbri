import argparse
from typing import List, Optional

from config import AppConfig


class SupportCLI:
    """Gestiona la entrada, validación y salida de la terminal."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.parser = argparse.ArgumentParser(
            description="Recibe una consulta de soporte para Nubbix."
        )
        self.parser.add_argument(
            "consulta", help="Consulta de soporte entre comillas."
        )
        self.parser.add_argument(
            "--provider",
            help="Proveedor a utilizar. Tiene prioridad sobre LLM_PROVIDER de config.toml.",
        )

    def run(self, argv: Optional[List[str]] = None) -> None:
        args = self.parser.parse_args(argv)

        consulta = args.consulta.strip()
        if not consulta:
            self.parser.error("La consulta no puede estar vacía.")

        provider = args.provider or self.config.default_provider
        # En el siguiente paso, el router recibirá el proveedor y la consulta.
        print(f"Proveedor seleccionado: {provider}")
        print(f"Consulta recibida: {consulta}")
        print("Etapa inicial: la consulta todavía no se envía a una API.")
