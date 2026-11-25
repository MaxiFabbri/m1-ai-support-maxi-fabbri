import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import AppConfig
from prompt_builder import PromptBuilder


PARAMETERS = {"temperature": 0.2, "top_p": 0.85, "max_output_tokens": 50}


class PromptTests(unittest.TestCase):
    def test_versioned_prompts_render_json_braces_and_query_without_reinterpreting_it(self):
        prompts = Path(__file__).resolve().parents[1] / "prompts"
        query = 'Consulta con {otra_variable} y {"dato": 1}'
        for path in sorted(prompts.glob("*.yaml")):
            with self.subTest(path=path.name):
                messages = PromptBuilder(query, path).build_messages()
                self.assertEqual(messages[0]["role"], "user")
                self.assertIn(query, messages[0]["content"])
                self.assertIn('"category":', messages[0]["content"])

    def test_building_messages_does_not_reload_yaml(self):
        path = Path(__file__).resolve().parents[1] / "prompts" / "support_prompt_v2.yaml"
        builder = PromptBuilder("Consulta", path)
        with patch.object(Path, "read_text", side_effect=AssertionError("No debe releer el YAML")):
            self.assertIn("Consulta", builder.build_messages()[0]["content"])

    def test_invalid_template_variables_are_rejected(self):
        for text in ("Sin variable", "{otra}", "{consulta} {otra}", '{"category": "..."} {consulta}'):
            data = {"plantilla": text, "parameters": PARAMETERS}
            with self.subTest(text=text), patch.object(Path, "read_text", return_value=yaml.safe_dump(data)):
                with self.assertRaisesRegex(ValueError, "Plantilla inválida"):
                    PromptBuilder("Consulta", Path("prompt.yaml")).build_prompt()

    def test_empty_query_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "vacío"):
            PromptBuilder(" \n", Path("prompt.yaml"))

    def test_invalid_yaml_and_parameters_are_rejected(self):
        invalid_documents = [
            "[sin, mapa]", "parameters: [", "parameters: {}", "plantilla: hola",
            "plantilla: hola\nparameters: []",
            *[
                "plantilla: '{consulta}'\nparameters:\n"
                + "".join(f"  {name}: {value}\n" for name, value in (PARAMETERS | {key: bad}).items())
                for key, bad in (("temperature", "true"), ("top_p", 2), ("max_output_tokens", 0),
                                 ("max_output_tokens", 1.5), ("temperature", ".nan"))
            ],
        ]
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / "prompt.yaml"
            for content in invalid_documents:
                with self.subTest(content=content):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        PromptBuilder("Consulta", path)

    def test_invalid_or_missing_configuration_has_clear_error(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path = Path(directory) / "config.toml"
            for content in (None, "invalid = [", 'LLM_PROVIDER = "gemini"',
                            'LLM_PROVIDER = 1\nPROMPT_FILE = "prompt.yaml"'):
                with self.subTest(content=content):
                    if content is not None:
                        path.write_text(content, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        AppConfig(path)


if __name__ == "__main__":
    unittest.main()
