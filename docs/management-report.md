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

O envio usa `GCHAT_GERENCIAL_WEBHOOK_URL` e a thread `gestao-gerencial` por padrão. O webhook operacional (`GCHAT_WEBHOOK_URL`) não é usado pelo relatório. A publicação é dividida em mensagens sequenciais quando necessário para preservar o relatório completo.

## Seções e critérios

### Acompanhamento de tarefas

Inclui tarefas no escopo de Integrações com status `Em Progresso`, `Bloqueada` ou `Para ser aprovada`. Exibe responsável, status, prazo, última atividade/status, comentário mais recente e link.

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
- O relatório depende de a integração ter acesso às páginas e aos comentários das quatro fontes.
- Registros COLTEC fora do escopo ou sem o gestor como responsável não entram na seção de responsabilidade, embora possam ser considerados na auditoria geral conforme a regra de escopo.
