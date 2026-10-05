import json
import unittest
from pathlib import Path

from horizon.validator import validate


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "saida_exemplo.json"


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_valid_example(self):
        self.assertEqual(validate(self.data), [])

    def test_missing_required_key(self):
        del self.data["humano"]
        self.assertTrue(any("Chaves ausentes" in e for e in validate(self.data)))

    def test_unconfirmed_product_cannot_claim_confirmation(self):
        self.data["produto"] = {"estado": "CONFIRMADO", "nome": "CALÇA", "evidencia": None}
        self.assertTrue(any("evidência" in e for e in validate(self.data)))

    def test_score_requires_enough_evidence(self):
        self.data["score_atendimento_anterior"]["nota"] = 8
        self.assertTrue(any("menos de três" in e for e in validate(self.data)))

    def test_invalid_stage(self):
        self.data["estagio"] = "VENDA CERTA"
        self.assertTrue(any("estagio" in e for e in validate(self.data)))

    def test_malformed_stage_does_not_crash(self):
        self.data["estagio"] = {"invalido": True}
        self.assertTrue(any("estagio" in e for e in validate(self.data)))


if __name__ == "__main__":
    unittest.main()
