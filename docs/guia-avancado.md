# Guia avançado de evolução — Gestão de Projetos

Análise técnica e plano de implementação • 15 de setembro de 2026

Repositório: https://github.com/leandroclf/gestao-projetos  
Referência analisada: `d8cee64160d51c804786b2583068afbcbb6018d5` (árvore retornada para main).  
Escopo: código Python, testes, configuração de empacotamento, documentação arquitetural e operacional e unidades systemd. Os materiais binários de marca não foram auditados. Não houve alteração do repositório remoto, acesso ao host operacional ou envio ao Google Chat.

## 1. Direção recomendada

Evoluir o projeto como uma camada confiável de acompanhamento gerencial sobre o Notion. Seu valor está em transformar registros em decisões e próximos passos verificáveis: identificar bloqueios, reduzir espera por aprovação, acompanhar compromissos e preparar a pauta da liderança.

A próxima entrega deve corrigir a semântica dos achados e a confiabilidade da publicação. Acrescentar IA, dashboards ou novas cobranças antes disso amplificaria sinais incorretos. A arquitetura atual de aplicação Python modular é adequada ao escopo observado; não há evidência que justifique microserviços, Kubernetes ou uma plataforma distribuída nesta etapa.

Preservar quatro decisões já estabelecidas: Notion como fonte oficial; comentários como histórico; escopo aplicado antes dos indicadores; publicação explicitamente habilitada. As recomendações deste guia são propostas, não funcionalidades implementadas ou decisões já aprovadas.

## 2. Estado real e maturidade

| Área | Evidência observada | Avaliação |
|---|---|---|
| Produto | Tarefas, projetos, COLTEC e solicitações de clientes | Escopo gerencial claro |
| Arquitetura | Adaptadores Notion/GChat e regras separadas | Boa base para evolução incremental |
| Segurança operacional | Leitura no Notion, envio com `--send`, parser de `.env` sem shell | Princípios adequados |
| Qualidade | 41 testes unitários executados com sucesso | Cobertura útil, mas faltam jornadas e falhas |
| Integração Notion | Paginação e timeout HTTP | Sem retry ou classificação operacional de erros |
| Alertas | Agrupamento e fingerprint por regra; escrita atômica do JSON | Lacunas no ciclo de vida e recuperação |
| Operação | Service com `flock`; timer em dias úteis | Configuração versionada; instalação real não verificada |
| Histórico | Snapshot JSON por dia | Sobrescreve execuções do mesmo dia; sem metadados de execução |
| CI | Nenhum workflow na árvore consultada | Automação de validação proposta |

Fontes internas: [arquitetura](https://github.com/leandroclf/gestao-projetos/blob/d8cee64160d51c804786b2583068afbcbb6018d5/docs/architecture.md), [instruções do projeto](https://github.com/leandroclf/gestao-projetos/blob/d8cee64160d51c804786b2583068afbcbb6018d5/AGENTS.md) e [código](https://github.com/leandroclf/gestao-projetos/tree/d8cee64160d51c804786b2583068afbcbb6018d5/src/notion_management).

## 3. Achados prioritários

Prioridades: P0 = corrigir antes de ampliar a operação; P1 = próximo ciclo; P2 = evolução após estabilização. A classificação expressa risco técnico proposto, sem alegar incidentes já ocorridos.

| ID | Prioridade | Achado e evidência | Consequência | Correção proposta |
|---|---|---|---|---|
| A01 | P0 | `cli.py`: `audit` sem JSON cai no ramo que acessa `args.rules`, ausente nesse subcomando; reproduzido | Comando documentado falha | Separar explicitamente os quatro comandos e testar seus caminhos |
| A02 | P0 | `quality.py`: qualquer comentário contendo `teste` ou `aprov` satisfaz a evidência; comentário antigo “teste não realizado” suprimiu o alerta | Pendência de aprovação fica invisível | Evidência do ciclo atual, autoria elegível, resultado explícito e referência verificável |
| A03 | P0 | `alerting.py`: estado da regra não é limpo quando não há achados; aberto → resolvido → reaberto gerou apenas um envio | Reincidência pode não avisar a equipe | Persistir ciclo de vida por achado e registrar resolução |
| A04 | P0 | Fingerprint não inclui destinatário; troca A → B produziu o mesmo hash | Redirecionamento pode ser suprimido | Hash semântico com destinatário, política, destino e fatos relevantes |
| A05 | P0 | Fingerprint é persistido antes do HTTP; exceções tratadas removem estado, mas interrupção abrupta entre persistência e envio não | Possível perda silenciosa de publicação | Estados pending/sending/sent/unknown e recuperação explícita |
| A06 | P1 | `notion_api.py` encapsula erro sem retry; pausa por `Retry-After` ausente | Falha transitória interrompe o ciclo | Política central de retry com orçamento e erros acionáveis |
| A07 | P1 | `service.py` reduz timestamps de comentários a `date` | Comentários do mesmo dia podem ser escolhidos incorretamente como mais recentes | Preservar datetime com timezone e ID do comentário |
| A08 | P1 | Atualização usa edição da página, mas o texto acusa ausência de atualização do responsável | Afirmação sem prova de autoria/conteúdo | Separar atualização da página de comentário elegível do responsável |
| A09 | P1 | Leitura de templates depende de `row.get('has_children')` em objeto de página | Conteúdo pode ser ignorado e gerar falsos achados | Consultar filhos da página quando política habilitada; testar payload realista |
| A10 | P1 | `split_management_report` aceita bloco único maior que seu limite; 9.000 caracteres permaneceram em uma parte | Divisão não garante payload válido | Dividir dentro de blocos e validar tamanho do JSON final |
| A11 | P1 | `notify` não usa o particionamento do relatório | Muitos responsáveis podem gerar mensagem grande | Pipeline comum de renderização, particionamento e entrega |
| A12 | P1 | Service encadeia notify e report com `&&`; cada comando consulta novamente o Notion | Falha do alerta impede relatório; dados podem divergir entre consultas | Uma coleta por execução, destinos com estados independentes |

Evidências: [CLI](https://github.com/leandroclf/gestao-projetos/blob/d8cee64160d51c804786b2583068afbcbb6018d5/src/notion_management/cli.py), [regras](https://github.com/leandroclf/gestao-projetos/blob/d8cee64160d51c804786b2583068afbcbb6018d5/src/notion_management/quality.py), [alertas](https://github.com/leandroclf/gestao-projetos/blob/d8cee64160d51c804786b2583068afbcbb6018d5/src/notion_management/alerting.py), [serviço de coleta](https://github.com/leandroclf/gestao-projetos/blob/d8cee64160d51c804786b2583068afbcbb6018d5/src/notion_management/service.py), [relatório](https://github.com/leandroclf/gestao-projetos/blob/d8cee64160d51c804786b2583068afbcbb6018d5/src/notion_management/management_report.py).

Há também divergências documentais: referências a “quatro status” convivem com três status ativos e isenção de `Feito`; o README apresenta implementação/agendamento como próximos passos apesar de já existirem componentes correspondentes. A validação de templates já existe e gera achados na auditoria; o envio desses alertas é que está desabilitado. Atualizar o roadmap para distinguir implementado, desabilitado e não implementado.

## 4. Boas práticas pesquisadas e aplicação

### 4.1 Integrações resilientes

A documentação atual do Notion prevê limites por conexão e por workspace, com tratamento de 429 e 529 e respeito a `Retry-After`. O limite varia conforme plano; evitar assumir universalmente três requisições por segundo. Centralizar backoff, jitter e tentativas máximas. [Notion — limites de requisição](https://developers.notion.com/reference/request-limits).

Aplicação proposta: injetar transporte, relógio e espera no cliente; testar sem rede e sem sleeps reais. Definir prazo total por coleta. Repetir consultas POST apenas por sua semântica de leitura conhecida, sem generalizar essa política a futuras escritas. Falhas de credencial, permissão e schema devem interromper o fluxo com diagnóstico sanitizado. Dados parciais devem carregar indicação explícita de incompletude e não produzir cobrança como se a ausência estivesse comprovada.

### 4.2 Contratos de dados explícitos

O conteúdo de uma página Notion é consultado como blocos; o objeto de página descreve propriedades e metadados. Isso sustenta a revisão do uso de `has_children` na coleta de templates. [Notion — objeto Page](https://developers.notion.com/reference/page).

Criar diagnóstico de schema por fonte: propriedades necessárias, tipos esperados, opções de status reconhecidas e permissões. Usar IDs de propriedades quando apropriado, com mapa legível para operação. Status desconhecido deve aparecer como incompatibilidade, nunca desaparecer silenciosamente. Unificar vocabulário usado por `quality.py` e `service.py`, preservando diferenças intencionais entre backlog, execução e relatório gerencial.

### 4.3 Publicação e interatividade

Webhooks de entrada do Google Chat são adequados a notificações unidirecionais; uma experiência com comandos e interação exige evolução para um aplicativo. Manter webhook enquanto a necessidade for publicação. [Google Chat — webhooks](https://developers.google.com/workspace/chat/quickstart/webhooks).

Não prometer entrega exatamente uma vez com o mecanismo atual. Um timeout pode ocorrer após o servidor aceitar a mensagem. Registrar entrega ambígua e definir reconciliação ou reenvio consciente. Chave de thread organiza conversas, mas não é comprovante de deduplicação. Validar contratos de threading e limites no sandbox do Workspace antes de alterar o adaptador.

### 4.4 Observabilidade que ajuda a agir

A orientação SRE enfatiza sinais úteis e alertas acionáveis. Para este batch, o principal sinal é a execução completa e recente, além da entrega, e não a mera existência de logs. [Google SRE — monitoramento](https://sre.google/sre-book/monitoring-distributed-systems/).

Proposta: cada execução recebe `run_id`, instante inicial/final, versão do código, versão das regras, contagens por fonte, duração, retries e resultado por destino. Um monitor externo deve detectar ausência de execução; falha do processo não pode depender exclusivamente do próprio processo para ser percebida.

### 4.5 Métricas de entrega sem confundir atividade com resultado

DORA mede desempenho de entrega de software; seus indicadores exigem eventos de entrega e produção, não apenas status de tarefas. Não chamar volume de comentários ou tarefas concluídas de produtividade DORA. Integrar Git/CI/CD apenas quando essa pergunta gerencial for relevante. [DORA — métricas de entrega](https://dora.dev/guides/dora-metrics/).

## 5. Arquitetura alvo incremental

Manter um processo Python e o layout `src`. Separar coleta, avaliação e entrega dentro da aplicação, sem criar serviços independentes.

| Componente proposto | Responsabilidade | Evolução do código atual |
|---|---|---|
| Coleta | Consultar quatro fontes e carregar evidências necessárias | Extrair de `service.py`, reutilizando `notion_api.py` |
| Contratos | Normalizar pessoas, status, propriedades, timestamps e completude | Evoluir `models.py` e normalização |
| Políticas | Avaliar regras puras com relógio e configuração explícitos | Evoluir `quality.py`, `scope.py`, `template.py` |
| Execuções | Persistir coleta, versão, achados e resultado | Evoluir `snapshot.py` |
| Entregas | Planejar partes, publicar, registrar confirmação e recuperar falha | Evoluir `alerting.py` e `gchat.py` |
| Apresentação | Gerar visão operacional e gerencial da mesma coleta | Reutilizar renderizadores existentes |

Sugestão de persistência inicial: SQLite da biblioteca padrão, se for mantido um único host, para transações de estado e histórico. JSON continua útil como exportação. Trata-se de proposta arquitetural; a migração deve preservar o estado atual e evitar disparo em massa. PostgreSQL só deve ser considerado diante de múltiplos escritores ou requisitos operacionais que justifiquem o custo.

Entidades mínimas: `Run`, `SourceResult`, `FindingState`, `Delivery`, `PolicyVersion`. Guardar IDs e fatos necessários; não duplicar todo o conteúdo de comentários por padrão. Snapshots imutáveis por `run_id`; índice para a última execução completa. Não sobrescrever o baseline diário sem versionamento.

## 6. Regras gerenciais avançadas

### Atualização e aprovação

Preservar o datetime original e converter para o fuso gerencial antes de calcular dias úteis. Proposta de fuso: `America/Sao_Paulo`, a confirmar para o host. Calendário deve explicitar tratamento de feriados e o instante em que vence a janela de dois dias úteis; o código atual conta apenas segunda a sexta e alerta quando o total é maior que dois.

Separar três fatos: última edição da página, último comentário observado e último comentário elegível do responsável. Autoria ausente significa “não foi possível verificar”, e não descumprimento. Para aprovação, identificar ciclo de aprovação, aprovadores por ID, resultado e referência de teste. “Teste pendente”, “reprovado” e evidência de ciclo anterior não satisfazem conclusão. Um resultado inconclusivo gera revisão humana, sem alterar o Notion.

### Bloqueios e responsabilidades

A última pessoa mencionada em qualquer comentário é apenas uma heurística de encaminhamento. Não prova que ela seja dona do bloqueio atual. A proposta é manter vínculo com comentário, momento do bloqueio e justificativa; quando ambíguo, encaminhar ao responsável com linguagem de confirmação.

Preservar a regra atual de não cobrar prazo vencido de tarefa bloqueada. Adicionar idade do bloqueio, impacto no compromisso e ação esperada como indicadores próprios. Campos de pessoas múltiplas também precisam ser normalizados integralmente: hoje o responsável é reduzido ao primeiro usuário, o que pode afetar o recorte por equipe.

### Templates e sugestões

Ativar templates primeiro em modo de observação, sem envio. Distinguir seção ausente, seção vazia e conteúdo não verificável; leitura recursiva deve ter limite de profundidade e orçamento. Validar tarefa concluída, headings aninhados, paginação e divergências de acentuação.

Depois, gerar propostas de vínculo entre solicitação, projeto e tarefa, sempre com origem, motivo, confiança e conflitos. Uma solicitação relevante não autoriza criação automática. Ações COLTEC podem originar candidatos, mas a decisão precisa ser confirmada e registrada no Notion.

## 7. Roadmap executável

Estimativas abaixo são ordens de grandeza para um desenvolvedor familiarizado com Python, com revisão técnica e acesso de validação disponível. Não são compromisso de calendário; recalibrar após cada ciclo.

| Ciclo | Esforço indicativo | Entregas | Critério de saída |
|---|---|---|---|
| 1 — Correção funcional | 3–5 dias úteis | A01–A04, testes de regressão, documentação consistente | Comandos funcionam; negativo não aprova; reabertura e troca de destino notificáveis |
| 2 — Integração e entrega | 5–8 dias úteis | Retry, timestamps, contratos, estado transacional, particionamento | Falhas e retomadas reproduzíveis, sem sucesso silencioso |
| 3 — Operação confiável | 3–5 dias úteis | Coleta única, run_id, snapshots, monitor externo e runbook | Execução completa e falha identificáveis; restauração ensaiada |
| 4 — Gestão e templates | 5–8 dias úteis | Observação de templates, aging, fluxo, propostas de vínculos | Revisão de amostra com falsos positivos medidos |
| 5 — Automação assistida | A estimar após piloto | Eventual Chat App, IA de resumo, escritas controladas | Caso de uso validado, permissões e critérios de segurança definidos |

Ordem sugerida de PRs: correção da CLI; aprovação; ciclo de vida dos achados; timestamps e contratos; cliente resiliente; persistência de entrega; payloads; execução/observabilidade; documentação e diagnóstico; piloto de templates. Cada PR deve ser pequeno o suficiente para revisão e reversão.

### Backlog com aceite

| Item | Dependência | Aceite verificável |
|---|---|---|
| CLI por comando | Nenhuma | `audit`, `audit --json`, `notify`, `report`, `snapshot` executam com coleta mockada e sem envio implícito |
| Evidência contextual | IDs/timestamps | Dado comentário negativo ou antigo, aprovação não é considerada comprovada |
| Ciclo de vida | Modelo de achado | Dado aberto → resolvido → reaberto, existe nova ocorrência elegível para entrega |
| Destinatário semântico | IDs de pessoas | Troca de responsável/aprovador atualiza a elegibilidade e o texto |
| Recuperação de entrega | Persistência | Interrupção antes/depois do HTTP deixa estado recuperável ou explicitamente ambíguo |
| Retry | Transporte injetável | 429/529 respeitam espera; erros permanentes não repetem indefinidamente |
| Schema | Contratos por fonte | Propriedade renomeada ou tipo inesperado aparece como erro diagnosticável |
| Payload | Renderização comum | Parte isolada grande e texto multibyte são divididos sem perder itens ou links |
| Coleta compartilhada | Run persistido | Alertas e relatório referenciam o mesmo run_id; falha de destino não apaga a coleta |
| Template em observação | Coleta de blocos | Ausência, vazio e falha de leitura produzem resultados distintos |

## 8. Indicadores úteis ao gestor

| Indicador proposto | Definição | Limitação/ação |
|---|---|---|
| Precisão dos alertas | Achados confirmados ÷ achados revisados | Amostra revisada por regra; revisar política quando cair |
| Idade do bloqueio | Agora − início do bloqueio atual | Precisa histórico de transição; não inferir de última edição |
| Espera por aprovação | Agora − entrada no ciclo atual de aprovação | Priorizar filas antigas e aprovadores sobrecarregados |
| WIP | Itens em execução por frente | Contagem não mede esforço nem capacidade individual |
| Tempo de ciclo | Conclusão − início da execução | Separar classes de trabalho; usar distribuição e percentis |
| Compromissos vencidos | Ativos elegíveis com prazo anterior ao corte | Preservar exclusão atual de bloqueados; mostrar risco separadamente |
| Confiabilidade da coleta | Execuções completas ÷ execuções previstas | Falha/incompletude é incidente operacional, não zero pendências |
| Recuperação de pendências | Tempo entre abertura e resolução do achado | Alteração de política deve quebrar ou identificar a série |

Snapshots diários só observam mudanças entre coletas. Não reconstruir transições intradiárias como se fossem conhecidas. Metas iniciais propostas para piloto: 100% dos achados publicados com origem e ação; precisão revisada de pelo menos 95% em amostra mínima de 30 achados, ou todos quando houver menos; dez ciclos úteis sem falha silenciosa. Esses números são critérios locais sugeridos, não benchmarks de mercado.

## 9. Operação, segurança e testes

O systemd versionado usa caminho específico do host, `flock` e horário 08:00 sem fuso explícito. Não comprova configuração instalada, execução recente, timeout total ou retry do host. Rever com usuário de serviço dedicado, permissões restritas para estado/credenciais, diretórios estáveis, prazo máximo de execução e logs sanitizados. `Persistent=true` pode disparar execução atrasada ao voltar; definir se uma cobrança fora da janela ainda deve sair.

A CLI imprime o relatório antes do envio; em execução pelo service, isso pode colocar títulos e comentários no journal. Definir saída resumida para batch, retenção e acesso aos logs. Tokens e URLs completas de webhook devem ser redigidos em erros. Minimizar conteúdo enviado a espaços mais amplos que o acesso ao Notion. Confirmar público de cada destino antes de ampliar a distribuição.

CI proposta: rodar unittest sem credenciais, validação de sintaxe e construção do pacote em PR; não executar scheduler nem enviar mensagens no CI. O AGENTS.md pede autorização para novas dependências; estas correções podem começar com a biblioteca padrão. Ferramentas adicionais de análise só devem entrar com justificativa e aprovação aplicável.

Testes necessários: todos os comandos CLI; paginação com cursor inválido; 401/403/404/429/529/5xx; timezone e fronteira de dois dias úteis; comentário sem autor, negativo e do mesmo dia; reabertura; troca de responsável; duas execuções concorrentes; estado corrompido; interrupção após envio; retomada de relatório parcialmente enviado; payload multibyte; falha de uma fonte. Testes de contrato em ambiente autorizado complementam mocks, sem publicar no canal real da equipe por padrão.

Rollback: interromper o timer durante migração de estado, preservar cópia consistente, atualizar, validar sem envio e reativar somente o destino previsto. Não usar `--force` como recuperação genérica: ele pode reenviar todas as pendências. Restaurar estado requer avaliar entregas ocorridas desde o backup.

## 10. Quando incluir IA e escrita

IA pode apoiar resumo de comentários, agrupamento de riscos e preparação de pauta após a estabilização. Toda sugestão deve referenciar registros consultados e explicitar ausência de informação. Avaliar em conjunto fixo de exemplos revisados pelo gestor, medindo omissão, invenção, custo e utilidade. Tratar conteúdo do Notion como dado não confiável para instruções: comentários não autorizam ferramentas ou escrita.

Uma etapa futura de escrita requer plano revisável com campos antes/depois, identidade do solicitante, chave de idempotência, precondição contra alteração concorrente e trilha de auditoria. `--apply` sozinho não resolve concorrência. Quando não houver atualização condicional atômica na API utilizada, declarar a limitação e usar reconciliação; não prometer ausência de corrida. Comentários existentes permanecem preservados conforme regra do projeto.

Não priorizar agora: ranking individual por atividade, migração de infraestrutura sem necessidade, múltiplos agentes, chatbot genérico ou alteração automática de status a partir de palavras-chave.

## 11. Validação realizada e limites

Foi executado `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B -m unittest discover -s tests -v` sobre os arquivos recuperados da referência analisada: **41 testes, todos aprovados**.

Verificações adicionais locais e sem rede reproduziram: AttributeError no audit simples; fingerprint igual após mudança de destinatário; um único envio na sequência aberto/resolvido/reaberto; ausência de achado de aprovação com comentário antigo “teste não realizado”; bloco de 9.000 caracteres não dividido.

Os demais riscos são conclusões da leitura estática e devem receber testes direcionados na implementação. Não foram consultados dados reais do Notion, credenciais, estado do host, entrega efetiva de mensagens, configurações remotas de proteção de branch ou produção. A aprovação dos testes existentes não certifica prontidão operacional.

## 12. Decisões a fechar durante a implementação

Confirmar fuso e calendário; definir evidência válida e ciclo de aprovação; escolher política para entregas ambíguas; estabelecer público e retenção por destino; decidir se haverá um único host; validar schema real das quatro fontes; definir prazo máximo aceitável da coleta. Essas decisões não impedem iniciar as correções reproduzidas do primeiro ciclo.

A primeira entrega recomendada é uma versão de estabilização com CLI corrigida, aprovação contextual, alertas de reincidência e destinatário correto. O ganho esperado é confiança nas ações sugeridas à equipe, condição necessária para expandir a automação gerencial.
