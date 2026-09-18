# Gestão da equipe de Integrações

Automação independente para consolidar tarefas, projetos, ações COLTEC e solicitações de clientes do Notion, com notificação opcional no Google Chat.

## Princípios

- Notion continua sendo a fonte oficial dos registros.
- Comentários e conteúdo das páginas não são alterados pelo auditor.
- A execução padrão é somente leitura e produz achados verificáveis.
- O envio ao GChat é opt-in, usando `--send`.
- Operações futuras de escrita deverão ser idempotentes, auditáveis e protegidas por `--apply`.

## Configuração

```bash
cp .env.example .env
# preencha NOTION_TOKEN; opcionalmente preencha os webhooks do Google Chat
PYTHONPATH=src python3 -m notion_management audit
PYTHONPATH=src python3 -m notion_management audit --json
PYTHONPATH=src python3 -m notion_management notify --send
PYTHONPATH=src python3 -m notion_management snapshot
PYTHONPATH=src python3 -m notion_management report
PYTHONPATH=src python3 -m notion_management doctor
PYTHONPATH=src python3 -m notion_management deliveries
PYTHONPATH=src python3 -m notion_management run --send
```

Como o projeto usa layout `src`, execute os comandos a partir da raiz com `PYTHONPATH=src` quando não estiver instalado como pacote:

```bash
PYTHONPATH=src python3 -m notion_management audit
PYTHONPATH=src python3 -m notion_management notify --send
```

O token não deve ser commitado. A CLI lê o `.env` local sem executá-lo como shell, o que também suporta URLs de webhook com caracteres especiais. A integração do Notion precisa ter acesso às quatro fontes configuradas no `.env.example`.

`notify` gera somente alertas de pendências acionáveis no escopo da equipe. Os alertas são separados por tipo, agrupados por responsável e limitados a três exemplos por responsável. O arquivo `GCHAT_ALERT_STATE_FILE` guarda uma impressão digital por tipo para evitar reenvio quando nada mudou. Use `--initial` e `--validation` para as mensagens de implantação inicial; use `--force` somente para validar ou reenviar alertas conscientemente.

Todas as auditorias aplicam escopo antes de calcular indicadores: tarefas e projetos entram pela área de Integrações ou por responsável da equipe/Leandro; COLTEC entra por `Área = Integração` ou Leandro; solicitações entram por `Time Responsável = HIVEPlace` ou Leandro. O relatório também informa quantos registros foram excluídos por fonte. O diretório de snapshots é configurado por `NOTION_SNAPSHOT_DIR` e, por padrão, fica em `reports/snapshots/`.

## Estrutura

```text
src/notion_management/
  cli.py          # comandos audit e notify
  management_report.py # relatório gerencial de tarefas, projetos e menções
  config.py       # ambiente e IDs das fontes
  models.py       # entidades e achados normalizados
  notion_api.py   # cliente HTTP somente leitura nesta fase
  gchat.py        # webhook opcional
  quality.py      # regras de qualidade e indicadores
  scope.py        # recorte gerencial da equipe de Integrações
  service.py      # orquestração da auditoria
  snapshot.py     # persistência local de baselines JSON
tests/
  test_quality.py
  test_scope.py
docs/
  architecture.md
```

## Documentação completa

Para uma visão consolidada das capacidades, fluxos, regras, estados de entrega,
agendamento, configuração e limites, consulte o
[`docs/system-overview.md`](docs/system-overview.md). O documento inclui
diagramas Mermaid de contexto, coleta, escopo, auditoria, alertas, relatório e
operação agendada.

## Indicadores calculados

O relatório calcula volume por fonte, status, responsável, itens sem prazo, aprovação pendente, bloqueios, P0, compromissos vencidos e cadência de atualização. As regras de tarefa são aplicadas somente nos status ativos `Em Progresso`, `Bloqueada` e `Para ser aprovada`:

- responsável obrigatório nesses quatro status;
- prazo obrigatório nesses quatro status;
- pelo menos uma `Aprovadora` quando o status for `Para ser aprovada`;
- atualização do responsável preferencialmente todos os dias úteis e, obrigatoriamente, no máximo a cada dois dias úteis até a conclusão;
- atualização registrada nos comentários da tarefa, com evolução, impedimento, evidência ou próximo passo;
- tarefa sem projeto é permitida e não gera achado;
- tarefa `Feito` sai do mapa de alertas e não gera nenhum achado, pois já foi concluída.

Tarefas e projetos ativos também podem ser verificados contra o template técnico. Tarefas devem conter as seções `Motivação e Contexto`, `Critério de pronto` e `Anotações`. Projetos devem conter a propriedade `Descrição` e as seções `Motivação e contexto`, `Definição de pronto e de sucesso`, `Aspectos críticos e condições de contorno`, `Outros pontos relevantes` e `Tarefas e desenvolvimento`. A validação e o alerta `Template incompleto` estão desabilitados na fase 1 e serão habilitados somente na fase 2.

Os valores devem ser comparados com as visões dinâmicas do [Painel de Gestão — Equipe de Integrações](https://app.notion.com/p/3d99821c9b7681538173ddf48d2fef79).

## Operação recomendada

Para acompanhar tendência, execute `snapshot` uma vez por período em um ambiente autorizado. O comando é local e somente leitura no Notion. Para publicar um resumo manual no espaço configurado, use `notify --send`; para agrupar alertas em uma conversa do Google Chat, informe `--thread-key <chave-estavel>`.

Para gerar o relatório gerencial completo, execute `PYTHONPATH=src python3 -m notion_management report`. O relatório inclui tarefas e projetos ativos, assuntos/ações da COLTEC sob responsabilidade do gestor, status, prazo quando aplicável, data da última atividade/status, comentário mais recente, uma visão diária de itens sem alertas agrupados por frente, concluídos/avanços, próximos passos, backlog e foco inferido do ciclo, além de uma seção com comentários que mencionaram o gestor configurado em `NOTION_MANAGER_ID`. Para enviar ao espaço gerencial, use `report --send`; o destino é `GCHAT_GERENCIAL_WEBHOOK_URL` e a thread padrão é `gestao-gerencial`. Alertas e relatórios são enviados com cards visuais e links acionáveis; configure `GCHAT_PROJECT_LOGO_URL` para exibir a logo do projeto.

Use `doctor` para validar configuração local sem consultar o Notion. Use `deliveries` para inspecionar estados `pending`, `sent` e `unknown`. Use `run` para realizar uma única coleta, persistir o snapshot e compartilhar o mesmo `run_id` entre alertas e relatório; publicações são bloqueadas quando alguma fonte falha.

O agendamento do host está definido em `ops/systemd/gestao-projetos-alertas.timer`, com armazenamento seguro das variáveis do `.env`, logs no journal, timeout, retry e controle de duplicidade. CI e outros schedulers não são ativados por este repositório.

## Identidade visual e comunicação

Alertas e relatórios usam cards com a identidade digital da HIVEPlace, categorias
semânticas, links acionáveis e linguagem objetiva orientada à próxima ação. As
regras de voz, paleta, tipografia e revisão estão em
[`docs/brand-communication.md`](docs/brand-communication.md). Os tokens visuais
ficam centralizados em `src/notion_management/brand.py`.

No host definido para esta operação, o systemd timer executa os alertas gerais diariamente em dias úteis às 8h e inclui `due_date_missing` adicionalmente às terças e quintas. O alerta `progress_update_missing` é verificado em dois ciclos: às 8h, somente para tarefas `Em Progresso` sem comentário no último dia útil; e às 17h, para tarefas sem comentário no dia atual. A cobrança da manhã não considera a ausência de comentário do próprio dia, pois o expediente ainda está começando. `urgent_without_project` e `template_incomplete` permanecem desabilitados na fase atual.

## Próximos incrementos seguros

1. Validar os snapshots por algumas semanas contra os painéis dinâmicos do Notion.
2. Implementar validação dos templates de projeto e tarefa, começando em modo somente leitura.
3. Criar sugestões de roteamento por frente e vínculo de solicitações com projetos/tarefas.
4. Definir e aprovar templates de mensagens antes de ativar alertas periódicos.
5. Agendar `snapshot`/`notify` em um ambiente autorizado.
6. Somente depois avaliar escritas controladas no Notion e uma Google Chat App com API/OAuth.
