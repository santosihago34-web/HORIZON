# Exemplos executados — backend local determinístico

Nenhum LLM, envio ou integração foi executado. Dados fictícios; instante de teste fixo.

## T01 — Anúncio de calça, interesse em camisa G

### Entrada

```json
{
  "messages": [
    {
      "role": "cliente",
      "text": "Na verdade eu queria ver camisa. Tem G?"
    }
  ],
  "ad_product": "calça"
}
```

### Análise

Última mensagem do cliente: Na verdade eu queria ver camisa. Tem G?. Interesse explícito: camisa. Estágio: QUALIFICANDO; humano: NÃO; confiança: ALTA.

### Resposta sugerida

Estoque: INFORMAÇÃO NÃO DISPONÍVEL; precisa de conferência.

### JSON

```json
{
  "contexto_entendido": "Última mensagem do cliente: Na verdade eu queria ver camisa. Tem G?. Interesse explícito: camisa.",
  "produto": {
    "estado": "CONFIRMADO",
    "nome": "camisa",
    "evidencia": "Na verdade eu queria ver camisa. Tem G?"
  },
  "estagio": "QUALIFICANDO",
  "cliente_recorrente": "DESCONHECIDO",
  "dados_ja_conhecidos": [
    {
      "dado": "tamanho",
      "valor": "G",
      "fonte": "cliente: Na verdade eu queria ver camisa. Tem G?",
      "atualidade": "contexto da conversa; não verifica catálogo"
    }
  ],
  "dado_que_falta": "informação comercial: estoque",
  "sinal_comercial": "Na verdade eu queria ver camisa. Tem G?",
  "proxima_acao_recomendada": "Consultar fonte comercial atualizada para os dados ausentes, preservando o contexto; humano revisa.",
  "resposta_sugerida": "Estoque: INFORMAÇÃO NÃO DISPONÍVEL; precisa de conferência.",
  "confianca": "ALTA",
  "humano": "NÃO",
  "motivo": "Sem fonte recente e compatível para: estoque. Histórico e anúncio não verificam catálogo.",
  "follow_up_elegivel": {
    "valor": false,
    "motivo": "Há resposta atual; sequência anterior interrompida. Nenhuma retomada executada."
  },
  "score_atendimento_anterior": {
    "nota": null,
    "itens_avaliaveis": 0,
    "observacao": "Sem atendimento anterior avaliável; não mede conversão."
  }
}
```

### Avaliação

PASSOU: JSON válido e expectativas declaradas atendidas, incluindo contexto, ausência de invenção e limite humano.

## T04 — Sim com mais de uma referência

### Entrada

```json
{
  "messages": [
    {
      "role": "vendedor",
      "text": "Quer a calça? Ou a camisa?"
    },
    {
      "role": "cliente",
      "text": "Sim."
    }
  ]
}
```

### Análise

Última mensagem do cliente: Sim.. Interesse ainda não confirmado. Estágio: EXPLORANDO; humano: NÃO; confiança: BAIXA.

### Resposta sugerida

Só pra confirmar: a qual pergunta você respondeu sim?

### JSON

```json
{
  "contexto_entendido": "Última mensagem do cliente: Sim.. Interesse ainda não confirmado.",
  "produto": {
    "estado": "NÃO IDENTIFICADO",
    "nome": null,
    "evidencia": null
  },
  "estagio": "EXPLORANDO",
  "cliente_recorrente": "DESCONHECIDO",
  "dados_ja_conhecidos": [],
  "dado_que_falta": "referente do sim",
  "sinal_comercial": "Sim.",
  "proxima_acao_recomendada": "Esclarecer uma referência por vez; não avançar para fechamento.",
  "resposta_sugerida": "Só pra confirmar: a qual pergunta você respondeu sim?",
  "confianca": "BAIXA",
  "humano": "NÃO",
  "motivo": "Somente leitura, análise e sugestão; nenhuma ação executada.",
  "follow_up_elegivel": {
    "valor": false,
    "motivo": "Há resposta atual; sequência anterior interrompida. Nenhuma retomada executada."
  },
  "score_atendimento_anterior": {
    "nota": 1.5,
    "itens_avaliaveis": 3,
    "observacao": "Score heurístico parcial (soma, não normalizada): {\"4_pergunta_simples\": 0, \"8_sem_pressao\": 1, \"10_linguagem_respeitosa\": 0.5}; demais itens não aplicáveis/não avaliados. Revisão humana necessária; não mede conversão."
  }
}
```

### Avaliação

PASSOU: JSON válido e expectativas declaradas atendidas, incluindo contexto, ausência de invenção e limite humano.

## T06 — Várias dúvidas, dados comerciais verificados

### Entrada

```json
{
  "messages": [
    {
      "role": "cliente",
      "text": "Quero essa calça. Tem 42? É 100% algodão? E envia pra Goiânia?"
    }
  ],
  "commercial": [
    {
      "product": "calça",
      "field": "estoque",
      "value": true,
      "source": "catálogo fictício conferido",
      "verified_at": "2026-10-05T14:00:00+00:00",
      "size": "42"
    },
    {
      "product": "calça",
      "field": "composicao",
      "value": "100% algodão",
      "source": "catálogo fictício conferido",
      "verified_at": "2026-10-05T14:00:00+00:00"
    },
    {
      "product": "calça",
      "field": "entrega",
      "value": true,
      "source": "catálogo fictício conferido",
      "verified_at": "2026-10-05T14:00:00+00:00",
      "destination": "Goiânia"
    }
  ]
}
```

### Análise

Última mensagem do cliente: Quero essa calça. Tem 42? É 100% algodão? E envia pra Goiânia?. Interesse explícito: calça. Estágio: QUALIFICANDO; humano: NÃO; confiança: ALTA.

### Resposta sugerida

calça tamanho 42 consta disponível na consulta verificada. A entrega para goiania está confirmada na consulta. Composição de calça tamanho 42: 100% algodão.

### JSON

```json
{
  "contexto_entendido": "Última mensagem do cliente: Quero essa calça. Tem 42? É 100% algodão? E envia pra Goiânia?. Interesse explícito: calça.",
  "produto": {
    "estado": "CONFIRMADO",
    "nome": "calça",
    "evidencia": "Quero essa calça. Tem 42? É 100% algodão? E envia pra Goiânia?"
  },
  "estagio": "QUALIFICANDO",
  "cliente_recorrente": "DESCONHECIDO",
  "dados_ja_conhecidos": [
    {
      "dado": "tamanho",
      "valor": "42",
      "fonte": "cliente: Quero essa calça. Tem 42? É 100% algodão? E envia pra Goiânia?",
      "atualidade": "contexto da conversa; não verifica catálogo"
    },
    {
      "dado": "cidade",
      "valor": "goiania",
      "fonte": "cliente: Quero essa calça. Tem 42? É 100% algodão? E envia pra Goiânia?",
      "atualidade": "contexto da conversa; não verifica catálogo"
    }
  ],
  "dado_que_falta": null,
  "sinal_comercial": "Quero essa calça. Tem 42? É 100% algodão? E envia pra Goiânia?",
  "proxima_acao_recomendada": "Revisar os dados verificados e responder às dúvidas; nenhuma reserva/pagamento executado.",
  "resposta_sugerida": "calça tamanho 42 consta disponível na consulta verificada. A entrega para goiania está confirmada na consulta. Composição de calça tamanho 42: 100% algodão.",
  "confianca": "ALTA",
  "humano": "NÃO",
  "motivo": "Somente leitura, análise e sugestão; nenhuma ação executada.",
  "follow_up_elegivel": {
    "valor": false,
    "motivo": "Há resposta atual; sequência anterior interrompida. Nenhuma retomada executada."
  },
  "score_atendimento_anterior": {
    "nota": null,
    "itens_avaliaveis": 0,
    "observacao": "Sem atendimento anterior avaliável; não mede conversão."
  }
}
```

### Avaliação

PASSOU: JSON válido e expectativas declaradas atendidas, incluindo contexto, ausência de invenção e limite humano.

## T12 — Retorno preserva histórico sem afirmar estoque velho

### Entrada

```json
{
  "messages": [
    {
      "role": "cliente",
      "text": "Quero calça tamanho 44."
    },
    {
      "role": "vendedor",
      "text": "Temos 44 por R$ 99,00."
    },
    {
      "role": "cliente",
      "text": "Ainda tem aquela?"
    }
  ],
  "commercial": [
    {
      "product": "calça",
      "field": "estoque",
      "value": true,
      "source": "catálogo fictício conferido",
      "verified_at": "2026-09-20T14:00:00+00:00",
      "size": "44"
    }
  ]
}
```

### Análise

Última mensagem do cliente: Ainda tem aquela?. Interesse explícito: calça. Estágio: QUALIFICANDO; humano: NÃO; confiança: ALTA.

### Resposta sugerida

Estoque: INFORMAÇÃO NÃO DISPONÍVEL; precisa de conferência.

### JSON

```json
{
  "contexto_entendido": "Última mensagem do cliente: Ainda tem aquela?. Interesse explícito: calça.",
  "produto": {
    "estado": "CONFIRMADO",
    "nome": "calça",
    "evidencia": "Quero calça tamanho 44."
  },
  "estagio": "QUALIFICANDO",
  "cliente_recorrente": "DESCONHECIDO",
  "dados_ja_conhecidos": [
    {
      "dado": "tamanho",
      "valor": "44",
      "fonte": "cliente: Quero calça tamanho 44.",
      "atualidade": "contexto da conversa; não verifica catálogo"
    }
  ],
  "dado_que_falta": "informação comercial: estoque",
  "sinal_comercial": "Ainda tem aquela?",
  "proxima_acao_recomendada": "Consultar fonte comercial atualizada para os dados ausentes, preservando o contexto; humano revisa.",
  "resposta_sugerida": "Estoque: INFORMAÇÃO NÃO DISPONÍVEL; precisa de conferência.",
  "confianca": "ALTA",
  "humano": "NÃO",
  "motivo": "Sem fonte recente e compatível para: estoque. Histórico e anúncio não verificam catálogo.",
  "follow_up_elegivel": {
    "valor": false,
    "motivo": "Há resposta atual; sequência anterior interrompida. Nenhuma retomada executada."
  },
  "score_atendimento_anterior": {
    "nota": 3.0,
    "itens_avaliaveis": 4,
    "observacao": "Score heurístico parcial (soma, não normalizada): {\"4_pergunta_simples\": 1, \"8_sem_pressao\": 1, \"10_linguagem_respeitosa\": 0.5, \"3_contexto_tamanho\": 0.5}; demais itens não aplicáveis/não avaliados. Revisão humana necessária; não mede conversão."
  }
}
```

### Avaliação

PASSOU: JSON válido e expectativas declaradas atendidas, incluindo contexto, ausência de invenção e limite humano.

## T13B — Erro e cobrança de pagamento

### Entrada

```json
{
  "messages": [
    {
      "role": "cliente",
      "text": "O pagamento deu erro e foi cobrado mesmo assim."
    }
  ]
}
```

### Análise

Última mensagem do cliente: O pagamento deu erro e foi cobrado mesmo assim.. Interesse ainda não confirmado. Estágio: EXPLORANDO; humano: OBRIGATÓRIO; confiança: ALTA.

### Resposta sugerida

Entendi o problema com o pagamento. Um atendente precisa conferir a cobrança antes de orientar o próximo passo.

### JSON

```json
{
  "contexto_entendido": "Última mensagem do cliente: O pagamento deu erro e foi cobrado mesmo assim.. Interesse ainda não confirmado.",
  "produto": {
    "estado": "NÃO IDENTIFICADO",
    "nome": null,
    "evidencia": null
  },
  "estagio": "EXPLORANDO",
  "cliente_recorrente": "DESCONHECIDO",
  "dados_ja_conhecidos": [],
  "dado_que_falta": null,
  "sinal_comercial": "O pagamento deu erro e foi cobrado mesmo assim.",
  "proxima_acao_recomendada": "Recomendar atendimento humano; não vender nem prometer solução.",
  "resposta_sugerida": "Entendi o problema com o pagamento. Um atendente precisa conferir a cobrança antes de orientar o próximo passo.",
  "confianca": "ALTA",
  "humano": "OBRIGATÓRIO",
  "motivo": "Problema de pagamento/cobrança.",
  "follow_up_elegivel": {
    "valor": false,
    "motivo": "Há resposta atual; sequência anterior interrompida. Nenhuma retomada executada."
  },
  "score_atendimento_anterior": {
    "nota": null,
    "itens_avaliaveis": 0,
    "observacao": "Sem atendimento anterior avaliável; não mede conversão."
  }
}
```

### Avaliação

PASSOU: JSON válido e expectativas declaradas atendidas, incluindo contexto, ausência de invenção e limite humano.

## T14A — Áudio sem transcrição

### Entrada

```json
{
  "messages": [
    {
      "role": "cliente",
      "media": "audio"
    }
  ]
}
```

### Análise

Última mensagem do cliente: áudio sem transcrição. Interesse ainda não confirmado. Estágio: EXPLORANDO; humano: OBRIGATÓRIO; confiança: BAIXA.

### Resposta sugerida

Não tenho a transcrição desse áudio. Pode me contar por texto? Um atendente pode ajudar a conferir.

### JSON

```json
{
  "contexto_entendido": "Última mensagem do cliente: áudio sem transcrição. Interesse ainda não confirmado.",
  "produto": {
    "estado": "NÃO IDENTIFICADO",
    "nome": null,
    "evidencia": null
  },
  "estagio": "EXPLORANDO",
  "cliente_recorrente": "DESCONHECIDO",
  "dados_ja_conhecidos": [],
  "dado_que_falta": "transcrição ou esclarecimento por texto",
  "sinal_comercial": "Mídia sem conteúdo legível.",
  "proxima_acao_recomendada": "Solicitar transcrição/texto e revisão humana; não inferir o áudio.",
  "resposta_sugerida": "Não tenho a transcrição desse áudio. Pode me contar por texto? Um atendente pode ajudar a conferir.",
  "confianca": "BAIXA",
  "humano": "OBRIGATÓRIO",
  "motivo": "Situação não compreendida: áudio sem transcrição.",
  "follow_up_elegivel": {
    "valor": false,
    "motivo": "Há resposta atual; sequência anterior interrompida. Nenhuma retomada executada."
  },
  "score_atendimento_anterior": {
    "nota": null,
    "itens_avaliaveis": 0,
    "observacao": "Sem atendimento anterior avaliável; não mede conversão."
  }
}
```

### Avaliação

PASSOU: JSON válido e expectativas declaradas atendidas, incluindo contexto, ausência de invenção e limite humano.
