import json
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from support_response import SupportResponse


class SupportResponseTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "answer": "Necesitamos conocer el mensaje de error.",
            "confidence": 0.8,
            "category": "account",
            "actions": ["Solicitar el mensaje de error."],
        }

    def test_valid_response_can_be_serialized_with_the_same_four_fields(self):
        response = SupportResponse.model_validate_json(json.dumps(self.data))
        self.assertEqual(response.answer, self.data["answer"])
        self.assertEqual(json.loads(response.model_dump_json()), self.data)

    def test_valid_categories_confidence_boundaries_and_empty_actions(self):
        for category in ("billing", "technical", "account", "other"):
            for confidence in (0, 0.0, 1, 1.0):
                with self.subTest(category=category, confidence=confidence):
                    data = self.data | {"category": category, "confidence": confidence, "actions": []}
                    response = SupportResponse.model_validate_json(json.dumps(data))
                    self.assertEqual(response.confidence, confidence)
                    self.assertEqual(response.actions, [])

    def test_non_json_and_non_object_responses_are_rejected(self):
        for raw in ("No puedo procesar la consulta.", '{"answer":', "[]", "null", '"texto"',
                    '```json\n{"category": "account"}\n```'):
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                SupportResponse.model_validate_json(raw)

    def test_all_four_fields_are_required(self):
        for field in self.data:
            data = dict(self.data)
            del data[field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                SupportResponse.model_validate_json(json.dumps(data))

    def test_invalid_field_values_are_rejected(self):
        invalid_values = {
            "answer": ("", 123, None),
            "confidence": (-0.1, 1.1, "0.8", True, None, float("nan"), float("inf")),
            "category": ("facturacion", "ACCOUNT", None),
            "actions": ("Solicitar el error", {}, [123], [None], None),
        }
        for field, values in invalid_values.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    SupportResponse.model_validate_json(json.dumps(self.data | {field: value}))

    def test_additional_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            SupportResponse.model_validate_json(json.dumps(self.data | {"extra": "no permitido"}))


if __name__ == "__main__":
    unittest.main()
