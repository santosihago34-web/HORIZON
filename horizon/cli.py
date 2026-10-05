"""python -m horizon.cli conversa.json [--now ISO] [--view]."""

import argparse
import json
import sys

from horizon.brain import Brain
from horizon.llm_brain import LLMBrain
from horizon.model_provider import ModelConfig, OpenAIResponsesProvider, ProviderError


def main():
    parser = argparse.ArgumentParser(description="Horizon V1: sugestão sem envio/CRM; backend local ou LLM explícito.")
    parser.add_argument("conversation")
    parser.add_argument("--backend", choices=("baseline", "llm"), default="baseline")
    parser.add_argument("--now", help="Instante ISO com fuso; por padrão usa o relógio atual.")
    parser.add_argument("--prompt", help="Prompt textual: referência no baseline, instrução executada no backend llm.")
    parser.add_argument("--policy", help="Arquivo das regras executáveis do backend local.")
    parser.add_argument("--view", action="store_true", help="Resumo e resposta em stderr; stdout continua sendo JSON.")
    args = parser.parse_args()
    try:
        with open(args.conversation, encoding="utf-8") as stream:
            data = json.load(stream)
        if args.backend == "llm":
            brain = LLMBrain(OpenAIResponsesProvider(ModelConfig.from_env()), args.prompt, args.policy)
        else:
            brain = Brain(args.prompt, args.policy)
        output = brain.analyze(data, args.now)
    except ProviderError as exc:
        print("Inferência não concluída: " + exc.code, file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Entrada/configuração inválida: {exc}", file=sys.stderr)
        return 2
    if args.view:
        print(f'Backend: {brain.backend}; prompt SHA256: {brain.prompt_hash}', file=sys.stderr)
        print(output["contexto_entendido"], file=sys.stderr)
        print(f'Estágio: {output["estagio"]}; humano: {output["humano"]}', file=sys.stderr)
        print("Resposta sugerida (não enviada): " + str(output["resposta_sugerida"]), file=sys.stderr)
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
