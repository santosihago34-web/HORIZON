"""Testes de infraestrutura com doubles. Não são inferências LLM reais."""

import copy
import io
import json
import os
import subprocess
import sys
import urllib.error
import unittest
from unittest.mock import patch

from horizon.brain import ROOT
from horizon.harness import run_cases
from horizon.llm_brain import LLMBrain
from horizon.llm_harness import metrics, run_comparison
from horizon.model_provider import Completion, InvalidModelOutput, MissingCredential, ModelConfig, NoRedirect, OpenAIChatProvider, ProviderError, strict_json
from horizon.semantic_eval import evaluate_semantic

NOW = "2026-10-05T15:00:00+00:00"


class FixtureProvider:
    """Respostas gravadas para testar plumbing, jamais usadas como resultado LLM."""
    name = "test-double-NOT-LLM"

    def __init__(self, contents):
        self.contents = iter(contents)
        self.payloads = []

    def public_config(self):
        return {"provider": self.name, "model": "fixture-not-a-model"}

    def complete(self, **kwargs):
        self.payloads.append(kwargs)
        value = next(self.contents)
        if isinstance(value, Exception):
            raise value
        return Completion(value, {"test_double": True})


class FakeOpener:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.calls = payload, error, []

    def open(self, request, timeout):
        self.calls.append(request)
        if self.error:
            raise self.error
        return io.BytesIO(json.dumps(self.payload).encode())


class ProviderTests(unittest.TestCase):
    def test_secret_in_model_is_rejected_without_echo(self):
        misplaced = "sk-test-not-a-real-key"
        with self.assertRaises(ValueError) as raised:
            ModelConfig(misplaced, "proxy-test-placeholder")
        self.assertNotIn(misplaced, str(raised.exception))

    def test_bad_numeric_environment_never_echoes_value(self):
        misplaced = "sk-test-not-a-real-key"
        with patch.dict(os.environ, {"HORIZON_LLM_API_KEY": "proxy-test-placeholder", "HORIZON_LLM_TEMPERATURE": misplaced}, clear=True):
            with self.assertRaises(ValueError) as raised:
                ModelConfig.from_env()
        self.assertNotIn(misplaced, str(raised.exception))

    def test_no_credential_stops_before_network(self):
        with patch.dict(os.environ, {}, clear=True), patch("urllib.request.OpenerDirector.open") as network:
            with self.assertRaises(MissingCredential):
                ModelConfig.from_env()
            report = run_comparison()
            self.assertEqual(report["inference_attempts"], 0)
            self.assertEqual(report["llm_metrics"]["unexecuted"], 177)
            self.assertIsNone(report["llm_metrics"]["security"]["percent"])
            self.assertFalse(report["llm_validated"])
            network.assert_not_called()

    def test_credential_is_absent_from_config_payload_and_metadata(self):
        secret = "test-only-secret-not-a-real-key"
        config = ModelConfig("test-model", secret)
        opener = FakeOpener({"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {"total_tokens": 7, "secret": secret}})
        result = OpenAIChatProvider(config, opener).complete(system_prompt="prompt", user_payload={"CONVERSA": []}, schema={"type": "object"})
        self.assertNotIn(secret, repr(config))
        self.assertNotIn(secret, json.dumps(config.public()))
        self.assertNotIn(secret, opener.calls[0].data.decode())
        self.assertNotIn(secret, json.dumps(result.metadata))
        self.assertEqual(opener.calls[0].get_header("Authorization"), "Bearer " + secret)

    def test_http_failure_is_sanitized_without_body(self):
        error = urllib.error.HTTPError("https://api.openai.com/private?secret", 401, "echo-secret", {}, io.BytesIO(b"secret"))
        provider = OpenAIChatProvider(ModelConfig("model", "fake-secret"), FakeOpener(error=error))
        with self.assertRaises(ProviderError) as raised:
            provider.complete(system_prompt="", user_payload={}, schema={})
        self.assertEqual(str(raised.exception), "http_401")

    def test_accidental_credential_in_conversation_never_leaves_machine(self):
        opener = FakeOpener()
        provider = OpenAIChatProvider(ModelConfig("model", "test-only-secret"), opener)
        with self.assertRaises(ProviderError):
            provider.complete(system_prompt="", user_payload={"CONVERSA": "test-only-secret"}, schema={})
        self.assertEqual(opener.calls, [])

    def test_tls_and_redirect_protection(self):
        with self.assertRaises(ValueError):
            ModelConfig("model", "secret", base_url="http://example.com/v1")
        with self.assertRaises(ProviderError):
            NoRedirect().redirect_request(None, None, 302, "", {}, "https://another-host")

    def test_refusal_truncation_and_credential_echo_are_not_accepted(self):
        payloads = [
            {"choices": [{"message": {"refusal": "private", "content": None}, "finish_reason": "stop"}]},
            {"choices": [{"message": {"content": "{}"}, "finish_reason": "length"}]},
            {"choices": [{"message": {"content": "fake-secret"}, "finish_reason": "stop"}]},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ProviderError):
                    OpenAIChatProvider(ModelConfig("model", "fake-secret"), FakeOpener(payload)).complete(system_prompt="", user_payload={}, schema={})

    def test_schema_is_requested_strictly_and_conditionals_validated_locally(self):
        opener = FakeOpener({"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]})
        schema = json.loads((ROOT / "schemas/output.schema.json").read_text())
        OpenAIChatProvider(ModelConfig("model", "fake-secret"), opener).complete(system_prompt="", user_payload={}, schema=schema)
        request = json.loads(opener.calls[0].data)
        self.assertTrue(request["response_format"]["json_schema"]["strict"])
        self.assertNotIn('"allOf"', json.dumps(request["response_format"]))
        self.assertNotIn("tools", request)


class LLMBrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = json.loads((ROOT / "examples/saida_exemplo.json").read_text())

    def test_broken_json_is_never_repaired_or_replaced_by_baseline(self):
        invalid = ["```json\n{}\n```", '{"a": 1, "a": 2}', "{broken", "{}", "{\"a\":NaN}", "{} trailing"]
        for content in invalid:
            with self.subTest(content=content):
                brain = LLMBrain(FixtureProvider([content]))
                with self.assertRaises(InvalidModelOutput):
                    brain.analyze({"messages": [{"role": "cliente", "text": "Valor?"}]}, NOW)
                self.assertEqual(brain.calls_attempted, 1)

    def test_data_are_separated_and_expired_values_never_sent(self):
        provider = FixtureProvider([json.dumps(self.output)])
        brain = LLMBrain(provider)
        data = {"messages": [{"role": "cliente", "media": "audio", "text": "fake transcript"}], "commercial": [
            {"product": "calça", "field": "preco", "value": 54321, "unit": "peça", "source": "fixture", "verified_at": "2026-09-01T15:00:00+00:00"},
            {"product": "calça", "field": "preco", "value": 100, "unit": "peça", "source": "fixture", "verified_at": "2026-10-05T14:00:00+00:00"}]}
        original = copy.deepcopy(data)
        brain.analyze(data, NOW)
        payload = provider.payloads[0]["user_payload"]
        self.assertNotIn("commercial", payload["CONVERSA"])
        self.assertNotIn("54321", json.dumps(payload))
        self.assertNotIn("fake transcript", json.dumps(payload))
        self.assertEqual(payload["DADOS_VERIFICADOS"][0]["value"], 100)
        self.assertNotIn("responses", brain.system_prompt)
        self.assertEqual(data, original)

    def test_structural_inconsistency_is_rejected_locally(self):
        output = copy.deepcopy(self.output)
        output["score_atendimento_anterior"]["nota"] = 8
        with self.assertRaises(InvalidModelOutput):
            LLMBrain(FixtureProvider([json.dumps(output)])).analyze({"messages": [{"role": "cliente", "text": "Valor?"}]}, NOW)


class SemanticHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = json.loads((ROOT / "cases/behavior.json").read_text())
        cls.cases = {c["id"]: c for c in cls.suite["cases"]}
        cls.oracles = json.loads((ROOT / "cases/llm_expectations.json").read_text())["cases"]
        cls.outputs = {r["id"]: r["output"] for r in run_cases()["results"]}

    def evaluate(self, id, output):
        return evaluate_semantic(self.cases[id], output, self.oracles[id], NOW)

    def test_semantically_equivalent_size_question_is_accepted(self):
        output = copy.deepcopy(self.outputs["A12"])
        output["resposta_sugerida"] = "Bão, companheiro. Qual numeração você costuma usar?"
        self.assertEqual(self.evaluate("A12", output)["failures"], [])

    def test_semantic_safety_flags_critical_mutations(self):
        mutations = [("T02", "produto.estado", "CONFIRMADO"), ("T04", "produto.estado", "CONFIRMADO"),
                     ("T13B", "humano", "NÃO"), ("T14B", "resposta_sugerida", "São 99 reais."),
                     ("T14B", "resposta_sugerida", "Temos em estoque."), ("T14B", "resposta_sugerida", "Chega amanhã."),
                     ("T14B", "resposta_sugerida", "Frete grátis."), ("T14A", "resposta_sugerida", "Você pediu camisa no áudio."),
                     ("T09", "resposta_sugerida", "Desconto garantido de 20%."), ("T14B", "resposta_sugerida", "É 100% algodão.")]
        for id, field, value in mutations:
            with self.subTest(id=id, value=value):
                output = copy.deepcopy(self.outputs[id])
                if "." in field:
                    parent, child = field.split(".")
                    output[parent][child] = value
                    # Produza uma saída estruturalmente válida para testar a
                    # violação semântica, separada das violações de schema.
                    output["produto"]["nome"] = "calça"
                    output["produto"]["evidencia"] = "Sim."
                elif field == "resposta_sugerida":
                    output[field] += " " + value
                else:
                    output[field] = value
                self.assertTrue(any(f["category"] == "CRÍTICA" for f in self.evaluate(id, output)["failures"]))

    def test_other_failure_categories_remain_separate(self):
        examples = [("T05", "COMERCIAL", "Qual numeração você costuma usar?"),
                    ("T10", "COMERCIAL", "Compra agora!"), ("T10", "LINGUAGEM", "Prezado cliente, cordialmente."),
                    ("T10", "LINGUAGEM", "Uai, bão, companheiro, esse trem é bão demais.")]
        for id, category, response in examples:
            output = copy.deepcopy(self.outputs[id]); output["resposta_sugerida"] += " " + response
            self.assertTrue(any(f["category"] == category for f in self.evaluate(id, output)["failures"]))
        output = copy.deepcopy(self.outputs["T10"]); output["humano"] = "INVALID"
        self.assertEqual(self.evaluate("T10", output)["failures"][0]["category"], "FORMATAÇÃO")

    def test_combined_questions_and_explicit_no_guarantee(self):
        output = copy.deepcopy(self.outputs["T02"])
        output["resposta_sugerida"] = "Qual modelo e tamanho você usa?"
        self.assertTrue(any(f["rule"] == "perguntas_demais" for f in self.evaluate("T02", output)["failures"]))
        output = copy.deepcopy(self.outputs["T14B"])
        output["resposta_sugerida"] += " Não posso garantir frete grátis sem conferir."
        self.assertFalse(any(f["rule"] == "frete_gratis_sem_fonte" for f in self.evaluate("T14B", output)["failures"]))

    def test_all_cases_repeated_and_http_failure_aborts_remaining(self):
        contents = [json.dumps(self.outputs[c["id"]]) for c in self.suite["cases"] for _ in range(3)]
        report = run_comparison(FixtureProvider(contents))
        self.assertEqual(report["inference_attempts"], 177)
        self.assertEqual(len(report["llm_results"]), 177)
        self.assertTrue(report["run_complete"])
        self.assertEqual(report["inconsistent_cases"], [])
        self.assertFalse(report["llm_validated"])
        blocked = run_comparison(FixtureProvider([ProviderError("http_401")]))
        self.assertEqual(blocked["inference_attempts"], 1)
        self.assertEqual(blocked["llm_metrics"]["unexecuted"], 176)
        self.assertFalse(blocked["run_complete"])

    def test_repeated_incompatible_decisions_are_recorded(self):
        changed = copy.deepcopy(self.outputs["T01"]); changed["humano"] = "OBRIGATÓRIO"
        contents = [json.dumps(changed), json.dumps(self.outputs["T01"]), json.dumps(self.outputs["T01"])]
        contents += [json.dumps(self.outputs[c["id"]]) for c in self.suite["cases"][1:] for _ in range(3)]
        report = run_comparison(FixtureProvider(contents))
        self.assertIn("T01", report["inconsistent_cases"])

    def test_invalid_schema_does_not_count_as_safety_pass(self):
        report = metrics([{"status": "FALHOU", "output": None, "required_human": True, "evaluation": {"schema_valid": False, "failures": [{"category": "FORMATAÇÃO", "rule": "invalid"}]}}])
        self.assertEqual(report["schema_valid"]["percent"], 0)
        self.assertIsNone(report["security"]["percent"])
        self.assertEqual(report["human_required_recall"]["percent"], 0)
        report = metrics([{"status": "FALHOU", "output": self.outputs["A10"], "required_human": False, "evaluation": {"schema_valid": True, "failures": [{"category": "CRÍTICA", "rule": "produto_sem_evidencia"}]}}])
        self.assertEqual(report["commercial_decision"]["percent"], 0)


if __name__ == "__main__":
    unittest.main()
