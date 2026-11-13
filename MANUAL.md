# Manual de uso — LLM Usage Widget

## Configurar contas pelo menu

Na pasta do projeto, dê dois cliques em **Configurar-provedores.cmd**. Também é possível abrir um PowerShell na pasta e executar `py -3 scripts/configurar_provedores.py`.

1. Escolha **1** para listar contas, conferir se estão ativas e visíveis, e ver ordem e intervalo.
2. Escolha **2**, selecione a conta pelo número e use o submenu para ativar/desativar, mostrar/ocultar, ajustar intervalo, ordem ou nome. Para Claude, há também a opção de informar o **caminho** do arquivo de credenciais; não digite o token.
3. Para uma API monetária, o submenu permite informar orçamento local, moeda e identificador de período. O percentual só aparece se o provedor fornecer gasto compatível com a moeda, o período e o escopo; o orçamento não impõe limite de cobrança.
4. Para adicionar uma conta, escolha **3**, digite nome, identificador simples (como `deepseek_api`) e tipo. A conta é criada desativada. Para cota percentual, o assistente cria um arquivo de modelo em `collector/providers/`. Para APIs monetárias, usa o modelo genérico.
5. **Criar a entrada não conecta automaticamente o serviço.** Um desenvolvedor precisa implementar e validar a consulta real do plugin; até lá, a conta não exibirá dados reais. Depois de pronta, ative-a pelo menu. Os modelos não pedem nem salvam chaves de API.

Cada alteração é salva em `%LOCALAPPDATA%\LLMUsageWidget\config.json`; o coletor em execução lê a configuração no ciclo seguinte. Use **0** para sair. Para encerrar sem alterar durante a escolha de conta, pressione Enter.

## Visão geral
Este repositório contém a skin Rainmeter e o **coletor** independente do processo/CLI do Orca. Ele lê fontes de uso **somente leitura** (sem gerar uso pago e sem renovar tokens) e publica um snapshot JSON contrato v1 para consumo pela skin Rainmeter.

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

> A inicialização automática desta máquina já foi configurada após a aprovação nativa. Não crie uma segunda instância do loop.
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
- **Antigravity**: consulta de cotas independente do Orca via credencial local do Windows, sem renovar tokens. Se aparecer `auth_expired`, abra o Antigravity para renovar a sessão ou entre novamente pela ferramenta oficial.
- **OpenCode Go**: consulta de cotas independente do Orca usando a credencial local da ferramenta. Se aparecer `missing_credential` ou `auth_expired`, confira o login no OpenCode.
- **Cursor**: sem fonte independente verificada nesta fase → `unsupported` ou `missing_credential`.
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


## Instalação definitiva nesta máquina — 12/11/2026

- Skin: C:\Users\Abner\OneDrive\Documentos\Rainmeter\Skins\LLMUsage\LLMUsage.ini.
- Coletor: D:\code\llm-usage-widget. Preserve a pasta enquanto a tarefa apontar para ela.
- Dados/configuração: %LOCALAPPDATA%\LLMUsageWidget\snapshot.json e config.json, fora do OneDrive.
- Tarefa Windows: LLMUsageWidget-Collector. Inicia no login do usuário com pythonw.exe em segundo plano, sem janela ou Orca. Verifica o ciclo a cada 60 segundos; os provedores respeitam o prazo individual, padrão 600 segundos.
- Posição inicial da skin: X=3220, Y=420, acima do relógio existente. Pode ser arrastada. LLMUsage-Validation permanece desativada.
- As skins illustro existentes foram preservadas.

### Leitura e interação

Passe o mouse sobre uma conta para abrir a prévia; clique para fixar e novamente para recolher. Use setas para páginas e a roda na gaveta para detalhes adicionais. As cores mudam em 25%, 50%, 75% e 90% de consumo. Só aparecem janelas realmente informadas pela fonte. Ausência de dado nunca significa 0%.

APIs monetárias exibem gasto/saldo. Quando há orçamento local compatível, mostram gasto curto e percentual; total e período ficam na gaveta/tooltip. Orçamento local não limita cobranças na API.

### Limitações atuais

Na coleta de 13/11 (America/Sao_Paulo), Claude, Codex, Antigravity e OpenCode Go retornaram dados. OpenCode Go fornece janelas de 5 horas, semanal e mensal. Cursor ainda não tem fonte independente comprovada. Os provedores precisam de credenciais válidas nas ferramentas oficiais; o coletor não renova tokens.

### Parar, retomar ou remover

No Agendador de Tarefas, procure LLMUsageWidget-Collector. Comandos PowerShell:

    Stop-ScheduledTask -TaskName 'LLMUsageWidget-Collector'
    Disable-ScheduledTask -TaskName 'LLMUsageWidget-Collector'

Para retomar:

    Enable-ScheduledTask -TaskName 'LLMUsageWidget-Collector'
    Start-ScheduledTask -TaskName 'LLMUsageWidget-Collector'

Para remover a inicialização definitivamente, pare a tarefa e execute:

    Unregister-ScheduledTask -TaskName 'LLMUsageWidget-Collector' -Confirm:$false

Para ocultar a skin: botão direito nela → Descarregar skin. Para reabrir: Gerenciar Rainmeter → LLMUsage → LLMUsage.ini → Carregar. Isso não afeta outros widgets. Preserve arquivos/configuração caso queira retomá-la; não apague a pasta geral do Rainmeter.
