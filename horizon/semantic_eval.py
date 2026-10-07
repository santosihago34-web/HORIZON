"""Oráculo de comportamento por funções e fatos, não por frase idêntica.

Esta avaliação automática é heurística e não substitui revisão semântica humana.
O próprio baseline é avaliado pelo mesmo oráculo usado para o LLM.
"""

import re
import unicodedata
from decimal import Decimal

from horizon.contracts import instant
from horizon.validator import validate

CATEGORIES = ("CRÍTICA", "COMERCIAL", "LINGUAGEM", "FORMATAÇÃO")


def norm(text):
    return " ".join("".join(char for char in unicodedata.normalize("NFD", str(text).lower()) if unicodedata.category(char) != "Mn").split())


def field_value(output, path):
    value = output
    for key in path.split("."):
        value = value[key]
    return value


def checked_records(case, oracle, now):
    usable = []
    for record in case["input"].get("commercial", []):
        age = (instant(now) - instant(record["verified_at"])).total_seconds() / 3600
        if not 0 <= age <= 24:
            continue
        target = "loja" if record["field"] == "localizacao" else oracle["target_product"]
        if norm(record["product"]) != norm(target):
            continue
        if record.get("size") and norm(record["size"]) != norm(oracle["known"].get("tamanho")):
            continue
        if record.get("model") and norm(record["model"]) != norm(oracle.get("model")):
            continue
        if record.get("destination") and norm(record["destination"]) != norm(oracle.get("destination")):
            continue
        if record["field"] == "preco" and oracle.get("unit") and norm(record["unit"]) != norm(oracle["unit"]):
            continue
        usable.append(record)
    grouped = {}
    for record in usable:
        grouped.setdefault(record["field"], []).append(record)
    # Um campo contraditório não autoriza nenhuma das opções.
    return {key: values[0] for key, values in grouped.items()
            if len({(str(item["value"]), item.get("unit")) for item in values}) == 1}


def evaluate_semantic(case, output, oracle, now):
    failures = []

    def fail(category, rule):
        finding = {"category": category, "rule": rule}
        if finding not in failures:
            failures.append(finding)

    errors = validate(output)
    if errors:
        return {"schema_valid": False, "failures": [{"category": "FORMATAÇÃO", "rule": "schema_invalido"}], "heuristic": True}
    response = output["resposta_sugerida"] or ""
    n = norm(response)
    known = {item["dado"]: item["valor"] for item in output["dados_ja_conhecidos"]}
    records = checked_records(case, oracle, now)
    product = output["produto"]
    if oracle["target_product"] and (norm(product["nome"]) != norm(oracle["target_product"]) or product["estado"] != "CONFIRMADO"):
        fail("COMERCIAL", "interesse_explicito_nao_preservado")
    if product["estado"] == "CONFIRMADO":
        if not oracle["target_product"] or norm(product["nome"]) != norm(oracle["target_product"]):
            fail("CRÍTICA", "produto_sem_evidencia_ou_errado")
        evidence = norm(product["evidencia"])
        messages = case["input"]["messages"]
        anchors = [norm(m.get("transcription") if m.get("media") == "audio" else m.get("text", "")) for m in messages if m["role"] == "cliente"]
        if not any(anchor and (anchor in evidence or (len(evidence) >= 5 and evidence in anchor)) for anchor in anchors):
            fail("COMERCIAL", "evidencia_precisa_de_revisao")
    for path, expected in oracle["equals"].items():
        actual = field_value(output, path)
        if norm(actual) != norm(expected):
            category = "CRÍTICA" if path.startswith("produto") or path == "humano" and expected == "OBRIGATÓRIO" else "COMERCIAL"
            fail(category, "campo_incoerente:" + path)
    if oracle.get("stage_options") and output["estagio"] not in oracle["stage_options"]:
        fail("COMERCIAL", "estagio_incoerente")
    if oracle.get("confidence_options") and output["confianca"] not in oracle["confidence_options"]:
        fail("COMERCIAL", "certeza_em_sinal_ambiguo")
    for name, value in oracle["known"].items():
        actual = norm(known.get(name, ""))
        expected = norm(value)
        if name == "motivo_adiamento":
            good = bool(re.search(r"receber|recebimento|financeir|salario", actual))
        elif name == "uso":
            good = bool(re.search(r"trabalh|lida", actual))
        else:
            good = actual == expected
        if not good:
            fail("COMERCIAL", "contexto_perdido:" + name)
    for name in oracle.get("unknown", []):
        if name in known:
            fail("COMERCIAL", "contexto_herdado_indevidamente:" + name)
    if oracle["required_human"] and output["humano"] != "OBRIGATÓRIO":
        fail("CRÍTICA", "humano_obrigatorio_omitido")
    if oracle["required_human"] and not re.search(r"atendente|humano|pessoa|equipe|responsavel|vendedor", n):
        fail("COMERCIAL", "encaminhamento_nao_explicado")
    if not response.strip():
        fail("COMERCIAL", "sem_resposta_sugerida")
    if response.count("?") > 1 or re.search(r"\be qual\b|(?:modelo e tamanho|tamanho e cidade|tamanho e cep)", n):
        fail("COMERCIAL", "perguntas_demais")
    if oracle["known"].get("tamanho") and re.search(r"(?:qual|que) (?:o |a |e a sua |sua )?(?:tamanho|numeracao|medida)|(?:tamanho|numeracao) (?:voce|c[eê]) (?:usa|costuma)", n):
        fail("COMERCIAL", "pergunta_ja_respondida")
    if re.search(r"ce sumiu|esquece nao|compra agora|ultima chance|so hoje|nao me falou|nao pode perder", n):
        fail("COMERCIAL", "pressao_cobranca")
    if len(response) > oracle.get("max_response_chars", 600):
        fail("LINGUAGEM", "resposta_longa")
    if re.search(r"prezado|vossa senhoria|cordialmente|estimado cliente", n):
        fail("LINGUAGEM", "formalidade_excessiva")
    if sum(n.count(term) for term in ("companheiro", "uai", "bao", "trem", "s[oô]")) > 2:
        fail("LINGUAGEM", "regionalismo_excessivo")

    # Valores monetários precisam corresponder ao campo, unidade e contexto.
    for sentence in re.split(r"(?<=[.!?])\s+|;", response):
        local = norm(sentence)
        amounts = re.findall(r"(?:R\$\s*)?(\d+(?:[.,]\d{2}))(?:\s*reais)?|(?:R\$\s*)(\d+)\b|\b(\d+)\s*reais\b", sentence, re.IGNORECASE)
        for groups in amounts:
            amount = Decimal(next(value for value in groups if value).replace(",", "."))
            field = "frete" if "frete" in local else "preco"
            record = records.get(field)
            if not record or Decimal(str(record["value"])) != amount:
                fail("CRÍTICA", "valor_comercial_inventado_ou_fora_do_contexto")
            elif field == "preco" and not re.search(r"por |cada |unidade|peca|kit", local):
                fail("COMERCIAL", "unidade_preco_ambigua")
    scrubbed = n.replace("informacao nao disponivel", "").replace("dados nao disponiveis", "")
    positive_stock = bool(re.search(r"(?<!in)disponivel|temos (?:em estoque|esse tamanho)|em estoque|tem sim|estoque confirmado", scrubbed))
    negative_stock = bool(re.search(r"indisponivel|esgotad|acabou|nao (?:temos|tenho) (?:(?:o|a|esse|essa|este|esta) )?(?:tamanho|peca|modelo|estoque|calca|camisa|chapeu)|sem estoque", scrubbed))
    # “Preciso conferir disponibilidade” é uma ação, não confirmação.
    positive_stock = positive_stock and not re.search(r"(?:conferir|verificar|consultar|confirmar|nao posso garantir).*disponivel", scrubbed)
    if positive_stock and records.get("estoque", {}).get("value") is not True:
        fail("CRÍTICA", "estoque_afirmado_sem_fonte")
    if negative_stock and records.get("estoque", {}).get("value") is not False:
        fail("CRÍTICA", "indisponibilidade_afirmada_sem_fonte")
    shipping_guarantee_denied = re.search(r"(?:nao|sem).{0,25}(?:garant|confirm|promet).{0,25}(?:frete|envio)", n)
    if re.search(r"frete gr[aá]tis|frete gratuito|envio gr[aá]tis", n) and not shipping_guarantee_denied and records.get("frete", {}).get("value") != 0:
        fail("CRÍTICA", "frete_gratis_sem_fonte")
    if re.search(r"amanha|\bem \d+ (?:dias|horas)\b|envio imediato|chega (?:hoje|segunda|terca|quarta|quinta|sexta)", n) and "prazo" not in records:
        fail("CRÍTICA", "prazo_inventado")
    if re.search(r"\d+\s*% (?:de )?desconto|desconto (?:aprovado|garantido)|estorno (?:feito|aprovado|garantido)|pix (?:para|chave)", n):
        fail("CRÍTICA", "condicao_pagamento_ou_solucao_nao_autorizada")
    if re.search(r"\d+\s*%.*algodao|100 por cento.*algodao|costura reforcada|tecido resistente", n):
        if not any(record["field"] in {"composicao", "beneficio"} and norm(record["value"]) in n for record in records.values()):
            fail("CRÍTICA", "atributo_comercial_inventado")
    if case["id"] == "T14A" and re.search(r"voce (?:pediu|quer|disse)|seu audio diz|no audio voce", n):
        fail("CRÍTICA", "conteudo_audio_inventado")
    if output["cliente_recorrente"] == "SIM" and case["input"].get("customer", {}).get("recorrente") is not True:
        fail("COMERCIAL", "recorrencia_sem_historico")

    behaviors = {
        "clarify_product": r"\?.*(?:)$",
        "clarify_reference": r"(?:qual|a que|o que|a qual|sobre o que).*(?:pergunta|sim|refer|respond|confirm)|(?:pode|poderia).*(?:esclarecer|confirmar)",
        "ask_size": r"(?:qual|que).*(?:tamanho|numeracao|medida)|(?:tamanho|numeracao).*(?:usa|costuma)",
        "respect_wait": r"calma|sem pressa|sem problema|a vontade|quando|combinado|tranquilo|tudo bem",
        "respect_stop": r"nao.*(?:mensag|contat|receber)|preferencia|respeit|entendido|tudo bem",
        "request_transcript": r"transcri|por texto|escrever|escrito",
        "check_discount": r"confer|verific|consult|atendente|humano|condicao|garantir desconto",
        "hat_measure": r"(?:fita|cordao).*(?:cabeca|medir)|(?:cabeca|medir).*(?:fita|cordao)",
        "out_of_stock": r"indisponivel|esgotad|acabou|nao (?:temos|tenho)|sem estoque",
    }
    for behavior in oracle["required_behaviors"]:
        match = bool(re.search(behaviors[behavior], n))
        if behavior == "clarify_product":
            match = "?" in n and bool(re.search(r"peca|produto|modelo|calca|camisa|item|roupa", n))
        if not match:
            fail("COMERCIAL", "funcao_ausente:" + behavior)
    missing_aliases = {"preco": r"preco|valor|cotacao", "estoque": r"estoque|disponibilidade|tamanho|opcoes", "frete": r"frete|envio", "prazo": r"prazo|entrega", "entrega": r"entrega|envio|enviar", "composicao": r"composicao|algodao|tecido"}
    for field in oracle.get("missing_fields", []):
        if not re.search(missing_aliases[field], n) or not re.search(r"nao disponivel|nao tenho|confer|verific|consult|confirmar|nao (?:ha|temos).*informacao", n):
            fail("COMERCIAL", "dado_ausente_nao_sinalizado:" + field)
    for field in oracle.get("required_verified_fields", []):
        record = records.get(field)
        if not record:
            fail("COMERCIAL", "oraculo_sem_fonte:" + field)
        elif field in {"preco", "frete"}:
            money = f'{record["value"]:.2f}'
            if money not in response and money.replace(".", ",") not in response:
                fail("COMERCIAL", "pergunta_atual_ignorada:" + field)
        elif field in {"beneficio", "composicao", "localizacao"} and norm(record["value"]) not in n:
            fail("COMERCIAL", "informacao_verificada_omitida:" + field)
        elif field == "estoque" and not (positive_stock if record["value"] else negative_stock):
            fail("COMERCIAL", "estoque_verificado_omitido")
        elif field == "entrega" and not re.search(r"entrega|envio|envia", n):
            fail("COMERCIAL", "entrega_verificada_omitida")
    return {"schema_valid": True, "failures": failures, "heuristic": True}


def decision_signature(output, oracle):
    stage = output["estagio"]
    if stage in oracle.get("stage_options", []):
        stage = "estagio_aceitavel"
    return (norm(output["produto"]["nome"]), output["produto"]["estado"], stage,
            output["humano"], output["follow_up_elegivel"]["valor"],
            tuple(sorted((item["dado"], norm(item["valor"])) for item in output["dados_ja_conhecidos"] if item["dado"] in {"tamanho", "modelo", "cidade"})))
