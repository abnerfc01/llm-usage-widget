# Integração OpenCode Go (Fonte Independente Somente Leitura)

## 1. Fonte Local e Endpoint Comprovados

A investigação local confirmou uma fonte independente para o OpenCode Go sem depender do Orca aberto, do seu cofre ou de CLI:

- **Credencial local (somente leitura):** arquivo padrão do OpenCode `auth.json` em:
  1. `credentials_path` / `opencode_credentials_path` / `auth_path` (quando configurado explicitamente);
  2. `$XDG_DATA_HOME/opencode/auth.json`;
  3. `~/.local/share/opencode/auth.json` (verificado neste ambiente);
  4. `%APPDATA%/opencode/auth.json`.
  O plugin lê exclusivamente a entrada `opencode-go.key` (API key do tipo `api`).
- **Endpoint de consumo (somente leitura):** `GET https://opencode.ai/zen/go/v1/usage` com cabeçalhos `Authorization: Bearer <key>` e `Accept: application/json`.
- **Estrutura de janelas retornada:** objeto `usage` contendo `rolling`, `weekly` e `monthly` (cada janela com `percent`, `resetsAt` e `status`).

## 2. Comprovação de `rolling` (5h) e Semântica de `percent` (Gasto)

- **Comprovação de `rolling` = 5 horas (`duration_seconds = 18000`):**
  1. Documentação/modelo do OpenCode Go define 3 janelas empilhadas: *5-hour rolling limit*, *weekly limit* e *monthly limit*.
  2. Implementação de referência do Orca (`app.asar`, função `ddr`) mapeia `usage.rolling` para `windowMinutes: 300` (5 horas) e `usage.weekly` para `windowMinutes: 10080` (7 dias).
  3. Propriedade observada na resposta real somente leitura de `GET https://opencode.ai/zen/go/v1/usage`: na janela `rolling` com `status='ok'` e `percent == 0`, o timestamp `resetsAt` menos o instante atual foi exatamente **`5.0` horas**.
- **Comprovação de `percent` = gasto (`used_percent`, não restante):**
  1. Propriedade observada na resposta real: janela `rolling` ociosa (`status='ok'`) reportou `percent == 0`, enquanto janela `monthly` atingida (`status='rate-limited'`) reportou `percent > 0`.
  2. Implementação de referência do Orca (`app.asar`, função `u$`) mapeia `e.percent` diretamente para `usedPercent` (sem inversão `100 - percent`).

## 3. Garantias de Segurança e Contrato

- **Sem Orca / sem CLI:** não executa `subprocess`, não acessa `orca_source` nem o cofre criptografado do Orca (`opencode-go-api-key.enc`).
- **No-refresh e sem geração paga:** apenas `GET` de leitura de uso; nunca renova tokens nem gera consumo.
- **Sem vazamento:** utiliza `collector.providers.http_util.get_json`; chaves, cabeçalhos e corpos brutos nunca aparecem em erros ou snapshots.
- **Mapeamento e validação estrita (Contrato v1):**
  - `rolling` → `id: "rolling_5h"`, `label: "5 horas"`, `duration_seconds: 18000`.
  - `weekly` → `id: "week"`, `label: "Semana"`, `duration_seconds: 604800`.
  - `monthly` → `id: "month"`, `label: "Mês"`, sem inferir `duration_seconds` de 30 dias sem duração explícita.
  - Janelas desconhecidas permanecem distintas pelo identificador sem duração inventada.
  - `percent` não finito (`NaN`, `inf`, `-inf`, `bool`) ou fora de `0..100` é rejeitado sem clamping para `0`/`100` falsos.

## 4. Verificação Executada

- **Suíte completa hermética (`python -B -m unittest discover -s tests -p "test_*.py"`):** **63/63** testes aprovados (sem rede real, sem acesso real a arquivos de credencial nem keyring durante os testes unitários).
  - `tests/test_opencode_go_source.py` (6 testes): mapeamento de janelas, rejeição de valores não finitos/fora de `0..100`, resolução de `auth.json`, `no-refresh` e falhas HTTP/rede/timeout sem vazamento.
  - `tests/test_independence.py` (2 testes): ambos bloqueando `orca`, `subprocess`, `_read_wincred_blob`, `_read_auth_file` e `urllib.request.urlopen`, validando independência de `antigravity` e `opencode_go` com credencial ausente e presente.
- **Prova isolada anterior em `TEMP` sem `orca` nem `agy` no `PATH`:** `python -B -m collector collect-once` retornou código `0`, `provider=opencode_go`, `result=success`, `freshness=fresh`, `quotas=3`, `windows=['rolling_5h', 'week', 'month']`.
