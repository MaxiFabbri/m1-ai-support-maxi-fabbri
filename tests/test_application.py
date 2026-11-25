import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import AppConfig
from prompt_builder import PromptBuilder
from main import main
from providers.base import Provider
from router import Router


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name)
        (self.project / "config.toml").write_text(
            'LLM_PROVIDER = "gemini"\nPROMPT_FILE = "prompt.yaml"\n', encoding="utf-8"
        )
        (self.project / "prompt.yaml").write_text(
            'version: v1\nparameters:\n  temperature: 0.2\n  top_p: 0.85\n'
            '  max_output_tokens: 50\nplantilla: "Clasificá: {consulta}"\n', encoding="utf-8"
        )
        self.config = AppConfig(self.project / "config.toml")
        self.usage = Mock()
        self.usage.model_dump_json.return_value = '{"total_tokens": 12}'
        self.response_data = {
            "answer": "Necesitamos conocer el mensaje de error.",
            "confidence": 0.8,
            "category": "account",
            "actions": ["Solicitar el mensaje de error."],
        }
        self.response_text = json.dumps(self.response_data)

    def consultar(self, name, query="No puedo ingresar."):
        builder = PromptBuilder(query, self.config.prompt_path)
        router = Router(self.config, name)
        answer = router.ask(builder.build_messages(), builder.parameters)
        return answer, router.obtener_usage()

    def test_three_providers_keep_sdk_arguments_and_raw_usage(self):
        for name in ("gemini", "openai", "nvidia"):
            with self.subTest(provider=name):
                prefix = name.upper()
                environment = {f"{prefix}_API_KEY": "test-key", f"{prefix}_MODEL_ID": "test-model"}
                if name == "nvidia":
                    environment["NVIDIA_BASE_URL"] = "https://example.invalid/v1"
                sdk_path = (
                    "providers.gemini_provider.genai.Client" if name == "gemini"
                    else f"providers.{name}_provider.OpenAI"
                )
                with patch.dict(os.environ, environment, clear=True), patch(sdk_path) as sdk:
                    client = sdk.return_value.__enter__.return_value
                    raw_response = SimpleNamespace(
                        text=self.response_text, usage_metadata=self.usage, usage=self.usage,
                        choices=[SimpleNamespace(message=SimpleNamespace(content=self.response_text))],
                    )
                    client.models.generate_content.return_value = raw_response
                    client.chat.completions.create.return_value = raw_response
                    stdout, stderr = io.StringIO(), io.StringIO()
                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        answer, usage = self.consultar(name)
                    self.assertEqual(answer, self.response_text)
                    self.assertIs(usage, self.usage)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertEqual(stderr.getvalue(), "")
                    self.assertEqual(sdk.call_args.kwargs["api_key"], "test-key")
                    if name == "gemini":
                        args = client.models.generate_content.call_args.kwargs
                        self.assertEqual(args["contents"][0].role, "user")
                        self.assertEqual(args["contents"][0].parts[0].text, "Clasificá: No puedo ingresar.")
                        self.assertEqual(args["config"].max_output_tokens, 50)
                        self.assertEqual(args["config"].temperature, 0.2)
                        self.assertEqual(args["config"].top_p, 0.85)
                        self.assertEqual(sdk.call_args.kwargs["http_options"].retry_options.attempts, 1)
                    else:
                        args = client.chat.completions.create.call_args.kwargs
                        self.assertEqual(args["messages"], [{"role": "user", "content": "Clasificá: No puedo ingresar."}])
                        token_key = "max_tokens" if name == "nvidia" else "max_completion_tokens"
                        self.assertEqual(args[token_key], 50)
                        self.assertNotIn("max_completion_tokens" if name == "nvidia" else "max_tokens", args)
                        self.assertEqual(args["temperature"], 0.2)
                        self.assertEqual(args["top_p"], 0.85)
                        self.assertEqual(sdk.call_args.kwargs["max_retries"], 0)
                        self.assertEqual(sdk.call_args.kwargs.get("base_url"), environment.get("NVIDIA_BASE_URL"))
                    self.assertEqual(args["model"], "test-model")

    def test_main_honors_provider_override_and_separates_output(self):
        environment = {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL_ID": "test-model"}
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, environment, clear=True), \
                patch("providers.openai_provider.OpenAI") as sdk, \
                patch.object(sys, "argv", ["main.py", "Consulta", "--provider", "OPENAI"]), \
                patch("main.__file__", str(self.project / "src" / "main.py")):
            client = sdk.return_value.__enter__.return_value
            client.chat.completions.create.return_value = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=self.response_text))], usage=self.usage
            )
            with redirect_stdout(stdout), redirect_stderr(stderr):
                main()
        self.assertEqual(json.loads(stdout.getvalue().splitlines()[-1]), self.response_data)
        self.assertEqual(json.loads(stderr.getvalue()), {"total_tokens": 12})

    def test_empty_query_is_rejected_before_building_application(self):
        with patch("main.AppConfig") as factory, \
                patch.object(sys, "argv", ["main.py", "   "]), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)
        factory.assert_not_called()

    def test_invalid_response_is_reported_without_retrying_or_showing_a_result(self):
        for raw in ("No es JSON", '{"category": "account"}',
                    json.dumps(self.response_data | {"confidence": 2})):
            with self.subTest(raw=raw), \
                    patch("main.__file__", str(self.project / "src" / "main.py")), \
                    patch.object(sys, "argv", ["main.py", "Consulta"]), \
                    patch("main.Router") as factory, \
                    patch("main.SupportCLI.show_response") as show_response, \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as stderr:
                factory.return_value.ask.return_value = raw
                with self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code, 2)
                self.assertIn("La respuesta del modelo no cumple el contrato", stderr.getvalue())
                factory.return_value.ask.assert_called_once()
                show_response.assert_not_called()

    def test_missing_selected_credentials_have_clear_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY"):
                self.consultar("gemini")

    def test_unknown_provider_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "desconocido"):
            Router(self.config, "desconocido")

    def test_shell_environment_takes_priority_over_dotenv(self):
        (self.project / ".env").write_text(
            "GEMINI_API_KEY=file-key\nGEMINI_MODEL_ID=file-model\n", encoding="utf-8"
        )
        with patch.dict(os.environ, {"GEMINI_API_KEY": "shell-key"}, clear=True), \
                patch.object(sys, "argv", ["main.py", "Consulta"]), \
                patch("main.__file__", str(self.project / "src" / "main.py")), \
                patch("providers.gemini_provider.genai.Client") as sdk, \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            client = sdk.return_value.__enter__.return_value
            client.models.generate_content.return_value = SimpleNamespace(
                text=self.response_text, usage_metadata=self.usage
            )
            main()
        self.assertEqual(sdk.call_args.kwargs["api_key"], "shell-key")
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], "file-model")

    def test_router_can_select_a_registered_provider(self):
        first, second = Mock(spec=Provider), Mock(spec=Provider)
        messages = [{"role": "user", "content": "Consulta"}]
        parameters = {"temperature": 0.2, "top_p": 0.85, "max_output_tokens": 50}
        second.ask.return_value = "resultado"
        with patch("router.GeminiProvider", return_value=first), \
                patch("router.OpenAIProvider", return_value=second):
            router = Router(self.config, "openai")
        self.assertEqual(router.ask(messages, parameters), "resultado")
        first.ask.assert_not_called()
        second.ask.assert_called_once_with(messages, parameters)

    def test_main_reports_configuration_errors_without_printing_a_response(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("main.AppConfig", side_effect=ValueError("Configuración inválida")), \
                patch.object(sys, "argv", ["main.py", "Consulta"]), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as error:
                main()
        self.assertEqual(error.exception.code, 2)
        self.assertIn("Configuración inválida", stderr.getvalue())
        self.assertNotIn(self.response_text, stdout.getvalue())

    def test_empty_sdk_responses_have_clear_errors(self):
        environment = {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL_ID": "test-model",
                       "OPENAI_API_KEY": "test-key", "OPENAI_MODEL_ID": "test-model"}
        for name in ("gemini", "openai"):
            sdk_path = (
                "providers.gemini_provider.genai.Client" if name == "gemini"
                else f"providers.{name}_provider.OpenAI"
            )
            with self.subTest(provider=name), patch.dict(os.environ, environment, clear=True), patch(sdk_path) as sdk:
                client = sdk.return_value.__enter__.return_value
                client.models.generate_content.return_value = SimpleNamespace(text=None, usage_metadata=None)
                client.chat.completions.create.return_value = SimpleNamespace(choices=[], usage=None)
                with self.assertRaisesRegex(RuntimeError, "no devolvió texto"):
                    self.consultar(name, "Consulta")


if __name__ == "__main__":
    unittest.main()
