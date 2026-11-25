from pathlib import Path
from string import Formatter

import yaml

from errors import ConsultaInvalidaError


class PromptBuilder:
    """Prepara el prompt a partir del YAML y la consulta del usuario."""

    def __init__(self, prompt: str, prompt_path: Path):
        self.prompt = prompt
        self.prompt_path = Path(prompt_path)
        self._validar_consulta()
        datos = self._leer_yaml()
        self.version = datos.get("version")
        self.template = datos.get("plantilla")
        self.parameters = datos.get("parameters")
        self._validar_plantilla()
        self._validar_parametros()

    def _validar_consulta(self) -> None:
        if not self.prompt.strip():
            raise ConsultaInvalidaError("El mensaje del usuario no puede estar vacío.")

    def _leer_yaml(self) -> dict:
        try:
            contenido = self.prompt_path.read_text(encoding="utf-8-sig")
            datos = yaml.safe_load(contenido)
        except (OSError, yaml.YAMLError) as error:
            raise ValueError(f"No se pudo cargar el prompt {self.prompt_path}: {error}") from error
        if not isinstance(datos, dict):
            raise ValueError("El YAML del prompt debe contener un mapa de campos.")
        return datos

    def _validar_plantilla(self) -> None:
        if not isinstance(self.template, str) or not self.template.strip():
            raise ValueError("El YAML debe incluir una plantilla de texto no vacía.")

    def _validar_parametros(self) -> None:
        if not isinstance(self.parameters, dict):
            raise ValueError("El YAML debe incluir el mapa parameters.")
        self._validar_muestreo()
        self._validar_limite_tokens()

    def _validar_muestreo(self) -> None:
        for nombre, minimo, maximo in (("temperature", 0, 2), ("top_p", 0, 1)):
            valor = self.parameters.get(nombre)
            if type(valor) not in (int, float) or not minimo <= valor <= maximo:
                raise ValueError(f"parameters.{nombre} debe ser un número entre {minimo} y {maximo}.")

    def _validar_limite_tokens(self) -> None:
        limite = self.parameters.get("max_output_tokens")
        if type(limite) is not int or limite < 1:
            raise ValueError("parameters.max_output_tokens debe ser un entero mayor que cero.")

    def _validar_variables(self) -> None:
        try:
            campos = []
            for _, campo, _, _ in Formatter().parse(self.template):
                if campo is not None:
                    campos.append(campo)
            if "consulta" not in campos:
                raise ValueError("La plantilla debe incluir {consulta}.")
            for campo in campos:
                if campo != "consulta":
                    raise ValueError("La plantilla debe usar {consulta} como única variable.")
        except ValueError as error:
            raise ValueError(
                f"Plantilla inválida: {error} Usá {{consulta}} y duplicá las llaves literales de JSON."
            ) from error

    def build_prompt(self) -> str:
        """Completa la plantilla sin reinterpretar las llaves de la consulta."""
        self._validar_variables()
        try:
            return self.template.format(consulta=self.prompt)
        except (KeyError, ValueError, IndexError) as error:
            raise ValueError(f"Plantilla inválida: {error}") from error

    def build_messages(self) -> list[dict[str, str]]:
        return [{"role": "user", "content": self.build_prompt()}]
