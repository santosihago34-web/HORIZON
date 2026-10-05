"""Contrato Responses API com fixtures; não realiza requisições externas."""

import io
import json
import unittest
import urllib.error

from horizon.model_provider import ModelConfig, OpenAIResponsesProvider, ProviderError


class Opener:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.requests = payload, error, []

    def open(self, request, timeout):
        self.requests.append(request)
        if self.error:
            raise self.error
        return io.BytesIO(json.dumps(self.payload).encode())


def response(text="{}"):
    return {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}], "usage": {"input_tokens": 5, "output_tokens": 6, "total_tokens": 11}}


class ResponsesTests(unittest.TestCase):
    def provider(self, opener):
        return OpenAIResponsesProvider(ModelConfig("test-model", "fake-test-secret"), opener)

    def test_responses_contract_and_usage(self):
        opener = Opener(response())
        completion = self.provider(opener).complete(system_prompt="rules", user_payload={"CONVERSA": "data"}, schema={"type": "object"})
        request = opener.requests[0]
        body = json.loads(request.data)
        self.assertTrue(request.full_url.endswith("/responses"))
        self.assertEqual(body["instructions"], "rules")
        self.assertFalse(body["store"])
        self.assertTrue(body["text"]["format"]["strict"])
        self.assertNotIn("tools", body)
        self.assertNotIn("messages", body)
        self.assertNotIn("fake-test-secret", request.data.decode())
        self.assertEqual(completion.metadata["usage"]["total_tokens"], 11)

    def test_invalid_status_refusal_or_multiple_texts_are_rejected(self):
        payloads = [{**response(), "status": "incomplete"}, {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]}, {**response(), "output": []}, response("fake-test-secret")]
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ProviderError):
                    self.provider(Opener(payload)).complete(system_prompt="", user_payload={}, schema={})

    def test_http_diagnostic_never_prints_server_message(self):
        error = urllib.error.HTTPError("https://api.openai.com/v1/responses", 429, "secret", {}, io.BytesIO(json.dumps({"error": {"code": "insufficient_quota", "message": "fake-test-secret"}}).encode()))
        with self.assertRaises(ProviderError) as raised:
            self.provider(Opener(error=error)).complete(system_prompt="", user_payload={}, schema={})
        self.assertEqual(str(raised.exception), "http_429:insufficient_quota")


if __name__ == "__main__":
    unittest.main()
