"""Mesmo contrato do baseline; prompt real + fornecedor substituível."""

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from horizon.brain import ROOT
from horizon.contracts import check_input, instant
from horizon.model_provider import InvalidModelOutput, strict_json
from horizon.validator import validate


class LLMBrain:
    backend = "llm"
    revision = "horizon-llm-1.2.0"

    def __init__(self, provider, prompt_path=None, policy_path=None):
        self.provider = provider
        self.prompt_path = Path(prompt_path or ROOT / "prompts/horizon_v1.md")
        self.policy_path = Path(policy_path or ROOT / "prompts/horizon_v1.policy.json")
        self.prompt = self.prompt_path.read_text(encoding="utf-8")
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.schema = json.loads((ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
        self.prompt_hash = hashlib.sha256(self.prompt.encode()).hexdigest()
        self.policy_hash = hashlib.sha256(self.policy_path.read_bytes()).hexdigest()
        self.overlay = (ROOT / "prompts/horizon_llm_context.md").read_text(encoding="utf-8")
        self.overlay_hash = hashlib.sha256(self.overlay.encode()).hexdigest()
        # Apoio comportamental sem respostas determinísticas pré-prontas.
        policy_support = {key: self.policy[key] for key in ("version", "freshness_hours")}
        self.system_prompt = self.prompt + "\n\n" + self.overlay + "\n\nPOLICY_APOIO:\n" + json.dumps(policy_support, ensure_ascii=False) + "\n\nSCHEMA_COMPLETO:\n" + json.dumps(self.schema, ensure_ascii=False)
        self.executed_prompt_hash = hashlib.sha256(self.system_prompt.encode()).hexdigest()
        self.calls_attempted = 0
        self.completions_received = 0
        self.last_metadata = {}

    def analyze(self, data, now=None):
        check_input(data)
        clock = instant(now) if isinstance(now, str) else (now or datetime.now(timezone.utc))
        if clock.tzinfo is None:
            raise ValueError("now precisa conter fuso.")
        conversation = copy.deepcopy(data)
        records = conversation.pop("commercial", [])
        fresh, unavailable = [], []
        for record in records:
            age = (clock - instant(record["verified_at"])).total_seconds() / 3600
            if 0 <= age <= self.policy["freshness_hours"]:
                fresh.append(record)
            else:
                # Não exponha valores vencidos como candidata a cotação.
                unavailable.append({key: record[key] for key in ("product", "field", "model", "size", "destination") if key in record})
        # Texto auxiliar em áudio não é uma transcrição. Nenhum conteúdo inferido.
        for message in conversation["messages"]:
            if message.get("media") == "audio":
                message.pop("text", None)
        payload = {"MODO": "LEITURA_ANALISE_SUGESTAO", "INSTANTE_AVALIACAO": clock.isoformat(),
                   "CONVERSA": conversation, "DADOS_VERIFICADOS": fresh,
                   "DADOS_INDISPONIVEIS_POR_DATA": unavailable}
        self.last_metadata = {}
        self.calls_attempted += 1
        completion = self.provider.complete(system_prompt=self.system_prompt, user_payload=payload, schema=self.schema)
        self.completions_received += 1
        self.last_metadata = completion.metadata
        output = strict_json(completion.content)
        errors = validate(output)
        if errors:
            # Não recupere via baseline, não repare JSON nem retente silenciosamente.
            raise InvalidModelOutput("Saída não atende ao schema Horizon.")
        return output
