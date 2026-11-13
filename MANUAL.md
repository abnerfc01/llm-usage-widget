# Manual de uso — LLM Usage Widget (backend/coletor v1)

## Visão geral
Este repositório contém o **coletor** (backend) independente do processo/CLI do Orca. Ele lê fontes de uso **somente leitura** (sem gerar uso pago e sem renovar tokens) e publica um snapshot JSON contrato v1 para consumo pela skin Rainmeter.

- Código: `collector/` (plugins em `collector/providers/`)
- Config exemplo: `examples/config.example.json`
- Scripts reversíveis: `scripts/collect_once.ps1`, `scripts/collect_once.cmd`, `scripts/init_config.ps1`
- Diagnóstico Orca **opt-in** (não usado no fluxo padrão): `scripts/diagnose_orca_import.py`
- Snapshot/config padrão: `%LOCALAPPDATA%\LLMUsageWidget\config.json` e `%LOCALAPPDATA%\LLMUsageWidget\snapshot.json` (fora do repo e fora da pasta de skins/OneDrive)

## Instalação / preparo (reversível)
1. Requisitos: Windows, Python 3.12+ (testado com 3.12). Sem dependências externas.
2. Criar config padrão (não altera Rainmeter, não instala serviço):
   - PowerShell, na pasta do projeto: `py -3 -m collector init-config`
   - ou `.\scripts\init_config.ps1`
3. Ajuste `config.json` em `%LOCALAPPDATA%\LLMUsageWidget\` se quiser ativar/desativar/ordenar provedores. **Nunca** coloque credenciais/tokens no config nem no repo; use `credential_ref` apenas como identificador opaco para armazenamento externo.

## Coleta
- Uma vez: `py -3 -m collector collect-once` (ou `.\scripts\collect_once.ps1`)
- Loop em primeiro plano (intervalo em segundos, padrão 300): `py -3 -m collector collect-loop --interval 300`
- Snapshot válido pode ser inspecionado em `%LOCALAPPDATA%\LLMUsageWidget\snapshot.json`.

> Não instale agendamento/serviço automaticamente nesta fase. Se quiser agendar, faça manualmente (ex.: Tarefa Agendada) apontando para o comando acima — operação reversível (basta remover a tarefa).
> O caminho `snapshot_path` no config suporta expansão de `%LOCALAPPDATA%` e deve resultar em caminho absoluto; caminhos relativos são rejeitados para evitar gravação acidental no repo/OneDrive.

## Leitura das barras, cores e estados (alinhado ao contrato/design)
- **Porcentagens de cota**: `data.quotas[].used_percent` (0–100+, valor real). `0%` = uso medido zero (não implica "não iniciada"). Janela só é comparável quando equivalente (5h/semana/mês conforme informado).
- **Reset**: `window.reset_at` quando conhecido. `reset_at` no passado invalida **apenas aquela janela** (não o provedor inteiro). Sem `reset_at` não há contagem/marcador de ritmo.
- **Frescor por provedor**: `freshness.state` (`fresh|stale|never`) e `freshness.stale_after` são calculados pelo coletor no momento da publicação. A **skin deve recalcular** o estado a partir do relógio local, `last_success_at` e `stale_after` (e `reset_at` de cada janela), porque o arquivo não envelhece sozinho se o coletor parar. `generated_at` é a publicação do arquivo, não prova sucesso individual. Erro de tentativa pode coexistir com dado fresco (último sucesso preservado).
- **Erros seguros**: `error.code` em `missing_credential`, `auth_expired`, `network`, `timeout`, `provider_unavailable`, `unsupported`, `invalid_response`. A skin mapeia para textos pt-BR; nenhum segredo/resposta bruta é gravado.
- **Dinheiro/orçamento**: `data.money` usa `currency` ISO 4217 e valores como strings. `budget` é **referência local** (`source: local_config`); percentual só faz sentido com moeda, período e escopo compatíveis (decisão do consumidor/UI).

## Hover/click e UI
A interação (prévia no hover com atrasos, clique para fixar, gaveta) é responsabilidade da **skin Rainmeter** (fase posterior). O backend apenas publica o snapshot estável.

## Provedores e estados comuns
- **Claude**: leitura direta somente leitura (OAuth usage), **sem refresh**. Fonte configurável: `credentials_path` explícito na config; senão `~/.claude/.credentials.json`; se ausente/expirado, fallback read-only a perfil gerenciado localmente (`%APPDATA%\orca\claude-profiles\*\home\.credentials.json`) sem processo/CLI Orca e sem copiar token. Se nenhuma credencial válida encontrada → `auth_expired`/`missing_credential`.
- **Codex**: leitura direta via `~/.codex/auth.json` (endpoint de uso). Sem refresh.
- **Antigravity / OpenCode Go / Cursor**: sem fonte independente verificada nesta fase → `unsupported` ou `missing_credential` (estado seguro, sem dado inventado). Cursor pode exigir `cursor-agent login` quando aplicável.
- **Disabled**: `enabled=false` não gera alerta (`error=null`, `state=disabled`, `last_attempt_result=never`); a skin pode omitir ou mostrar como desativado.
- Falhas são isoladas por provedor; um provedor com erro não apaga o último sucesso dos demais nem o seu próprio último dado válido. Agendamento por provedor (`next_attempt_at`), com backoff em erro e sem forjar `last_attempt_at` em tentativas puladas/disabled. Providers são executados com timeout isolado (processo terminado em estouro).
- **Validação de payload**: o coletor aplica allowlist estrita em `data` e valida tipos; chaves desconhecidas (ex. tokens brutos) são descartadas e o provedor é marcado como `invalid_response`, sem afetar os demais.

## Refazer logins / credenciais
- O coletor **não renova tokens nem altera logins**. Para corrigir `auth_expired`/`missing_credential`, reautentique na ferramenta oficial correspondente (ex.: Claude/Cursor) e rode nova coleta.
- A fonte Claude é configurável conceitualmente; preferir fonte válida sem Orca aberto. Não copie segredos para o repo.

## Solução de problemas
- **Snapshot não atualiza**: verifique permissões em `%LOCALAPPDATA%\LLMUsageWidget\`, execute `collect-once` e confira `generated_at`. Se a escrita/validação falhar, `collect-once` retorna erro e exit code não-zero e o snapshot anterior é preservado.
- **Provider `unsupported`**: fonte independente ainda não verificada para aquele provedor; comportamento esperado (sem dado inventado).
- **Provider `auth_expired`**: credencial local expirada/inválida; refazer login na ferramenta oficial ou configurar `credentials_path`/fonte válida.
- **Coleta lenta/travada**: cada provider roda isolado com timeout e é terminado em estouro; verifique `error.code=timeout` por provedor.
- **Teste de independência**: o fluxo padrão não chama `orca`. `scripts/diagnose_orca_import.py` é diagnóstico opt-in separado.
- **Cache antigo**: um erro posterior preserva `last_success_at` e `data` anteriores; `last_attempt_result`/`error` refletem a última tentativa (não promove leitura de cache a novo sucesso). `next_attempt_at` controla quando nova tentativa ocorre. Se a origem do provedor mudar (plugin, `credential_ref`, `credentials_path`, `credential_source`), o cache anterior é invalidado via `origin_signature`.
- **Inspecionar snapshot**: `py -3 -m collector show-snapshot` (padrão) ou `py -3 -m collector show-snapshot --snapshot <caminho>` / `--config <caminho>`.

## Extensibilidade
Para adicionar provedor: criar `collector/providers/<nome>.py` com `collect(cfg, previous) -> {ok, data, kind|error}` e usar `plugin: "collector.providers.<nome>:collect"` no `config.json` — não é necessário editar o núcleo. Também é possível registrar em `collector/providers/__init__.py` para usar apenas o nome curto. Para APIs pagas por uso, usar `kind` `metered/mixed` e `data.money` (valores string, `currency` ISO 4217, budget local). Ver `examples/provider_api_metered.example.jsonc`.

O retorno do plugin deve conter apenas chaves permitidas em `data` (`quotas`/`money` com subcampos validados); chaves extras são descartadas.

