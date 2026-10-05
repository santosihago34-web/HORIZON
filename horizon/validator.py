"""Valida a estrutura de uma sugestão. Não chama APIs nem envia mensagens."""

import json
import math
import sys
from pathlib import Path

STAGES = {
    "EXPLORANDO", "INTERESSE CONFIRMADO", "QUALIFICANDO", "COMPARANDO",
    "COMPRA PROVÁVEL", "OBJETANDO", "ESFRIOU", "CLIENTE RECORRENTE",
}
PRODUCT_STATES = {"CONFIRMADO", "PROVÁVEL", "NÃO IDENTIFICADO"}
REQUIRED = {
    "contexto_entendido", "produto", "estagio", "cliente_recorrente",
    "dados_ja_conhecidos", "dado_que_falta", "sinal_comercial",
    "proxima_acao_recomendada", "resposta_sugerida", "confianca",
    "humano", "motivo", "follow_up_elegivel", "score_atendimento_anterior",
}


def validate(data):
    """Return a list of format/coherence errors; never execute the suggestion."""
    errors = []
    if not isinstance(data, dict):
        return ["A saída precisa ser um objeto JSON."]
    missing = REQUIRED - data.keys()
    extra = data.keys() - REQUIRED
    if missing:
        errors.append("Chaves ausentes: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("Chaves inesperadas: " + ", ".join(sorted(extra)))
    if missing:
        return errors

    for key in ("contexto_entendido", "sinal_comercial", "proxima_acao_recomendada", "motivo"):
        if not isinstance(data[key], str) or not data[key].strip():
            errors.append(f"{key} deve ser texto não vazio.")
    for key in ("dado_que_falta", "resposta_sugerida"):
        if data[key] is not None and not isinstance(data[key], str):
            errors.append(f"{key} deve ser texto ou null.")

    for key, allowed in (
        ("estagio", STAGES), ("cliente_recorrente", {"SIM", "NÃO", "DESCONHECIDO"}),
        ("confianca", {"ALTA", "MÉDIA", "BAIXA"}),
        ("humano", {"NÃO", "SUGERIDO", "OBRIGATÓRIO"}),
    ):
        if not isinstance(data[key], str) or data[key] not in allowed:
            errors.append(f"{key} fora das opções permitidas.")

    product = data["produto"]
    if not isinstance(product, dict) or set(product) != {"estado", "nome", "evidencia"}:
        errors.append("produto exige estado, nome e evidencia.")
    else:
        if not isinstance(product["estado"], str) or product["estado"] not in PRODUCT_STATES:
            errors.append("produto.estado inválido.")
        for key in ("nome", "evidencia"):
            if product[key] is not None and not isinstance(product[key], str):
                errors.append(f"produto.{key} deve ser texto ou null.")
        if product["estado"] == "CONFIRMADO" and not product["evidencia"]:
            errors.append("Produto confirmado requer evidência explícita.")
        if product["estado"] == "CONFIRMADO" and (not isinstance(product["nome"], str) or not product["nome"].strip()):
            errors.append("Produto confirmado requer nome não vazio.")
        if product["estado"] == "NÃO IDENTIFICADO" and product["nome"] is not None:
            errors.append("Produto não identificado não deve ter nome.")

    known = data["dados_ja_conhecidos"]
    if not isinstance(known, list):
        errors.append("dados_ja_conhecidos deve ser lista.")
    else:
        for i, item in enumerate(known):
            if not isinstance(item, dict) or set(item) != {"dado", "valor", "fonte", "atualidade"} or not all(isinstance(v, str) for v in item.values()):
                errors.append(f"dados_ja_conhecidos[{i}] exige dado, valor, fonte e atualidade em texto.")

    follow = data["follow_up_elegivel"]
    if not isinstance(follow, dict) or set(follow) != {"valor", "motivo"} or type(follow.get("valor")) is not bool or not isinstance(follow.get("motivo"), str):
        errors.append("follow_up_elegivel exige valor booleano e motivo em texto.")
    score = data["score_atendimento_anterior"]
    if not isinstance(score, dict) or set(score) != {"nota", "itens_avaliaveis", "observacao"}:
        errors.append("score_atendimento_anterior exige nota, itens_avaliaveis e observacao.")
    else:
        note, count = score["nota"], score["itens_avaliaveis"]
        if type(count) is not int or not 0 <= count <= 10:
            errors.append("itens_avaliaveis deve ser inteiro entre 0 e 10.")
        if note is not None and (type(note) not in (int, float) or not math.isfinite(note) or not 0 <= note <= 10):
            errors.append("nota deve ser número entre 0 e 10 ou null.")
        if type(count) is int and count < 3 and note is not None:
            errors.append("Com menos de três itens avaliáveis, nota deve ser null.")
        if not isinstance(score["observacao"], str):
            errors.append("observacao deve ser texto.")
    return errors


def main():
    if len(sys.argv) != 2:
        print("Uso: python -m horizon.validator arquivo.json", file=sys.stderr)
        return 2
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Não foi possível ler o JSON: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    if errors:
        for error in errors:
            print("ERRO:", error)
        return 1
    print("OK: estrutura válida. Conteúdo comercial ainda requer revisão humana.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
