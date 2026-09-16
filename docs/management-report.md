# Relatório gerencial

## Objetivo

Dar ao gestor uma visão diária e somente leitura da situação das atividades de Integrações, das demandas de clientes, dos assuntos sob sua responsabilidade na COLTEC e dos pontos que podem exigir decisão ou desdobramento.

## Execução

```bash
# Conferir sem publicar
PYTHONPATH=src python3 -m notion_management report

# Publicar no espaço gerencial
PYTHONPATH=src python3 -m notion_management report --send
```

O envio usa `GCHAT_GERENCIAL_WEBHOOK_URL` e a thread `gestao-gerencial` por padrão. O webhook operacional (`GCHAT_WEBHOOK_URL`) não é usado pelo relatório. A publicação gerencial envia somente um resumo executivo compacto, com indicadores e até três exceções críticas; o relatório completo permanece disponível no terminal e no Notion. Como o card repete o texto com markup e botões, cada bloco usa um limite conservador de 8.000 caracteres para evitar rejeição por tamanho após o processamento do Google Chat. As mensagens usam cards `cardsV2` com o nome do projeto, logo opcional, formatação visual por categoria e botões para abrir os links; o campo `text` permanece como fallback.

São consideradas críticas as ocorrências de bloqueio, prazo vencido, aprovação pendente, aprovador ausente ou solicitação P0. Pendências de qualidade, como ausência de prazo ou template incompleto, não aparecem individualmente no canal gerencial; permanecem no relatório detalhado e nos alertas operacionais aplicáveis.

Configure `GCHAT_PROJECT_LOGO_URL` com uma URL HTTPS de uma imagem PNG ou JPEG quadrada para exibir a identidade visual no cabeçalho do card. O nome e o avatar do remetente principal continuam sendo configurados no cadastro do webhook dentro do espaço do Google Chat.

## Seções e critérios

### Acompanhamento de tarefas

Inclui tarefas no escopo de Integrações com status `Em Progresso`, `Bloqueada` ou `Para ser aprovada`. Exibe responsável, status, prazo, última atividade/status, comentário mais recente e link. Para tarefas `Para ser aprovada`, exibe também o campo `Aprovador(es)` com as pessoas da propriedade `Aprovadora`.

### Acompanhamento de projetos

Inclui projetos no escopo com status `Doing`, `Blocked`, `TBA` ou equivalentes em português. Exibe responsável, status, última atividade/status, comentário mais recente e link.

### COLTEC sob responsabilidade do gestor

Inclui registros não concluídos da fonte COLTEC cujo responsável é o usuário definido em `NOTION_MANAGER_ID`. Exibe os mesmos dados de acompanhamento, incluindo prazo quando disponível.

### Demandas de clientes

Inclui solicitações ativas dentro das regras de escopo da área de Integrações. O campo `Quem atende` é apresentado como responsável, `Prazo prometido ao cliente` como prazo e `Status da solicitação` como status.

### Apoio à pauta e às decisões

As sugestões são informativas e não alteram dados:

- **Sugestões de assuntos para levar à pauta da COLTEC:** tarefas e projetos com achados de bloqueio, aprovação pendente, prazo vencido ou atualização pendente, além de registros com menção estruturada ao gestor nos comentários.
- **Sugestões de demandas após decisões da COLTEC:** registros COLTEC não concluídos sob responsabilidade do gestor, para confirmar se a decisão exige criação de projeto ou tarefa para a equipe.

O relatório não interpreta uma sugestão como decisão, não cria projeto/tarefa e não altera status, propriedades ou comentários.

## Identidade da mensagem

O relatório usa o posicionamento digital da HIVEPlace e a paleta centralizada em
`src/notion_management/brand.py`. O cabeçalho usa o nome do relatório, logo
opcional e categoria `management_report`; o corpo mantém o texto de fallback e
links acionáveis. A comunicação é objetiva e orientada à decisão, sem atribuir
culpa. O padrão completo está em `docs/brand-communication.md`.

## Menções ao gestor

A seção de itens mencionados verifica as menções estruturadas nos comentários por meio do ID configurado em `NOTION_MANAGER_ID`. Texto comum contendo o nome do gestor, sem uma menção de usuário do Notion, não é tratado como notificação confiável.

## Agendamento

O serviço `ops/systemd/gestao-projetos-alertas.service` executa os alertas operacionais e o relatório gerencial no ciclo diário do timer de dias úteis às 8h. Depois de instalar ou alterar a unidade, recarregue a configuração do usuário:

```bash
systemctl --user daemon-reload
```

## Limites conhecidos

- `last_edited_time` é uma aproximação da última atividade quando não há propriedade de atualização preenchida; não comprova autoria nem que a alteração foi comentário.
- Comentários são resumidos em até 500 caracteres por item para manter legibilidade.
- A autoria vem do campo `created_by` retornado pelo Notion. Se esse campo não estiver disponível, o relatório informa `Autor não identificado`.
- O relatório depende de a integração ter acesso às páginas e aos comentários das quatro fontes.
- Registros COLTEC fora do escopo ou sem o gestor como responsável não entram na seção de responsabilidade, embora possam ser considerados na auditoria geral conforme a regra de escopo.
