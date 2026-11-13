# Correção de Cotas Exclusivas de Modelo / Grupo de Modelos (Antigravity)

**Data:** 13/11/2026  
**Arquivo alterado:** `skin/@Resources/Scripts/main.lua` (UTF-16 LE com BOM)  
**SHA-256 (`main.lua`):** `AEBC8C93003E524A284DE7EA27F35449C986D350C3CF55D3CB283D6EDA5679AF`  
**Nova suíte de testes:** `skin/tests/test_model_only.py` (SHA-256: `ECB54B1CC976A9BA1FCEAF81E118BDCBA7799A91B72D0D2F17C78D8AE75D0B76`)

---

## 1. Causa Raiz Identificada

Em `ProcessProvider` (`skin/@Resources/Scripts/main.lua`), a leitura de cotas de escopo `model` / `model_group` dependia de `p.h5`, `p.week` ou `p.month` já terem sido preenchidos por uma cota prévia de escopo `account`. Isso gerava dois problemas:
1. Contas sem cota geral `account` (como o Antigravity, que publica 2 cotas `model_group` nas janelas `rolling_5h` e `week`) exibiam a linha compacta vazia.
2. Quando uma cota de modelo mais restritiva aparecia **antes** da cota `account` no array `data.quotas`, a atribuição posterior da cota `account` sobrescrevia o resumo da janela, tornando a agregação dependente da ordem do JSON e ignorando o status de expiração individual.

---

## 2. Alterações Implementadas

1. **Agregação em Duas Passagens Independente da Ordem (`ProcessProvider` + `SelectWindowQuota`):**
   - **Passagem 1:** Coleta todas as cotas nas janelas equivalentes (`5h`, `week`, `month`) em `candidates["5h"]`, `candidates["week"]` e `candidates["month"]`, mantendo `p.extraQuotas` para demais janelas de `account` e preservando integralmente todas as cotas de escopo não-`account` em `p.models` para exibição na gaveta.
   - **Passagem 2 (`SelectWindowQuota`):** Para cada janela separadamente (sem misturar `5h`/`week`/`month` e sem converter `nil` em `0`), seleciona a cota com maior `usedPercent` válido e não expirado (`not isExpired`). Em empate exato, prefere escopo `account`. Se todas as cotas válidas da janela estiverem expiradas, preserva o estado expirado (`bestExpired`) para exibição como `…`.
   - O resumo selecionado carrega integralmente `usedPercent`, `resetEpoch`, `isExpired`, `resetText`, `modelTight = (scopeType ~= "account")`, `tightModelLabel` e `scopeType`.

2. **Marcador, Tooltip e Detalhes de Origem:**
   - Na tabela compacta (`RenderCompactPage`), cotas com `modelTight = true` mantêm o marcador `•` junto ao percentual (ex: `25%•`, `0%•`) e recebem `ToolTipText` específico na célula (`RowNColXText`) e agregado na linha (`RowNHitbox`), identificando `modelo` ou `grupo de modelos` e o respectivo rótulo.
   - Na gaveta (`RenderDrawer`), `DrawerWin1Reset`, `DrawerWin2Reset` e `DrawerWin3Reset` exibem o tempo de reset real da cota selecionada acrescido da origem (`(escopo grupo de modelos: <label>)` ou `(escopo modelo: <label>)`), enquanto os slots roláveis (`DrawerSlot1..4`) continuam listando todos os modelos/grupos.

---

## 3. Resultados das Suítes Executadas (Lua 5.1 Real via Lupa)

- `skin/tests/test_model_only.py`: **7/7 testes aprovados** (`0.078s`) — cobre conta `model_group` somente 5h/week, independência de ordem antes/depois de `account`, cota de modelo expirada ignorada frente a cota válida, cota de modelo válida substituindo `account` expirada, conta sem dados e `null` vs `0` explícito, isolamento entre `5h`/`week`/`month`, e preservação de estado em erro com cache.
- `skin/tests/runtime_qa.py` (inalterado): **36/36 testes aprovados** (`0.463s`).
- `skin/tests/test_live_geometry.py`: **8/8 testes aprovados** (`0.076s`).
- `skin/tests/test_skin_logic.py`: **4/4 testes aprovados** (`0.000s`).

Nenhuma instalação ativa do Rainmeter, configuração global, backend (`collector/`) ou histórico git foi alterado.
