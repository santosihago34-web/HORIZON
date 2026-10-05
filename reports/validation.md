# Relatório de validação local — HORIZON IA V1

O protótipo offline de leitura, análise e sugestão foi implementado e executado.
O backend é `local-deterministic`; não houve inferência de modelo de linguagem.
O lote passou, mas a missão de validar um cérebro com prompt executado por LLM
permanece pendente de definição de provedor/modelo e de inferência real.
Nenhum ambiente foi publicado, mensagem enviada, CRM/pipeline alterado,
automação ativada ou integração Nextags configurada. Nenhuma credencial Nextags
foi usada. Não foram feitos push ou publicação de código.

## 1. Arquivos

Alterados: `README.md` e `horizon/validator.py` (nome obrigatório de produto
confirmado e rejeição de score não finito). Arquivos anteriores de teste,
lockfiles, CI e exemplo original foram preservados. Criados:

- `horizon/brain.py`
- `horizon/contracts.py`
- `horizon/cli.py`
- `horizon/harness.py`
- `prompts/horizon_v1.md`
- `prompts/horizon_v1.policy.json`
- `schemas/input.schema.json`
- `schemas/output.schema.json`
- `cases/behavior.json`
- `tests/test_brain.py`
- `examples/conversa_camisa.json`
- `examples/conversa_verificada.json`
- `docs/HORIZON IA - Cerebro de Atendimento V1.md`
- `docs/HORIZON IA - Casos de Teste V1.md`
- `reports/behavior.initial.json`
- `reports/behavior.expanded-before-fix.json`
- `reports/behavior.spec-examples-before-fix.json`
- `reports/behavior.json`
- `reports/examples.md`
- `reports/validation.md`

## 2. Arquitetura

`conversa JSON → check_input → Brain.analyze → validator.validate → saída JSON`.
A CLI oferece resumo e resposta em stderr, JSON em stdout. O harness compara
expectativas independentes por campo, dados conhecidos, termos obrigatórios,
termos proibidos, dinheiro autorizado e violações de segurança. Retorna 1
para falhas e 2 para entrada/lote inválido; lote vazio não é aprovado.
Tudo usa biblioteca padrão de Python 3.12, sem serviços, pacotes ou APIs.
A própria suíte de teste exercita os processos reais da CLI e do validador.

O catálogo é fornecido pelo operador; fatos têm fonte e instante, no máximo
24h de idade, e precisam corresponder a produto, modelo, tamanho e destino.
Preço de kit e de peça são separados. Conflitos exigem revisão humana.
Informações do vendedor em mensagens antigas não comprovam o catálogo atual.

## 3. Prompt e regras executadas

Prompt textual: `prompts/horizon_v1.md`. Policy: `prompts/horizon_v1.policy.json`.
Prompt SHA256: `bf4f350045d6831fa441cff11af103513bc44229689d6d11ea2279b5da5e26ae`.

Policy SHA256: `56805590596c437294446e4eb631ee0360cec25aff235f0d0d1a0808d4884f8e`.


O prompt foi carregado e registrado, **não executado por LLM**. O motor executou
a policy e lógica determinística. A policy permite alterar frases, produtos,
gatilhos e validade sem mudar a aplicação; isso foi testado com arquivo
alternativo. Alterar somente o Markdown não muda a classificação local.
Os documentos originais são especificação de produto, não autorização para
executar os fluxos futuros descritos neles.

## 4. Schema final

Contratos JSON Schema 2020-12 em `schemas/`. O validador Python continua sendo
a verificação executável local, com coerência adicional de produto e score.
Nenhuma chave extra é permitida no objeto de saída. A saída contém:

`contexto_entendido`, `produto` (estado/nome/evidencia), `estagio`,
`cliente_recorrente`, `dados_ja_conhecidos` (dado/valor/fonte/atualidade),
`dado_que_falta`, `sinal_comercial`, `proxima_acao_recomendada`,
`resposta_sugerida`, `confianca`, `humano`, `motivo`,
`follow_up_elegivel` (valor/motivo), `score_atendimento_anterior`
(nota/itens_avaliaveis/observacao).

Enums preservam o contrato existente: `INTERESSE CONFIRMADO`, `MÉDIA` e
`OBRIGATÓRIO` usam espaços/acentos, em vez dos aliases dos casos do documento.
Produto: CONFIRMADO, PROVÁVEL ou NÃO IDENTIFICADO. Humano: NÃO, SUGERIDO
ou OBRIGATÓRIO. Score null se menos de três itens forem avaliáveis.

## 5–7. Quantidade e resultados

- Cenários comportamentais finais: **59**.
- Aprovados: **59**.
- Reprovados finais: **0**.

- Cobertura: 16 entradas do documento de casos (incluindo variantes A/B),
  10 reconstruções dos exemplos A–J da especificação, 26 cenários adicionais
  e 7 cenários de regressão.
- Unittest: **15 métodos passaram** (os seis originais e nove novos).
- Sensibilidade: **12 violações injetadas foram reprovadas pelo harness**;
  essas rejeições são o resultado esperado, não falhas do lote funcional.
- CLI → JSON → validador executados com sucesso, inclusive cotação fictícia
  verificada de R$ 159,90 por peça.
- Exemplo original validado. `git diff --check` passou.

## 8–9. Falhas encontradas e correções

Oito falhas distintas foram observadas antes das correções:

| Caso | Falha | Correção |
| --- | --- | --- |
| T07 | Produto abandonado entrou como segundo interesse | Descartar menção com “deixa a …” antes de selecionar o novo produto |
| R02 | Cancelamento manteve interesse e tamanho | Reconhecer “não quero mais a …” e limpar associação anterior |
| R03 | Mensagem incompreensível não escalou | Solicitar esclarecimento e humano obrigatório |
| R04 | Reclamação de entrega não escalou | Acrescentar gatilhos de pedido não entregue e insatisfação à policy |
| R05 | Problema anterior de pagamento virou venda | Manter revisão obrigatória de exceções ainda sem resolução confiável |
| E-A | Localização conhecida não foi respondida | Consultar fonte de loja separada do interesse comercial |
| E-C | Perguntou tamanho de chapéu que cliente não sabia | Oferecer procedimento de medição, sem garantir caimento |
| E-H | Não usou benefício verificado para a lida | Relacionar uso conhecido ao benefício fornecido pela fonte |

Além disso, o teste passou a verificar preço de kit separado de peça, opt-out
anterior, campos de contrato, política alternativa e código de saída real.

## 10. Regressão

- Rodada inicial: 42 casos, 41 passaram, T07 falhou.
- Ampliação adversarial: 47 casos, 42 passaram, cinco falharam.
- Correções dos cinco: repetidos os cinco afetados e depois todos os 47; passou.
- Exemplos A–J: 57 casos, 54 passaram, E-A/E-C/E-H falharam.
- Correções dos três: repetidos os afetados, adicionados R06/R07 e executados
  todos os 59; passou. Suite completa de 15 métodos também passou.
- Relatórios anteriores preservam falhas reais. `behavior.json` contém a execução
  final, cada entrada, expectativa, saída e avaliação.

## 11. Exemplos reais de execução

`reports/examples.md` contém seis exemplos completos, T01, T04, T06, T12,
T13B e T14A, com Entrada, Análise, Resposta sugerida, JSON e Avaliação.
São saídas reais do programa sobre entradas fictícias/anonimizadas; não são
conversas novas extraídas da Nextags nem mensagens enviadas.

| Entrada resumida | Análise | Sugestão e avaliação |
| --- | --- | --- |
| Anúncio de calça, “queria ver camisa. Tem G?” | Camisa confirmada, G conhecido, QUALIFICANDO | Falta de estoque sinalizada; não repete tamanho. PASSOU |
| Duas perguntas, “Sim.” | Produto não identificado, confiança BAIXA | Pergunta qual referência foi respondida. PASSOU |
| Calça 42, algodão, envio para Goiânia, dados recentes fornecidos | Contexto e fonte compatíveis | Responde as três dúvidas sem inventar. PASSOU |
| Retorno depois, “Ainda tem aquela?” | Calça 44 preservada, catálogo velho rejeitado | Estoque indisponível como informação. PASSOU |
| Pagamento com erro e cobrança | Humano OBRIGATÓRIO | Conferência humana, sem promessa de estorno. PASSOU |
| Áudio sem transcrição | Conteúdo desconhecido, humano OBRIGATÓRIO | Solicita texto sem inferir áudio. PASSOU |

## 12. Limitações e pendências

1. **Inferência real de LLM não executada.** Não foi definido provedor/modelo.
   Não há variável de endpoint/modelo/chave LLM identificada na máquina ou
   requisito de credencial desse tipo no ambiente consultado. A validação
   determinística não comprova comportamento de um modelo futuro.
2. Reconhecimento por vocabulário/regras tem cobertura limitada de português:
   paráfrases, negação complexa, múltiplos produtos, ironia e referências longas
   precisam de novos casos e revisão. Estágios são heurísticos.
3. Score é parcial: pergunta simples, ausência de pressão, respeito lexical,
   repetição de tamanho e clareza de preço quando observáveis. Não implementa
   uma avaliação semântica completa das dez rubricas, nem mede conversão.
4. Fonte comercial é metadado fornecido pelo operador, não uma consulta externa
   autenticada. A janela conservadora de 24h exige atualização manual e não
   garante que estoque/preço continue válido durante todo o período.
5. Follow-up apenas recomenda elegibilidade, com permissão e motivo verificado.
   Não modela calendário 4h/7d/20d, horários silenciosos ou execução. Resposta
   atual interrompe a sequência; opt-out anterior prevalece sem novo consentimento.
6. Não há transcrição automática de áudio, imagens, pagamento, resolução de
   tickets, reserva, catálogo de alternativas ou CRM. Exceções anteriores
   continuam obrigatoriamente humanas nesta versão conservadora.
7. Os exemplos A–J foram reconstruídos dos resumos fornecidos, não são
   reproduções dos históricos completos das 30 conversas.
8. Esta suíte finita, criada a partir da especificação, não é avaliação cega
   com atendimento de produção. É um primeiro lote local de regressão.

Para concluir a validação da IA por modelo, falta definir provedor/modelo,
configurar credenciais por canal seguro quando necessárias e executar o mesmo
lote com esse backend. Não publicar nem conectar à Nextags nessa continuação.

HORIZON IA V1 AINDA PRECISA DE CORREÇÕES
