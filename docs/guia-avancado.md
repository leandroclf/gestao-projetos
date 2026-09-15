# Guia avançado — Gestão de Projetos

Revisão 2 • 15 de setembro de 2026 • Estratégia, arquitetura e backlog de implementação

Referência verificada na main: `985c437fdd8a4e23a4c5ce86facf54c0411c3be1`. [Commit analisado](https://github.com/leandroclf/gestao-projetos/commit/985c437fdd8a4e23a4c5ce86facf54c0411c3be1).

## 1. Parecer executivo

O projeto é uma automação gerencial Python sobre Notion e Google Chat, com quatro fontes: tarefas, projetos, COLTEC e solicitações. A base modular é adequada à necessidade observada. A evolução de maior valor é produzir achados confiáveis e próximos passos verificáveis, com histórico de execução e entrega recuperável.

A implementação desta revisão conclui o núcleo operacional priorizado: aprovação contextual, ciclo de vida dos alertas, execução única, persistência de run, diagnóstico local, retry, particionamento e CI. Recursos como escrita no Notion, Chat App interativa e IA permanecem deliberadamente condicionais ao piloto e às decisões de governança.

Recomendação: consolidar aprovação estruturada, persistência transacional e operação; em seguida ampliar métricas, templates e sugestões. IA e escrita são investimentos condicionais ao sucesso do piloto, não requisitos para tornar a automação atual confiável.

## 2. O que existe e o que falta

| Área | Estado verificado | Próxima ação |
|---|---|---|
| CLI audit | Corrigida para texto e JSON | Cobrir todos os subcomandos, erros e ausência de envio implícito |
| Aprovação | Evidência positiva/negativa contextual e ciclo ainda sem campo dedicado | Adicionar autoria elegível, ciclo e referência de teste estruturada |
| Reincidência | Corrigida também com seleção diária; estados de entrega persistidos | Expandir estado por achado individual se houver múltiplos episódios simultâneos |
| Destinatário | Fingerprint inclui nome e URL | Incluir IDs, destino lógico, versão de política e fatos relevantes |
| Retry Notion | Backoff, jitter, Retry-After e limite de tentativas implementados | Orçamento total, transporte/relógio injetáveis, diagnóstico sanitizado |
| Particionamento | Alerta usa divisão; bloco grande pode ser cortado | Validar bytes do payload completo e preservar links |
| Testes/CI | 45 testes na entrega; CI remoto concluído com sucesso | Testes de falha, concorrência e contratos externos |
| Persistência | JSON por regra e snapshot por data | Estado transacional e snapshots imutáveis por execução |
| Modelo de comentários | Data sem hora; autor preservado quando disponível | Timestamp com timezone, ID e contexto da transição |
| Operação | systemd usa `run --send --schedule` e coleta única; monitor externo ainda ausente | Adicionar monitor externo e ensaio de restauração |
| Templates | Regra implementada; alertas desabilitados | Corrigir coleta dos blocos e observar precisão antes de enviar |
| Governança | Resposta da API informa main sem proteção | Propor PR/revisão e CI obrigatório para alterações futuras |

[CI verificado: execução 34936039144](https://github.com/leandroclf/gestao-projetos/actions/runs/34936039144). CI verde demonstra aprovação das verificações configuradas; não comprova completude do roadmap nem operação no host.

## 3. Diagnóstico atualizado por risco

P0 significa prioridade antes de ampliar uso; P1 significa próximo ciclo de estabilização. São prioridades propostas para este projeto, não classificação de incidentes já ocorridos.

| ID | Prioridade | Evidência e impacto | Aceite para encerrar |
|---|---|---|---|
| A01 | Concluído no caminho reproduzido | audit simples não acessa mais args.rules | Manter regressão e testar demais comandos |
| A02 | Parcial | Negações agora não satisfazem evidência; autoria e ciclo ainda não são estruturados | Exigir aprovador elegível, ciclo atual, resultado e referência de teste |
| A03 | Concluído no núcleo | Estado é limpo pelo conjunto completo mesmo quando o envio usa rules/--schedule | Evoluir para episódios individuais quando necessário |
| A04 | Parcial | Destinatário/URL no hash; faltam IDs e destino de publicação | Mudança real de destino gera nova elegibilidade, sem depender de nome de exibição |
| A05 | P0 | Estado gravado antes do HTTP permanece; crash pode suprimir envio | pending/sending/sent/unknown, reconciliação e testes de interrupção |
| A06 | P1 | Retry existe, mas sem prazo global e teste de falha dedicado | Cliente respeita orçamento total, Retry-After e falha permanente |
| A07 | P1 | Comentários convertidos a date na normalização | Ordenação inequívoca entre comentários do mesmo dia |
| A08 | P1 | last_edited_time ainda usado para afirmar atualização do responsável | Distinguir edição da página, comentário e autoria verificável |
| A09 | P1 | Coleta de blocos condicionada a has_children no objeto de página | Payload de página realista produz leitura correta; erro não vira seção ausente |
| A10 | P1 | Corte por caracteres não valida JSON/card e pode separar URL | Partes respeitam bytes após serialização e preservam links acionáveis |
| A11 | Parcial | notify agora usa divisão, sem confirmação por parte | Falha na parte N permite retomar sem reenviar partes confirmadas |
| A12 | P1 | systemd encadeia duas coletas com && | Alertas e relatório usam mesmo run_id; falha em destino não impede o outro |

A03 merece tratamento de domínio: regra fora da seleção de envio não é regra resolvida. Primeiro avaliar o conjunto completo; depois atualizar estados; por último selecionar quais notificações saem naquele dia. Uma limpeza indiscriminada do estado pode gerar reenvios em massa.

A02 também não se resolve ampliando indefinidamente uma lista de palavras. Recomenda-se um registro explícito de resultado, autor elegível, comentário de origem e ciclo. Quando a fonte não permitir comprovar o ciclo, informar “evidência não verificável” e solicitar revisão; não inventar data de entrada no status.

Fontes do código: [quality.py](https://github.com/leandroclf/gestao-projetos/blob/985c437fdd8a4e23a4c5ce86facf54c0411c3be1/src/notion_management/quality.py), [alerting.py](https://github.com/leandroclf/gestao-projetos/blob/985c437fdd8a4e23a4c5ce86facf54c0411c3be1/src/notion_management/alerting.py), [service.py](https://github.com/leandroclf/gestao-projetos/blob/985c437fdd8a4e23a4c5ce86facf54c0411c3be1/src/notion_management/service.py), [CLI](https://github.com/leandroclf/gestao-projetos/blob/985c437fdd8a4e23a4c5ce86facf54c0411c3be1/src/notion_management/cli.py).

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

CI existente e aprovada no commit analisado: unittest sem credenciais, validação de sintaxe e construção do pacote em PR; não executar scheduler nem enviar mensagens no CI. O AGENTS.md pede autorização para novas dependências; estas correções podem começar com a biblioteca padrão. Ferramentas adicionais de análise só devem entrar com justificativa e aprovação aplicável.

Testes necessários: todos os comandos CLI; paginação com cursor inválido; 401/403/404/429/529/5xx; timezone e fronteira de dois dias úteis; comentário sem autor, negativo e do mesmo dia; reabertura; troca de responsável; duas execuções concorrentes; estado corrompido; interrupção após envio; retomada de relatório parcialmente enviado; payload multibyte; falha de uma fonte. Testes de contrato em ambiente autorizado complementam mocks, sem publicar no canal real da equipe por padrão.

Rollback: interromper o timer durante migração de estado, preservar cópia consistente, atualizar, validar sem envio e reativar somente o destino previsto. Não usar `--force` como recuperação genérica: ele pode reenviar todas as pendências. Restaurar estado requer avaliar entregas ocorridas desde o backup.

## 10. Quando incluir IA e escrita

IA pode apoiar resumo de comentários, agrupamento de riscos e preparação de pauta após a estabilização. Toda sugestão deve referenciar registros consultados e explicitar ausência de informação. Avaliar em conjunto fixo de exemplos revisados pelo gestor, medindo omissão, invenção, custo e utilidade. Tratar conteúdo do Notion como dado não confiável para instruções: comentários não autorizam ferramentas ou escrita.

Uma etapa futura de escrita requer plano revisável com campos antes/depois, identidade do solicitante, chave de idempotência, precondição contra alteração concorrente e trilha de auditoria. `--apply` sozinho não resolve concorrência. Quando não houver atualização condicional atômica na API utilizada, declarar a limitação e usar reconciliação; não prometer ausência de corrida. Comentários existentes permanecem preservados conforme regra do projeto.

Não priorizar agora: ranking individual por atividade, migração de infraestrutura sem necessidade, múltiplos agentes, chatbot genérico ou alteração automática de status a partir de palavras-chave.

## 11. Modelo de implementação e recuperação

### Identidade e estados

Chave sugerida de achado: fonte + page_id + rule_id + policy_version. Manter episódio de abertura/reabertura separado da identidade. Persistir first_seen, last_seen, resolved_at e evidências mínimas; não marcar resolução quando a fonte estiver incompleta.

Chave de entrega: episódio + destino lógico + thread + versão do renderizador + índice da parte + hash semântico. Evitar guardar o webhook como identificador, pois contém segredo. Estado pending representa parte planejada; sending representa tentativa iniciada; sent exige confirmação recebida; unknown representa interrupção ou resposta ambígua. Retry automático de unknown exige garantia ou política explícita de duplicidade aceitável.

SQLite é uma opção proposta para um host único. Migrar com backup consistente, transação e simulação do próximo envio. Preservar a baseline do JSON antigo; diferenças na versão do hash não autorizam republicar tudo. Bloqueio no systemd ajuda a execução agendada, mas comandos manuais também precisam respeitar a exclusão ou transações.

### Contrato de execução

Run deve conter run_id, schema_version, policy_version, code_version, started_at, finished_at e resultado complete/partial/failed. SourceResult registra coletados, incluídos, excluídos e falhas por fonte. Uma coleta incompleta pode gerar diagnóstico operacional; não deve gerar cobrança baseada em ausência de dados.

`run` já coleta uma vez e, com `--send`, entrega alertas e relatório. `doctor` já valida configuração local sem consultar o Notion. `deliveries` já lista as entregas registradas e retorna código 2 quando existe estado `unknown`; a resolução explícita de ambiguidades continua sendo uma evolução.

### Payloads e mensagens

Validar o JSON serializado, incluindo fallback, HTML, botões e widgets; limite por caracteres da mensagem é apenas heurística. A API de mensagens documenta cards e limites próprios, que precisam ser incorporados ao contrato do adaptador. [Google Chat — recurso Message](https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages).

Evitar cortar URLs; quando um item não couber, reduzir texto mantendo referência ao Notion. Exibir total de pendências mesmo com amostra de exemplos. Incluir identificador estável da execução no relatório e preservar confirmação por parte, sem declarar entrega exatamente uma vez.

## 12. Engenharia, governança e atualização contínua

O pipeline de CI existe e passou. Próximo passo: fixar Actions por SHA completo, manter permissões mínimas e automatizar propostas de atualização. GitHub recomenda pinagem por SHA para imutabilidade e proteção da cadeia de execução. [GitHub — uso seguro de Actions](https://docs.github.com/en/actions/reference/security/secure-use).

Propor proteção de main com CI obrigatório e revisão. A consulta atual retornou protected=false; isso é evidência de configuração, não prova de incidente ou acesso indevido. Não alterar proteção durante a produção deste guia.

Rotina sugerida: semanalmente rever changelogs de Notion e Google Chat; mensalmente atualizar dependências de desenvolvimento e Actions via PR; antes de trocar Notion-Version, executar contrato com fixtures e sandbox. Fixar a versão operacional e evitar atualização automática de API sem validação. A aplicação continua sem dependências obrigatórias adicionais; o AGENTS.md deve ser respeitado nas escolhas de ferramentas.

Manter uma matriz requisito → implementação → teste → evidência → status. “Concluído” exige comportamento verificável; documento incluído no repositório, classe criada ou teste verde isolado não comprovam execução de todo o requisito.

## 13. Plano de validação do próximo ciclo

| Cenário | Resultado esperado |
|---|---|
| Negação: não aprovado / sem sucesso | Nenhuma evidência positiva confirmada |
| Aprovado por pessoa fora da lista | Exigir validação de aprovador elegível |
| Aprovação antiga após reabertura | Não reutilizar evidência de ciclo anterior |
| Reincidência com filtro de envio | Novo episódio permanece notificável |
| Regra omitida na terça ou quinta | Omissão de publicação não resolve o achado |
| Dois comentários no mesmo dia | Mais recente escolhido por timestamp e desempate estável |
| API 429 ou 529 | Espera prescrita, orçamento finito e erro explícito ao esgotar |
| Cursor ausente com has_more=true | Falha de integridade, não coleta completa silenciosa |
| Falha em uma fonte | Relatório parcial explícito; ausência não gera cobrança |
| Processo encerra após o HTTP | Entrega unknown; retomada não presume falha |
| Estado corrompido | Diagnóstico e recuperação; não reiniciar deduplicação silenciosamente |
| Falha na segunda parte do relatório | Primeira parte permanece confirmada |
| Emoji, HTML escapado e URL longa | Payload válido e link preservado |
| Duas execuções concorrentes | Sem sobrescrita de estados ou dupla reserva da mesma entrega |

Não foram executados testes reais contra Notion ou Google Chat nesta revisão. O CI remoto está aprovado; as reproduções locais foram convertidas em regressões para CLI, aprovação, reincidência e particionamento. Estado do host, permissões das quatro fontes, calendário e público dos espaços permanecem não verificados.

## 14. Critérios de produto e decisões finais

Usar quatro perguntas para priorizar: o achado é verdadeiro? a pessoa certa pode agir? o histórico explica o ocorrido? a próxima execução se recupera de falha? Entregas que respondem a essas perguntas têm prioridade sobre novos canais e interface.

Critérios propostos para piloto: 100% dos alertas com origem e ação; ao menos 95% de precisão em amostra revisada de 30 achados, ou todos quando houver menos; dez ciclos úteis sem falha silenciosa. São metas locais propostas, não padrão universal. Medir tempo poupado em cobranças manuais e redução da espera por aprovação junto com qualidade e ruído.

Responsabilidades sugeridas: liderança decide políticas, calendário e destinatários; desenvolvimento implementa regras e contratos; operação valida scheduler, retenção e restauração; aprovadores participam da amostra de qualidade. Não inferir desempenho individual de quantidade de comentários.

A próxima entrega deve encerrar A02 e A05 com campos de ciclo, testes de autoria e recuperação de entrega. Em paralelo ao planejamento — sem necessidade de novos serviços — preparar modelo temporal, coleta única e diagnóstico de schema. A expansão gerencial vem após confiança demonstrada nos dados e na entrega.
