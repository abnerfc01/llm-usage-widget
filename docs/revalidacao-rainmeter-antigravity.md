# Revalidação nativa no Rainmeter — 12/11/2026 (Antigravity QA)

**Resultado: Aprovado integralmente.**  
A geometria agora se ajusta automaticamente ao mover sem refresh (52,7 ms em 150 px e 104,7 ms em 50 px), a contenção física da janela nativa foi comprovada (137 px e 35 px, respectivamente), o gasto monetário curto `US$ 12,40 (62%)` e a gaveta com total e período específico `(Novembro)` estão íntegros sem truncamento, o isolamento estrito de `SnapshotPath` sem fallback foi confirmado, e todas as interações (hover cronometrado, clique fixa/solta, paginação, rolagem e polling automático) foram validadas no Rainmeter real.

---

## 1. Ambiente, Hashes e Isolamento

- **Processo:** Rainmeter `4.5.28.3936`, PID `46832`, Session ID `1`.
- **Caminho das Skins (`SkinPath`):** `C:\Users\Abner\OneDrive\Documentos\Rainmeter\Skins\`
- **Monitores Físicos Detectados:**
  - **Primário (Vertical):** `0,0,1080,1920`, área de trabalho útil `X=62, Y=0, W=1018, H=1920`.
  - **Secundário (Horizontal):** `1080,0,3640,1080`, área de trabalho útil `X=1080, Y=40, W=2560, H=1040` (base em `Y=1080`).
- **DPI e Escala:** `96×96 DPI` (escala 100%), sem alteração de configurações globais de exibição.
- **Backup Prévio:** Criado backup integral antes dos testes em `C:\Users\Abner\AppData\Local\Temp\llm-validation-backup-20261112-215300\`.
- **Hashes Criptográficos SHA-256 (Staging e Cópia de Validação coincidente):**
  - `skin/LLMUsage.ini`: `F08CCC84B5CCA584FA4186A2E1778E75C8A895BA9217E0FB64FB78AD63EC81F1`
  - `skin/@Resources/Scripts/main.lua`: `A24A3DE9FFB2000C0B5E0BB2A3F4244C2050454A43EC595CC5AF39F751D01CF4`
  - `skin/@Resources/Scripts/json.lua`: `3287FA1513EB3363AE309E07D4E0107F32F6F67411D27E57EC2020283FE8E1D1`
  - `skin/@Resources/Variables.inc`: `FFFFE0452D095D6BA82568774E49C10E0C7CADCAC4203C945992A7DDB213F792`
  - `skin/@Resources/Styles.inc`: `3B787A29FF25265710C13AA5F0E35FA8C4468A29786768FE26C56AF558B361B2`
  - `snapshot-synthetic.json`: `BADF20ED462EC033BB409DDB8CC92D548058EFAD5F693BF5D3346C8EEE6A87EC`

---

## 2. Coleta Real E2E (Collect-Once) e Suítes Automatizadas

1. **Execução de Coleta Real Hermética:**
   - Pasta de execução isolada fora do OneDrive: `C:\Users\Abner\AppData\Local\Temp\llm-usage-widget-nativeqa-20261112-215400\`.
   - Executado: `python -B -m collector collect-once --config config.json --snapshot snapshot.json`.
   - Saída: `{"ok": true, "generated_at": "2026-11-12T21:54:27-03:00", "providers": 5}`.
   - Estados observados:
     - `claude`: `never`, `auth_expired` (sem dados ou cotas simuladas).
     - `codex`: `fresh`, 2 janelas de cotas reportadas.
     - `antigravity`, `opencode_go`, `cursor`: `never`, `unsupported` (independent sources unverified).
   - O arquivo `snapshot.json` formatado com quebras de linha e ident=2 foi carregado diretamente no Rainmeter sem compactação. Nenhuma credencial ou resposta privada foi exposta.
2. **Suítes de Regressão Automatizadas:**
   - `python -B skin/tests/runtime_qa.py`: **36/36 testes aprovados** em 0,402s.
   - `python -B -m unittest skin.tests.test_live_geometry`: **8/8 testes aprovados** em 0,076s.
   - `python -B skin/tests/test_skin_logic.py`: **4/4 testes aprovados** em 0,001s.
   - `python -B -m unittest discover -s tests -q`: **43/43 testes backend aprovados** em 4,11s.

---

## 3. Matriz de Resultados da Validação Nativa (N1 a N5)

| ID | Descrição | Comportamento Observado no Rainmeter Real | Status |
|---|---|---|---|
| **N1** | **Suporte a JSON formatado sem minificação** | O `snapshot.json` real formatado com `null` e quebras de linha foi renderizado normalmente, exibindo Claude, Codex e os estados `unsupported` sem requerer minificação. Evidência: `artifacts/native-qa/antigravity-initial-compact.png`. | **Aprovado** |
| **N2** | **Reflow dinâmico ao mover sem refresh** | Com a skin em `X=1400, Y=120` (`211×187` px), foi enviado comando de movimentação para `Y=930` (150 px restantes na tela secundária) **sem !Refresh nem RefreshSnapshot**. A rotina `CheckLiveGeometry` detectou o deslocamento em **52,7 ms** e recompôs a janela para `(1400, 930, 1611, 1067)` com tamanho `211×137` px (corpo 136 + 1 px de borda), cabendo rigorosamente nos 150 px disponíveis. Ao mover para `Y=1030` (50 px restantes) sem refresh, a janela colapsou em **104,7 ms** para `(1400, 1030, 1611, 1065)` com tamanho `211×35` px (corpo 34 + 1 px de borda). Ao mover de volta para `Y=120`, restaurou em **53,4 ms** para `211×187` px com as 5 linhas visíveis. Evidências: `antigravity-live-150.png`, `antigravity-live-50.png` e `antigravity-live-return-safe.png`. | **Aprovado** |
| **N3** | **Codificação UTF-16 LE e renderização GDI** | Títulos acentuados, avisos e caracteres especiais (`DADOS SINTÉTICOS`, `MÊS`, setas `‹`/`›`, `•`) foram renderizados sem qualquer mojibake ou corrupção de caracteres. | **Aprovado** |
| **N4** | **Apresentação de orçamento, dinheiro curto e período específico** | Na página 2 sintética, DeepSeek exibiu o gasto curto em pt-BR `US$ 12,40` e `62%` sem sobreposição sobre o nome nem truncamento. Na gaveta expandida, exibiu `Gasto US$ 12,40 de orçamento US$ 20,00 (Novembro)`, apresentando o total e o período específico completo, eliminando o fallback genérico `(mês)`. Evidências: `antigravity-demo-dinheiro.png` e `antigravity-demo-gaveta-orcamento.png`. | **Aprovado** |
| **N5** | **Contenção física da janela nativa do Windows** | Em todas as configurações compactas e colapsadas, o bounding box nativo da janela `RainmeterMeterWindow` reportado pelo sistema operacional acompanhou estritamente o corpo desenhado: `211×137` px em 150 px livres, `211×35` px em 50 px livres, e `211×187` px em repouso. O problema histórico de 156 px fixos causados por meters inativos foi completamente eliminado. | **Aprovado** |

---

## 4. Testes de Isolamento e Interações

1. **Caminho Explícito Ausente (`SnapshotPath`):**
   - Configurado `SnapshotPath` para arquivo inexistente (`nonexistent_snap_qa_12345.json`) seguido de `RefreshSnapshot()`.
   - A skin apresentou estado vazio ("Sem dados disponíveis") e `MeterEmptyNotice` visível, sem efetuar fallback para `%LOCALAPPDATA%` nem exibir dados de usuários locais. Evidência: `antigravity-origem-ausente.png`.
2. **Isolamento de Origens Sintéticas A e B:**
   - Comutada a variável `SnapshotPath` entre `origin_a.json` (`Origem Alpha`) e `origin_b.json` (`Origem Beta`).
   - A transição invalidou imediatamente os dados em cache da origem anterior, exibindo estritamente a nova conta sem resíduos visuais. Evidências: `antigravity-origin-a.png` e `antigravity-origin-b.png`.
3. **Hover Cronometrado:**
   - Acionamento de hover na primeira linha registrou abertura da gaveta em **467,5 ms**, em plena conformidade com o temporizador nativo de 8 ticks (400 ms) mais o ciclo de update.
4. **Fixação por Clique (Pin/Unpin):**
   - Clique na linha fixou a gaveta; o afastamento do cursor do mouse além da área da skin por 600 ms manteve a gaveta aberta (altura 499 px).
   - Um segundo clique soltou e recolheu a gaveta para 187 px.
5. **Paginação e Rolagem:**
   - Paginação para `2/2` e retorno para `1/2` funcionaram deterministamente.
   - Rolagem com roda do mouse (`OnScrollDown`) na gaveta Antigravity com 8 slots sintéticos deslocou os itens visíveis de `1–4` para `2–5`. Evidências: `antigravity-demo-scroll-antes.png` e `antigravity-demo-scroll-depois.png`.
6. **Polling Nativo Automático sem Bang:**
   - Modificação do arquivo sintético em disco (`POLL INITIAL` → `POLL UPDATED`, cota de 30% para 75%) sem nenhum bang enviado ao Rainmeter.
   - O widget atualizou automaticamente a interface após **11,5 s** (intervalo de 200 ticks * 50 ms = 10 s). Evidência: `antigravity-polling-updated.png`.

---

## 5. Restauração do Ambiente e Integridade do Sistema

- **Arquivos da Validação:** `Variables.inc` e `snapshot-synthetic.json` na pasta `LLMUsage-Validation` foram restaurados byte a byte para coincidir com os arquivos limpos de staging.
- **Configuração do Rainmeter (`Rainmeter.ini`):**
  - Seção `[LLMUsage-Validation]` redefinida para `Active=0`, `WindowX=1400`, `WindowY=120`, `KeepOnScreen=1`, `AlwaysOnTop=0`.
  - A skin de validação foi devidamente desativada (`!DeactivateConfig "LLMUsage-Validation"`), confirmando ausência de sua janela no desktop.
  - Todas as 6 seções das skins `illustro` (`Clock`, `Disk`, `System`, `Welcome`, `Google`, `Network`) mantiveram rigorosamente seus valores originais de `Active` e posições de tela.
- **Processo Rainmeter:** Permaneceu ativo e estável (PID `46832`). Nenhum serviço global, DPI ou arquivo de sistema foi alterado.

---

## 6. Conclusão

A rodada de revalidação nativa no Rainmeter real confirmou que todos os bloqueadores técnicos e visuais (N1 a N5) foram sanados com precisão. O reflow dinâmico em tempo real ao mover sem refresh (`CheckLiveGeometry`), a contenção física da janela nativa, a apresentação completa de orçamentos e períodos em português e o isolamento de dados de snapshots estão prontos e aprovados para entrega.
