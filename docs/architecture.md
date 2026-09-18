# Arquitetura da automação

## Contexto

As fontes de entrada são tarefas e projetos técnicos, ações da COLTEC e solicitações de clientes. A equipe é dividida nas frentes IA, Directs e InterJus. O painel do Notion é a camada de consulta gerencial; o GChat é canal de alerta e coordenação.

## Decisões

### Leitura antes de escrita

A primeira versão somente consulta as bases e gera achados. Isso reduz o risco de alterar status, comentários ou relações de trabalho sem validação. Escritas futuras deverão ter comando explícito, idempotência e registro de auditoria.

### Adaptadores por canal

`notion_api.py` e `gchat.py` isolam protocolos externos do domínio. Assim, as regras de qualidade podem ser testadas sem rede e o GChat pode ser substituído por outro canal.

### Escopo antes dos indicadores

`service.py` normaliza os registros e aplica `scope.py` antes de chamar as regras de qualidade. Essa ordem é obrigatória: qualquer indicador, alerta ou snapshot precisa nascer do conjunto já filtrado. Os registros excluídos são contabilizados por fonte para permitir auditoria do recorte.

O recorte é configurável para a área e os membros, com Leandro mantido como responsável gestor. As regras específicas por fonte são:

- tarefas/projetos: relação com a área de Integrações ou responsável da equipe/Leandro;
- COLTEC: `Área = Integração` ou responsável Leandro;
- solicitações: `Time Responsável = HIVEPlace` ou atendente Leandro.

### Matriz de revisão de tarefas

As regras de qualidade de tarefa são deliberadamente restritas aos status ativos `Em Progresso`, `Bloqueada` e `Para ser aprovada`; tarefas `Feito` são excluídas antes da geração de qualquer achado:

| Regra | Critério |
| --- | --- |
| Dono | `Responsável` obrigatório nos quatro status controlados. |
| Prazo | `Prazo` obrigatório nos quatro status controlados. |
| Aprovação | `Aprovadora` deve conter ao menos uma pessoa em `Para ser aprovada`. |
| Atualização | Preferencialmente todos os dias úteis e, obrigatoriamente, no máximo a cada dois dias úteis até a conclusão; o registro deve estar nos comentários da tarefa. |
| Projeto | Relação `Projeto` é recomendada, mas não obrigatória. |
| Conclusão | Tarefa `Feito` sai do mapa de alertas e não gera achados. |

### Validação do template técnico

Tarefas ativas devem conter as seções `Motivação e Contexto`, `Critério de pronto` e `Anotações`. Projetos ativos devem conter a propriedade `Descrição` e as seções `Motivação e contexto`, `Definição de pronto e de sucesso`, `Aspectos críticos e condições de contorno`, `Outros pontos relevantes` e `Tarefas e desenvolvimento`. O resultado é o achado `template_incomplete`, destinado ao responsável, sem escrita no Notion. A geração desse alerta está desabilitada na fase 1 e será habilitada na fase 2. Status concluídos são excluídos dessa validação.

Para `Para ser aprovada`, a auditoria lê os comentários e procura evidências de teste/aprovação; o alerta `Aguardando aprovação` é destinado ao aprovador e orienta incluir evidências nos comentários e registrar como feito caso os testes tenham sucesso. Para `Bloqueada`, a auditoria lê as menções nos comentários e direciona a cobrança ao último mencionado no comentário de bloqueio — mesmo que seja alguém fora da equipe de Integrações, já que o bloqueio costuma depender de outra equipe —, pedindo avanço ou desbloqueio para levar a tarefa a `Feito`; sem menção identificável, a cobrança recai sobre o responsável da tarefa. Tarefas bloqueadas nunca caem no alerta genérico de atualização pendente nem geram alerta de prazo vencido. Os alertas carregam o link da tarefa e nunca escrevem no Notion.

O campo `last_edited_time` é usado como proxy da última atualização. Ele não comprova, sozinho, que a edição foi feita pelo responsável nem que foi um comentário. A validação completa da autoria e do conteúdo da atualização depende da leitura do histórico de comentários do Notion e permanece como evolução posterior.

### Configuração fora do código

IDs de bases, token e webhooks vêm de variáveis de ambiente. O `.env.example` documenta os nomes. A aplicação lê um `.env` local com um parser próprio de pares simples, sem executá-lo como shell; variáveis já presentes no ambiente têm precedência. `GCHAT_WEBHOOK_URL` é o destino operacional dos alertas; `GCHAT_GERENCIAL_WEBHOOK_URL` é o destino exclusivo do relatório gerencial.

### Identidade visual e renderização

Os tokens institucionais e as cores semânticas ficam centralizados em
`brand.py`; a lógica não deve espalhar hexadecimais. Cards recebem uma categoria
visual explícita, separando identidade da classificação operacional. O texto dos
widgets não usa cores HTML fixas: como o webhook não informa o tema do usuário,
o Google Chat precisa fornecer uma cor adaptativa para manter a leitura nos
temas claro e escuro. O texto de fallback permanece completo porque o webhook
não garante a mesma apresentação em todos os clientes do Google Chat. As regras
de voz, paleta, tipografia e estrutura de mensagem estão em
`docs/brand-communication.md`.

### Relatório gerencial

O comando `report` reutiliza a consulta, normalização e regra de escopo existentes, mas apresenta o resultado em seções gerenciais independentes:

- tarefas ativas em `Em Progresso`, `Bloqueada` e `Para ser aprovada`;
- projetos ativos em `Doing`, `Blocked` e `TBA`, além dos equivalentes em português;
- assuntos e ações da COLTEC não concluídos sob responsabilidade do gestor configurado em `NOTION_MANAGER_ID`;
- demandas de clientes nos status ativos da base de solicitações, dentro do escopo de Integrações;
- apoio à pauta e às decisões.

Cada atividade inclui responsável, status, prazo quando aplicável, data da última atividade/status, comentário mais recente e link direto. A data de atividade usa a propriedade configurada de última atualização e, quando ausente, o `last_edited_time` da página. O comentário mais recente é obtido pela API de discussões do Notion.

Quando uma tarefa está em `Para ser aprovada`, o relatório e os alertas exibem também o(s) responsável(is) pela aprovação (`Aprovadora`). Qualquer comentário apresentado por uma extração inclui o autor retornado em `created_by`; quando a API não informar o autor, a saída usa `Autor não identificado`.

A seção de menções identifica menções estruturadas ao ID de `NOTION_MANAGER_ID` nos comentários. As sugestões de pauta são candidatas geradas a partir de achados de bloqueio, aprovação, prazo, atualização ou menção ao gestor. Os registros da COLTEC sob responsabilidade do gestor são apresentados como candidatos a desdobramento em projeto/tarefa após confirmação da decisão. Essas sugestões não escrevem no Notion e não criam demandas automaticamente.

O webhook gerencial recebe um resumo executivo em uma thread própria (`gestao-gerencial`). O resumo apresenta indicadores e até três exceções críticas; o relatório completo continua disponível na saída local e no Notion. As mensagens são publicadas com texto de fallback e cards `cardsV2`, usando cabeçalho, logo opcional, cores por categoria e botão para abrir o primeiro link do registro. O webhook continua limitado ao espaço em que foi criado e não recebe respostas interativas.

O estado local de alertas mantém, por página e regra, o ciclo de vida do achado. A primeira ocorrência é `aberto`, repetições ficam `mantido`, a ausência em uma coleta posterior marca `resolvido` e o retorno de um achado resolvido marca `reaberto`. Esse histórico apoia a redução de ruído e futuras métricas de recuperação, sem substituir o histórico oficial dos comentários no Notion.

Nos ciclos agendados, o adaptador operacional consolida achados por página e mantém somente a regra de maior prioridade: bloqueio, prazo vencido, aprovação, atualização e demais pendências. Isso limita o canal da equipe a uma mensagem por ciclo, sem ocultar o detalhamento no Notion.

## Fluxo

```text
Notion API
   ↓
normalização de propriedades
   ↓
filtro de escopo gerencial
   ↓
regras de qualidade + indicadores
   ↓
relatório JSON/Markdown + snapshot local opcional
   ↓ (opcional: --send)
Google Chat webhook
```

## Limites da primeira versão

- Não cria projeto ou tarefa automaticamente.
- Não altera comentários nem propriedades.
- Não substitui as visões dinâmicas do Notion.
- O agendamento do host é mantido nas unidades versionadas em `ops/systemd/`.
- Webhook do GChat cobre publicação simples; leitura de espaços e autenticação avançada ficam para uma etapa posterior com credenciais próprias do Google Workspace.
