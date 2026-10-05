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
