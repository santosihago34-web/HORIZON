"""Comparação pareada baseline/LLM; resultados incompletos nunca são aprovados."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from horizon.brain import Brain, ROOT
from horizon.contracts import check_input
from horizon.llm_brain import LLMBrain
from horizon.model_provider import InvalidModelOutput, MissingCredential, ModelConfig, OpenAIResponsesProvider, ProviderError
from horizon.semantic_eval import CATEGORIES, decision_signature, evaluate_semantic


def metric(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "percent": round(100 * numerator / denominator, 2) if denominator else None}


def metrics(items):
    evaluated = [r for r in items if r["status"] in {"PASSOU", "FALHOU"}]
    counts = {category: sum(any(f["category"] == category for f in r["evaluation"]["failures"]) for r in evaluated) for category in CATEGORIES}
    valid = [r for r in evaluated if r["evaluation"]["schema_valid"]]
    by_category = {category: metric(sum(not any(f["category"] == category for f in r["evaluation"]["failures"]) for r in valid), len(valid)) for category in CATEGORIES}
    required = [r for r in evaluated if r["required_human"]]
    true_positive = sum(r["output"] is not None and r["output"].get("humano") == "OBRIGATÓRIO" for r in required)
    predicted = [r for r in evaluated if r["output"] is not None and r["output"].get("humano") == "OBRIGATÓRIO"]
    predicted_correct = sum(r["required_human"] for r in predicted)
    return {"evaluated": len(evaluated), "passed": sum(r["status"] == "PASSOU" for r in evaluated),
            "failed": sum(r["status"] == "FALHOU" for r in evaluated), "failures_by_category": counts,
            "schema_valid": metric(sum(r["evaluation"]["schema_valid"] for r in evaluated), len(evaluated)),
            "security": by_category["CRÍTICA"],
            "commercial_decision": metric(sum(not any(f["category"] in {"CRÍTICA", "COMERCIAL"} for f in r["evaluation"]["failures"]) for r in valid), len(valid)),
            "language_heuristic": by_category["LINGUAGEM"],
            "human_required_recall": metric(true_positive, len(required)),
            "human_required_precision": metric(predicted_correct, len(predicted)),
            "unexecuted": sum(r["status"] == "NÃO EXECUTADO" for r in items)}


def suites(case_file, oracle_file):
    raw = Path(case_file).read_bytes()
    oracle_raw = Path(oracle_file).read_bytes()
    suite = json.loads(raw)
    oracle = json.loads(oracle_raw)["cases"]
    if not suite["cases"] or len({c["id"] for c in suite["cases"]}) != len(suite["cases"]):
        raise ValueError("Lote vazio ou IDs duplicados.")
    if {c["id"] for c in suite["cases"]} != set(oracle):
        raise ValueError("Oráculo sem cobertura exata de todos os casos do lote.")
    for case in suite["cases"]:
        check_input(case["input"])
    return suite, oracle, hashlib.sha256(raw).hexdigest(), hashlib.sha256(oracle_raw).hexdigest()


def run_comparison(provider=None, *, repeats=3, case_file=None, oracle_file=None, blocker=None):
    if type(repeats) is not int or not 2 <= repeats <= 10:
        raise ValueError("Use 2 a 10 repetições por caso, inclusive nos casos críticos.")
    suite, oracles, suite_hash, oracle_hash = suites(case_file or ROOT / "cases/behavior.json", oracle_file or ROOT / "cases/llm_expectations.json")
    baseline = Brain()
    engine = LLMBrain(provider) if provider is not None else None
    baseline_items, llm_items = [], []
    blocked = blocker or ("missing_credential" if engine is None else None)
    observed_schema_signatures = {}
    for case in suite["cases"]:
        oracle = oracles[case["id"]]
        output = baseline.analyze(case["input"], suite["now"])
        evaluation = evaluate_semantic(case, output, oracle, suite["now"])
        baseline_items.append({"id": case["id"], "repeat": 1, "status": "FALHOU" if evaluation["failures"] else "PASSOU", "required_human": oracle["required_human"], "output": output, "evaluation": evaluation})
        for repetition in range(1, repeats + 1):
            item = {"id": case["id"], "repeat": repetition, "required_human": oracle["required_human"],
                    "status": "NÃO EXECUTADO", "output": None, "evaluation": None}
            if blocked:
                item["blocker"] = blocked
                llm_items.append(item)
                continue
            try:
                output = engine.analyze(case["input"], suite["now"])
                evaluation = evaluate_semantic(case, output, oracle, suite["now"])
                item.update(output=output, evaluation=evaluation,
                            status="FALHOU" if evaluation["failures"] else "PASSOU", metadata=engine.last_metadata)
                observed_schema_signatures.setdefault(case["id"], set()).add(decision_signature(output, oracle))
            except InvalidModelOutput:
                item.update(status="FALHOU", evaluation={"schema_valid": False, "heuristic": True,
                            "failures": [{"category": "FORMATAÇÃO", "rule": "json_ou_schema_invalido_sem_reparo"}]})
            except ProviderError as exc:
                # Só código estável e sanitizado; não registre mensagens do serviço.
                item["blocker"] = exc.code
                item["status"] = "ERRO DE INFERÊNCIA"
                if exc.code in {"model_refusal", "incomplete_completion", "invalid_completion_content", "invalid_provider_response"}:
                    item.update(status="FALHOU", evaluation={"schema_valid": False, "heuristic": True,
                                "failures": [{"category": "FORMATAÇÃO", "rule": exc.code}]})
                else:
                    blocked = exc.code
            llm_items.append(item)
    inconsistent = sorted(key for key, values in observed_schema_signatures.items() if len(values) > 1)
    complete = engine is not None and all(item["status"] in {"PASSOU", "FALHOU"} for item in llm_items)
    report = {"revision": "horizon-llm-1.2.0", "created_at": datetime.now(timezone.utc).isoformat(),
              "evaluation_instant": suite["now"], "provider": provider.public_config() if provider is not None else None,
              "requested_default_provider": "openai-responses", "model_used": provider.public_config().get("model") if provider is not None else None,
              "suite_sha256": suite_hash, "oracle_sha256": oracle_hash,
              "base_prompt_sha256": baseline.prompt_hash, "policy_sha256": baseline.policy_hash,
              "overlay_sha256": engine.overlay_hash if engine else hashlib.sha256((ROOT / "prompts/horizon_llm_context.md").read_bytes()).hexdigest(),
              "executed_prompt_sha256": engine.executed_prompt_hash if engine else None,
              "repeats_per_case": repeats, "case_count": len(suite["cases"]), "planned_inferences": len(llm_items),
              "inference_attempts": engine.calls_attempted if engine else 0,
              "completions_received": engine.completions_received if engine else 0,
              "run_complete": complete, "blocker": blocked,
              "evaluation_method": "semantic_function_and_fact_heuristics; requires human review",
              "llm_validated": False,
              "inconsistent_cases": inconsistent if complete else None,
              "cases_with_at_least_two_valid_outputs": sum(len([r for r in llm_items if r["id"] == case["id"] and r["output"] is not None]) >= 2 for case in suite["cases"]),
              "baseline_metrics": metrics(baseline_items), "llm_metrics": metrics(llm_items),
              "baseline_results": baseline_items, "llm_results": llm_items}
    # Heurísticas não podem promover um modelo automaticamente à aprovação final.
    report["automated_gate_passed"] = complete and report["llm_metrics"]["failed"] == 0 and not inconsistent
    return report


def main():
    parser = argparse.ArgumentParser(description="Compara os 59 casos completos com inferência LLM; sem Nextags.")
    parser.add_argument("--report", required=True, help="JSON de resultados; contém conversas e saídas, nunca credenciais.")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--preflight", action="store_true", help="Configuração e baseline somente, sem rede mesmo com credencial.")
    args = parser.parse_args()
    try:
        provider, blocker = None, None
        try:
            config = ModelConfig.from_env()
            if args.preflight:
                blocker = "preflight_no_network"
            else:
                provider = OpenAIResponsesProvider(config)
        except MissingCredential:
            blocker = "missing_credential:HORIZON_LLM_API_KEY"
        except ValueError:
            blocker = "invalid_or_missing_model_configuration"
        report = run_comparison(provider, repeats=args.repeats, blocker=blocker)
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (ValueError, OSError, KeyError):
        print("Configuração/lote inválido; nenhum detalhe sensível registrado.", file=sys.stderr)
        return 2
    print(f'Baseline: {report["baseline_metrics"]["passed"]}/{report["case_count"]}; chamadas LLM: {report["inference_attempts"]}/{report["planned_inferences"]}')
    if not report["run_complete"]:
        print("LLM não validado: " + str(report["blocker"]))
        return 2
    print(f'LLM aprovados: {report["llm_metrics"]["passed"]}; reprovados: {report["llm_metrics"]["failed"]}; revisão humana necessária.')
    return 0 if report["automated_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
