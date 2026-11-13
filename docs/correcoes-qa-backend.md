# Correções de QA — backend

## Plano
Corrigir achados B1-B7 e melhorias M1-M8 pertinentes sem reescrever correções anteriores (timeout real, agendamento, propagação de erro de escrita, fonte Claude configurável, message_key fechado).

1. **B1/B2 — allowlist/normalização e isolamento de payload inválido**: adicionar `normalize_provider_data()` em `collector/contract.py` com allowlist estrita de chaves (`quotas`, `money` e seus subcampos). Descartar chaves desconhecidas (ex. `raw_token`) e validar campos obrigatórios. Se inválido, converter só aquele provedor em `error: invalid_response`, não publicar payload arbitrário e não impedir publicação dos demais.
2. **B3 — caminho absoluto e expansão**: `load_config`/`collect_once` expande `%VAR%`/`$VAR` e `~` em `snapshot_path` e `config_path`; valida que é absoluto; exemplo atualizado para caminho resolvido ou placeholder com comentário.
3. **B4 — invalidação de cache por mudança de origem**: computar `origin_signature` a partir de `plugin`, `credential_ref`, `credentials_path`, `credential_source` (sem segredos) e gravar no snapshot. Se mudar, descartar `data`/`last_success_at`/`error` anteriores.
4. **B5 — duração Codex real**: não inventar 5h; usar duração informada pela fonte (`limit_window_seconds`, `windowMinutes`, etc.) ou omitir `duration_seconds`; rotular com base na duração real ou deixar neutro.
5. **B6 — extensibilidade sem editar núcleo**: implementar carregamento dinâmico controlado de plugins (`plugin` como `module:attr` ou `plugin_path` relativo a `collector/providers/`); restringir `_test_provider` a namespace `tests.` e a modo de teste.
6. **B7 — IDs únicos**: rejeitar IDs duplicados em config e snapshot.
7. **M1 — validação temporal/monetária**: `validate_snapshot` reforçado (ISO 8601 com fuso, used_percent finito não-bool, currency ISO 4217 3 letras, amount decimal finito, campos obrigatórios de scope/window/period).
8. **M2 — preservar zero**: `claude_direct.py` usar `is not None` em `extra_usage`.
9. **M3 — scripts preservam exit code**: corrigir `scripts/collect_once.ps1`, `scripts/init_config.ps1`, `scripts/collect_once.cmd`.
10. **M4 — testes de independência herméticos**: `tests/test_independence.py` mocka credenciais e `urlopen` antes de chamar plugins.
11. **M5 — show-snapshot com caminho**: CLI aceita `--config`/`--snapshot` e reporta origem.
12. **M6 — timestamps**: `last_success_at` = horário após retorno bem-sucedido do provider; `generated_at` = horário após coleta de todos providers.
13. **M7 — disabled sem alerta**: `enabled=false` gera `error=null`, `last_attempt_result="never"`, sem alerta.
14. **M8 — frescor**: documentar que a skin deve recalcular `freshness` a partir do relógio local (`stale_after`, `last_success_at`, `reset_at`); manter função utilitária pública.

## Execução e resultados
- Testes regressivos: `python -m unittest discover -s tests -v` → **38/38 ok**.
- Smoke real com `orca` ausente do PATH: `claude=success`, `codex=success`, `antigravity=unsupported`, `opencode_go=unsupported`, `cursor=unsupported`, exit 0.
- Scripts `collect_once.cmd` e `collect_once.ps1` propagam exit code não-zero em falha.
- Não alterar design/, skin/, kanban, tarefas, decisões, git, Rainmeter, serviços.
