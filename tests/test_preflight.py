"""Gate de uma chamada testado com fixtures; nunca chama serviço real."""

import json
import unittest

from horizon.brain import ROOT
from horizon.harness import run_cases
from horizon.model_provider import Completion, ModelConfig, ProviderError
from horizon.real_validation import preflight


class Provider:
    def __init__(self, response):
        self.config = ModelConfig("test-model", "fake-test-secret")
        self.response, self.calls = response, 0

    def public_config(self):
        return {"provider": "fixture-NOT-LLM", **self.config.public()}

    def complete(self, **kwargs):
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return Completion(self.response, {"http_status": 200})


class PreflightTests(unittest.TestCase):
    def test_auth_failure_does_not_retry_and_never_passes(self):
        provider = Provider(ProviderError("http_401:invalid_api_key"))
        report = preflight(provider)
        self.assertEqual(provider.calls, 1)
        self.assertFalse(report["passed"])
        self.assertEqual(report["http_status"], 401)
        self.assertEqual(report["completions"], 0)
        self.assertNotIn("fake-test-secret", json.dumps(report))

    def test_success_requires_schema_and_semantic_validity(self):
        output = next(r["output"] for r in run_cases()["results"] if r["id"] == "T03")
        provider = Provider(json.dumps(output))
        report = preflight(provider)
        self.assertEqual(provider.calls, 1)
        self.assertTrue(report["passed"])
        self.assertTrue(report["schema_valid"])
        self.assertTrue(report["secret_audit_passed"])

    def test_bad_json_stops_with_no_repair(self):
        provider = Provider("{broken")
        report = preflight(provider)
        self.assertEqual(provider.calls, 1)
        self.assertFalse(report["passed"])
        self.assertFalse(report["schema_valid"])
        self.assertEqual(report["http_status"], 200)


if __name__ == "__main__":
    unittest.main()
