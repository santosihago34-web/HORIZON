"""Protótipo offline determinístico: sem APIs, envios ou mutações comerciais."""

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from horizon.contracts import check_input, instant
from horizon.validator import validate

ROOT = Path(__file__).resolve().parents[1]


def normal(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def contents(message):
    if message.get("media") == "audio":
        return message.get("transcription", "")
    return message.get("text", "")


class Brain:
    backend = "local-deterministic"

    def __init__(self, prompt_path=None, policy_path=None):
        self.prompt_path = Path(prompt_path or ROOT / "prompts/horizon_v1.md")
        self.policy_path = Path(policy_path or ROOT / "prompts/horizon_v1.policy.json")
        self.prompt = self.prompt_path.read_text(encoding="utf-8")
        self.policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.prompt_hash = hashlib.sha256(self.prompt.encode()).hexdigest()
        self.policy_hash = hashlib.sha256(self.policy_path.read_bytes()).hexdigest()
        if not self.prompt.strip() or not 0 < self.policy["freshness_hours"] <= 24:
            raise ValueError("Prompt vazio ou validade comercial fora do limite de 24h.")

    def has(self, text, trigger):
        return any(term in normal(text) for term in self.policy["triggers"][trigger])

    def products(self, text, intention=False):
        result = []
        normalized = normal(text)
        for product, names in self.policy["products"].items():
            for match in re.finditer(r"\b(?:" + "|".join(map(re.escape, names)) + r")\b", normalized):
                prefix = normalized[max(0, match.start() - 40):match.start()]
                if intention and re.search(r"(?:nao (?:quero|era|gostei d[ao])|deixa|anuncio (?:de|da|do))\s*$", prefix):
                    continue
                result.append((match.start(), product))
        return list(dict.fromkeys(product for _, product in sorted(result)))

    def facts(self, data):
        product, evidence, size, model, destination = None, None, None, None, None
        known = {}
        previous_seller = ""
        ambiguous = False
        last_customer_index = max(i for i, m in enumerate(data["messages"]) if m["role"] == "cliente")
        for i, message in enumerate(data["messages"][:last_customer_index + 1]):
            text = contents(message)
            if message["role"] == "vendedor":
                previous_seller = text
                continue
            n = normal(text)
            choices = self.products(text, intention=True)
            if len(choices) == 1:
                chosen = choices[0]
                if chosen != product:
                    size, model = None, None
                    known.pop("tamanho", None)
                    known.pop("modelo", None)
                product, evidence = chosen, text
                ambiguous = False
            elif len(choices) > 1:
                # A ordem dos substantivos não autoriza escolher um interesse.
                product, evidence, size, model = None, None, None, None
                known.pop("tamanho", None)
                known.pop("modelo", None)
                ambiguous = True
            elif re.fullmatch(r"sim[.!\s]*", n):
                seller_products = self.products(previous_seller)
                explicit_question = re.search(r"(?:quer|interess|procura)", normal(previous_seller))
                clear = len(seller_products) == 1 and previous_seller.count("?") == 1 and explicit_question
                clear = clear and not re.search(r"\b(?:ou| e )\b", normal(previous_seller))
                if clear:
                    if product != seller_products[0]:
                        size, model = None, None
                        known.pop("tamanho", None)
                        known.pop("modelo", None)
                    product = seller_products[0]
                    evidence = f'Pergunta: {previous_seller} Resposta do cliente: {text}'
                elif i == last_customer_index:
                    ambiguous = True
            elif not product and re.search(r"\b(?:essa|aquela|esse|aquele)\b", n):
                refs = self.products(previous_seller)
                if len(refs) == 1:
                    product = refs[0]
                    evidence = f'Referência: {previous_seller} Pedido do cliente: {text}'

            size_match = re.search(r"\b(?:uso|visto|tamanho|numero|tem|quero)\s+(?:o\s+)?(\d{2,3}(?:/\d{2,3})?|pp|p|m|g|gg|xg)\b", n)
            if not size_match:
                size_match = re.search(r"\b(?:camisa|camiseta|calca|chapeu)\s+(pp|p|m|g|gg|xg|\d{2,3})\b", n)
            if size_match:
                size = size_match[1].upper()
                known["tamanho"] = self.fact("tamanho", size, text)
            model_match = re.search(r"\bmodelo\s+([a-z0-9_-]+)\b", n)
            if model_match:
                model = model_match[1]
                known["modelo"] = self.fact("modelo", model, text)
            city = re.search(r"(?:\bpra|\bpara|\bsou de|\bcidade de)\s+([\w\s]+?)(?=[?.,!]|$)", n)
            if city and not re.search(r"^(?:trabalhar|lida|depois|pensar|receber)\b", city[1]):
                destination = city[1].strip()
                known["cidade"] = self.fact("cidade", destination, text)
            if re.search(r"\b(?:trabalhar|lida)\b", n):
                known["uso"] = self.fact("uso", "trabalho/lida", text)
            if self.has(text, "wait"):
                known["motivo_adiamento"] = self.fact("motivo_adiamento", text, text)
            elif self.has(text, "think"):
                known["motivo_adiamento"] = self.fact("motivo_adiamento", "vou pensar", text)
        return product, evidence, size, model, destination, list(known.values()), ambiguous

    @staticmethod
    def fact(name, value, source):
        return {"dado": name, "valor": value, "fonte": "cliente: " + source, "atualidade": "contexto da conversa; não verifica catálogo"}

    def catalogue(self, data, product, size, model, destination, now):
        values, conflict = {}, False
        if not product:
            return values, conflict
        for record in data.get("commercial", []):
            age = (now - instant(record["verified_at"])).total_seconds() / 3600
            if age < 0 or age > self.policy["freshness_hours"]:
                continue
            if normal(record["product"]) != normal(product):
                continue
            if record.get("model") and normal(record["model"]) != model:
                continue
            if record.get("size") and record["size"].upper() != size:
                continue
            if record.get("destination") and normal(record["destination"]) != destination:
                continue
            field = record["field"]
            if field in values and (values[field]["value"], values[field].get("unit")) != (record["value"], record.get("unit")):
                conflict = True
            values[field] = record
        return values, conflict

    def score(self, data, known):
        messages = data["messages"]
        last_customer_index = max(i for i, m in enumerate(messages) if m["role"] == "cliente")
        previous = messages[:last_customer_index]
        sellers = [m for m in previous if m["role"] == "vendedor" and contents(m).strip()]
        if not sellers:
            return {"nota": None, "itens_avaliaveis": 0, "observacao": "Sem atendimento anterior avaliável; não mede conversão."}
        reply = contents(sellers[-1])
        # Avaliação parcial e explícita, sem inventar rubricas sem evidência.
        rubric = {"4_pergunta_simples": 1 if reply.count("?") <= 1 else 0,
                  "8_sem_pressao": 0 if self.has(reply, "pressure") else 1,
                  "10_linguagem_respeitosa": 0 if re.search(r"\b(?:burro|idiota)\b", normal(reply)) else 0.5}
        seller_index = max(i for i, m in enumerate(previous) if m["role"] == "vendedor" and contents(m).strip())
        earlier = previous[:seller_index]
        if any(re.search(r"\b(?:uso|tamanho|visto)\s+\d{2,3}", normal(contents(m))) for m in earlier if m["role"] == "cliente"):
            rubric["3_contexto_tamanho"] = 0 if re.search(r"qual (?:o )?tamanho", normal(reply)) else 0.5
        if any(re.search(r"\b(?:valor|preco|quanto)\b", normal(contents(m))) for m in earlier if m["role"] == "cliente"):
            clear_price = re.search(r"R\$\s*\d", reply) and re.search(r"\b(?:por|peca|unidade|kit)\b", normal(reply))
            rubric["7_clareza_preco"] = 1 if clear_price else 0
        return {"nota": sum(rubric.values()), "itens_avaliaveis": len(rubric),
                "observacao": "Score heurístico parcial (soma, não normalizada): " + json.dumps(rubric, ensure_ascii=False) + "; demais itens não aplicáveis/não avaliados. Revisão humana necessária; não mede conversão."}

    def analyze(self, data, now=None):
        check_input(data)
        now = instant(now) if isinstance(now, str) else (now or datetime.now(timezone.utc))
        if now.tzinfo is None:
            raise ValueError("now requer fuso horário.")
        customer_messages = [m for m in data["messages"] if m["role"] == "cliente"]
        latest = customer_messages[-1]
        text, n = contents(latest), normal(contents(latest))
        product, evidence, size, model, destination, known, ambiguous = self.facts(data)
        values, conflict = self.catalogue(data, product, size, model, destination, now)
        ad = self.products(data.get("ad_product", ""))
        product_state = "CONFIRMADO" if product else ("PROVÁVEL" if len(ad) == 1 else "NÃO IDENTIFICADO")
        recurring = data.get("customer", {}).get("recorrente")
        result = {
            "contexto_entendido": f'Última mensagem do cliente: {text or "áudio sem transcrição"}. ' + (f'Interesse explícito: {product}.' if product else "Interesse ainda não confirmado."),
            "produto": {"estado": product_state, "nome": product or (ad[0] if len(ad) == 1 else None), "evidencia": evidence if product else None},
            "estagio": "INTERESSE CONFIRMADO" if product else "EXPLORANDO",
            "cliente_recorrente": "SIM" if recurring is True else ("NÃO" if recurring is False else "DESCONHECIDO"),
            "dados_ja_conhecidos": known,
            "dado_que_falta": None,
            "sinal_comercial": text or "Mídia sem conteúdo legível.",
            "proxima_acao_recomendada": "Revisar a sugestão antes de qualquer atendimento.",
            "resposta_sugerida": None,
            "confianca": "ALTA" if product and not ambiguous else "BAIXA",
            "humano": "NÃO",
            "motivo": "Somente leitura, análise e sugestão; nenhuma ação executada.",
            "follow_up_elegivel": {"valor": False, "motivo": "Há resposta atual; sequência anterior interrompida. Nenhuma retomada executada."},
            "score_atendimento_anterior": self.score(data, known),
        }
        responses = self.policy["responses"]

        def finish(response, action, human="NÃO", reason=None):
            result.update(resposta_sugerida=response, proxima_acao_recomendada=action, humano=human)
            if reason:
                result["motivo"] = reason
            errors = validate(result)
            if errors:
                raise ValueError("Saída interna inválida: " + "; ".join(errors))
            return result

        # Os limites prudenciais têm prioridade sobre venda e preço.
        if latest.get("media") == "audio" and not text.strip():
            result["confianca"] = "BAIXA"
            result["dado_que_falta"] = "transcrição ou esclarecimento por texto"
            return finish(responses["audio"], "Solicitar transcrição/texto e revisão humana; não inferir o áudio.", "OBRIGATÓRIO", "Situação não compreendida: áudio sem transcrição.")
        for trigger in ("complaint", "payment_problem", "exception"):
            if self.has(text, trigger):
                result["confianca"] = "ALTA"
                return finish(responses[trigger], "Recomendar atendimento humano; não vender nem prometer solução.", "OBRIGATÓRIO", {"complaint": "Reclamação/irritação ou erro de pedido.", "payment_problem": "Problema de pagamento/cobrança.", "exception": "Exceção fora da regra comercial."}[trigger])
        if conflict:
            return finish(responses["conflict"], "Conferir fontes comerciais contraditórias com humano.", "OBRIGATÓRIO", "Informação comercial contraditória; nenhuma condição pode ser confirmada.")
        if self.has(text, "stop"):
            result["follow_up_elegivel"]["motivo"] = "Cliente pediu para não receber contato. Nenhuma retomada é elegível."
            return finish(responses["stop"], "Respeitar o pedido de não contatar; não executar alterações.")
        if ambiguous and re.fullmatch(r"sim[.!\s]*", n):
            result["confianca"] = "BAIXA"
            result["dado_que_falta"] = "referente do sim"
            result["estagio"] = "EXPLORANDO"
            return finish(responses["ambiguous_yes"], "Esclarecer uma referência por vez; não avançar para fechamento.")
        if self.has(text, "discount"):
            result["estagio"] = "OBJETANDO"
            return finish(responses["discount"], "Conferir condição com humano; não conceder desconto.", "SUGERIDO", "Negociação depende de condição autorizada.")
        for trigger in ("wait", "think"):
            if self.has(text, trigger):
                result["estagio"] = "OBJETANDO"
                permission = data.get("follow_up_permission") is True or self.has(text, "permission")
                eligible = bool(permission and product and values.get("estoque", {}).get("value") is True)
                result["follow_up_elegivel"] = {"valor": eligible, "motivo": "Somente elegibilidade futura: " + ("permissão, produto e disponibilidade verificada; humano decide. " if eligible else "faltam permissão explícita ou motivo comercial verificado. ") + "Resposta atual interrompe sequência anterior; nada agendado/enviado."}
                return finish(responses[trigger], "Respeitar o adiamento declarado e guardar contexto somente na análise.")

        requested = []
        if re.search(r"\b(?:valor|preco|quanto|custa)\b", n):
            requested.append("preco")
            result["estagio"] = "COMPARANDO"
        if re.search(r"\b(?:frete|entrega|envia|enviam)\b", n):
            requested.append("frete" if "frete" in n else "entrega")
            if result["estagio"] != "COMPARANDO":
                result["estagio"] = "QUALIFICANDO"
        if re.search(r"\b(?:prazo|chega|dias)\b", n):
            requested.append("prazo")
        if re.search(r"\b(?:algodao|tecido|composicao|elastano)\b", n):
            requested.append("composicao")
            if result["estagio"] != "COMPARANDO":
                result["estagio"] = "QUALIFICANDO"
        if re.search(r"\b(?:tem|estoque|disponivel|disponibilidade)\b", n):
            requested.insert(0, "estoque")
        if size and result["estagio"] == "INTERESSE CONFIRMADO":
            result["estagio"] = "QUALIFICANDO"
        if recurring is True and not requested:
            result["estagio"] = "CLIENTE RECORRENTE"
        if re.search(r"\b(?:pagar|pagamento|reservar|reserva|despacho|comprar)\b", n):
            result["estagio"] = "COMPRA PROVÁVEL"
            requested.extend(["estoque", "preco"])
            result["humano"] = "SUGERIDO"
        requested = list(dict.fromkeys(requested))
        if not product:
            result["dado_que_falta"] = "produto/modelo de interesse"
            prefix = " ".join(f'{self.label(field)}: INFORMAÇÃO NÃO DISPONÍVEL sem identificar a peça.' for field in requested)
            question = f'Você quer ver a {ad[0]} do anúncio ou procura outra peça?' if len(ad) == 1 else responses["unknown_product"]
            return finish((prefix + " " + question).strip(), "Confirmar produto; anúncio não é evidência de intenção.")

        if values.get("estoque", {}).get("value") is False:
            # Preserva também as demais dúvidas quando houver várias.
            response_parts = [responses["out_of_stock"]]
            requested = [field for field in requested if field != "estoque"]
        else:
            response_parts = []
        missing = []
        for field in requested:
            if field not in values:
                missing.append(field)
                response_parts.append(f'{self.label(field)}: INFORMAÇÃO NÃO DISPONÍVEL; precisa de conferência.')
            else:
                response_parts.append(self.render(field, values[field], product, size, model, destination))
        if not requested and not response_parts:
            if not size:
                response_parts.append(f'Entendi, você quer ver {product}. Qual tamanho você usa?')
                result["dado_que_falta"] = "tamanho"
            elif "estoque" in values:
                response_parts.append(self.render("estoque", values["estoque"], product, size, model, destination))
            else:
                missing.append("estoque")
                response_parts.append(f'Vou considerar {product} no tamanho {size}. Estoque: INFORMAÇÃO NÃO DISPONÍVEL; precisa de conferência.')
        if missing:
            result["dado_que_falta"] = "informação comercial: " + ", ".join(self.label(field).lower() for field in missing)
            result["motivo"] = "Sem fonte recente e compatível para: " + ", ".join(missing) + ". Histórico e anúncio não verificam catálogo."
        action = "Consultar fonte comercial atualizada para os dados ausentes, preservando o contexto; humano revisa." if missing else "Revisar os dados verificados e responder às dúvidas; nenhuma reserva/pagamento executado."
        return finish(" ".join(response_parts), action, result["humano"])

    @staticmethod
    def label(field):
        return {"preco": "Preço", "estoque": "Estoque", "frete": "Frete", "prazo": "Prazo", "composicao": "Composição", "entrega": "Entrega"}.get(field, field)

    @staticmethod
    def render(field, record, product, size, model, destination):
        value = record["value"]
        item = product + (f' modelo {model}' if model else "") + (f' tamanho {size}' if size else "")
        if field in {"preco", "frete"}:
            money = f'{value:.2f}'.replace(".", ",")
            return f'{item}: R$ {money} por {record["unit"]}.' if field == "preco" else f'Frete para {destination}: R$ {money}.'
        if field == "estoque":
            return f'{item} consta disponível na consulta verificada.' if value else f'{item} consta indisponível na consulta verificada.'
        if field == "entrega":
            return f'A entrega para {destination} está ' + ("confirmada na consulta." if value else "indisponível na consulta.")
        if field == "prazo":
            return f'Prazo para {destination}: {value} (fonte verificada).'
        return f'{Brain.label(field)} de {item}: {value}.'
