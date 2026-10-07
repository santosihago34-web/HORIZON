"""Contratos locais. Conversas e catálogo são dados, sem execução de comandos."""

import math
from datetime import datetime, timezone


FIELDS = {"preco", "estoque", "frete", "prazo", "composicao", "entrega", "beneficio", "localizacao"}


def instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Horários precisam conter fuso (ex.: +00:00).")
    return result.astimezone(timezone.utc)


def check_input(data):
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list) or not data["messages"]:
        raise ValueError("messages deve ser uma lista não vazia.")
    allowed = {"messages", "ad_product", "commercial", "customer", "follow_up_permission"}
    if data.keys() - allowed:
        raise ValueError("Campos de entrada desconhecidos: " + ", ".join(sorted(data.keys() - allowed)))
    for message in data["messages"]:
        if not isinstance(message, dict) or message.get("role") not in {"cliente", "vendedor"}:
            raise ValueError("Cada mensagem precisa ter role cliente ou vendedor.")
        if message.keys() - {"role", "text", "media", "transcription"}:
            raise ValueError("Campo de mensagem desconhecido.")
        for key in ("text", "transcription"):
            if key in message and not isinstance(message[key], str):
                raise ValueError(f"{key} deve ser texto.")
        if message.get("media") not in {None, "audio"}:
            raise ValueError("Só mídia audio é suportada nesta versão.")
        if not message.get("text", "").strip() and not message.get("transcription", "").strip() and message.get("media") != "audio":
            raise ValueError("Mensagem vazia.")
    if not any(m["role"] == "cliente" for m in data["messages"]):
        raise ValueError("A conversa precisa conter mensagem do cliente.")
    if "ad_product" in data and not isinstance(data["ad_product"], str):
        raise ValueError("ad_product deve ser texto.")
    if "follow_up_permission" in data and type(data["follow_up_permission"]) is not bool:
        raise ValueError("follow_up_permission deve ser booleano.")
    customer = data.get("customer", {})
    if not isinstance(customer, dict) or customer.keys() - {"recorrente", "fonte"}:
        raise ValueError("customer exige metadados de histórico, não dados pessoais.")
    if "recorrente" in customer and type(customer["recorrente"]) is not bool:
        raise ValueError("customer.recorrente deve ser booleano.")
    if "recorrente" in customer and not isinstance(customer.get("fonte"), str):
        raise ValueError("Recorrência requer fonte do histórico.")
    if "recorrente" in customer and not customer["fonte"].strip():
        raise ValueError("Fonte do histórico vazia.")
    records = data.get("commercial", [])
    if not isinstance(records, list):
        raise ValueError("commercial deve ser lista.")
    for record in records:
        required = {"product", "field", "value", "source", "verified_at"}
        if not isinstance(record, dict) or not required <= record.keys():
            raise ValueError("Registro comercial incompleto.")
        if record.keys() - (required | {"model", "size", "destination", "unit"}):
            raise ValueError("Campo comercial desconhecido.")
        for key in ("product", "source", "verified_at", "model", "size", "destination", "unit"):
            if key in record and (not isinstance(record[key], str) or not record[key].strip()):
                raise ValueError(f"commercial.{key} deve ser texto não vazio.")
        if record["field"] not in FIELDS:
            raise ValueError("Campo comercial não suportado.")
        value = record["value"]
        if record["field"] in {"preco", "frete"}:
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Preço/frete deve ser número finito não negativo em BRL.")
            if record["field"] == "preco" and not record.get("unit"):
                raise ValueError("Preço requer unidade explícita (peça/kit).")
        elif record["field"] in {"estoque", "entrega"}:
            if type(value) is not bool:
                raise ValueError("Estoque/entrega deve ser booleano.")
            if record["field"] == "estoque" and not record.get("size"):
                raise ValueError("Estoque requer tamanho explícito.")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError("Informação comercial textual vazia ou inválida.")
        if record["field"] in {"frete", "prazo", "entrega"} and not record.get("destination"):
            raise ValueError("Frete/prazo/entrega requer destino explícito.")
        instant(record["verified_at"])
    return data
