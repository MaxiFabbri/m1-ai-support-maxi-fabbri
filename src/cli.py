import argparse

from usage import mostrar_usage


class SupportCLI:
    """Recibe argumentos y muestra los resultados en la terminal."""

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Recibe una consulta de soporte para Nubbix."
        )
        self.parser.add_argument("consulta", help="Consulta de soporte entre comillas.")
        self.parser.add_argument(
            "--provider",
            help="Proveedor a utilizar. Tiene prioridad sobre LLM_PROVIDER de config.toml.",
        )

    def read_arguments(self):
        args = self.parser.parse_args()
        if not args.consulta.strip():
            self.show_error("La consulta no puede estar vacía.")
        return args

    def show_response(self, answer: str, usage) -> None:
        mostrar_usage(usage)
        print(answer)

    def show_error(self, message: str) -> None:
        self.parser.error(message)
