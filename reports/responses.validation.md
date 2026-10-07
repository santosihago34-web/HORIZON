# Responses API — preflight da revisão 1.2.0

A migração de transporte foi implementada. CLI e harness LLM usam agora
`OpenAIResponsesProvider`, endpoint `/v1/responses`, com `instructions`, entrada
separada, `text.format` JSON Schema estrito, `max_output_tokens` e `store=false`.
Nenhuma ferramenta Nextags, CRM, pagamento ou envio está disponível.
O transporte Chat anterior foi mantido apenas para compatibilidade/histórico;
nenhuma inferência desta missão utilizou Chat Completions.

## Resultado real

- Modelo configurado: `gpt-4.1-mini-2025-04-14`.
- Requisições de inferência: **1**, exclusivamente preflight T03 (“Valor?”).
- Respostas de modelo recebidas: **0**.
- HTTP: **401**.
- Código retornado pelo provedor: **invalid_api_key**.
- Preflight: **FALHOU** na autenticação.
- Schema de resposta: **não avaliado**; não houve completion.
- Auditoria de segredo no relatório/log diagnóstico atual: **passou**.
- Lote principal: **177 não executadas**.
- Não houve segunda tentativa externa ou retentativa automática.

Uma consulta anterior a `/models` com HTTP 200 não prova que esta requisição
Responses autenticou. Esta chamada real foi rejeitada. Não é possível concluir
somente com o código se a causa é valor inválido/revogado, chave de outro
contexto ou aplicação de binding; não foi impresso corpo da resposta nem segredo.
O código exato disponível foi registrado, sem inventar uma causa adicional.

## Trabalho local e regressão

Baseline, prompt/policy, schema e gabaritos de 59 casos foram preservados.
Os **46 métodos unittest passaram**, incluindo regressão semântica 59/59,
contrato Responses, segredo omitido, código HTTP sanitizado, gate de uma única
chamada, recusa/truncamento e JSON inválido sem reparo. Os testes de transporte
usam doubles; não são inferências extras. A10 continua corrigido.

Arquivos alterados: `horizon/model_provider.py`, `horizon/cli.py`,
`horizon/llm_harness.py`, `horizon/llm_brain.py` e `README.md`.
Criados: `horizon/real_validation.py`, `tests/test_responses.py`,
`tests/test_preflight.py`, `reports/responses.preflight.json` e este relatório.
Não houve mudança de prompt/policy para corrigir autenticação.

## Métricas

Segurança, decisões comerciais, linguagem, transferência humana, consistência
em três execuções e prompt injection do **LLM** permanecem **não medidos**.
A rejeição HTTP não é uma reprovação comercial/semântica do modelo. Não foi
substituída por resposta do baseline nem descrita como aprovação.
Os resultados locais de baseline/injection anteriores continuam disponíveis
nos relatórios de correção A10 e nos testes de regressão.

## Próximo requisito

Verificar a credencial ativa do projeto OpenAI e seu binding em
`HORIZON_LLM_API_KEY`, por canal seguro, e aplicar a configuração à sessão.
Nunca enviar chave no chat. Não adicionar requisito duplicado: a variável já
existe, mas a operação de inferência foi rejeitada. Após a correção efetiva,
repetir **um** preflight Responses; só depois de passar iniciar as 177 inferências.
A configuração de rede já alcançou o serviço (resposta HTTP recebida), portanto
não se pede ampliar rede nem publicar aplicação para resolver este 401.

Nenhuma Nextags, usuário/cliente real, WhatsApp, CRM/pipeline, automação,
endpoint público ou publicação de aplicação foi envolvida.

HORIZON IA V1 AINDA PRECISA DE AJUSTES NO LLM
