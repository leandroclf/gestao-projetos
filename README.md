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
# preencha NOTION_TOKEN; opcionalmente preencha GCHAT_WEBHOOK_URL
PYTHONPATH=src python3 -m notion_management audit
PYTHONPATH=src python3 -m notion_management audit --json
PYTHONPATH=src python3 -m notion_management notify --send
PYTHONPATH=src python3 -m notion_management snapshot
```

Como o projeto usa layout `src`, execute os comandos a partir da raiz com `PYTHONPATH=src` quando não estiver instalado como pacote:

```bash
PYTHONPATH=src python3 -m notion_management audit
PYTHONPATH=src python3 -m notion_management notify --send
```

O token não deve ser commitado. A CLI lê o `.env` local sem executá-lo como shell, o que também suporta URLs de webhook com caracteres especiais. A integração do Notion precisa ter acesso às quatro fontes configuradas no `.env.example`.

Todas as auditorias aplicam escopo antes de calcular indicadores: tarefas e projetos entram pela área de Integrações ou por responsável da equipe/Leandro; COLTEC entra por `Área = Integração` ou Leandro; solicitações entram por `Time Responsável = HIVEPlace` ou Leandro. O relatório também informa quantos registros foram excluídos por fonte. O diretório de snapshots é configurado por `NOTION_SNAPSHOT_DIR` e, por padrão, fica em `reports/snapshots/`.

## Estrutura

```text
src/notion_management/
  cli.py          # comandos audit e notify
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

## Indicadores calculados

O relatório calcula volume por fonte, status, responsável, itens sem prazo, aprovação pendente, bloqueios, P0, compromissos vencidos e cadência de atualização. As regras de tarefa são aplicadas somente nos status `Em Progresso`, `Bloqueada`, `Para ser aprovada` e `Feito`:

- responsável obrigatório nesses quatro status;
- prazo obrigatório nesses quatro status;
- pelo menos uma `Aprovadora` quando o status for `Para ser aprovada`;
- atualização do responsável em no máximo dois dias úteis para tarefas não concluídas;
- atualização do responsável no último dia útil para tarefas `Bloqueada`;
- tarefa sem projeto é permitida e não gera achado;
- tarefa `Feito` não é cobrada por atualização, pois já foi concluída.

Os valores devem ser comparados com as visões dinâmicas do [Painel de Gestão — Equipe de Integrações](https://app.notion.com/p/3d99821c9b7681538173ddf48d2fef79).

## Operação recomendada

Para acompanhar tendência, execute `snapshot` uma vez por período em um ambiente autorizado. O comando é local e somente leitura no Notion. Para publicar um resumo manual no espaço configurado, use `notify --send`; para agrupar alertas em uma conversa do Google Chat, informe `--thread-key <chave-estavel>`.

O agendamento deve ser configurado posteriormente no ambiente operacional escolhido, com armazenamento seguro das variáveis do `.env`, logs sem segredos, timeout, retry e controle de duplicidade. Este repositório não ativa cron, CI ou qualquer scheduler automaticamente.

## Próximos incrementos seguros

1. Validar os snapshots por algumas semanas contra os painéis dinâmicos do Notion.
2. Implementar validação dos templates de projeto e tarefa, começando em modo somente leitura.
3. Criar sugestões de roteamento por frente e vínculo de solicitações com projetos/tarefas.
4. Definir e aprovar templates de mensagens antes de ativar alertas periódicos.
5. Agendar `snapshot`/`notify` em um ambiente autorizado.
6. Somente depois avaliar escritas controladas no Notion e uma Google Chat App com API/OAuth.
