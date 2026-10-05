# HORIZON — protótipo local do cérebro de atendimento V1

Este repositório contém um ambiente **isolado** para conferir análises e sugestões da Horizon IA V1. Não se conecta à Nextags, WhatsApp ou OpenAI, não envia mensagens e não altera contatos. O repositório é público: não inclua dados reais de clientes nem chaves de API.

## Executar o protótipo

Python 3.12, somente biblioteca padrão; nenhuma instalação ou credencial.
Use o checkout existente; nenhuma worktree ou serviço precisa ser criado.

```bash
cd /workspace/HORIZON
python -m horizon.cli examples/conversa_camisa.json --view > /tmp/horizon_saida.json
python -m horizon.validator /tmp/horizon_saida.json
python -m horizon.harness --report /tmp/horizon_comportamento.json --examples /tmp/horizon_exemplos.md
python -m unittest discover -s tests -v
```

A CLI imprime JSON em stdout e o resumo em stderr. Não grava a conversa nem
executa a resposta sugerida. O harness retorna código 1 se houver falha e 2 se
o lote/configuração for inválido; registra PASSOU/FALHOU por caso. Relatórios
incluem entradas: use arquivos externos/ignorados para dados privados.

O backend **local-deterministic** usa regras conservadoras e frases da policy.
Não há inferência de LLM. O prompt textual é carregado e identificado por SHA256,
mas não é executado por um modelo. Alterar só o Markdown não muda esse backend;
`--policy caminho.json` altera regras, frases e vocabulário sem reescrever a
aplicação. `--prompt caminho.md` permite substituir o texto de referência.

- Especificação e casos originais: `docs/`.
- Prompt textual: `prompts/horizon_v1.md`; regras: `prompts/horizon_v1.policy.json`.
- Contratos: `schemas/input.schema.json` e `schemas/output.schema.json`.
- Cenários e expectativas: `cases/behavior.json`.
- Resultados, seis exemplos completos e limitações: `reports/`.

Para cotar, forneça fatos em `commercial`, com `source` e `verified_at` (ISO com
fuso). O motor aceita somente fatos de até 24h, nunca de data futura, e compara
produto/modelo/tamanho/destino. Preço requer unidade; frete/prazo/entrega requerem
destino e estoque requer tamanho. Valores monetários são BRL. A aplicação não
verifica a fonte externamente: o operador é responsável pela autenticidade.
Histórico de vendedor e anúncio não verificam dados comerciais.

`--now` permite testes com instante fixo; omita em uso manual para verificar
a validade com o relógio atual. `examples/conversa_verificada.json` usa dados
fictícios e requer `--now 2026-10-05T15:00:00+00:00` para reproduzir o teste.

Score é uma avaliação heurística **parcial** do atendimento anterior; itens não
observáveis não recebem nota. Follow-up é somente elegibilidade futura, com
permissão e motivo verificado, sem horários, agendamento ou envio. Exceções
anteriores mantêm humano obrigatório: não existe resolução de tickets nesta V1.

Passar o lote determinístico não comprova que um futuro LLM passa os mesmos
testes, nem desempenho em conversas arbitrárias. Nenhuma publicação faz parte
deste fluxo.

## Inferência LLM — revisão 1.1.0

O baseline permanece como padrão e seus arquivos/regras foram preservados.
`ModelProvider` isola o provedor; `OpenAIChatProvider` implementa Chat Completions
com JSON Schema estrito. `LLMBrain` usa o prompt original e o contexto adicional
`prompts/horizon_llm_context.md`, sem enviar gabaritos, respostas da policy ou
saídas do baseline ao modelo.

Requisitos seguros no processo, sem colocar valores no código ou em arquivos:

| Nome | Uso |
| --- | --- |
| `HORIZON_LLM_API_KEY` | Credencial secreta para o endpoint; ausência bloqueia antes da rede |
| `HORIZON_LLM_MODEL` | Modelo que aceite `json_schema` e os parâmetros configurados |
| `HORIZON_LLM_BASE_URL` | Padrão `https://api.openai.com/v1`; outro endpoint requer destino autorizado |
| `HORIZON_LLM_TEMPERATURE` | Padrão 0.2 |
| `HORIZON_LLM_MAX_TOKENS` | Padrão 1800 |

Uma `OPENAI_API_KEY` já presente também pode ser reutilizada, sem imprimir seu
valor. A sugestão de modelo no rascunho é `gpt-4.1-mini-2025-04-14`; isso não
comprova acesso nem significa que o modelo foi executado. Não desative TLS.
HTTP, redirecionamentos, ecos de chave e chave no conteúdo do prompt são bloqueados.
Não há retentativas automáticas nem fallback silencioso para o baseline.

```bash
cd /workspace/HORIZON
# Sempre sem rede; saída 2 significa configuração/inferência incompleta.
python -m horizon.llm_harness --preflight --report /tmp/horizon-preflight.json

# Somente quando a credencial e o modelo estiverem disponíveis no processo:
python -m horizon.cli examples/conversa_camisa.json --backend llm --view
python -m horizon.llm_harness --repeats 3 --report /tmp/horizon-llm-run.json
```

O lote LLM executa **todos os 59 casos três vezes** (177 chamadas planejadas),
com baseline uma vez nos mesmos casos. Não envia conversas reais nem acessa
Nextags. Fatos recentes são enviados em `DADOS_VERIFICADOS`; valores vencidos
são removidos do payload. O modelo precisa conferir escopo/modelo/unidade.
JSON quebrado, duplicado, fora do schema, recusa ou truncamento falham. Erro de
autenticação/rede/schema do provedor interrompe o lote, preservando os demais
casos como NÃO EXECUTADO, sem insistir no mesmo erro.

O oráculo adicional `cases/llm_expectations.json` avalia funções e fatos, aceitando
variações de linguagem e enums de estágio previstos no documento. O relatório
separa CRÍTICA, COMERCIAL, LINGUAGEM e FORMATAÇÃO, registra denominadores,
recall/precisão humana e decisões incompatíveis. Percentuais de segurança,
decisão e linguagem usam saídas estruturalmente válidas; resultados não
executados não são considerados aprovação. Linguagem e semântica são heurísticas
limitadas e precisam de revisão humana antes de aprovação final.

No preflight da revisão 1.1.0, nenhuma inferência ocorreu por falta de credencial. Os 59
testes antigos continuam aprovados; o novo oráculo encontrou uma confirmação
indevida no baseline A10 (58/59 no novo critério). O baseline foi mantido como
referência, e os dois resultados foram registrados sem substituir o histórico.

Os requisitos de credencial/modelo e o destino `api.openai.com` foram salvos em
rascunho de configuração. O rascunho indica `requires_publish=true`; nenhuma
publicação foi feita. Para continuar respeitando a restrição de não publicar,
a plataforma precisa disponibilizar a credencial/modelo na máquina sem essa
publicação. Se isso não estiver disponível, a inferência permanece bloqueada.
Veja `reports/llm.validation.md` e `reports/llm.preflight.json`.

## Abrir o ambiente

1. Na página do repositório, clique em **Code → Codespaces → Create codespace on main**.
2. Aguarde a abertura do editor. O Codespace usa Python 3.12; não há pacote para instalar.
3. No terminal, execute:

   ```bash
   python -m unittest discover -s tests -v
   python -m horizon.validator examples/saida_exemplo.json
   ```

   O primeiro comando testa o validador. O segundo confere um exemplo fictício de saída.

## Testar uma sugestão manualmente

1. Prepare um caso **fictício ou anonimizado**, sem telefone, nome, pedido ou outra identificação de cliente.
2. Use o prompt Horizon IA V1 em uma sessão de teste separada, somente para leitura e sugestão. Nesta versão, o repositório não chama modelo algum.
3. Salve o objeto JSON produzido pela IA em um arquivo local do Codespace, por exemplo `minha_saida.json`. Não faça commit de casos ou saídas reais.
4. Execute `python -m horizon.validator minha_saida.json`. O validador confere formato, tipos, opções permitidas e coerência básica. Ele **não** comprova a veracidade comercial da resposta: o vendedor ainda precisa revisar contexto, preço, estoque, frete e política.

## Limites

- Validar um JSON não envia a `resposta_sugerida` a ninguém.
- Um resultado `OK` significa somente que o contrato de dados foi respeitado.
- Preço, estoque, frete e prazo exigem fonte atualizada. O ambiente não consulta esses dados.
- A etapa de conectar um modelo e a Nextags depende de decisão e testes posteriores.

## Correção de evidência A10 — revisão 1.1.1

A extração determinística deixou de usar cláusulas com ordens explícitas sobre
regras, schema, administração ou dados inventados como evidência comercial.
As tentativas são registradas em `dados_ja_conhecidos` como
`tentativa_manipulacao`, com fonte no texto original. Cláusulas legítimas e
histórico anterior são preservados; reclamações/pagamento continuam sendo
triados no texto original, para não ocultar humano obrigatório.

A10 agora retorna produto NÃO IDENTIFICADO. Sem alterar os casos/gabaritos,
os dois oráculos passam 59/59. Os sete tipos de ataque em
`cases/prompt_injection.json` passaram na defesa local; 38 métodos unittest
passaram. O detector é heurístico de padrões explícitos, não prova proteção
contra toda formulação ou contra ataques a um LLM real.

A credencial `HORIZON_LLM_API_KEY` e `HORIZON_LLM_MODEL` continuam ausentes.
Conforme a prioridade do pedido, a execução parou após a correção e regressão
A10, antes de preflight externo, liberação/publicação de rede ou do lote LLM.
O lote permanece 59 × 3 = 177; os sete testes locais são suplementares.

A autorização de aplicar/publicar apenas a configuração de saída para
`api.openai.com` fica registrada, sem publicar aplicação/produção. Quando
houver credencial, a próxima integração OpenAI deverá usar **Responses API**;
o transporte anterior Chat Completions não foi migrado nesta parada e não
deve ser usado para iniciar as próximas inferências. Antes do lote, migrar e
testar o transporte, verificar rede/autenticação e uma resposta estruturada.
Veja `reports/a10.validation.md`, `reports/semantic.a10-fixed.json` e
`reports/injection.baseline.json`; os relatórios anteriores são históricos.

## Responses API — revisão 1.2.0

CLI/harness agora usam `OpenAIResponsesProvider`, `/v1/responses`, saída
estruturada em `text.format`, `store=false` e nenhum tool comercial.
O transporte anterior não é utilizado pelas entradas LLM ativas.

Antes do lote, execute exatamente um preflight:

```bash
python -m horizon.real_validation --report /tmp/horizon-responses-preflight.json
```

Somente se retornar 0 e `passed=true`, execute as 177 inferências:

```bash
python -m horizon.llm_harness --repeats 3 --report /tmp/horizon-responses-run.json
```

O preflight real desta revisão retornou HTTP 401 (`invalid_api_key`) na única
requisição. O lote não foi iniciado. Corrigir credencial/binding por canal seguro
antes de novo teste. Ver `reports/responses.validation.md`; métricas LLM ainda
não medidas. Os relatórios anteriores são históricos.
