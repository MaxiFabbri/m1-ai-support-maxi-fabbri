import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from providers.base import Provider
from errors import ContratoInvalidoError
from response_handler import ResponseHandler
from router import Router


class ResponseHandlerTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "answer": "Necesitamos conocer el mensaje de error.",
            "confidence": 0.8,
            "category": "account",
            "actions": ["Solicitar el mensaje de error."],
        }
        self.valid = json.dumps(self.data)
        self.messages = [{"role": "user", "content": "No puedo ingresar."}]
        self.parameters = {"temperature": 0.2, "top_p": 0.85, "max_output_tokens": 400}
        self.router = Mock()
        self.handler = ResponseHandler(self.router)

    def test_first_valid_response_stops_after_one_call(self):
        self.router.ask.return_value = self.valid
        result = self.handler.obtener_respuesta_validada(self.messages, self.parameters)
        self.assertEqual(json.loads(result.model_dump_json()), self.data)
        self.router.ask.assert_called_once_with(self.messages, self.parameters)

    def test_invalid_json_or_contract_can_be_followed_by_a_valid_response(self):
        for invalid in ("No es JSON", '{"category": "account"}',
                        json.dumps(self.data | {"confidence": 5})):
            with self.subTest(invalid=invalid):
                self.router.reset_mock()
                self.router.ask.side_effect = [invalid, self.valid, "No debe consultarse"]
                result = self.handler.obtener_respuesta_validada(self.messages, self.parameters)
                self.assertEqual(result.confidence, 0.8)
                self.assertEqual(self.router.ask.call_count, 2)

    def test_valid_response_on_third_attempt_is_returned(self):
        self.router.ask.side_effect = ["No es JSON", json.dumps(self.data | {"confidence": 5}), self.valid]
        result = self.handler.obtener_respuesta_validada(self.messages, self.parameters)
        self.assertEqual(result.answer, self.data["answer"])
        self.assertEqual(self.router.ask.call_count, 3)
        calls = self.router.ask.call_args_list
        self.assertEqual([len(call.args[0]) for call in calls], [1, 2, 2])
        self.assertEqual(calls[0].args[0], self.messages)
        self.assertEqual(calls[1].args[0][-1]["role"], "user")
        self.assertIn("json_invalid", calls[1].args[0][-1]["content"])
        self.assertIn("Intento 1:", calls[1].args[0][-1]["content"])
        self.assertNotIn("Intento 2:", calls[1].args[0][-1]["content"])
        self.assertIn("confidence", calls[2].args[0][-1]["content"])
        self.assertIn("less_than_equal", calls[2].args[0][-1]["content"])
        self.assertIn("json_invalid", calls[2].args[0][-1]["content"])
        self.assertIn("Intento 1:", calls[2].args[0][-1]["content"])
        self.assertIn("Intento 2:", calls[2].args[0][-1]["content"])
        self.assertEqual(calls[2].args[0][-1]["content"].count("Intento 1:"), 1)
        for call in calls:
            self.assertEqual(call.args[0][0], self.messages[0])
            self.assertIs(call.args[1], self.parameters)
        self.assertEqual(self.messages, [{"role": "user", "content": "No puedo ingresar."}])

    def test_exhaustion_reports_all_errors_after_exactly_three_calls(self):
        self.router.ask.side_effect = ["No es JSON", "{}", json.dumps(self.data | {"confidence": 5})]
        with self.assertRaises(ContratoInvalidoError) as error:
            self.handler.obtener_respuesta_validada(self.messages, self.parameters)
        self.assertEqual(self.router.ask.call_count, 3)
        self.assertIn("Se agotaron los 3 intentos", str(error.exception))
        self.assertIn("confidence", str(error.exception))
        self.assertIn("json_invalid", str(error.exception))
        for attempt in (1, 2, 3):
            self.assertIn(f"Intento {attempt}:", str(error.exception))

    def test_attempt_limit_is_used(self):
        self.handler.max_intentos = 1
        self.router.ask.return_value = "No es JSON"
        with self.assertRaises(ContratoInvalidoError):
            self.handler.obtener_respuesta_validada(self.messages, self.parameters)
        self.router.ask.assert_called_once()

    def test_previous_error_is_not_reused_for_a_new_query(self):
        self.router.ask.side_effect = ["No es JSON", self.valid, self.valid]
        self.handler.obtener_respuesta_validada(self.messages, self.parameters)
        new_messages = [{"role": "user", "content": "Quiero cambiar el email de mi cuenta."}]
        self.handler.obtener_respuesta_validada(new_messages, self.parameters)
        self.assertEqual(self.router.ask.call_args.args[0], new_messages)
        self.assertEqual(len(self.router.ask.call_args.args[0]), 1)

    def test_api_and_configuration_errors_are_not_retried(self):
        for error in (RuntimeError("Error de API"), ValueError("Falta una clave")):
            with self.subTest(error=error):
                self.router.reset_mock()
                self.router.ask.side_effect = error
                with self.assertRaises(type(error)) as raised:
                    self.handler.obtener_respuesta_validada(self.messages, self.parameters)
                self.assertIs(raised.exception, error)
                self.router.ask.assert_called_once()

    def test_validation_error_from_sdk_is_not_mistaken_for_response_validation(self):
        from support_response import SupportResponse

        try:
            SupportResponse.model_validate_json("{}")
        except ValidationError as error:
            sdk_error = error
        self.router.ask.side_effect = sdk_error
        with self.assertRaises(ValidationError) as raised:
            self.handler.obtener_respuesta_validada(self.messages, self.parameters)
        self.assertIs(raised.exception, sdk_error)
        self.router.ask.assert_called_once()


class RouterTests(unittest.TestCase):
    def test_router_leaves_retry_decisions_to_handler(self):
        provider = Mock(spec=Provider)
        error = RuntimeError("Error de API")
        provider.ask.side_effect = error
        config = Mock(default_provider="gemini")
        with patch("router.GeminiProvider", return_value=provider):
            router = Router(config)
        with self.assertRaises(RuntimeError) as raised:
            router.ask([], {})
        self.assertIs(raised.exception, error)
        provider.ask.assert_called_once_with([], {})


if __name__ == "__main__":
    unittest.main()
