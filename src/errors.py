class ConsultaInvalidaError(Exception):
    """La consulta no se puede procesar. No se reintenta."""


class ContratoInvalidoError(Exception):
    """Se agotaron los intentos sin obtener una respuesta que cumpla el contrato."""
