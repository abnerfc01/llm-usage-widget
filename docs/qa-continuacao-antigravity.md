# QA Independente: Preparação e ampliação de regressões offline Lua 5.1

**Data:** 12/11/2026  
**Agente:** Antigravity (QA Independente)  
**Tarefa Orca:** `task_529c36b44550` (Dispatch `ctx_b34dc7c409d0`)  
**Status da preparação:** **Concluída com sucesso.** Suíte offline ampliada de 32 para 36 testes; 36/36 aprovados.  
**Alinhamento:** Respeita as decisões de `docs/decisoes-coordenador.md`, o contrato técnico v1 de `docs/contrato-coletor-proposta.md`, `docs/validacao-rainmeter-nativa.md`, `docs/revalidacao-rainmeter-nativa.md`, `docs/revalidacao-rainmeter-final.md` e `docs/revisao-integracao-regressoes.md`.

---

## 1. Escopo e Isolamento Estrito

- **Arquivos modificados por QA:** Exclusivamente `skin/tests/runtime_qa.py` e este relatório `docs/qa-continuacao-antigravity.md`.
- **Arquivos intocados por QA:** Nenhum arquivo de produto (`skin/LLMUsage.ini`, `skin/@Resources/*`), backend (`collector/`), git, kanban ou cópia de validação do Rainmeter foi editado por este QA.
- **Ambiente de execução dos testes:** O harness executa `main.lua` e `json.lua` reais via runtime oficial Lua 5.1 (`Lupa`), apontando `PYTHONPATH` isoladamente para `%TEMP%\llm-usage-widget-luaqa`. Nenhuma biblioteca foi instalada globalmente.
- **Isolamento de dados e rede:** Nenhum acesso à rede, coleta real, credencial ou resposta privada de LLM foi realizada. Todos os cenários utilizam estruturas sintéticas herméticas. O Rainmeter nativo **não** foi ativado nesta etapa preparatória, aguardando a rodada de validação nativa autorizada pela coordenação.

---

## 2. Hashes Criptográficos dos Arquivos Observados (SHA-256)

| Arquivo | Hash SHA-256 | Papel no projeto |
|---|---|---|
| `skin/LLMUsage.ini` | `F08CCC84B5CCA584FA4186A2E1778E75C8A895BA9217E0FB64FB78AD63EC81F1` | Produto (Skin INI staging) |
| `skin/@Resources/Scripts/main.lua` | `A24A3DE9FFB2000C0B5E0BB2A3F4244C2050454A43EC595CC5AF39F751D01CF4` | Produto (Lógica Lua staging, atualizada por Miiaq) |
| `skin/@Resources/Scripts/json.lua` | `3287FA1513EB3363AE309E07D4E0107F32F6F67411D27E57EC2020283FE8E1D1` | Produto (Parser JSON rxi com Whitespace N1) |
| `skin/@Resources/Variables.inc` | `FFFFE0452D095D6BA82568774E49C10E0C7CADCAC4203C945992A7DDB213F792` | Configuração staging |
| `skin/@Resources/Styles.inc` | `3B787A29FF25265710C13AA5F0E35FA8C4468A29786768FE26C56AF558B361B2` | Estilos visuais staging |
| `skin/tests/runtime_qa.py` | `05A0A506F57681FF23365749E3216F4E2DE59882CCF865CC225C163D6BB4CE91` | Harness offline Lua 5.1 (ampliado para 36 testes) |
| `skin/tests/test_skin_logic.py` | `4E799242CAEFDF23D095F62E18490F43C39EF6FD36DB9BA55D7724B79732794C` | Suíte unitária Python da lógica de skin |

*Nota de versão concorrente:* O hash anterior de `main.lua` era `D06039692B357F38108C02EE0E5960B48911BDE1E41BC16A22870A2A1B7C4D66`. Durante a execução da tarefa paralela `task_e881dff91a00`, a designer Miiaq atualizou `main.lua` para a versão `A24A3DE9FFB2000C0B5E0BB2A3F4244C2050454A43EC595CC5AF39F751D01CF4`.

---

## 3. Comandos e Resultados de Execução

Comandos executados a partir da raiz `D:\code\llm-usage-widget`:

```powershell
$env:PYTHONPATH = Join-Path $env:TEMP 'llm-usage-widget-luaqa'
python -B skin/tests/runtime_qa.py -v
python -B skin/tests/test_skin_logic.py
python -B -m unittest discover -s tests -q
```

### Sumário dos Testes Automatizados:

1. **Harness Lua 5.1 Real (`skin/tests/runtime_qa.py` via Lupa):**
   - **Total de testes:** 36 executados.
   - **Resultado:** **36/36 aprovados (Ran 36 tests in 0.499s OK).**
   - **Preservação:** Todas as 32 asserções originais permaneceram intactas e verdes.
   - **Novos testes:** 4 novos testes implementados e aprovados.

2. **Lógica Offline da Skin (`skin/tests/test_skin_logic.py`):**
   - **Total de testes:** 4 executados.
   - **Resultado:** **4/4 aprovados (Ran 4 tests in 0.001s OK).**

3. **Backend e Regressões Coletor (`tests/`):**
   - **Total de testes:** 43 executados (incluindo regressão temporal `test_temporal_cache_regression.py`).
   - **Resultado:** **43/43 aprovados (Ran 43 tests in 4.111s OK).**

---

## 4. Detalhamento dos Novos Testes Adicionados

| Nome do Teste | O que exercita e valida | Resultado |
|---|---|---|
| `test_move_without_refresh_updates_geometry_and_safe_return` | Inicializa a skin em posição segura (`X=1400, Y=120`, área disponível de 960 px no monitor secundário). Altera `CURRENTCONFIGY` para `930` (150 px disponíveis até a borda inferior) e invoca `Update()` **sem** chamar `RefreshSnapshot()` ou `Initialize()`. Exige que `SkinHeight <= 150` e nenhum meter transborde (`overflowing(150) == []`). Em seguida, move para `Y=1030` (50 px disponíveis) chamando `Update()`, exigindo `SkinHeight <= 50` sem transbordo. Por fim, executa o **retorno seguro** para `Y=120`, comprovando que ao chamar `Update()` a skin restaura integralmente a altura compacta (`SkinHeight = 186`) e os meters da linha 1 permanecem visíveis. | **Aprovado** |
| `test_negative_monitor_coordinates_geometry` | Configura topologia multi-monitor contendo display secundário com coordenadas negativas à esquerda do primário (`WORKAREAX@2 = -1920, WORKAREAY@2 = 0, WORKAREAWIDTH@2 = 1920, WORKAREAHEIGHT@2 = 1080`). Valida que `GetCurrentMonitorWorkArea()` mapeia corretamente coordenadas negativas (`X=-1400`), reduz o layout em `Update()` sem refresh para 150 px e 50 px, e recompõe na posição segura. | **Aprovado** |
| `test_budget_matching_period_shows_specific_month_label` | Fornece gasto e orçamento combinados para conta monetária onde `period` define `id="2026-11"` e `label="Novembro"`. Comprova que o `ToolTipText` da coluna compacta (`Row1Col1Text`) e a gaveta detalhada de orçamento (`DrawerWin3Reset`) apresentam explicitamente `"Novembro"` e **não** exibem o termo genérico `"(mês)"`. | **Aprovado** |
| `test_budget_specific_month_derived_from_period_id` | Fornece período sem o campo explícito `label`, apenas com `id="2026-03"`. Valida a conversão determinística por `FormatPeriodName` para o nome por extenso em português (`"Março"`), garantindo que tanto o tooltip quanto a gaveta reflitam `"Março"` sem recair em fallback genérico. | **Aprovado** |

---

## 5. Análise Técnica das Alterações de Produto Observadas em Staging

A verificação do código atualizado de `skin/@Resources/Scripts/main.lua` (`A24A3DE9FFB2000C0B5E0BB2A3F4244C2050454A43EC595CC5AF39F751D01CF4`) confirmou as seguintes implementações pela designer Miiaq:

1. **Detecção Dinâmica de Movimentação em `Update()` (CheckLiveGeometry):**
   - Foi introduzida a rotina `CheckLiveGeometry(force)` no início de cada tick de `Update()`.
   - Compara as variáveis `CURRENTCONFIGX/Y` e as dimensões da área de trabalho do monitor atual (`lastWorkX/Y/W/H`).
   - Caso haja deslocamento, reexecuta `UpdateLayoutBounds()`, redimensiona e recompõe os meters da página compacta e da gaveta sem exigir intervenção manual ou `!Refresh` do usuário.
2. **Preservação de Objeto de Período em `MatchBudget()`:**
   - Na função `MatchBudget()`, o retorno da tabela passou a incluir explicitamente `period = bPeriod or sPeriod`.
   - Essa preservação permite que `FormatPeriodName(b.period and b.period.id)` receba o identificador ou label do período e formate meses como `"Novembro"` e `"Março"`, eliminando o bug anterior que recebia `nil` e emitia `"(mês)"`.

---

## 6. Estado Atual e Próximos Passos (Transição para Validação Nativa)

1. **Estado Offline:** Todas as 36 verificações em Lua 5.1 real e 43 testes de backend em Python estão **100% aprovados e verdes**.
2. **Bloqueador Pendente:** A validação final ainda depende de **reteste nativo no Rainmeter instalado**, pois testes em stub/harness offline não avaliam o subsistema de renderização DirectWrite/GDI real do Windows, medição física de fontes, nem o comportamento exato de `KeepOnScreen=1` com o gerenciador de janelas.
3. **Escopo Futuro da Validação Nativa (quando liberada pela Coordenação):**
   - Conferir que `Rainmeter.exe` está ativo e verificar o `SkinPath`.
   - Utilizar exclusivamente a pasta isolada `LLMUsage-Validation`, realizando backup antes de qualquer teste e restaurando byte a byte ao final.
   - Preservar integralmente o estado `Active` e as posições das skins `illustro`.
   - Testar o reposicionamento sem refresh no Rainmeter para `Y=930` e `Y=1030` no monitor secundário, verificando o redimensionamento nativo da janela e ausência de clipping.
   - Confirmar visualmente os glifos pt-BR, o período `"Novembro"` e a formatação monetária `US$ 12,40`.
