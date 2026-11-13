# Decisões do coordenador — 12/11/2026
O usuário autorizou coordenação ativa e decisões autônomas. Contrato v1 adotado como base técnica; avançar com desenvolvimento reversível.
- Preservar ícones solicitados à Miiaq, com fallback.
- Colunas fixas só para janelas equivalentes; janelas extras nos detalhes e indicador na linha.
- Reset desconhecido: omitir contagem/marcador; 0% não implica janela não iniciada.
- Reset vencido invalida apenas a janela; frescor e erro separados por provedor.
- Orçamento é referência local; percentual só com moeda, período e escopo compatíveis.
- Lista maior que tela: paginação explícita e posições estáveis por página; gaveta limitada e rolável.
- Maior percentual por modelo só entre janelas equivalentes, identificando escopo.
- Dados e credenciais fora de OneDrive/repo; não renovar tokens ou alterar logins. Fonte Claude configurável, preferir fonte válida sem Orca aberto.
- Cursor indisponível não bloqueia demais provedores; nunca inventar dados.
- Não instalar no Rainmeter nem publicar remoto antes da validação da integração.
Miiaq altera design/ e docs/revisao-design.md. Dev altera backend, testes, scripts, exemplos e manual. Coordenador mantém kanban.

## Troca de modelo do dev solicitada pelo usuário
Após concluir a tarefa atual task_1bfbc07e1726 / ctx_193e671c8e00, trocar o dev OpenCode para Kimi K2.7 Code antes de despachar nova tarefa. Não interromper a tarefa atual e não enviar novo trabalho ao modelo anterior. Modelo verificado no catálogo local via opencode models: opencode-go/kimi-k2.7-code. Troca ainda pendente da conclusão; usar seleção explícita verificada no Orca, preservando o contexto por resumo se uma nova sessão for necessária.

Troca concluída após término da tarefa: API local OpenCode switchModel na sessão existente, confirmada por GET com model.id=kimi-k2.7-code e providerID=opencode-go. Próxima rodada task_01313421d143 / ctx_2e81c9c418c3 despachada via Orca. Seleção --model do Orca recusada por capability_unsupported; nenhum trabalho enviado ao modelo anterior.
