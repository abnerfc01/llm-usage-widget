# Integração Antigravity (Fonte Independente Somente Leitura)

## 1. Fonte Local e Endpoint Comprovados

A investigação baseada em evidências no ambiente local identificou a fonte independente do Antigravity sem dependência de Orca, `agy` CLI ou processo IDE aberto:

- **Credencial local (Windows Credential Manager):** target genérico `gemini:antigravity` (UTF-8 JSON contendo `token.access_token` Bearer e `token.expiry` ISO 8601). Também há suporte opcional a `credentials_path` / `antigravity_credentials_path` na configuração do provedor.
- **Endpoint primário (somente leitura):** `POST https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary` com `Authorization: Bearer <access_token>` e corpo `{}`.
- **Fallback de projeto:** se `retrieveUserQuotaSummary` retornar HTTP 400 ou grupos vazios, consulta `POST https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist` (`{"metadata": {"ideType": "ANTIGRAVITY"}}`) para obter `cloudaicompanionProject` e repete `retrieveUserQuotaSummary` com `{"project": "<id>"}`.

## 2. Garantias de Segurança e Contrato

- **Sem CLI / sem Orca:** não executa `subprocess` nem depende de processo `agy` ou `orca` ativo.
- **No-refresh:** nunca chama `oauth2.googleapis.com/token` nem altera/renova credenciais locais. Se `expiry` já venceu ou a API responde HTTP 401/403, publica `error.code = "auth_expired"`.
- **Sem geração paga e sem vazamento:** apenas leitura de resumo de cota; nenhum token, e-mail ou payload bruto é incluído em erros ou snapshots.
- **Mapeamento e distinção de janelas (Contrato v1):**
  - `window == "5h"` (ou `duration_seconds == 18000`) → `id: "rolling_5h"`, `label: "5 horas"`, `duration_seconds: 18000` (ordenado primeiro).
  - `window == "weekly"` / `"week"` (ou `duration_seconds == 604800`) → `id: "week"`, `label: "Semana"`, `duration_seconds: 604800`.
  - `window == "monthly"` / `"month"` → `id: "month"`, `label: "Mês"`, sem inferir `duration_seconds` de 30 dias quando a API não informar duração explícita.
  - Janelas desconhecidas mantêm `id` e `label` distintos a partir dos identificadores recebidos, sem inferência por nomes vagos.
  - `remainingFraction` fora de `0..1` ou não finito (`NaN`, `inf`, `-inf`, `bool`) é tratado como inválido (bucket descartado; se nenhum bucket válido restar, retorna `invalid_response` / `unrecognized_usage_response`), nunca convertido em `0%` ou `100%` falsos.
- **FFI Windows Credential Manager:** usa `ctypes.WinDLL("advapi32", use_last_error=True)` com `CredReadW` e `CredFree` sempre garantido em `finally` quando o ponteiro é alocado.

## 3. Limitação Operacional Conhecida

- O `access_token` armazenado em `gemini:antigravity` possui validade limitada (observado ~1h). Como o coletor respeita `no-refresh`, quando o token local expirar e o usuário ainda não tiver reaberto/autenticado no `agy` ou Antigravity, o provedor reportará `auth_expired` até que o próprio cliente Antigravity renove a sessão.

## 4. Verificação Executada

- **Suíte completa (`python -B -m unittest discover -s tests -p "test_*.py" -v`):** **57/57** testes aprovados (sem rede real nem acesso ao Windows Credential Manager real durante os testes unitários).
  - `tests/test_antigravity_source.py` (12 testes): mapeamento de janelas 5h/semanal/mensal/desconhecidas sem inferência vaga, rejeição de frações fora de `0..1` e não finitas, validação pelo contrato (`normalize_provider_data`), FFI `CredReadW`/`CredFree`, `no-refresh` em token expirado, fallback de projeto via `loadCodeAssist`, e falhas HTTP/rede/timeout.
  - `tests/test_independence.py` (2 testes): ambos bloqueando `orca`, `subprocess`, `_read_wincred_blob` e `urllib.request.urlopen`, validando ausência de Orca tanto sem credencial (`missing_credential`) quanto com credencial mockada (`ok=True`).
- **Coleta isolada anterior em `TEMP` sem `orca` nem `agy` no `PATH`:** `python -B -m collector collect-once` retornou código `0`, com `claude` e `antigravity` ambos em `result=success`, `freshness=fresh`, `quotas=2` e `windows=['rolling_5h', 'week']`.
