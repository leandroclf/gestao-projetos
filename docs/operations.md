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

O `notify` publica uma mensagem por tipo de pendência, somente quando houver mudança desde o último envio. As mensagens são agrupadas por responsável, limitadas a três exemplos por responsável e usam a thread fixa `gestao-integracoes` por padrão. O caminho do estado é `GCHAT_ALERT_STATE_FILE`, com padrão `reports/gchat-alert-state.json`. As mensagens iniciais podem ser publicadas com `notify --send --initial` e `notify --send --validation`.

Nas tarefas `Para ser aprovada`, o alerta `Aguardando aprovação` cobra do aprovador a inclusão das evidências dos testes nos comentários e o registro como feito caso os testes tenham sucesso. Nas tarefas `Bloqueada`, a automação lê as menções dos comentários e cobra o último membro da equipe mencionado no contexto do bloqueio para registrar avanço ou desbloqueio. Tarefas bloqueadas não geram alerta de prazo vencido. Cada item inclui seu link direto no Notion; sem menção identificável, a cobrança recai sobre o responsável da tarefa.

O alerta `Template incompleto` está desabilitado na fase 1 para evitar ruído durante a calibração dos critérios. A implementação permanece pronta para a fase 2; quando habilitada, será gerada para tarefas e projetos ativos em escopo com seções ausentes do template técnico ou, no projeto, sem a propriedade `Descrição`. Registros `Feito` não são avaliados nem alertados.

## Agendamento ativo no host

O manifesto `ops/gestao-projetos.cron` define o agendamento do host. A instalação é feita no crontab do usuário, com execução protegida por `flock` para impedir sobreposição. A rotina é:

1. executar `notify --send` nos ciclos definidos; a deduplicação impede repetição quando o conjunto de pendências não mudou;
3. armazenar `NOTION_TOKEN` e `GCHAT_WEBHOOK_URL` no cofre de segredos do ambiente;
4. manter logs sem tokens, webhooks ou conteúdo sensível;
5. alertar quando a execução falhar, sem transformar falha técnica em mensagem falsa de saúde.

Manifesto de cron instalado no host:

```cron
0 8 * * 1,3,5 cd /home/leandro/IdeaProjects/lfsolucoes/gestao-projetos && /usr/bin/flock -n /tmp/gestao-projetos-alertas.lock /usr/bin/env PYTHONPATH=src /usr/bin/python3 -m notion_management notify --send --rules overdue,stale,approval_update_missing,blocked_follow_up >> reports/cron-alertas.log 2>&1
0 8 * * 2,4 cd /home/leandro/IdeaProjects/lfsolucoes/gestao-projetos && /usr/bin/flock -n /tmp/gestao-projetos-alertas.lock /usr/bin/env PYTHONPATH=src /usr/bin/python3 -m notion_management notify --send --rules overdue,stale,approval_update_missing,blocked_follow_up,due_date_missing >> reports/cron-alertas.log 2>&1
```

No host, o cron executa às 8h em dias úteis os alertas `stale`, `overdue`, `approval_update_missing` e `blocked_follow_up`. Às terças e quintas, inclui `due_date_missing`. `urgent_without_project` está desabilitado na fase atual. O estado permanece persistido em `GCHAT_ALERT_STATE_FILE`.

## Baseline validado — 12/09/2026

Com as quatro fontes acessíveis, a auditoria filtrada encontrou:

- 731 tarefas;
- 39 projetos;
- 23 solicitações;
- 0 ações COLTEC no recorte atual;
- 62 achados de qualidade;
- 2.088 registros excluídos por escopo.

Os 62 achados estão distribuídos em 45 tarefas sem prazo, 1 tarefa sem aprovador, 11 tarefas sem atualização dentro da cadência definida e 5 tarefas com prazo vencido. Não houve achados de responsável ausente na execução. Esse baseline é histórico e preserva a regra vigente na data da execução; novas execuções devem aplicar as regras atuais.

O baseline completo está em `reports/snapshots/2026-09-12.json`. Esses números são uma fotografia e devem ser comparados com os painéis do Notion antes de virar meta ou alerta.

## Validação de recorte — 12/09/2026

Primeira execução do próximo incremento 1 (comparar auditoria e snapshots com os painéis dinâmicos do Notion).

- Contagens confirmadas: a auditoria de hoje repetiu 731 tarefas, 39 projetos e 23 solicitações, iguais ao baseline. Os achados de qualidade caíram de 62 para 16 (`due_date_missing` foi de 45 para 5); antes de tratar isso como melhoria real, revisar por amostragem se houve preenchimento genuíno de prazo ou mudança de status para fora do recorte controlado.
- Corrigido: `_relation()` em `src/notion_management/service.py` usava apenas o primeiro item do relacionamento `Área` de cada tarefa/projeto, descartando registros cuja Área "Integrações" não fosse a primeira do relacionamento e cujo responsável também não batesse. Adicionado `_relation_ids()` e o campo `Record.area_ids` (todas as áreas relacionadas), com `scope.in_scope` agora verificando qualquer uma delas. Após a correção, a auditoria passou a incluir 754 tarefas (antes 731) e 44 projetos (antes 39), confirmando a hipótese; achados de qualidade subiram de 16 para 27 porque mais registros passaram a entrar no recorte. Testes de regressão em `tests/test_scope.py` cobrem o caso de área alvo fora da primeira posição.
- Achado confirmado no Notion: a view "Tarefas · Visão geral" do Painel Operacional (`https://app.notion.com/p/df2c96f891e343bb820f96c09acfd932`) filtra `Responsável` por apenas 2 dos 6 IDs de `NOTION_TEAM_MEMBER_IDS` (mais o gestor). Os outros 4 membros da equipe não aparecem nesse board específico, então a comparação visual entre CLI e Notion pode divergir por configuração da própria view, não por erro da automação.

## Próxima validação gerencial

Antes de automatizar mensagens periódicas, revisar os 62 achados por amostragem e separar:

- falha real de preenchimento;
- registro que deveria estar concluído/arquivado;
- exceção legítima;
- regra que precisa ser ajustada.

Essa classificação evita transformar volume bruto em ruído operacional.
