import math
import random
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


class CuotaAgotadaError(RuntimeError):
    """El proveedor no tiene cuota disponible; esperar no resuelve el problema."""


class ReintentosAgotadosError(RuntimeError):
    """El proveedor sigue limitado después de todos los intentos permitidos."""


def obtener_codigo_http(error: Exception):
    """Unifica dónde buscar el código HTTP sin depender de un SDK concreto."""
    codigo = getattr(error, "status_code", None)
    if codigo is None:
        codigo = getattr(error, "code", None)
    return codigo


def leer_retry_info_gemini(error: Exception):
    """Extrae el tiempo indicado en RetryInfo, si está disponible."""
    detalles = getattr(error, "details", {})
    if not isinstance(detalles, dict):
        return None

    datos = detalles.get("error", detalles)
    if not isinstance(datos, dict):
        return None

    for detalle in datos.get("details", []):
        if isinstance(detalle, dict) and detalle.get("@type", "").endswith("google.rpc.RetryInfo"):
            return str(detalle.get("retryDelay", "")).removesuffix("s")

    return None


def leer_retry_after(error: Exception) -> float | None:
    """Busca la espera del proveedor y la convierte a segundos válidos."""
    valor = getattr(error, "retry_after", None)

    if valor is None:
        respuesta = getattr(error, "response", None)
        headers = getattr(respuesta, "headers", {})
        valor = headers.get("retry-after")

    if valor is None:
        valor = leer_retry_info_gemini(error)

    if valor is None:
        return None

    try:
        segundos = float(valor)
    except (TypeError, ValueError):
        # Retry-After también puede indicar una fecha HTTP en vez de segundos.
        try:
            fecha = parsedate_to_datetime(str(valor))
            segundos = max(0.0, (fecha - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None

    return segundos if math.isfinite(segundos) and segundos >= 0 else None


def calcular_espera(error: Exception, intento: int) -> float:
    """Prioriza la espera del proveedor; si falta, usa backoff exponencial con jitter."""
    retry_after = leer_retry_after(error)
    if retry_after is not None:
        return retry_after

    return (2 ** intento) + random.uniform(0, 1)


def call_with_backoff(fn, max_retries: int = 5):
    """Reintenta una operación; max_retries cuenta los intentos totales.

    Informa cuota agotada o intentos agotados con errores distintos, para que
    el router pueda decidir si cambia de proveedor. Esta función no lo elige.
    """
    if max_retries < 1:
        raise ValueError("max_retries debe ser al menos 1.")

    for intento in range(max_retries):
        try:
            return fn()
        except Exception as error:
            if obtener_codigo_http(error) != 429:
                raise

            # La falta de saldo de OpenAI también usa 429, pero no es temporal.
            if getattr(error, "code", None) == "insufficient_quota":
                raise CuotaAgotadaError(
                    "El proveedor informa cuota o saldo agotado. Revisá la facturación."
                ) from error

            if intento == max_retries - 1:
                raise ReintentosAgotadosError(
                    f"Se agotaron los {max_retries} intentos por límite de solicitudes."
                ) from error

            espera = calcular_espera(error, intento)
            print(
                f"Límite de solicitudes. Intento {intento + 1}/{max_retries}: esperando {espera:.2f} s.",
                file=sys.stderr,
            )
            time.sleep(espera)
