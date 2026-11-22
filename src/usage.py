import sys


def mostrar_usage(usage) -> None:
    """Muestra los datos de consumo entregados por el SDK, sin calcular ni renombrar.

    exclude_unset evita agregar campos opcionales que no llegaron en la respuesta.
    Si no hay metadata de consumo, muestra null. La salida va por stderr para
    mantenerla separada del texto de la respuesta del modelo.
    """
    if usage is None:
        print("null", file=sys.stderr)
        return

    print(usage.model_dump_json(indent=2, exclude_unset=True), file=sys.stderr)
