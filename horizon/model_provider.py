"""Transporte isolado para modelos. Nenhuma credencial em prompt ou relatório."""

import json
import math
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlsplit


class MissingCredential(ValueError):
    pass


class ProviderError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class InvalidModelOutput(ValueError):
    pass


def strict_json(text):
    def pairs(items):
        output = {}
        for key, value in items:
            if key in output:
                raise InvalidModelOutput("JSON com chave duplicada.")
            output[key] = value
        return output

    def constant(_):
        raise InvalidModelOutput("JSON com número não finito.")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError) as exc:
        raise InvalidModelOutput("Resposta não é JSON estrito; nenhuma reparação aplicada.") from None


@dataclass(frozen=True)
class ModelConfig:
    model: str
    api_key: str = field(repr=False)
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.2
    max_tokens: int = 1800
    timeout: float = 60.0

    def __post_init__(self):
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise MissingCredential("Configure HORIZON_LLM_API_KEY nas configurações seguras do ambiente.")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Configure HORIZON_LLM_MODEL com um modelo que aceite saída estruturada.")
        if self.api_key in self.model or self.api_key in self.base_url:
            raise ValueError("Credencial não pode fazer parte do modelo ou endpoint.")
        url = urlsplit(self.base_url)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("Endpoint precisa ser HTTPS, sem credenciais, query ou fragmento.")
        if not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
            raise ValueError("temperature fora do intervalo 0..2.")
        if type(self.max_tokens) is not int or not 100 <= self.max_tokens <= 10000:
            raise ValueError("max_tokens fora do intervalo 100..10000.")
        if not math.isfinite(self.timeout) or not 0 < self.timeout <= 60:
            raise ValueError("timeout fora do intervalo 0..60 segundos.")

    @classmethod
    def from_env(cls):
        key = os.environ.get("HORIZON_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise MissingCredential("Configure HORIZON_LLM_API_KEY nas configurações seguras do ambiente. Nenhuma chamada externa foi feita.")
        return cls(model=os.environ.get("HORIZON_LLM_MODEL", ""), api_key=key,
                   base_url=os.environ.get("HORIZON_LLM_BASE_URL", "https://api.openai.com/v1"),
                   temperature=float(os.environ.get("HORIZON_LLM_TEMPERATURE", "0.2")),
                   max_tokens=int(os.environ.get("HORIZON_LLM_MAX_TOKENS", "1800")))

    def public(self):
        # Whitelist explícita; nunca use asdict(config), que incluiria api_key.
        return {"model": self.model, "base_url": self.base_url,
                "temperature": self.temperature, "max_tokens": self.max_tokens,
                "timeout_seconds": self.timeout, "credentials_logged": False}


@dataclass
class Completion:
    content: str
    metadata: dict = field(default_factory=dict)


class ModelProvider(Protocol):
    name: str

    def public_config(self) -> dict: ...

    def complete(self, *, system_prompt: str, user_payload: dict, schema: dict) -> Completion: ...


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError("redirect_blocked")


def transport_schema(schema):
    """OpenAI aceita subconjunto: coerência if/then continua obrigatória localmente."""
    if isinstance(schema, list):
        return [transport_schema(value) for value in schema]
    if not isinstance(schema, dict):
        return schema
    return {key: transport_schema(value) for key, value in schema.items()
            if key not in {"$schema", "title", "allOf", "if", "then", "else"}}


class OpenAIChatProvider:
    name = "openai-chat-completions"

    def __init__(self, config, opener=None):
        self.config = config
        self.opener = opener or urllib.request.build_opener(NoRedirect())

    def public_config(self):
        return {"provider": self.name, **self.config.public()}

    def complete(self, *, system_prompt, user_payload, schema):
        request_data = {"model": self.config.model, "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                        "messages": [{"role": "system", "content": system_prompt},
                                     {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, allow_nan=False)}],
                        "response_format": {"type": "json_schema", "json_schema": {
                            "name": "horizon_v1", "strict": True, "schema": transport_schema(schema)}}}
        body = json.dumps(request_data, ensure_ascii=False, allow_nan=False).encode()
        if self.config.api_key.encode() in body:
            raise ProviderError("credential_in_payload_blocked")
        request = urllib.request.Request(self.config.base_url.rstrip("/") + "/chat/completions",
                                         data=body,
                                         headers={"Authorization": "Bearer " + self.config.api_key,
                                                  "Content-Type": "application/json"}, method="POST")
        try:
            with self.opener.open(request, timeout=self.config.timeout) as response:
                payload = response.read(2_000_001)
                if len(payload) > 2_000_000:
                    raise ProviderError("response_too_large")
        except urllib.error.HTTPError as exc:
            # Não registre corpo, URL, headers ou mensagem do servidor.
            raise ProviderError(f"http_{exc.code}") from None
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError):
            raise ProviderError("network_or_timeout") from None
        try:
            decoded = strict_json(payload.decode("utf-8"))
            choice = decoded["choices"][0]
            message = choice["message"]
            if message.get("refusal"):
                raise ProviderError("model_refusal")
            if choice.get("finish_reason") != "stop":
                raise ProviderError("incomplete_completion")
            content = message["content"]
            if not isinstance(content, str):
                raise ProviderError("invalid_completion_content")
            # O segredo não é enviado ao modelo; bloqueie qualquer eco do serviço.
            if self.config.api_key in content:
                raise ProviderError("credential_echo_blocked")
            usage = decoded.get("usage", {})
            metadata = {key: usage[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                        if type(usage.get(key)) is int and usage[key] >= 0}
            return Completion(content, {"usage": metadata, "finish_reason": "stop"})
        except (KeyError, IndexError, TypeError, UnicodeError, InvalidModelOutput):
            raise ProviderError("invalid_provider_response") from None
