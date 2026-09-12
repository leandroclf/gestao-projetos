# Runbook operacional

## Execução manual

A partir da raiz do projeto:

```bash
PYTHONPATH=src python3 -m notion_management audit
PYTHONPATH=src python3 -m notion_management snapshot
PYTHONPATH=src python3 -m notion_management notify
```

Use `notify --send` somente quando a publicação estiver prevista para aquele ciclo. Para manter os alertas agrupados no Google Chat, escolha uma chave estável por finalidade, por exemplo:

```bash
PYTHONPATH=src python3 -m notion_management notify --send --thread-key gestao-integracoes-diaria
```

O webhook publica apenas no espaço em que foi criado. A mensagem deve ser tratada como sinal de acompanhamento; a decisão, a evolução e a evidência continuam nos comentários do registro oficial no Notion.

## Agendamento futuro

O projeto está pronto para ser chamado por cron, CI, Cloud Run Job ou outro executor autorizado, mas nenhum agendamento é ativado por este repositório. A rotina recomendada é:

1. executar `snapshot` diariamente ou em cada ciclo de gestão;
2. executar `notify --send` somente após definir a política de repetição e severidade;
3. armazenar `NOTION_TOKEN` e `GCHAT_WEBHOOK_URL` no cofre de segredos do ambiente;
4. manter logs sem tokens, webhooks ou conteúdo sensível;
5. alertar quando a execução falhar, sem transformar falha técnica em mensagem falsa de saúde.

Exemplo de cron local, para ser adaptado e aprovado no ambiente operacional:

```cron
0 8 * * 1-5 cd /caminho/absoluto/notion && PYTHONPATH=src /usr/bin/python3 -m notion_management snapshot >> /var/log/hive-notion.log 2>&1
```

Não configurar o `notify --send` automaticamente até definir:

- quais regras geram alerta;
- janela e frequência por severidade;
- chave de thread por tipo de mensagem;
- responsável por tratar cada alerta;
- comportamento de retry e deduplicação.

## Baseline validado — 12/09/2026

Com as quatro fontes acessíveis, a auditoria filtrada encontrou:

- 731 tarefas;
- 39 projetos;
- 23 solicitações;
- 0 ações COLTEC no recorte atual;
- 62 achados de qualidade;
- 2.088 registros excluídos por escopo.

Os 62 achados estão distribuídos em 45 tarefas sem prazo, 1 tarefa sem aprovador, 6 tarefas bloqueadas sem atualização no último dia útil, 5 tarefas sem atualização há mais de dois dias úteis e 5 tarefas com prazo vencido. Não houve achados de responsável ausente na execução.

O baseline completo está em `reports/snapshots/2026-09-12.json`. Esses números são uma fotografia e devem ser comparados com os painéis do Notion antes de virar meta ou alerta.

## Próxima validação gerencial

Antes de automatizar mensagens periódicas, revisar os 62 achados por amostragem e separar:

- falha real de preenchimento;
- registro que deveria estar concluído/arquivado;
- exceção legítima;
- regra que precisa ser ajustada.

Essa classificação evita transformar volume bruto em ruído operacional.
