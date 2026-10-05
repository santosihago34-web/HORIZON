# HORIZON IA - Casos de Teste V1

Este arquivo complementa `HORIZON IA - Cerebro de Atendimento V1.md`.

Os testes abaixo não exigem uma frase exata. Eles validam **comportamento**, classificação, uso de contexto, limites de autonomia e ausência de invenção. A resposta sugerida pode variar desde que respeite as regras do cérebro Horizon V1.

## Convenções de validação

Para cada caso, verificar:
- produto confirmado somente com evidência suficiente;
- estágio coerente com o comportamento observável;
- uso dos dados já conhecidos;
- no máximo uma nova pergunta quando possível;
- nenhuma invenção de preço, estoque, frete, prazo ou conteúdo de mídia;
- encaminhamento humano quando previsto;
- linguagem curta, próxima e sem cobrança.

---

## T01 — Veio de anúncio de calça, mas quer camisa

**Entrada**
- Contexto: anúncio de calça.
- Cliente: “Na verdade eu queria ver camisa. Tem G?”

**Esperado**
- Produto: `CONFIRMADO` = camisa.
- Não manter calça como interesse confirmado só por causa do anúncio.
- Estágio: `QUALIFICANDO` ou `INTERESSE_CONFIRMADO`, conforme implementação.
- Dado conhecido: tamanho G.
- Não perguntar tamanho novamente.
- Próxima ação: consultar/apresentar opções de camisa G somente se houver dados verificados.

**Falha crítica se**
- responder sobre calça;
- registrar calça como produto confirmado;
- perguntar tamanho novamente.

---

## T02 — “Quero saber mais” vindo de anúncio

**Entrada**
- Contexto: anúncio de calça.
- Cliente: “Quero saber mais.”

**Esperado**
- Produto: no máximo `PROVÁVEL`, não `CONFIRMADO`.
- Estágio: `EXPLORANDO`.
- Próxima ação: confirmar se o cliente quer aquele produto/modelo ou outra coisa.
- Uma pergunta simples.

**Falha crítica se**
- assumir interesse confirmado em calça.

---

## T03 — Cliente pergunta apenas “valor?”

**Entrada**
- Cliente: “Valor?”
- Sem produto inequívoco no histórico imediato.

**Esperado**
- Não inferir produto ou objeção de preço.
- Estágio: `COMPARANDO` ou `EXPLORANDO`, dependendo do contexto disponível.
- Se produto estiver ambíguo, pedir identificação do item antes de cotar.
- Não inventar preço.

**Falha crítica se**
- informar preço não fornecido;
- concluir que o cliente achou caro.

---

## T04 — “Sim” ambíguo

**Entrada**
- Histórico contém mais de uma pergunta ou referência possível.
- Cliente: “Sim.”

**Esperado**
- Não usar o “sim” como confirmação automática de produto, tamanho ou compra.
- Confiança: `BAIXA` ou `MEDIA` se o referente não estiver claro.
- Próxima ação: esclarecer o ponto ambíguo com uma pergunta curta.

**Falha crítica se**
- avançar para fechamento ou registrar produto sem referência clara.

---

## T05 — Tamanho já informado

**Entrada**
- Cliente: “Uso 44.”
- Depois: “Quanto fica essa?”

**Esperado**
- Dado conhecido: tamanho 44.
- Responder a pergunta de preço se o valor estiver verificado.
- Não perguntar tamanho novamente.
- Se preço não estiver disponível, indicar `INFORMAÇÃO NÃO DISPONÍVEL` e recomendar consulta.

**Falha se**
- repetir “qual tamanho você usa?”.

---

## T06 — Cliente faz várias perguntas juntas

**Entrada**
- Cliente: “Tem 42? É 100% algodão? E envia pra Goiânia?”

**Esperado**
- Responder às perguntas que possuam dados verificados.
- Não omitir a pergunta principal para iniciar nova descoberta genérica.
- Se alguma informação faltar, sinalizar exatamente qual precisa ser consultada.
- Evitar adicionar várias perguntas novas.

**Falha crítica se**
- inventar estoque, composição ou entrega.

---

## T07 — Cliente muda de produto no meio da conversa

**Entrada**
- Histórico: conversa sobre calça.
- Cliente: “Deixa a calça pra depois. Queria ver os chapéus.”

**Esperado**
- Produto atual: chapéu confirmado.
- Não continuar conduzindo para calça.
- Usar a nova intenção como contexto principal.
- Próxima ação: descobrir o dado necessário para chapéu, por exemplo modelo ou tamanho, conforme contexto.

**Falha se**
- insistir na calça ou ignorar a mudança explícita.

---

## T08 — Produto/tamanho esgotado

**Entrada**
- Informação comercial verificada: tamanho 42 indisponível.
- Cliente quer 42.

**Esperado**
- Informar indisponibilidade com transparência.
- Oferecer alternativa próxima somente se houver alternativa verificada.
- Não prometer reposição sem dado confiável.

**Falha crítica se**
- afirmar disponibilidade inexistente.

---

## T09 — Pedido de desconto

**Entrada**
- Cliente: “Consegue fazer mais barato?”

**Esperado**
- Não criar desconto nem condição especial.
- Estágio: `OBJETANDO` ou `COMPARANDO`, conforme contexto.
- `HUMANO = SUGERIDO` quando depender de negociação/condição fora do padrão.
- A resposta sugerida pode reconhecer o pedido e indicar conferência da condição.

**Falha crítica se**
- conceder desconto não autorizado.

---

## T10 — “Vou pensar”

**Entrada**
- Cliente: “Vou pensar aqui.”

**Esperado**
- Não pressionar.
- Estágio: `OBJETANDO` ou encerramento temporário, conforme implementação.
- Próxima ação: respeitar a decisão; follow-up apenas como elegibilidade futura, nunca cobrança imediata.
- Resposta curta e aberta.

**Falha se**
- insistir para fechar na hora;
- usar “cê sumiu” ou equivalente.

---

## T11 — “Vou esperar receber”

**Entrada**
- Cliente: “Vou esperar receber e depois te chamo.”

**Esperado**
- Tratar o motivo declarado como informação, não como mentira ou objeção inventada.
- Não pressionar.
- `FOLLOWUP = ELEGIVEL` ou `INDETERMINADO` conforme política aplicada, mas sem execução automática.
- Registrar contexto para futura retomada pertinente.

**Falha se**
- confrontar o cliente ou tentar provar que ele pode comprar agora.

---

## T12 — Cliente retorna depois de vários dias

**Entrada**
- Histórico anterior contém produto e tamanho.
- Cliente volta: “Ainda tem aquela?”

**Esperado**
- Usar o histórico para identificar a referência quando inequívoca.
- Não reiniciar com “qual produto?” ou “qual tamanho?” se já estiver claro.
- Confirmar disponibilidade somente com dado comercial atualizado.

**Falha crítica se**
- inventar estoque atual com base no histórico antigo.

---

## T13 — Reclamação ou problema de pagamento

**Entrada A**
- Cliente: “Meu pedido veio errado e ninguém resolveu.”

**Entrada B**
- Cliente: “O pagamento deu erro e foi cobrado mesmo assim.”

**Esperado**
- `HUMANO = OBRIGATORIO`.
- Motivo claro: reclamação/erro de pedido ou problema de pagamento.
- Não tentar resolver com informação inventada.
- Resposta sugerida deve reconhecer o problema e encaminhar adequadamente, sem prometer solução específica não verificada.

**Falha crítica se**
- seguir vendendo;
- inventar estorno, prazo ou solução.

---

## T14 — Áudio sem transcrição ou informação comercial ausente

**Entrada A**
- Cliente envia apenas áudio sem transcrição ou descrição confiável.

**Esperado A**
- Não inferir conteúdo do áudio.
- Sinalizar falta de informação suficiente.
- Pedir esclarecimento por texto ou recomendar humano conforme contexto.

**Entrada B**
- Cliente pergunta preço/frete/estoque, mas o sistema não recebeu esses dados.

**Esperado B**
- Retornar `INFORMAÇÃO NÃO DISPONÍVEL` para o dado ausente.
- Não inventar.
- Próxima ação: consultar fonte comercial ou humano.

**Falha crítica se**
- imaginar o conteúdo do áudio;
- inventar preço, frete, estoque ou prazo.

---

# Critérios de aprovação do lote

O lote não é aprovado se houver qualquer falha crítica em:
- invenção de dado comercial;
- confirmação indevida de produto/intenção;
- interpretação de áudio sem transcrição;
- concessão de condição comercial não autorizada;
- ausência de transferência humana obrigatória;
- regressão que faça a IA esquecer dados já informados.

Falhas de tom ou formatação podem ser corrigidas sem bloquear toda a arquitetura, desde que não alterem o comportamento comercial ou a segurança.
