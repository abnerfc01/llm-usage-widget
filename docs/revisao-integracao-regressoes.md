# Regressões offline da integração coletor → skin

**Escopo:** somente `skin/tests/runtime_qa.py` e este relatório foram editados por QA. O harness executa `main.lua` e `json.lua` reais em Lua 5.1 via Lupa isolado em TEMP; não inicia Rainmeter, plugins de provedor, contas ou rede. Os cenários usam valores sintéticos. O relatório [nativo anterior](validacao-rainmeter-nativa.md) permanece a referência para o comportamento visto no Rainmeter.

## Revisões observadas durante a execução

Miiaq alterou o produto em paralelo entre os testes. QA não editou `skin/` fora de `skin/tests/runtime_qa.py`, nem a cópia `LLMUsage-Validation`, configurações do Rainmeter ou git.

| Arquivo | Antes, observado a partir de 13:26 | Depois, observado às 17:22–17:24 (America/Sao_Paulo) |
| --- | --- | --- |
| `skin/LLMUsage.ini` | `3CA64DAB263DF3C0DA3C621A78D73916B35B11A14124C0C019B7EBC0BC678983` | `F08CCC84B5CCA584FA4186A2E1778E75C8A895BA9217E0FB64FB78AD63EC81F1` |
| `skin/@Resources/Scripts/main.lua` | `68CBEBBCBA5FF7C054504F938B97468C24426373455E9E5A5399798CDCE01DAD` | `4D8057B6CFC5F76FFAA6E18FF18420ABBDD62F5C0DD7BA0E1DFA9B004C36E75D` |
| `skin/@Resources/Scripts/json.lua` | `6439A20CE3C8C3522FED93D5AC91813738B2D1A2FDFA25A2A01A6A3134C85B2B` | `3287FA1513EB3363AE309E07D4E0107F32F6F67411D27E57EC2020283FE8E1D1` |
| `collector/contract.py` | `478F3CA218F77BB982A4C2BF3252C6999C9E518295D44B0B3E43DAB68512886F` | mesmo hash |

O arquivo `Variables.inc` também foi atualizado pela designer; não havia hash inicial registrado para compará-lo. Na revisão final, seu SHA-256 foi `FFFFE0452D095D6BA82568774E49C10E0C7CADCAC4203C945992A7DDB213F792`. O hash final de `Styles.inc` foi `3B787A29FF25265710C13AA5F0E35FA8C4468A29786768FE26C56AF558B361B2`.

## Testes e resultados

Comando executado da raiz do projeto:

```powershell
$env:PYTHONPATH = Join-Path $env:TEMP 'llm-usage-widget-luaqa'
python -B skin/tests/runtime_qa.py
python -B skin/tests/test_skin_logic.py
```

Antes da alteração da Miiaq, a primeira versão ampliada do harness executou **28 testes, 8 falhas e 12 erros**. Os 23 testes anteriores não falharam; os erros novos foram `null`/`true`/`false` seguidos de whitespace, e números com whitespace já passavam. Corrigida uma asserção do próprio teste que esperava `"data": null` sem a vírgula emitida pelo serializer, sem reduzir a exigência de leitura do arquivo integral. Após a atualização da designer, os cenários separados rodaram **30/30 verdes** e os sete testes novos direcionados **7/7 verdes**. Depois foram acrescentados dois casos de `SnapshotPath`: **32 executados, 31 verdes e 1 vermelho** (a falha de isolamento descrita abaixo); uma execução da suíte excluindo apenas esse caso confirmou **31/31 verdes** às 17:26. `test_skin_logic.py` executou **4/4 verdes**; são testes Python e não executam Lua.

| Regressão | Como é exercitada | Antes → depois |
| --- | --- | --- |
| JSON publicado pelo coletor, sem minificar | `collector.contract.atomic_write_json` grava contrato v1 sintético em `TemporaryDirectory`; `read_bytes()` alimenta o `json.lua` real via harness, com LF original e CRLF derivado sem alterar conteúdo. O teste exige duas linhas `null` e os dois provedores visíveis. | Vermelho → verde. `json.lua:143` passou a delimitar `space`, `tab`, CR e LF. |
| Valores JSON e whitespace | Lua 5.1 decodifica `null`, `true`, `false`, `123` e `1.25` antes de LF, CRLF, tab e espaço. | `null`/booleans vermelhos → verdes; números verdes → verdes. |
| Dois monitores e borda inferior | Stub fornece primário `WORKAREAY=0`, `WORKAREAHEIGHT=1920`, secundário `WORKAREAX@2=1080`, `WORKAREAY@2=40`, `WORKAREAWIDTH@2=2560`, `WORKAREAHEIGHT@2=1040`, e `CURRENTCONFIGX=1400`, `CURRENTCONFIGY=930/1030`. Exige corpo compacto, gaveta e todos os meters visíveis dentro de 150/50 px físicos. | Vermelho → verde. `LLMUsage.ini:10` passou a declarar `AutoSelectScreen=1`; `main.lua:675-701` também resolve área por monitor. |
| Codificação da fonte Rainmeter | Para `.ini`, `.inc` e `.lua` que contêm Unicode, exige UTF-16 LE; leitor do harness aceita esses arquivos para continuar executando Lua real. | Vermelho → verde. `LLMUsage.ini`, `Variables.inc` e `main.lua` agora começam com BOM `FF FE`; `Styles.inc` e `json.lua` permanecem ASCII. |
| Dinheiro na linha compacta | Fixture sintética com gasto `US$ 12.40 de 20`; inspeciona a caixa efetiva do meter que apresenta moeda contra `Row1Name`, sem impor nome de meter dedicado. Um guard geométrico conservador não substitui medida de fonte nativa. | Vermelho → verde. `Row1Col1Text` agora usa `X=158`, `W=78`, `ClipString=1`; sua caixa começa em 80 px e o nome termina em 78 px. |
| `SnapshotPath` explícito válido | Arquivo isolado sintético e cache padrão sintético diferentes; exige leitura apenas do caminho explícito. | Verde. |
| `SnapshotPath` explícito ausente | Caminho isolado ausente com cache padrão sintético presente; exige estado vazio e nenhuma leitura do cache padrão. | **Vermelho atual.** `main.lua:98-127` cai no cache `%LOCALAPPDATA%\LLMUsageWidget\snapshot.json` quando o override existe mas o arquivo não. Isso pode apresentar dados de outra origem e torna o isolamento do teste enganoso. Tratar o override como fonte autoritativa ou explicitar fallback como escolha de usuário; levar ao coordenador para atribuição. |

O helper antigo `snapshot()` continua compacto para testes de lógica locais, mas não é usado pela nova ponte de publicação. A ponte usa exatamente o formato `indent=2` emitido por `atomic_write_json`; assim, `json.dumps` compacto não consegue mais esconder N1. Não foram afrouxadas as asserções anteriores para obter verde.

## Base dos nomes de variáveis e limites do stub

A [documentação oficial de variáveis do Rainmeter](https://docs.rainmeter.net/manual/variables/built-in-variables/) informa que `WORKAREAY`/`WORKAREAHEIGHT` sem `@N` usam o monitor primário por padrão, salvo `AutoSelectScreen=1`; `WORKAREAY@N`/`WORKAREAHEIGHT@N` identificam monitores numerados, e `CURRENTCONFIGX/Y` são dinâmicas. O stub representa essas duas áreas e aceita tanto `AutoSelectScreen=1` em INI ou bang quanto consultas `@2`. Ele não representa enumeração real, mudanças de monitor durante a execução, DPI, `KeepOnScreen`, dimensão de janela, z-order nem hit testing. A [orientação oficial de Unicode](https://docs.rainmeter.net/tips/unicode-in-rainmeter/) pede UTF-16 LE para fontes `.ini`/`.inc`/`.lua` com caracteres Unicode; o teste estático verifica bytes, sem prometer que Rainmeter renderizou os glifos novos.

## Checklist para reteste nativo após Miiaq concluir

1. Registrar novos hashes; confirmar que `LLMUsage-Validation` continua própria e inativa. Copiar **somente a skin atualizada** para essa pasta de validação, preservando as configurações e posições das skins illustro. Conferir `SnapshotPath` absoluto fora do OneDrive e o estado do fallback quando o arquivo apontado não existe.
2. Gerar um snapshot **sintético** pelo `atomic_write_json` em TEMP com `null`, booleans e números formatados em LF. Apontar a validação para esse arquivo sem compactação, ativar apenas a validação e confirmar linhas visíveis, estados, ausência de erro de INI/Lua/Shape no *Sobre Rainmeter*. Testar também CRLF em arquivo isolado.
3. No monitor secundário observado (`WORKAREAY=40`, `WORKAREAHEIGHT=1040`), verificar o valor real que Lua recebe e a skin em `X=1400,Y=930` e `Y=1030` com 150/50 px restantes. Conferir cabeçalho, todas as linhas visíveis, gaveta, paginação e que `KeepOnScreen`/altura nativa não impedem posicionamento seguro. O caso 0 px só pode ser verificado sem alegar visibilidade fora da tela.
4. Verificar setas, banner DEMO opt-in, acentos nas strings Lua e formato monetário em `96 dpi`; confirmar que nome e `US$ 12.40 de 20` não se sobrepõem nem são cortados de modo a perder significado. DPI alternativo exige ambiente apropriado; não mudar o DPI global desta estação como parte deste harness.
5. Repetir hover de 400 ms com medição, clique fixa/solta, rolagem, página 2, polling sem bang, falha de leitura após sucesso e animação em quadros intermediários. Confirmar que o JSON real do coletor, quando houver autorização para leitura, funciona sem transformação intermediária. Desativar só a validação ao final.

**Pendência atual:** N1–N4 estão cobertos e verdes offline na revisão final, mas precisam da observação nativa acima; N5 (janela de 484 px no modo compacto) é exclusivamente nativo. O fallback de `SnapshotPath` ausente permanece vermelho em teste offline e deve ser decidido/corrigido antes de afirmar isolamento completo.
