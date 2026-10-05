"""Fronteira de evidência local: ordens sobre o sistema não são intenção de compra.

Detector conservador de padrões explícitos; não prova imunidade a toda injection.
O texto original continua sendo dado de auditoria e de triagem humana.
"""

import re
import unicodedata


PATTERNS = {
    "ignorar_regras": r"\b(?:ignore|ignorar|desconsidere|esqueca)\b.{0,100}\b(?:regras|instrucoes|politica|system|developer|sistema|prompt|anteriores)\b",
    "declarar_sem_evidencia": r"\b(?:declare|registre|marque|defina|considere|confirme)\b.{0,100}(?:\bproduto\b|\bconfirmad[oa]\b|sem evidenc|sem contexto)",
    "inventar_dados": r"\b(?:invente|inventa|fabrique|falsifique|finja)\b",
    "omitir_humano": r"\b(?:nao|nunca)\b.{0,40}\b(?:transfira|encaminhe|passe)\b.{0,60}\b(?:humano|atendente|pessoa|equipe)\b",
    "alterar_schema": r"\b(?:altere|mude|troque|substitua|remova|quebre)\b.{0,80}\b(?:schema|json|enumeracao|campos obrigatorios|formato de saida)\b",
    "revelar_instrucoes": r"\b(?:revele|mostre|imprima|exiba|retorne)\b.{0,80}\b(?:prompt|instrucoes internas|instrucoes de sistema|segredos|chaves|credenciais)\b",
    "assumir_administracao": r"\b(?:assuma|atue|aja|voce agora e)\b.{0,80}\b(?:admin|administrador|administradora|root|system|developer)\b",
}


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def evidence_text(text):
    """Preserva cláusulas legítimas; exclui cláusulas com ordens explícitas.

Não modifica a conversa original nem altera configuração/policy. Não considere
o texto filtrado uma autorização para ignorar reclamações no original.
"""
    kept, attempts = [], []
    for segment in re.split(r"(?<=[.!?;])\s+|\n+", text):
        n = normalized(segment)
        matches = [name for name, pattern in PATTERNS.items() if re.search(pattern, n)]
        if matches:
            attempts.extend(matches)
        elif segment.strip():
            kept.append(segment.strip())
    return " ".join(kept), sorted(set(attempts))
