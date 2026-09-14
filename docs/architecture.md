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

Tarefas ativas devem conter as seções `Motivação e Contexto`, `Critério de pronto` e `Anotações`. Projetos ativos devem conter a propriedade `Descrição` e as seções `Motivação e contexto`, `Definição de pronto e de sucesso`, `Aspectos críticos e condições de contorno`, `Outros pontos relevantes` e `Tarefas e desenvolvimento`. O resultado é o achado `template_incomplete`, destinado ao responsável, sem escrita no Notion. Status concluídos são excluídos dessa validação.

Para `Para ser aprovada`, a auditoria lê os comentários e procura evidências de teste/aprovação; o alerta `Aguardando aprovação` é destinado ao aprovador e orienta incluir evidências nos comentários e registrar como feito caso os testes tenham sucesso. Para `Bloqueada`, a auditoria lê as menções nos comentários e direciona a cobrança ao último membro da equipe mencionado, pedindo avanço ou desbloqueio para levar a tarefa a `Feito`; tarefas bloqueadas não geram alerta de prazo vencido. Os alertas carregam o link da tarefa e nunca escrevem no Notion.

O campo `last_edited_time` é usado como proxy da última atualização. Ele não comprova, sozinho, que a edição foi feita pelo responsável nem que foi um comentário. A validação completa da autoria e do conteúdo da atualização depende da leitura do histórico de comentários do Notion e permanece como evolução posterior.

### Configuração fora do código

IDs de bases, token e webhook vêm de variáveis de ambiente. O `.env.example` documenta os nomes. A aplicação lê um `.env` local com um parser próprio de pares simples, sem executá-lo como shell; variáveis já presentes no ambiente têm precedência.

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
- Não ativa agendamento externo por conta própria.
- Webhook do GChat cobre publicação simples; leitura de espaços e autenticação avançada ficam para uma etapa posterior com credenciais próprias do Google Workspace.
