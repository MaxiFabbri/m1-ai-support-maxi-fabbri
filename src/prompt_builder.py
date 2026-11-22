from pathlib import Path
from string import Formatter

import yaml


class PromptBuilder:
    """Lee una plantilla YAML y completa su variable con la consulta del usuario."""

    def __init__(self, prompt: str, prompt_path: Path):
        if not prompt.strip():
            raise ValueError("El mensaje del usuario no puede estar vacío.")

        self.prompt = prompt
        self.prompt_path = Path(prompt_path)

        try:
            contenido = self.prompt_path.read_text(encoding="utf-8-sig")
            datos = yaml.safe_load(contenido)
        except (OSError, yaml.YAMLError) as error:
            raise ValueError(f"No se pudo cargar el prompt {self.prompt_path}: {error}") from error

        if not isinstance(datos, dict):
            raise ValueError("El YAML del prompt debe contener un mapa de campos.")

        self.version = datos.get("version")
        self.template = datos.get("plantilla")
        if not isinstance(self.template, str) or not self.template.strip():
            raise ValueError("El YAML debe incluir una plantilla de texto no vacía.")

        self.parameters = datos.get("parameters")
        self._validar_parametros()

    def _validar_parametros(self) -> None:
        """Detecta errores de configuración antes de consultar una API."""
        if not isinstance(self.parameters, dict):
            raise ValueError("El YAML debe incluir el mapa parameters.")

        for nombre, minimo, maximo in (("temperature", 0, 2), ("top_p", 0, 1)):
            valor = self.parameters.get(nombre)
            if type(valor) not in (int, float) or not minimo <= valor <= maximo:
                raise ValueError(f"parameters.{nombre} debe ser un número entre {minimo} y {maximo}.")

        limite = self.parameters.get("max_output_tokens")
        if type(limite) is not int or limite < 1:
            raise ValueError("parameters.max_output_tokens debe ser un entero mayor que cero.")

    def build_prompt(self) -> str:
        """Reemplaza {consulta}; las llaves literales de JSON se escriben dobles."""
        try:
            campos = [campo for _, campo, _, _ in Formatter().parse(self.template) if campo is not None]
            if "consulta" not in campos or any(campo != "consulta" for campo in campos):
                raise ValueError("La plantilla debe usar {consulta} como única variable.")
            return self.template.format(consulta=self.prompt)
        except (KeyError, ValueError, IndexError) as error:
            raise ValueError(
                f"Plantilla inválida: {error} Usá {{consulta}} y duplicá las llaves literales de JSON."
            ) from error

    def build_messages(self) -> list[dict[str, str]]:
        """Envía el prompt completo como un único mensaje, como en el ejemplo del curso."""
        return [{"role": "user", "content": self.build_prompt()}]
