from pydantic import ValidationError

from errors import ContratoInvalidoError
from support_response import SupportResponse


class ResponseHandler:
    """Obtiene una respuesta válida, repitiendo solo si falla la validación."""

    def __init__(self, router):
        self.router = router
        self.max_intentos = 3

    def obtener_respuesta_validada(self, messages, parameters) -> SupportResponse:
        errores_previos = ""
        mensajes_actuales = messages.copy()

        # El límite incluye la primera llamada al proveedor.
        for intento in range(1, self.max_intentos + 1):
            answer = self.router.ask(mensajes_actuales, parameters)

            try:
                return SupportResponse.model_validate_json(answer)
            except ValidationError as error:
                errores_previos += f"Intento {intento}: {error}\n\n"
                mensajes_actuales = messages.copy()
                mensajes_actuales.append({
                    "role": "user",
                    "content": (
                        f"Estos fueron los errores de tus respuestas anteriores:\n{errores_previos}\n"
                        "Corregilos y devolvé únicamente el JSON con los cuatro campos del contrato."
                    ),
                })

        raise ContratoInvalidoError(
            f"Se agotaron los {self.max_intentos} intentos. "
            f"La respuesta del modelo no cumple el contrato:\n{errores_previos}"
        )
