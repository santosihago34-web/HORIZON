"""Preflight de uma chamada, antes do lote; sem retentativas automáticas."""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from horizon.brain import ROOT
from horizon.llm_brain import LLMBrain
from horizon.model_provider import InvalidModelOutput, ModelConfig, OpenAIResponsesProvider, ProviderError
from horizon.semantic_eval import evaluate_semantic


def secret_free(text, key):
    return key not in text and not re.search(r"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}", text)


def preflight(provider):
    suite = json.loads((ROOT / "cases/behavior.json").read_text())
    case = next(c for c in suite["cases"] if c["id"] == "T03")
    oracle = json.loads((ROOT / "cases/llm_expectations.json").read_text())["cases"]["T03"]
    brain = LLMBrain(provider)
    report = {"revision": "horizon-llm-1.2.0", "created_at": datetime.now(timezone.utc).isoformat(),
              "provider": provider.public_config(), "case": "T03", "passed": False,
              "attempts": 0, "completions": 0, "schema_valid": False, "http_status": None,
              "executed_prompt_sha256": brain.executed_prompt_hash, "secret_audit_passed": False}
    try:
        output = brain.analyze(case["input"], suite["now"])
        evaluation = evaluate_semantic(case, output, oracle, suite["now"])
        report.update(schema_valid=True, http_status=brain.last_metadata.get("http_status"),
                      metadata=brain.last_metadata, evaluation=evaluation)
        if not secret_free(json.dumps(output), provider.config.api_key):
            report["failure"] = "secret_audit_failed; output withheld"
        else:
            report["output"] = output
            report["secret_audit_passed"] = True
            report["passed"] = not evaluation["failures"] and report["http_status"] == 200
            if not report["passed"]:
                report["failure"] = "preflight_semantic_or_http_failure"
    except ProviderError as exc:
        report["failure"] = exc.code
        if exc.code.startswith("http_"):
            report["http_status"] = int(exc.code.split(":")[0].split("_")[1])
        report["secret_audit_passed"] = True
    except InvalidModelOutput:
        report["failure"] = "json_or_schema_invalid"
        report["secret_audit_passed"] = True
        report["http_status"] = brain.last_metadata.get("http_status")
        report["metadata"] = brain.last_metadata
    report.update(attempts=brain.calls_attempted, completions=brain.completions_received)
    if not secret_free(json.dumps(report), provider.config.api_key):
        raise RuntimeError("Secret audit failed; report withheld.")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        provider = OpenAIResponsesProvider(ModelConfig.from_env())
        report = preflight(provider)
    except (ValueError, RuntimeError):
        print("Preflight bloqueado por configuração ou auditoria; detalhes sensíveis omitidos.")
        return 2
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report.get(k) for k in ("passed", "attempts", "completions", "http_status", "schema_valid", "secret_audit_passed", "failure")}, ensure_ascii=False))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
