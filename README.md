# HORIZON — ambiente de teste da IA V1

Este repositório contém um ambiente **isolado** para conferir análises e sugestões da Horizon IA V1. Não se conecta à Nextags, WhatsApp ou OpenAI, não envia mensagens e não altera contatos. O repositório é público: não inclua dados reais de clientes nem chaves de API.

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
