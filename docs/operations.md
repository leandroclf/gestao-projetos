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

O `notify` manual publica uma mensagem por tipo de pendência. Nos ciclos automatizados (`--schedule` e `--progress-schedule`), as regras são consolidadas em um digest operacional: cada item aparece uma única vez, pela regra de maior prioridade, e os grupos continuam limitados a três exemplos por responsável. A thread padrão é `gestao-integracoes`. O caminho do estado é `GCHAT_ALERT_STATE_FILE`, com padrão `reports/gchat-alert-state.json`. Além da deduplicação de entregas, o estado registra o ciclo de vida de cada achado (`aberto`, `mantido`, `resolvido` ou `reaberto`) em `lifecycle`; esse histórico não altera o Notion. As mensagens iniciais podem ser publicadas com `notify --send --initial` e `notify --send --validation`.

O relatório gerencial é somente leitura e pode ser conferido com `PYTHONPATH=src python3 -m notion_management report`. No terminal, ele lista todas as tarefas e projetos em `Em Progresso`, `Bloqueada`, `Para ser aprovada` ou nos equivalentes de projetos `Doing`, `Blocked` e `TBA`, além dos assuntos e ações da COLTEC não concluídos sob responsabilidade do gestor. Cada item inclui responsável, status, prazo quando aplicável, data da última atividade/status, comentário mais recente e links. A seção de menções identifica comentários que mencionam o usuário configurado em `NOTION_MANAGER_ID`. O envio explícito com `report --send` usa exclusivamente `GCHAT_GERENCIAL_WEBHOOK_URL`, na thread `gestao-gerencial` por padrão, e publica apenas o resumo executivo com indicadores e até três exceções críticas.

O relatório também lista as demandas de clientes ativas da área de Integrações. Na seção de apoio à pauta, uma tarefa ou projeto pode ser sugerido para avaliação na COLTEC quando houver achado de bloqueio, aprovação, prazo vencido, atualização pendente ou menção ao gestor. Registros da COLTEC sob responsabilidade do gestor aparecem como candidatos para avaliar a criação de projeto ou tarefa após uma decisão. Essas são sugestões gerenciais; nenhuma alteração ou criação é feita automaticamente.

Regra transversal de identificação: toda tarefa em `Para ser aprovada` deve exibir o(s) aprovador(es) na mensagem de alerta e no relatório gerencial. Todo comentário exibido deve informar o autor registrado pelo Notion. Se o retorno da API não trouxer `created_by`, informar `Autor não identificado`; não inferir autoria pelo texto do comentário.

As mensagens operacionais e gerenciais são enviadas com cards `cardsV2`, cabeçalho de Gestão de Projetos e botões de abertura dos links. Para exibir o logo do projeto, configure `GCHAT_PROJECT_LOGO_URL` com uma URL HTTPS de imagem PNG ou JPEG. O envio divide relatórios grandes em blocos de até 8.000 caracteres para manter o payload, incluindo cards e markup, dentro do limite seguro do Google Chat.

Quando o relatório excede o limite seguro do webhook, a CLI envia vários blocos completos na mesma thread. A mensagem exibida no terminal permanece integral para conferência local.

Nas tarefas `Para ser aprovada`, o alerta `Aguardando aprovação` cobra do aprovador a inclusão das evidências dos testes nos comentários e o registro como feito caso os testes tenham sucesso. Nas tarefas `Bloqueada`, a automação lê as menções dos comentários e cobra o último mencionado no contexto do bloqueio para registrar avanço ou desbloqueio, mesmo que a menção seja de alguém fora da equipe de Integrações. Tarefas bloqueadas não geram alerta de prazo vencido nem caem no alerta genérico de atualização pendente. Cada item inclui seu link direto no Notion; sem menção identificável, a cobrança recai sobre o responsável da tarefa.

O alerta `Template incompleto` está desabilitado na fase 1 para evitar ruído durante a calibração dos critérios. A implementação permanece pronta para a fase 2; quando habilitada, será gerada para tarefas e projetos ativos em escopo com seções ausentes do template técnico ou, no projeto, sem a propriedade `Descrição`. Registros `Feito` não são avaliados nem alertados.

## Agendamento ativo no host

O timer de usuário `ops/systemd/gestao-projetos-alertas.timer` define o agendamento do host. A unidade é persistente e executa a última ocorrência perdida quando a máquina retorna. A rotina é:

1. executar `notify --send` nos ciclos definidos; a deduplicação impede repetição quando o conjunto de pendências não mudou;
2. executar `report --send` no mesmo ciclo diário, publicando o resumo executivo no espaço gerencial configurado; o acompanhamento completo permanece no Notion e na saída local;
3. armazenar `NOTION_TOKEN`, `GCHAT_WEBHOOK_URL` e `GCHAT_GERENCIAL_WEBHOOK_URL` no cofre de segredos do ambiente;
4. manter logs sem tokens, webhooks ou conteúdo sensível;
5. alertar quando a execução falhar, sem transformar falha técnica em mensagem falsa de saúde.

Manifesto do timer instalado no host:

```ini
OnCalendar=Mon..Fri *-*-* 08:00:00
Persistent=true
```

No host, o timer executa às 8h em dias úteis um único digest com os alertas `stale`, `overdue`, `approval_update_missing` e `blocked_follow_up`. Às terças e quintas, inclui `due_date_missing`. `urgent_without_project` está desabilitado na fase atual. O estado permanece persistido em `GCHAT_ALERT_STATE_FILE`.

O alerta `progress_update_missing` possui dois momentos de verificação, sempre de segunda a sexta no horário de Brasília. No ciclo da manhã, às **08:00**, ele considera somente tarefas em `Em Progresso` sem comentário no último dia útil. No ciclo da tarde, às **17:00**, pela unidade `ops/systemd/gestao-projetos-andamento.timer`, ele considera tarefas em `Em Progresso` sem comentário no dia atual, na thread `gestao-integracoes-andamento`. A separação evita cobrar o dia atual antes do início do expediente e mantém uma janela adequada para o registro do andamento durante o dia. A regra não substitui `stale`, que continua avaliando a cadência máxima de dois dias úteis.

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
