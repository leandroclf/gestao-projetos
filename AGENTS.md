# Instruções do projeto — Automação Notion/GChat

## Escopo

Este arquivo é a memória operacional local do codebase `gestao-projetos`. Ele orienta agentes que continuarem o trabalho em novas conversas. Use a raiz do repositório (`.`) e caminhos relativos; não dependa do diretório local usado em uma máquina específica. O projeto é uma automação independente da equipe de Integrações.

## Objetivo do produto

Consolidar informações gerenciais do Notion e publicar alertas opcionais no Google Chat para apoiar o acompanhamento da equipe de Integrações.

O Notion permanece como fonte oficial para:

- tarefas técnicas;
- projetos;
- ações, decisões e riscos da COLTEC;
- solicitações de clientes.

Comentários dentro da tarefa, projeto ou solicitação são a linha do tempo oficial. O Google Chat é canal de alerta e coordenação rápida; não deve substituir o histórico do Notion.

## Estado atual

- A primeira versão é somente leitura no Notion.
- O auditor calcula achados de qualidade e não altera status, propriedades, relações, comentários ou conteúdo.
- O envio ao GChat é explícito e exige `notify --send`; a thread padrão é `gestao-integracoes`.
- O webhook do Google Chat foi validado com uma mensagem real.
- Os testes unitários cobrem qualidade, escopo, normalização e snapshot; devem ser executados antes de qualquer entrega.
- A integração do Notion usada localmente é identificada como `Automação`.
- A auditoria real já conseguiu consultar as quatro fontes configuradas; o recorte atual pode resultar em zero registros COLTEC quando nenhum dos dois registros atende às regras de Integração/Leandro.
- Nunca registrar tokens, URLs de webhook, chaves, arquivos de credencial ou valores do `.env` neste arquivo, no README ou em commits.

## Organização do código

```text
src/notion_management/
  __main__.py      entrada para python -m notion_management
  cli.py           comandos audit e notify
  config.py        ambiente, parser seguro do .env e IDs das fontes
  models.py        Record, Finding e AuditReport
  notion_api.py    cliente HTTP do Notion, paginação e leitura de comentários
  quality.py       regras de qualidade e status ativos
  service.py       normalização, consulta, filtragem e relatório
  scope.py         regra única de recorte da área de Integrações
  snapshot.py      baseline JSON datado
  gchat.py         publicação simples via webhook e agrupamento opcional por thread
tests/
  test_quality.py  testes unitários sem rede
  test_scope.py    escopo, normalização, snapshot e thread do GChat
docs/
  architecture.md  decisões e limites da solução
  operations.md    execução, baseline e critérios de agendamento
```

## Fontes e escopo gerencial

Os IDs e nomes técnicos das fontes ficam no `.env.example` e em `config.py`. Não duplicar esses valores em outros módulos. A regra reutilizável de inclusão está em `scope.py`.

O painel gerencial do Notion está organizado em três níveis:

1. **Executivo** — decisões, riscos, ações COLTEC, prioridades críticas e compromissos externos.
2. **Gestão da Equipe** — capacidade, responsáveis, bloqueios, projetos e qualidade do fluxo.
3. **Operacional** — filas, tarefas por frente, solicitações e atualização diária.

Ao criar ou alterar indicadores no Notion:

- tarefas e projetos devem ser filtrados pela relação da área de Integrações ou por responsável da equipe/gestor;
- registros COLTEC devem usar `Área = Integração` ou o gestor como responsável;
- solicitações de clientes devem usar `Time Responsável = HIVEPlace` ou o gestor como atendente;
- qualquer auditoria local deve aplicar essas mesmas regras antes de gerar indicadores, alertas ou snapshots;
- o relatório deve preservar a contagem de registros excluídos por fonte para facilitar a conferência do recorte;
- visões por frente devem restringir os responsáveis à respectiva frente;
- qualquer visão antiga preservada deve receber o mesmo filtro ou permanecer identificada como legada;
- não usar contagens fixas em texto quando uma visão dinâmica puder representar o dado.

### Regras obrigatórias de revisão de tarefas

Aplicar somente aos status `Em Progresso`, `Bloqueada`, `Para ser aprovada` e `Feito`:

- `Responsável` é obrigatório;
- `Prazo` é obrigatório;
- `Para ser aprovada` exige ao menos uma pessoa em `Aprovadora`;
- toda tarefa deve receber atualização do responsável preferencialmente todos os dias úteis e, obrigatoriamente, no máximo a cada dois dias úteis até sua conclusão;
- tarefas sem `Projeto` são permitidas e não devem gerar achado;
- tarefas `Feito` não precisam continuar recebendo atualização, mas continuam exigindo dono e prazo.

As atualizações devem ser registradas nos comentários da tarefa, contendo evolução, impedimento, evidência ou próximo passo. O auditor usa `last_edited_time` como aproximação da última atualização. Não afirmar que a atualização foi feita pelo responsável ou que ocorreu em comentário sem consultar o histórico de discussões do Notion.

### Regras específicas de alertas

- tarefas `Para ser aprovada` devem ter comentário com evidências dos testes de aprovação; a cobrança é direcionada ao aprovador, não ao responsável da execução;
- o alerta `Aguardando aprovação` deve orientar: incluir evidências dos testes nos comentários e registrar como feito caso sucesso nos testes;
- tarefas `Bloqueada` não geram alerta de prazo vencido;
- tarefas `Bloqueada` consultam os comentários da tarefa; a cobrança é direcionada ao último membro da equipe mencionado no contexto do bloqueio, solicitando avanço ou desbloqueio até a conclusão;
- os alertas incluem o link direto da tarefa;
- se não houver membro identificável no comentário do bloqueio, a cobrança permanece com o responsável da tarefa;
- a leitura de comentários é somente leitura e não altera o histórico oficial.

## Configuração

Copie `.env.example` para `.env` e preencha o token do Notion, a versão da API e, opcionalmente, o webhook do GChat. A aplicação lê o arquivo automaticamente com parser próprio; não use `source .env`, porque URLs de webhook podem conter caracteres interpretados pelo shell.

O arquivo `.env` deve permanecer local e ter permissão restrita, preferencialmente `600`.

O token do Notion precisa ter acesso às bases de tarefas, projetos, COLTEC e solicitações. Um erro `404 object_not_found` mencionando uma base normalmente significa que a base não foi compartilhada com a integração, não necessariamente que o ID está errado.

## Comandos

Execute a partir da raiz do projeto:

```bash
PYTHONPATH=src python3 -m notion_management audit
PYTHONPATH=src python3 -m notion_management audit --json
PYTHONPATH=src python3 -m notion_management notify
PYTHONPATH=src python3 -m notion_management notify --send
PYTHONPATH=src python3 -m notion_management snapshot
```

`audit` exibe o relatório sem envio. `notify` exibe somente pendências acionáveis; `notify --send` publica no Google Chat. Use `notify --send --initial` e `notify --send --validation` apenas para a implantação inicial.
`snapshot` executa a mesma auditoria filtrada e salva um JSON datado em `NOTION_SNAPSHOT_DIR` (padrão: `reports/snapshots/`). O `notify` aceita `--thread-key` para agrupar mensagens em uma thread estável.

## Validação obrigatória

Antes de entregar alterações:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B -m unittest discover -s tests -v
```

Também é aceitável validar a sintaxe com AST da biblioteca padrão. Não afirmar que uma consulta real passou se as credenciais ou permissões não permitirem acesso às bases.

## Segurança e operação

- Não imprimir segredo, token ou URL de webhook nos logs.
- Não executar `source .env`.
- Não adicionar dependências sem autorização explícita.
- Não habilitar escrita automática no Notion sem idempotência, modo `--apply`, confirmação e trilha de auditoria.
- Não criar tarefas/projetos automaticamente apenas porque uma solicitação parece relevante; primeiro gerar sugestão ou relatório.
- Não alterar comentários: eles são parte do histórico oficial da demanda.
- Tratar rate limit, timeout, 401, 403 e 404 com mensagens acionáveis.
- Webhook é unidirecional e específico do espaço onde foi criado. Para ler mensagens, responder comandos ou operar múltiplos espaços com maior controle, será necessária uma Google Chat App com API/OAuth e permissões próprias.

## Próximos incrementos aprováveis

Implementar em etapas pequenas e verificáveis:

1. Comparar a auditoria filtrada e os primeiros snapshots com os painéis dinâmicos do Notion.
2. Consultar o histórico de comentários para validar autoria e conteúdo das atualizações.
3. Implementar validação dos templates de projeto e tarefa em modo somente leitura.
4. Criar modo de sugestões de correção, sem aplicar alterações.
5. Definir templates de mensagens e chaves de thread por tipo de alerta.
6. Adicionar agendamento em ambiente autorizado.
7. Somente depois avaliar escrita controlada e integração completa com Google Chat API.

## Regras de continuidade

- Ler este arquivo, `README.md` e `docs/architecture.md` antes de mudar o fluxo.
- Preservar o layout `src` e a ausência de dependências obrigatórias.
- Manter adaptadores externos isolados da lógica em `quality.py`.
- Preferir mudanças pequenas, testadas e reversíveis.
- Ao mudar um indicador do Notion, validar a propriedade e o filtro na base antes de atualizar a visão.
- Documentar cada novo requisito de permissão, escrita ou agendamento.
