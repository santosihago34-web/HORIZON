"""Harness declarativo independente: compara expectativas e registra resultados."""

import argparse
import json
import re
import sys
from pathlib import Path

from horizon.brain import Brain, ROOT
from horizon.validator import validate


def at(output, path):
    value = output
    for key in path.split("."):
        value = value[key]
    return value


def evaluate(output, expected):
    errors = ["schema: " + error for error in validate(output)]
    for path, value in expected.get("eq", {}).items():
        try:
            actual = at(output, path)
        except (KeyError, TypeError):
            errors.append(f"{path}: campo ausente")
            continue
        if actual != value:
            errors.append(f"{path}: esperado {value!r}; recebido {actual!r}")
    for path, values in expected.get("one_of", {}).items():
        try:
            actual = at(output, path)
        except (KeyError, TypeError):
            errors.append(f"{path}: campo ausente")
            continue
        if actual not in values:
            errors.append(f"{path}: {actual!r} não é uma opção esperada")
    known = {item["dado"]: item["valor"] for item in output.get("dados_ja_conhecidos", [])}
    for key, value in expected.get("known", {}).items():
        if known.get(key) != value:
            errors.append(f"Dado já conhecido perdido: {key}={value}")
    for key in expected.get("unknown", []):
        if key in known:
            errors.append(f"Dado não sustentado: {key}={known[key]}")
    response = output.get("resposta_sugerida") or ""
    for phrase in expected.get("contains", []):
        if phrase.casefold() not in response.casefold():
            errors.append(f"Resposta omitiu: {phrase}")
    for pattern in expected.get("forbidden", []):
        if re.search(pattern, response, re.IGNORECASE):
            errors.append(f"Resposta proibida: {pattern}")
    if response.count("?") > 1:
        errors.append("Mais de uma pergunta nova")
    if "tamanho" in known and re.search(r"qual (?:o )?tamanho (?:você|voce|cê|ce|usa)", response, re.IGNORECASE):
        errors.append("Repetiu pergunta sobre tamanho conhecido")
    if re.search(r"c[eê] sumiu|esquece n[aã]o|compra agora|[uú]ltima chance|s[oó] hoje", response, re.IGNORECASE):
        errors.append("Pressão/cobrança indevida")
    money = re.findall(r"R\$\s*([0-9]+(?:[.,][0-9]{2})?)", response)
    allowed = expected.get("allowed_money", [])
    if any(value.replace(".", ",") not in allowed for value in money):
        errors.append("Preço/frete não autorizado na resposta")
    if expected.get("max_length") and len(response) > expected["max_length"]:
        errors.append("Resposta longa para este cenário")
    return errors


def run_cases(case_file=None, brain=None):
    path = Path(case_file or ROOT / "cases/behavior.json")
    suite = json.loads(path.read_text(encoding="utf-8"))
    engine = brain or Brain()
    results = []
    for case in suite["cases"]:
        try:
            output = engine.analyze(case["input"], suite["now"])
            errors = evaluate(output, case["expected"])
        except Exception as exc:
            output, errors = None, [f"Execução falhou: {type(exc).__name__}: {exc}"]
        results.append({"id": case["id"], "origin": case["origin"], "name": case["name"],
                        "status": "FALHOU" if errors else "PASSOU", "errors": errors,
                        "input": case["input"], "expected": case["expected"], "output": output})
    passed = sum(item["status"] == "PASSOU" for item in results)
    return {"backend": engine.backend, "prompt_executed_by_llm": False,
            "prompt_sha256": engine.prompt_hash, "policy_sha256": engine.policy_hash,
            "policy_version": engine.policy["version"], "evaluation_instant": suite["now"],
            "total": len(results), "passed": passed, "failed": len(results) - passed, "results": results}


def write_examples(report, path):
    chosen = {"T01", "T04", "T06", "T12", "T13B", "T14A"}
    text = "# Exemplos executados — backend local determinístico\n\nNenhum LLM, envio ou integração foi executado. Dados fictícios; instante de teste fixo.\n"
    for item in report["results"]:
        if item["id"] not in chosen:
            continue
        output = item["output"]
        text += f'\n## {item["id"]} — {item["name"]}\n\n### Entrada\n\n```json\n' + json.dumps(item["input"], ensure_ascii=False, indent=2) + "\n```\n"
        text += "\n### Análise\n\n" + (f'{output["contexto_entendido"]} Estágio: {output["estagio"]}; humano: {output["humano"]}; confiança: {output["confianca"]}.' if output else "Erro de execução.") + "\n"
        text += "\n### Resposta sugerida\n\n" + (output["resposta_sugerida"] if output else "Sem resposta.") + "\n"
        text += "\n### JSON\n\n```json\n" + json.dumps(output, ensure_ascii=False, indent=2) + "\n```\n"
        text += "\n### Avaliação\n\n" + item["status"] + ": " + ("; ".join(item["errors"]) or "JSON válido e expectativas declaradas atendidas, incluindo contexto, ausência de invenção e limite humano.") + "\n"
    Path(path).write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Executa casos locais, compara comportamento e preserva status de falha.")
    parser.add_argument("--cases", default=str(ROOT / "cases/behavior.json"))
    parser.add_argument("--report", help="Arquivo JSON de resultado (use somente dados fictícios).")
    parser.add_argument("--examples", help="Arquivo Markdown dos seis exemplos completos.")
    args = parser.parse_args()
    try:
        report = run_cases(args.cases)
        if args.report:
            Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        if args.examples:
            write_examples(report, args.examples)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Harness inválido: {exc}", file=sys.stderr)
        return 2
    for result in report["results"]:
        print(f'{result["status"]} {result["id"]}: {result["name"]}')
        for error in result["errors"]:
            print("  " + error)
    print(f'Total: {report["total"]}; aprovados: {report["passed"]}; reprovados: {report["failed"]}')
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
