# Kanban: skin de consumo de LLM no Rainmeter

Atualizado em: 2026-11-12 18:02 America/Sao_Paulo
Run atual: run_8c99adf597d9
Run histórico somente leitura: run_e29986923056

## Fazendo

| Responsável | Tarefa | Identificação Orca |
|---|---|---|
| Dev — OpenCode / Kimi K2.7 Code | Investigação documental somente; limitado pelo OpenCode Go | task_efe425ed1139 / ctx_68fc93a937ce |
| QA — Codex | Revalidar nativamente alturas136/34 e demais N1-N5 na versão atual | task_529c36b44550 / ctx_a8ff09bf6e7d |
| Coordenador — Codex | Decisões, integração, revisão das entregas e distribuição das próximas tarefas | run_8c99adf597d9 |

Consulta Orca às 18:02: `task-list` registra 17 tarefas `completed` e duas `dispatched`. Estão concluídas a preparação das regressões N1–N5 (`task_eb700a15cfc3`), a correção do isolamento de `SnapshotPath` (`task_e32c246cea9b`) e a correção temporal do cache (`task_60420f567bb3`). A revalidação nativa (`task_529c36b44550` / `ctx_a8ff09bf6e7d`) segue `ready`, `in_progress`, `live` e terminal `active`; houve um dispatch anterior `failed` para a mesma tarefa, sem concluir a tentativa atual. A investigação de fontes independentes (`task_efe425ed1139` / `ctx_68fc93a937ce`) segue `ready`, `in_progress`, `live`, terminal `retained`. `docs/implementacao-skin.md` relata 32/32 testes Lua offline após as correções; `docs/correcao-cache-temporal.md` registra 43/43 testes backend herméticos. `docs/revalidacao-rainmeter-nativa.md` ainda documenta a rodada anterior às correções finais, com altura nativa e orçamento pendentes. Não há aprovação nativa integrada confirmada nesta consulta.

Consulta Orca às 17:01: `task-list` confirma 13 tarefas `completed` e duas `dispatched`, sem nova conclusão desde 16:01. `worker-list` mantém a preparação de regressões N1–N5 (`task_eb700a15cfc3`) como `ready`, `in_progress`, `live`, terminal `active`; a investigação das fontes restantes (`task_efe425ed1139`) segue `ready`, `in_progress`, `liveness=unverifiable`, terminal `retained`. Vivacidade não verificável não confirma execução atual, conclusão nem parada. Os relatórios locais permanecem sem reteste nativo após N1–N5; não há evidência nova para mover tarefas a Feito ou encerrar as pendências de integração.

Consulta Orca às 16:01: `task-list` confirma 13 tarefas `completed` e duas `dispatched`, sem nova conclusão desde 15:02. `worker-list` mostra a preparação de regressões N1–N5 (`task_eb700a15cfc3`) como `ready`, `in_progress`, `live` e terminal `active`; a investigação das fontes restantes (`task_efe425ed1139`) como `ready`, `in_progress`, `liveness=unverifiable` e terminal `retained`. Esse último estado não confirma execução atual, conclusão nem parada. Os relatórios locais consultados não registram reteste nativo após as correções N1–N5; a aprovação da integração permanece pendente.

Consulta Orca às 15:02: 13 tarefas `completed`, incluindo correções S1–S8 (`task_ce896b4d72ea`), QA nativo (`task_0a0541a706b5`) e correções N1–N5 (`task_a95b058b2eaf`, worker `succeeded`). Duas tarefas permanecem `dispatched`: investigação das fontes restantes (`ready`, `in_progress`, vivacidade `unverifiable`) e preparação das regressões N1–N5 (`ready`, `in_progress`, `live`). Vivacidade `unverifiable` não confirma conclusão nem parada. `docs/implementacao-skin.md` relata 30/30 testes Lua 5.1 e 38/38 testes do produto após N1–N5; o reteste no Rainmeter real e a revisão independente dessas correções ainda não estão confirmados.

Consulta Orca às 13:01: dez tarefas `completed`, incluindo o QA da skin (`task_ce3914aecd89`, worker `succeeded`). Duas tarefas `dispatched`: correção S1–S8 com worker `ready`, `in_progress` e `live`; investigação das fontes restantes com worker `ready`, `in_progress` e vivacidade `unverifiable`. Esta última condição não confirma conclusão nem parada. O relatório `docs/revisao-skin-qa.md` registra oito bloqueadores na execução de Lua 5.1; não há confirmação de correção, integração ou instalação.

Consulta Orca às 12:01: nove tarefas constam como `completed`; o QA da skin (`task_ce3914aecd89`) segue `dispatched`, com worker `ready`, `in_progress` e `live`. Correção final da skin (`task_0d8ff53cc7c6`) e rodada Dev Kimi (`task_01313421d143`) continuam `completed`, com workers `succeeded`. Não há resultado confirmado do QA da skin nem aprovação da integração ou revalidação independente dos achados.

Consulta anterior às 11:01: nove tarefas `completed`; QA da skin `dispatched`, com worker `ready`, `in_progress` e `live`. Correção final da skin e rodada Dev Kimi `completed`, com workers `succeeded`.

Consulta anterior às 10:01: QA da skin `dispatched`, worker `ready`, `in_progress` e `live`. Correção final da skin (`task_0d8ff53cc7c6`) e rodada Dev Kimi (`task_01313421d143`) constavam como `completed`, com workers `succeeded`.

Consulta de 07:01: correção da skin estava `dispatched`, com worker `ready`, `in_progress` e `live`; correção anterior do dev e QA do backend já constavam como concluídos no Orca.

## A fazer

- Aguardar o resultado da revalidação nativa em andamento (`task_529c36b44550`), revisar as correções N1–N5 e o isolamento de `SnapshotPath` no Rainmeter real. O relatório da Miiaq registra 32/32 testes Lua offline; essa evidência não valida a altura nativa nem a legibilidade monetária na revisão atual.
- Revisar o resultado da investigação das fontes independentes restantes quando houver entrega confirmada; não presumir disponibilidade dos provedores.
- Revalidar na versão integrada os bloqueadores B1–B7 e as melhorias M1–M8 do relatório `docs/revisao-backend-qa.md`. A rodada `docs/tarefas/dev-kimi-qa.md` foi concluída no Orca e o dev relatou correções em `docs/correcoes-qa-backend.md`; isso ainda não equivale a fechamento independente dos achados.
- Revisar skin em staging implementada pela Miiaq contra contrato v1.
- Testar integração e comportamento real, preparar instalação reversível.
- Conferir manual e versionar somente arquivos do projeto, identidade abnerfc01 / abnerfc01@gmail.com.
- Conferir acesso GitHub atual antes de publicar. Ausência de login no histórico ainda não foi revalidada.
- Revalidar correções do backend e da skin, incluindo os achados do QA independente, antes da instalação final.

## Revisão da rodada atual

- Correção temporal recebida, código e teste novo conferidos. Coordenador repetiu suíte backend:43/43 passaram. Validação distingue success/error/never sem alterar horários/cache; regressões determinísticas com minutos/dias. QA nativo ativo foi avisado e autorizado a uma coleta real isolada somente leitura para E2E, sem defaults do usuário nem captura de dados reais.

- Miiaq reportou alturas nativas136/34 e orçamento curto, cópia sincronizada/inativa. Coordenador confirmou32/32 Lua. QA reaberto na mesma tarefa nativa com escopo explícito após prompt histórico vazio; recebeu instrução e iniciou sem duplicação de teste.
- Correção temporal retirada formalmente do escopo dev Kimi (limite Go) e atribuída a worker pontual separado com propriedade contract.py/teste novo/doc própria. Dev continua modelo Kimi e pesquisa documental; sem conflito de edição.

- SnapshotPath entregue e coordenador confirmou 32/32 testes Lua. Complemento nativo da Miiaq gerou aviso de início não observado; inspeção posterior mostrou comandos em execução, sem duplicar worker.
- Dev estava no seletor de modelo OpenCode (sessão já Kimi). Coordenador fechou só o menu com Escape e reenviou instrução na mesma tarefa via orquestração; confirmação de execução ainda pendente. Correção temporal continua necessária.

- Revalidação nativa parcial confirmou JSON formatado e glifos corrigidos na revisão testada. Persistem janela 156px em espaço50/150 e dinheiro truncado. Fallback foi testado antes da edição atual de Miiaq, não é evidência contra nova revisão. Tarefa de Miiaq ampliada sem duplicação para prova nativa da altura e compacto monetário curto com detalhe integral na gaveta.
- Falta ainda repetir hover cronometrado, rolagem com vários itens, regressão backend de cache após erro e aprovação nativa integrada. Validação desativada, illustro preservado.

- QA entregou docs/revisao-integracao-regressoes.md: 32 testes Lua, 31 verdes e fallback explícito vermelho. Coordenador confirmou causa em ResolveSnapshotPath. Decisão: caminho explícito autoritativo, sem fallback silencioso ao cache padrão; troca de caminho invalida cache de origem anterior. Miiaq recebeu correção pontual. Reteste nativo permanece próximo passo após verde.

- N1-N5 entregues por Miiaq. Coordenador confirmou 30/30 Lua real e 4/4 lógica Python. Backend rodou 38 testes com 1 erro: validador rejeita cache cujo último sucesso precede tentativa falha; isso viola preservação do último sucesso. Dev recebeu correção prioritária e teste com datas determinísticas.
- QA recebeu retomada autorizada após limite e revalidação nativa da mesma tarefa, preservando relatório anterior. Nenhuma aprovação nativa nova até worker_done com evidência.

- Miiaq concluiu no Orca a tarefa N1–N5 e registrou em `docs/implementacao-skin.md` correções de parser, geometria multimonitor, codificação, layout monetário e tamanho da janela. Os 30/30 testes Lua 5.1 e 38/38 testes do produto são resultados relatados pela autora; a tarefa de preparar regressões segue em andamento no Orca e o reteste nativo permanece pendente.
- QA nativo reprovou integração: N1 parser rejeita null antes de whitespace no JSON formatado real; N2 usa área útil do primário no secundário; N3 encoding corrompido; N4 dinheiro sobrepõe nome; N5 janela nativa alta mesmo recolhida. Evidência em docs/validacao-rainmeter-nativa.md. Miiaq recebeu correções e QA regressões sem minificação.
- LLMUsage-Validation desativada no fim do teste; illustro preservado. Novos testes nativos só após correções. Snapshot real Claude/Codex funcionou apenas no diagnóstico minificado, não conta como aprovação do fluxo padrão.

- Correções S1-S8 entregues. Coordenador repetiu suíte na versão atual: Lua real 23/23, backend 38/38 e lógica Python 4/4, todos passaram. Regressões anteriores resolvidas nos cenários cobertos; runtime Rainmeter ainda não validado.
- QA nativo despachado: pode copiar código para nova skin isolada LLMUsage-Validation, criar snapshot/config de teste separados, ativar só essa skin e verificar logs/visual/interação. Não modificar skins atuais, DPI global ou serviços. Documentar evidência em docs/validacao-rainmeter-nativa.md.

- QA independente da skin concluído no Orca. `docs/revisao-skin-qa.md` registra execução do `main.lua` e `json.lua` reais em Lua 5.1 isolado: 23 métodos, 19 falhas de asserção e 1 erro; os 4 testes Python passaram, mas não validam o Lua. S1–S8 abrangem snapshot inválido, comandos de grupos, meters fora da área, frescor, cache em erro, saldo pré-pago, percentual nulo e caminho de ícone. O relatório exige correção e nova validação antes da integração. A tarefa de correção está `dispatched`, sem resultado confirmado nesta consulta.

- Limite do QA recuperado: main.lua/json.lua executados em Lua 5.1 isolado. QA encontrou S1-S8; coordenador repetiu na revisão atual e confirmou 23 testes com 19 falhas de asserção e 1 erro. Os 4 testes Python não detectavam as falhas do Lua real.
- Miiaq recebeu correções S1-S8 e melhorias de animação/contrato, obrigada a executar harness Lua preservado. Instalação bloqueada até regressões resolvidas; docs/revisao-skin-qa.md registra repros e hashes.

- Entregas backend e skin recebidas. Coordenador confirmou 38/38 testes backend e 4/4 testes lógica Python da skin nesta rodada. Lua real ainda pendente.
- QA parou por limite Codex. Usuário autorizou continuar se voltou. Mesma tarefa task_ce3914aecd89 / ctx_b3620dbe7a48 recebeu retomada com contexto preservado; mensagem aceita, cota e execução ainda não confirmadas. Harness parcial skin/tests/runtime_qa.py preservado.
- Dev Kimi recebeu investigação documental dos três provedores ainda unsupported; sem alterações concorrentes no produto durante QA.

- Na consulta das 12:01, a correção final da skin permanece concluída no Orca. `docs/implementacao-skin.md` relata correspondência positiva de períodos, geometria efetiva e invalidação individual de modelos/extras; relata 4/4 suítes offline e análise léxica Lua. Execução Lua real segue com o QA `task_ce3914aecd89`, sem resultado confirmado nesta consulta.
- A rodada Dev Kimi está concluída no Orca. `docs/correcoes-qa-backend.md` relata correções B1–B7 e M1–M8 pertinentes, 38/38 testes e smoke real Claude/Codex sem Orca no PATH; `docs/implementacao-backend.md` registra detalhes e limitações. São evidências relatadas pelo dev, ainda não revalidadas pelo coordenador nesta atualização.

- Skin refatorada entregue: coordenador executou 6/6 testes Python, mas são cópia da lógica e não prova de execução Lua. Revisão encontrou orçamento com período ausente aceito e layout forçando mínimo maior que área livre. Miiaq recebeu ajustes; QA recebeu tarefa para executar Lua real isolado com SKIN stub e registrar evidência. Instalação Rainmeter segue pendente.

- QA entregou sete bloqueadores adicionais e oito melhorias. Hashes principais coincidem com versão revisada. Coordenador reproduziu B3 (caminho exemplo relativo) e B5 (1h Codex rotulado 5h). Dev Kimi recebeu correções por prioridade.
- Rodada anterior do dev reportou 16/16 testes e smoke real Claude/Codex sucesso sem Orca no PATH; evidência recebida, ainda não reexecutada pelo coordenador nesta versão.

- Skin staging entregue; revisão do coordenador NÃO aceita prontidão para runtime. Blockers: fallback sintético automático apesar de flag 0, fuso ignorado, ausência de polling, orçamento sem compatibilidade de período/escopo, relógio CPU/timers, modelos extras e rolagem incompletos, limites de tela não garantidos. Correções despachadas à Miiaq; instalação permanece pendente.

- Backend v1 entregue; coordenador executou 9 testes, todos passaram. Evidência de smoke real do dev: Codex sucesso; Claude auth_expired; demais fontes ainda unsupported. Smoke não foi repetido pelo coordenador.
- Leitura anterior revelou timeout ineficaz por shutdown(wait=True) e falha de publicação silenciada; revisão solicitou também scheduler/backoff, fonte Claude configurável e vocabulário fechado de erros. Essa etapa motivou a correção do dev e o QA independente registrados abaixo.
- A tarefa de correção do dev (`task_1bfbc07e1726`) foi concluída no Orca. `docs/implementacao-backend.md` relata timeout por processo, erro de publicação propagado, agendamento/backoff e fonte Claude configurável; relata smoke real sem CLI Orca com Claude e Codex em sucesso e os outros provedores em estado indisponível. Esses resultados são evidência do relatório do dev, não execução repetida nesta atualização.
- O QA independente (`task_fe63a39a1607`) foi concluído e registrou sete bloqueadores B1–B7 e oito melhorias M1–M8 em `docs/revisao-backend-qa.md`. O relatório observou edição concorrente e exige revalidação na versão integrada. Na atualização das 07:07, nenhum desses achados havia sido marcado como corrigido.

- Miiaq entregou design reconciliado: arquivos conferidos pelo coordenador; runtime Rainmeter e DPI ainda não validados.
- Follow-up despachado à Miiaq: skin em staging, sem instalação; corrigir promessa de caber em qualquer tela e restringir 5H a janela equivalente.
- Dev recebeu correção: plano/código em andamento usavam Orca como fonte principal. Execução produtiva deve usar fontes diretas ou estado indisponível, com teste sem CLI Orca. Não aceitar cache antigo como coleta nova.

## Feito

- Requisitos recuperados e workspace conferido; sessão Claude histórica preservada.
- Especificação visual e mockup disponíveis; Miiaq incluiu ícones por solicitação direta do usuário.
- Jayla entregou docs/contrato-coletor-proposta.md e apontou seis incompatibilidades de UI.
- Usuário autorizou coordenação ativa e decisões autônomas em 12/11.
- Coordenador adotou base técnica e registrou decisões em docs/decisoes-coordenador.md.
- Miiaq e dev existentes receberam tarefas independentes com arquivos de propriedade separados.
- Correção anterior do dev e revisão QA independente concluídas no Orca; relatórios locais registrados em `docs/implementacao-backend.md` e `docs/revisao-backend-qa.md`.
- Correção final da Miiaq e rodada Dev Kimi concluídas no Orca; entregas relatadas em `docs/implementacao-skin.md` e `docs/correcoes-qa-backend.md`, sujeitas a revisão e integração.
- QA independente da skin concluído no Orca; bloqueadores S1–S8 documentados em `docs/revisao-skin-qa.md` e correção concluída no Orca, com 23/23 testes Lua repetidos pelo coordenador na rodada anterior.
- QA nativo concluído no Orca; `docs/validacao-rainmeter-nativa.md` registrou N1–N5. Correção N1–N5 concluída no Orca e relatada em `docs/implementacao-skin.md`, sujeita a revisão e reteste nativo.
- Preparação das regressões N1–N5 (`task_eb700a15cfc3`), correção do isolamento de `SnapshotPath` (`task_e32c246cea9b`) e correção temporal do cache (`task_60420f567bb3`) concluídas no Orca. Os relatórios locais registram 32/32 testes Lua offline e 43/43 testes backend herméticos; a validação nativa integrada segue em andamento.
- Automação horária do kanban criada e habilitada no Orca: 542f3927-f0b8-4287-8f80-ba315f07ede8, America/Sao_Paulo, a cada hora cheia. Primeira execução ainda não confirmada.

## Troca de modelo solicitada

- Pedido do usuário: ao terminar task_1bfbc07e1726 / ctx_193e671c8e00, trocar o dev para Kimi K2.7 Code antes de qualquer nova tarefa. ID confirmado no catálogo local: opencode-go/kimi-k2.7-code. A tarefa anterior e a rodada `docs/tarefas/dev-kimi-qa.md` (`task_01313421d143`) constam como concluídas no Orca. `worker-list` identifica o agente da rodada como `opencode`, sem informar o modelo; a troca efetiva de modelo permanece não confirmada por estas consultas.

## Decisões

- Preservar ícones com fallback genérico e estilo illustro.
- Detalhes por hover e clique para fixar; cores nos limiares 25/50/75/90.
- Janelas equivalentes nas colunas; janelas extras nos detalhes sem inventar duração.
- Reset desconhecido sem contagem; reset vencido invalida só sua janela.
- Dados e erros por provedor; orçamento local separado de cota.
- Paginação para lista maior que tela; gaveta limitada e rolável.
- Coletor sem processo Orca aberto, sem renovar tokens; credenciais e cache fora do repo/OneDrive.
- Escolhas técnicas delegadas não exigem novas perguntas de detalhe.

## Pendências e limitações

- A correção temporal preserva o último sucesso após erro nos cenários offline documentados; confirmar o fluxo integrado e a revalidação nativa da skin antes de aprovar instalação.
- `docs/implementacao-backend.md` relata smoke real Claude/Codex com sucesso e Antigravity/OpenCode Go/Cursor sem fonte independente verificada; revalidar na integração. Sem dados reais, publicar estado indisponível.
- Cursor e fonte de autenticação Claude tinham problemas no histórico; o dev relatou sucesso Claude com fallback local somente leitura nesta rodada. Só pedir intervenção do usuário se verificação atual confirmar necessidade; não bloqueiam os demais.
- Nenhum serviço/agendamento do coletor ou instalação Rainmeter autorizado nesta rodada técnica; preparar e validar primeiro.
- Automação do kanban depende do serviço local Orca e sua disponibilidade; não implica dependência Orca para o coletor final.

## Bloqueio atual do dev
Inspeção após fechar seletor confirmou mensagem real OpenCode Go usage limit reached, retry attempt2, sessão Kimi K2.7 Code. O limite do provedor está impedindo o avanço do dev; nenhuma troca de modelo adicional foi feita. Miiaq continua trabalho de skin independentemente.
