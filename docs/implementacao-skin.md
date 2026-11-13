# Implementação da Skin (Staging) — Rainmeter «Uso de IA»

**Data:** 12/11/2026  
**Autora:** Miiaq (UI/UX Designer)  
**Status:** Correções S1–S8, N1–N5 e Resolução de Autoritatividade de SnapshotPath Concluídas e Aprovadas (32/32 testes no QA Lua 5.1 Real e 38/38 na suíte de testes de produto).  
**Alinhamento:** Respeita as decisões de `docs/decisoes-coordenador.md`, o contrato técnico v1 de `docs/contrato-coletor-proposta.md`, o relatório de auditoria `docs/revisao-skin-qa.md` e o relatório de validação nativa `docs/validacao-rainmeter-nativa.md`.

---

## 1. Hashes Criptográficos dos Arquivos de Staging (SHA-256)

| Arquivo | Hash SHA-256 |
|---|---|
| `skin/@Resources/Scripts/main.lua` | `A24A3DE9FFB2000C0B5E0BB2A3F4244C2050454A43EC595CC5AF39F751D01CF4` |
| `skin/LLMUsage.ini` | `F08CCC84B5CCA584FA4186A2E1778E75C8A895BA9217E0FB64FB78AD63EC81F1` |
| `skin/@Resources/Variables.inc` | `FFFFE0452D095D6BA82568774E49C10E0C7CADCAC4203C945992A7DDB213F792` |
| `skin/@Resources/Scripts/json.lua` | `3287FA1513EB3363AE309E07D4E0107F32F6F67411D27E57EC2020283FE8E1D1` |
| `skin/tests/test_skin_logic.py` | `4E799242CAEFDF23D095F62E18490F43C39EF6FD36DB9BA55D7724B79732794C` |
| `skin/tests/test_live_geometry.py` | `5C47622CE8F0290633AFE587D0ED0EA5590B33D3E82A70DE11B2E490AB2C97F3` |
| `skin/tests/runtime_qa.py` | `05A0A506F57681FF23365749E3216F4E2DE59882CCF865CC225C163D6BB4CE91` |

*Nota: O harness independente `skin/tests/runtime_qa.py` foi executado integralmente sem qualquer alteração por parte desta designer.*

---

## 2. Resultados dos Testes de QA (Antes vs. Depois)

### Execução no Harness Lua 5.1 Real (`skin/tests/runtime_qa.py` via Lupa):
- **Auditoria Inicial:** `Ran 23 tests FAILED (failures=19, errors=1)`
- **Pós S1–S8:** `Ran 23 tests in 0.108s OK`
- **Validação Nativa Pós N1–N5:** `Ran 30 tests in 0.189s OK`
- **Pós Ampliação da Suíte QA (SnapshotPath autoritativo):** `Ran 32 tests in 0.184s OK (32/32 testes aprovados)`
- **Suíte Estendida Atual de Regressões:** `Ran 36 tests in 0.424s OK (36/36 testes aprovados)`

### Execução da Suíte Própria de Geometria Dinâmica (`skin/tests/test_live_geometry.py`):
- `Ran 8 tests in 0.077s OK (8/8 testes aprovados)`

### Execução da Suíte de Lógica Offline (`skin/tests/test_skin_logic.py`):
- `Ran 4 tests in 0.001s OK (4/4 suites aprovadas)`

### Execução da Suíte Completa de Testes do Coletor (`tests/`):
- `Ran 38 tests in 4.269s OK (38/38 testes aprovados)`

---

## 3. Resolução Detalhada dos Bloqueadores S1–S8 e Melhorias Iniciais

### S1: Validação Transacional de Envelope, Provedores, Cotas e Nulls
- **Problema:** Erro de tipo (ex: `data.quotas="wrong"`, `providers=null`, `providers=[null]`) quebrava o parser em tempo de execução ou sobrescrevia indevidamente o estado válido anterior com lista vazia.
- **Correção:**
  - Implementada a função `ValidateAndProcessSnapshot(parsed)` que valida transacionalmente todos os níveis do JSON antes de promover a nova lista.
  - Rejeição prévia de arrays com valores nulos (`rawText:match("%[%s*null%s*[,%]]")`), prevenindo que o decodificador omita índices e gere listas corrompidas.
  - Em qualquer falha de validação ou leitura (`status == false`, tipo incompatível, schema inválido), a skin **preserva integralmente a lista anterior** (`lastValidProvidersList`), ativa `staleReadError = true` e exibe `! Leitura falhou` no rodapé.

### S2: Correção de Bangs de Grupo e Limpeza Visual de Estado
- **Problema:** Chamadas a `!ShowMeter Row1Col1` e `!HideMeter Row1Col1` falhavam no Rainmeter pois `Row1Col1` é um `Group` e não um meter. Além disso, a alternância de orçamentos deixava resíduos de valores anteriores visíveis.
- **Correção:**
  - Substituição sistemática por `!ShowMeterGroup` e `!HideMeterGroup` para as células de colunas (`RowNCol1`, `RowNCol2`, `RowNCol3`).
  - Ao alternar ou ocultar uma coluna, o texto é limpo com `Text=""` e a largura da barra é zerada, impedindo persistência visual de valores desatualizados.

### S3: Inclusão de Hitboxes em Grupos e Contenção Física Estrita
- **Problema:** As hitboxes das linhas 1 a 5 (`Row1Hitbox` .. `Row5Hitbox`) não possuíam `Group=RowN`, permanecendo visíveis quando o grupo da linha era ocultado. Em áreas restritas, meters como `DrawerTip` ultrapassavam o viewport.
- **Correção:**
  - Adicionado `Group=RowN` a todas as 5 seções `[RowNHitbox]` em `skin/LLMUsage.ini`.
  - **Espaço Nulo (`availableHeight <= 0`):** Toda a skin e todos os seus meters recebem `!HideMeter`, e `SkinHeight` é ajustado para `0`.
  - **Espaço Ínfimo (`availableHeight <= 50 px`):** Apenas os meters com cota inferior `<= availableHeight` permanecem visíveis (título e botões de cabeçalho). Linhas, colunas, rodapé e gaveta são ocultados.
  - **Espaço Parcial (`150 px`):** Ocultação da linha 5 (inclusive hitbox) e reposicionamento dinâmico do rodapé para encostar na base da linha 3 (`SkinHeight = 136`).
  - **Gaveta Controlada por Posição Real (`300 px`, `450 px`, `600 px`):** Cada meter da gaveta é testado contra `availableHeight`. Se a cota inferior ultrapassar o limite, recebe `!HideMeter`. O meter `[DrawerTip]` só é exibido se `498 <= availableHeight`. O `SkinHeight` acompanha rigorosamente a base do último elemento visível, eliminando qualquer transbordamento.

### S4: Recálculo Determinístico de Frescor sem Dependência de Nova Publicação
- **Problema:** Provedor com `stale_after` vencido mantinha estado `fresh` se o coletor parasse de publicar novos snapshots.
- **Correção:**
  - O loop de 1 segundo (20 ticks a 50 ms) em `Update()` compara o horário atual (`os.time()`) com `acc.staleAfterEpoch`.
  - Ao ultrapassar `stale_after`, o provedor transiciona para `stale`, incrementa o contador de alertas e redesenha a interface com aviso no rodapé e estilo esmaecido.

### S5: Apresentação de Cache Antigo em Erro e Estilo Visual Stale
- **Problema:** Provedor com erro transitório na última tentativa mas com dados em cache ocultava as cotas válidas e exibia apenas texto de erro; cotas obsoletas mantinham cores ativas em vez de esmaecidas.
- **Correção:**
  - Se o provedor possui cache (`hasCache = true`), as cotas anteriores continuam visíveis na tabela compacta.
  - Caso o provedor esteja com erro ou com estado `stale`, os percentuais e barras utilizam o estilo atenuado `COLOR_MUTED` (`255,255,255,150`), diferenciando dado histórico de dado fresco.

### S6: Exibição de Saldo em Linha Compacta para APIs Pré-pagas
- **Problema:** Contas do tipo `kind=metered` com saldo (`balance`) mas sem orçamento configurado ficavam com a linha compacta em branco.
- **Correção:**
  - Contas monetárias sem orçamento utilizam a primeira coluna para exibir o saldo disponível (`Row1Col1Text` com valor formatado, ex: `US$ 4.20`), mantendo a informação compacta visível conforme o design spec.

### S7: Diferenciação entre Null e Zero Medido
- **Problema:** Cotas com `used_percent: null` eram convertidas indevidamente para `0%` por fallback numérico.
- **Correção:**
  - Ausência de valor (`null`) é tratada como `nil`. O widget omite o percentual ou exibe `—`, reservando `0%` exclusivamente para quando o provedor reportar zero medido.

### S8: Sanitização Estrita de Identificadores contra Travessia de Diretório
- **Problema:** Provedores com IDs maliciosos ou anômalos (ex: `..\..\QA_ESCAPE`) podiam tentar acessar arquivos fora de `Icons/`.
- **Correção:**
  - Validação regex estrita do ID: `acc.id:match("^[A-Za-z0-9_%-]+$")`.
  - IDs que contenham caracteres especiais, pontos ou barras são impedidos de consultar o disco e utilizam diretamente `default.png`.

---

## 4. Resolução Detalhada dos Achados da Validação Nativa (N1 a N5)

### N1: Tokenização e Suporte a Whitespace no Parser `json.lua` (Bloqueador)
- **Problema Identificado:** O `json.lua` continha `delim_chars` restrito a `{"{", "}", "[", "]", ":", ","}`, sem incluir caracteres de espaçamento (`" "`, `"\t"`, `"\r"`, `"\n"`). Quando o coletor publicava JSON real formatado (ex: `"stale_after": null\n`), a rotina `parse_literal` consumia além do token literal, resultando em erro `invalid literal 'null\r\n'` e silenciando todo o snapshot válido.
- **Correção:**
  - Restaurado `delim_chars = create_set(" ", "\t", "\r", "\n", "]", "}", ",")`, conforme especificação canônica do decodificador rxi, preservando a licença MIT no cabeçalho.
  - O decodificador agora aceita legitimamente quebras de linha (LF, CRLF), tabs e espaços adjacentes a literais (`null`, `true`, `false`) e números (`123`, `1.25`).
  - O snapshot real emitido pelo coletor em Python é parseado integralmente sem requerer minificação ou qualquer alteração no backend.
  - Aprovado no teste QA `test_collector_atomic_writer_bytes_parse_without_compaction` e na matriz de testes de whitespace.

### N2: Resolução Dinâmica de Geometria em Múltiplos Monitores (Bloqueador)
- **Problema Identificado:** Em sistemas com múltiplos monitores (ex: primário vertical de 1920p e secundário horizontal de 1080p), o Rainmeter expõe as variáveis globais não qualificadas `#WORKAREAHEIGHT#` e `#WORKAREAY#` baseadas exclusivamente no monitor primário se o monitor atual não for resolvido. Quando a skin era posicionada no monitor secundário (ex: `Y=930`, com apenas 150 px disponíveis até a borda), o widget presumia 990 px livres e mantinha layout de 5 linhas.
- **Correção:**
  - Adicionada a diretiva `AutoSelectScreen=1` na seção `[Rainmeter]` de `skin/LLMUsage.ini`.
  - Implementada em `main.lua` a função `GetCurrentMonitorWorkArea()`, que consulta as variáveis `#WORKAREAX@N#`, `#WORKAREAY@N#`, `#WORKAREAWIDTH@N#` e `#WORKAREAHEIGHT@N#` para os monitores `N=1..10`.
  - A detecção cruza a posição corrente (`CURRENTCONFIGX`, `CURRENTCONFIGY`) com a geometria de cada display, suportando coordenadas negativas (monitores à esquerda ou acima do primário) e áreas de tarefa personalizadas.
  - A altura útil restante (`availableHeight`) é calculada estritamente sobre a área do monitor ativo da skin. Em 150 px físicos restantes, o widget reduz para 3 linhas (`SkinHeight=136`); em 50 px, entra em modo título recolhido (`SkinHeight=34`), sem overflow.
  - Aprovado no teste QA `test_secondary_monitor_workarea_at_bottom_positions`.

### N3: Codificação Nativa UTF-16 LE com BOM para Fontes GDI e Strings
- **Problema Identificado:** Glifos de paginação `‹` e `›`, o marcador `•` e títulos acentuados como `DADOS SINTÉTICOS`, `MÊS` e textos em pt-BR sofriam corrupção de mojibake (ex: `SINTÃ‰TICOS`), pois o subsistema GDI do Rainmeter em Windows requer UTF-16 LE com BOM (`\xFF\xFE`) para fontes e arquivos `.ini`/`.inc`/`.lua` que contenham caracteres além da faixa ASCII básica.
- **Correção:**
  - Os arquivos `skin/LLMUsage.ini`, `skin/@Resources/Variables.inc` e `skin/@Resources/Scripts/main.lua` foram re-salvos com codificação UTF-16 LE com BOM binário explícito.
  - O código Lua e os bangs continuam emitindo caracteres nativos da língua portuguesa (`DADOS SINTÉTICOS`, `USO DE IA (recolhido)`, `Sem dados disponíveis`, `Orçamento (ref. local)`), agora renderizados sem distorção pelo GDI do Rainmeter.
  - Aprovado no teste QA `test_rainmeter_source_with_unicode_uses_utf16le`.

### N4: Bounding Box, Formatação pt-BR e Apresentação Dedicada de Orçamento e Dinheiro
- **Problema Identificado:** Em contas com `kind=metered`, strings monetárias longas (ex: `US$ 12.40 de 20` ou `US$ 4.20`) gravadas em `RowNCol1Text` com `StringAlign=Right` em `X=116` expandiam para a esquerda e invadiam o retângulo do nome do provedor em `RowNName` (`X=25`, `W=53`, abrangendo de 25 a 78 px). Além disso, na revalidação nativa no Windows GDI, a string `"US$ 12.40 de 20"` sofria truncamento para `"US$ 12.40 de..."` dentro da área restrita de 78 px.
- **Decisão de Design e Correção:**
  - **Contas com Orçamento Casado (`acc.budgetMatch`):** A linha compacta exibe o valor gasto curto em pt-BR (ex: `US$ 12,40`) em `RowNCol1Text` (`X=158`, `W=78`, `ClipString=1`, `StringAlign=Right`), eliminando qualquer risco de truncamento por excesso de caracteres. A coluna do mês (`RowNCol3Text`) exibe a porcentagem consumida com barra colorida. O valor total de referência e o período correspondente são apresentados de forma completa e legível no `ToolTipText` do mouse (`"Gasto US$ 12,40 de orçamento US$ 20,00 (Novembro)"`) sobre o texto, hitbox e porcentagem, bem como no detalhe da gaveta (`DrawerWin3Reset`).
  - **Contas Monetárias sem Orçamento (`acc.money`):** Utilizam o span total disponível das três colunas (`X=200`, `W=120`, `ClipString=1`, `StringAlign=Right`), permitindo folga ampla para apresentação do saldo disponível (ex: `US$ 4.20`) com `ToolTipText` detalhado (`"Saldo disponível: US$ 4,20"`).
  - Ao alternar para contas padrão de cotas, a coluna restaura `X=116`, `W=36`, `ClipString=0` e limpa os tooltips.
  - Aprovado no teste QA `test_compact_money_text_does_not_enter_provider_name_box` e `test_metered_without_budget_has_compact_money_value`.

### N5: Redução Efetiva da Janela Nativa e Prevenção de Bloqueio por `KeepOnScreen`
- **Problema Identificado:** Mesmo com a skin compacta (corpo de 186 px), a janela nativa do Windows reportada pelo sistema operacional media 213×484 px na auditoria inicial, e na revalidação nativa reportou 156 px fixos no secundário (`Y=930` e `Y=1030`) mesmo quando o corpo reduzia para 136 px ou 34 px. A causa raiz exata identificada: no Rainmeter com `DynamicWindowSize=1`, meters inativos/ocultos (especialmente os trilhos da Linha 5 em `Y=156` e meters da gaveta com `H > 0`) mantinham posições estáticas e dimensões não zeradas no GDI, estendendo o bounding box nativo da janela para 156 px.
- **Correção:**
  - Implementadas em `main.lua` as tabelas canônicas de métricas `rowMeterDefs` e `drawerMeterDefaultMetrics`, juntamente com as funções `RestoreRowMetrics(r)`, `CollapseRowMetrics(r, targetH)` e a expansão de `CollapseDrawerMeters(targetH)`.
  - **Colapso Dinâmico de Linhas e Meters Inativos:** Ao reduzir o número de linhas (`itemsPerPage < 5`) ou recolher o corpo (`isSpaceCollapsed` / `availableHeight <= 50`), todos os meters das linhas inativas têm suas posições Y movidas dinamicamente para `targetHeight` e suas dimensões zeradas (`H=0`, `W=0`), além de receberem `!HideMeterGroup`.
  - Cabeçalhos de coluna (`MeterCol5H`, `MeterColWeek`, `MeterColMonth`), aviso de estado vazio (`MeterEmptyNotice`), rodapé (`FooterSeparator`, `MeterFooterSnapshot`, `MeterFooterAlert`) e meters da gaveta (`DrawerGroup`) também têm suas cotas Y e dimensões colapsadas para `targetHeight` quando inativos.
  - Ao expandir ou restaurar linhas, `RestoreRowMetrics(r)` e `SafeShowMeter` recompõem os valores originais de Y, W e H definidos no design spec.
  - Como resultado, a extensão física nativa da janela do Rainmeter acompanha rigorosamente a altura do corpo (`SkinHeight = 136 px` em `Y=930` e `SkinHeight = 34 px` em `Y=1030`), sem qualquer pixel excedente além da área útil restante.
  - Aprovado nos testes QA `test_secondary_monitor_workarea_at_bottom_positions` e `test_small_viewports_contain_every_visible_meter`.

---

## 5. Autoritatividade Estrita de `SnapshotPath` e Isolamento de Cache

- **Problema Identificado:** Quando uma variável `SnapshotPath` era explicitamente configurada (ex: apontando para uma pasta isolada de teste), mas o arquivo estava temporariamente ausente, a rotina `ResolveSnapshotPath()` executava fallback silencioso para `%LOCALAPPDATA%\LLMUsageWidget\snapshot.json`. Isso violava o isolamento de teste/usuário e podia exibir dados da conta pessoal quando um caminho customizado falhava.
- **Decisão e Correção:**
  - `SnapshotPath` não vazio e diferente do marcador não resolvido `#SnapshotPath#` é estritamente **autoritativo**.
  - Se configurado, a skin consulta exclusivamente este caminho. Se o arquivo estiver ausente ou inacessível, **não há fallback** para `%LOCALAPPDATA%` nem para fixture.
  - O fallback padrão para `%LOCALAPPDATA%\LLMUsageWidget\snapshot.json` ocorre **única e exclusivamente** se `SnapshotPath` for vazio ou não definido.
  - O uso de fixtures sintéticas requer estritamente `UseSyntheticFixture=1` com banner explícito.
  - Implementado isolamento de cache transacional por identificador de origem (`lastSnapshotOrigin`). Caso o usuário altere `SnapshotPath` (ex: de uma pasta A para pasta B), o cache de dados válidos da origem anterior é **imediatamente invalidado**, impedindo a apresentação indevida de dados da conta anterior.
  - Aprovado no novo teste QA `test_missing_explicit_snapshot_path_does_not_fall_back_to_user_cache`.

---

## 6. Detecção Dinâmica de Geometria ao Vivo (`Update()`) e Resolução do Período de Orçamento

### 6.1 Reflow Dinâmico Durante Movimentação sem `!Refresh`
- **Problema Identificado no QA Final:** Ao mover a skin para posições inferiores no monitor secundário (ex: `Y=930` com 150 px disponíveis ou `Y=1030` com 50 px disponíveis), a janela permanecia com 187 px após 3 segundos e após `!Update`. A readequação para 137 px ou 35 px só ocorria após `!Refresh`. O código anterior apenas invocava `UpdateLayoutBounds()` durante `Initialize()` e `RefreshSnapshot()`, sem detectar movimentação durante o ciclo `Update()`.
- **Correção:**
  - Implementada a função `CheckLiveGeometry(force)` executada no início de `Update()`.
  - **Consulta Leve:** Lê `CURRENTCONFIGX`, `CURRENTCONFIGY` e a geometria da área útil do monitor via variáveis em memória (`SKIN:GetVariable`). Se as coordenadas não tiverem mudado em relação ao último tick, a função retorna imediatamente em 0 ms sem disparar nenhum Bang, sem atualizar meters e sem chamar `!Redraw`.
  - **Reflow Sob Mudança:** Ao detectar alteração nas coordenadas ou no monitor de exibição, executa `UpdateLayoutBounds()`, `RenderCompactPage(false)`, reposiciona o rodapé, recolhe/restaura meters das linhas e da gaveta, e emite `!UpdateMeter BackgroundBody` e `!Redraw`.
  - **Preservação de Interação:** Caso a gaveta estivesse fixada (`isDrawerPinned = true`), ela é temporariamente ocultada em viewports insuficientes (`availableHeight < compactHeight + 70`) para prevenir overflow e automaticamente reaberta em altura plena ao retornar a uma área com espaço suficiente, sem exigir novo clique do usuário. A página corrente (`currentPage`) é preservada.
  - Aprovado na nova suíte `skin/tests/test_live_geometry.py` (8/8 testes).

### 6.2 Propagação de `period.label` ("Novembro") em Orçamentos
- **Problema Identificado:** A gaveta e tooltips exibiam `(mês)` em vez do nome específico do período configurado no snapshot (ex: `"Novembro"`). A função `MatchBudget` não retornava o objeto `period` no resultado correspondido, fazendo com que `FormatPeriodName` recebesse `nil` e recaísse no fallback genérico `"mês"`.
- **Correção:**
  - `MatchBudget` agora retorna o campo `period = bPeriod or sPeriod`.
  - `FormatPeriodName(p)` aceita tanto tabela de período (`p.label`, `p.name`, `p.id`) quanto string de ID (ex: `"2026-11"`). Prioriza o rótulo explícito (ex: `"Novembro"`) e deriva o mês por extenso em português a partir do padrão ISO `YYYY-MM`.
  - Tooltips da linha compacta (`RowNCol1Text`, `RowNCol3Text`, `RowNHitbox`) e o descritivo da gaveta (`DrawerWin3Reset`) agora exibem `"Gasto US$ 12,40 de orçamento US$ 20,00 (Novembro)"`.
  - Aprovado em `test_live_geometry.py` (`test_budget_period_label_novembro`).

---

## 7. Resumo da Conformidade

Todas as correções foram implementadas nos arquivos de staging em `skin/` e validadas nas suítes automatizadas offline:
- `skin/tests/runtime_qa.py`: 36/36 testes aprovados (incluindo todas as 32 regressões originais).
- `skin/tests/test_live_geometry.py`: 8/8 testes aprovados (geometria ao vivo, 150/50px, retorno seguro, monitor negativo, persistência de página/gaveta e período 'Novembro').
- `skin/tests/test_skin_logic.py`: 4/4 testes aprovados.
- `tests/`: 38/38 testes de produto aprovados.

O staging em `skin/` permanece pronto e offline para que a equipe de QA realize a sincronização e revalidação nativa no Rainmeter real.
