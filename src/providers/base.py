import os


class Provider:
    """Define la llamada común y la lectura de variables que usan los proveedores."""

    def __init__(self):
        self.model = None
        self.last_usage = None

    def leer_variable_entorno(self, nombre: str) -> str:
        valor = os.getenv(nombre, "").strip()
        if not valor:
            raise ValueError(f"Completá {nombre} en el archivo .env.")
        return valor

    def ask(self, messages, parameters) -> str:
        raise NotImplementedError("Cada proveedor debe implementar el método ask.")
