# Implementação do backend (coletor) — v1

## Resumo
Coletor Python (`collector/`) **independente do processo e do CLI do Orca** no fluxo padrão/produtivo. Plugins leem fontes **somente leitura**, sem geração paga e **sem renovar tokens ou alterar logins**. Publica snapshot contrato v1 (`schema_version` 1.0) com escrita atômica em `%LOCALAPPDATA%\LLMUsageWidget\snapshot.json` (temp no mesmo diretório + `os.replace`), preservando último sucesso/dados por provedor em falhas. Configuração externa em `%LOCALAPPDATA%\LLMUsageWidget\config.json` (exemplo sem segredos em `examples/config.example.json`). `orca_source.py` e `scripts/diagnose_orca_import.py` existem apenas como **diagnóstico opt-in separado** e não são usados pelos plugins produtivos nem pelos testes de independência.

## Plano executado
1. **Contrato/núcleo**: `collector/contract.py` (modelo v1, `freshness` por provedor = `max(3×collection_interval_seconds, 1800)` após `last_success_at`, `safe_error` de vocabulário fechado, sanitização, `validate_snapshot`, `atomic_write_json`, `read_snapshot` que ignora snapshot inválido).
2. **Config**: `collector/config.py` (defaults, ordem, `snapshot_path`, `credential_ref` opaco; sem segredos). `collector init-config` cria config local.
3. **Runner**: `collector/runner.py` coleta por provedor com timeout/isolamento, mantém `last_success_at` e último `data` válido após erro, atualiza `generated_at` a cada publicação, anexa `budget` local (`source: local_config`) a `money` quando moeda compatível (referência local; compatibilidade de período/escopo é regra do consumidor).
4. **Plugins produtivos (independentes do Orca)**:
   - `claude` (`claude_direct.py`): lê `~/.claude/.credentials.json` (`claudeAiOauth.accessToken/expiresAt`), **não renova token**; se expirado/ausente → `auth_expired/missing_credential`. GET somente leitura `https://api.anthropic.com/api/oauth/usage` (sem geração paga). Mapeia janelas reconhecidas (5h/semana e modelos semanais quando presentes) sem inventar campos.
   - `codex` (`codex_direct.py`): lê `~/.codex/auth.json` (tokens), **não renova**; GET somente leitura `https://chatgpt.com/backend-api/wham/usage` com `ChatGPT-Account-Id` quando disponível. Mapeia janelas primária/secundária quando reconhecidas.
   - `antigravity`: fonte independente não verificada sem Orca → `unsupported` (`independent_source_unverified`), seguro.
   - `opencode_go`: fonte independente não verificada sem Orca → `unsupported` (`independent_source_unverified`), seguro.
   - `cursor`: heurística local de presença de estado do app Cursor (somente leitura) sem probe/refresh; sem endpoint independente verificado → `unsupported` (`independent_source_unverified`) ou `missing_credential` se sem estado local. Nunca inventa dados.
   - `metered_generic`: template futuro para APIs pagas por uso (`money`/`budget`), retorna `missing_credential`/`unsupported` sem endpoint verificado.
5. **Diagnóstico opt-in (separado)**: `collector/providers/orca_source.py` + `scripts/diagnose_orca_import.py` (execução explícita). Não registrado no fluxo padrão.
6. **Scripts reversíveis**: `scripts/collect_once.ps1|.cmd`, `scripts/init_config.ps1`, `python -m collector collect-loop` (1º plano). Nenhum serviço/agendamento instalado, Rainmeter não alterado.
7. **Testes** (`python -m unittest discover -s tests -v`, **38/38 ok**): contrato, frescor (`never/fresh/stale`), erro seguro/normalizado, escrita atômica+validação, rejeição de money amount não-string e tipos inválidos, allowlist/normalização de payload, invalidação de cache por `origin_signature`, IDs únicos, caminho absoluto/expandido, falha isolada, **preservação de último sucesso/dados**, budget local anexado quando compatível, exceção isolada/segura, **independência hermética** (plugins produtivos não chamam `subprocess`/Orca nem leem perfis/rede; ausência de `orca` no PATH não quebra coleta padrão), duração real Codex, carregamento dinâmico controlado, disabled sem alerta.

## Situação real por provedor (evidência)
| Provedor | Fonte produtiva (indep. Orca) | Evidência real (smoke leitura, 2026-11-12, sem geração paga/sem refresh) | Estado observado | Observações |
|---|---|---|---|---|
| Claude | `credentials_path` explícito, ou `~/.claude/.credentials.json`, ou fallback read-only a perfil gerenciado local (`%APPDATA%\orca\claude-profiles\*\home\.credentials.json`, sem processo/CLI Orca) + GET `/api/oauth/usage` | **Real**: com `orca` ausente do PATH e sem `credentials_path` explícito, o fallback encontrou credencial local gerenciada válida e a coleta retornou `success/fresh` com quotas mapeadas. (Smoke anterior, antes do fallback, havia retornado `auth_expired` para `~/.claude` expirado.) | `success`, `fresh` (neste ambiente) | Fonte configurável; não renova token nem copia credencial. Resultado depende da validade da credencial local selecionada. |
| Codex | `~/.codex/auth.json` + GET `chatgpt.com/backend-api/wham/usage` | **Real**: sucesso, 2 janelas de cota mapeadas no snapshot de smoke (com Orca ausente do PATH) | `success`, `fresh` | Leitura somente leitura; valores reais obtidos no ambiente (não fixture). |
| Antigravity | (nenhuma verificada independente) | **Real (comportamento)**: plugin executou sem Orca e publicou estado seguro | `error` `unsupported` (`independent_source_unverified`) | Sem fonte independente comprovada; não inventa buckets/modelos. |
| OpenCode Go | (nenhuma verificada independente) | **Real (comportamento)**: estado seguro sem Orca | `error` `unsupported` (`independent_source_unverified`) | Fonte de uso independente não verificada; sem dado inventado. |
| Cursor | heurística local de estado, sem endpoint verificado | **Real (comportamento)**: estado seguro | `error` `unsupported` (`independent_source_unverified`) ou `missing_credential` conforme estado | KANBAN indica login expirado/pendente (`cursor-agent login`); sem probe/refresh. |

> **Fixture vs real**: testes unitários usam providers/mockados e dados sintéticos (fixture) para contrato/frescor/cache/falhas/timeout/agendamento/escrita. Resultados acima de Claude/Codex e estados seguros vêm de execução real do coletor no ambiente (smoke), com rede apenas para endpoints de uso leitura e com credenciais locais lidas sem modificação. **Não se alega que todos os provedores estejam funcionais com dados reais.**

## Evidência de independência do Orca e correções QA
- Smoke com **`orca` ausente do PATH** (PATH filtrado no processo, sem fechar app), coleta padrão: `orca_in_path=None` e `claude=success, codex=success, antigravity=unsupported, opencode_go=unsupported, cursor=unsupported` (exit 0, snapshot publicado) — produtivo não depende de Orca/CLI.
- **Timeout real**: provider travado isolado em subprocesso com término/kill; teste `test_timeout_bounded_for_hanging_provider` comprova retorno em tempo limitado (~<8s no teste) com `timeout`.
- **Falha de escrita**: `collect-once` propaga exceção de escrita/replace/validação e retorna exit code 1 com mensagem segura (`snapshot not published`), preservando arquivo anterior (testes `test_write_failure_propagates_and_preserves_previous` e `test_atomic_write_failure_on_replace_preserves_previous`).
- **Agendamento**: `next_attempt_at` por provedor, skip antes do prazo sem forjar `last_attempt_at`, disabled sem chamada/forja/alerta (`error=null`, `state=disabled`), backoff em erro.
- **Allowlist/normalização**: `normalize_provider_data` descarta chaves desconhecidas e valida tipos; payload inválido isola só o provedor como `invalid_response` sem bloquear publicação dos demais (testes em `test_qa_fixes.py`).
- **Caminhos**: variáveis de ambiente expandidas e caminho absoluto exigido; exemplo atualizado com comentário de expansão.
- **Cache/identidade**: `origin_signature` invalida `data`/`last_success_at` anteriores quando plugin/credencial/perfil muda; IDs únicos rejeitados em config/snapshot.
- **Extensibilidade**: carregamento dinâmico controlado via `plugin: module:attr`; `_test_provider` limitado a namespace `tests.` e modo de teste.
- **Codex**: duração real lida da fonte; 3600s mapeado como `rolling_1h`, não como 5h.
- **Scripts**: `collect_once.ps1` e `init_config.ps1` preservam `$LASTEXITCODE`; `collect_once.cmd` só faz fallback de `py` para `python` quando o launcher não é encontrado (código 9009), não repetindo coleta que falhou.
- `test_independence` hermético: mocka credenciais e `urlopen`, não lê perfis nem rede.

## Comandos
- Testes: `cd D:\code\llm-usage-widget; $env:PYTHONPATH='D:\code\llm-usage-widget'; python -m unittest discover -s tests -v` (38/38)
- Init config: `py -3 -m collector init-config`
- Coleta única: `py -3 -m collector collect-once` (ou `scripts\collect_once.ps1|.cmd`)
- Loop: `py -3 -m collector collect-loop --interval 300`
- Diagnóstico Orca (opt-in, separado): `py -3 scripts\diagnose_orca_import.py`

## Alinhamento com decisões/design/contrato
- `0%` medido preservado; sem inferência de "não iniciada"/reset. `reset_at` desconhecido omitido na origem quando ausente; **reset vencido invalida apenas a janela** (dado no snapshot, consumidor/UI aplica). Frescor e erro separados por provedor; erro posterior não apaga `last_success_at`/`data` anterior (leitura de cache antigo **não** vira novo sucesso).
- Orçamento é referência local anexada apenas com moeda compatível (percentual/escopo/período validados pelo consumidor). Valores monetários em string; `currency` ISO 4217; `used_percent` finito não-bool; campos obrigatórios de scope/window/period validados.
- Credenciais/dados fora do repo e fora de OneDrive (`%LOCALAPPDATA%`), snapshot sem segredos/respostos brutas/paths, erros de vocabulário fechado. Allowlist estrita de chaves em `data`; payload inválido converte só o provedor em `invalid_response` sem publicar dados arbitrários e sem impedir os demais.
- `origin_signature` por provedor invalida cache quando plugin/perfil/referência de origem muda; IDs únicos em config/snapshot; caminhos absolutos após expansão de variáveis; `_test_provider` restrito a modo de teste.
- Duração real das janelas Codex preservada (não inventa 5h); rótulo neutro quando desconhecida.

## Limitações / bloqueios (não resolvidos no backend)
- Antigravity/OpenCode Go/Cursor **sem fonte independente verificada** → permanecem `unsupported/missing_credential` com segurança até endpoint/credencial independente comprovada (somente leitura, sem renovar login). Não se afirma suporte funcional com dados reais para eles.
- Cursor pode requerer `cursor-agent login` (ação do usuário/ferramenta oficial). Claude depende de credencial local válida acessível (explícita/default/perfil gerenciado local lido read-only). Skin/design/instalação Rainmeter e publicação remota fora desta fase.

