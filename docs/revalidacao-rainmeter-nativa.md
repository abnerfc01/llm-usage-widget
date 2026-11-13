# Revalidação nativa — 12/11/2026

**Resultado: aprovação ponta a ponta pendente.** O JSON real formatado passou a aparecer, mas a janela nativa ainda excede a área disponível em posições baixas e o valor monetário sintético é truncado. O histórico de reprovação em `docs/validacao-rainmeter-nativa.md` foi preservado.

Às 17:27–17:30, no Rainmeter 4.5.28 existente, a cópia própria `LLMUsage-Validation` estava inativa antes da rodada. Foi feito backup em `C:\Users\Abner\AppData\Local\Temp\llm-validation-backup-20261112-172749`, atualizada a cópia com staging e configurado `SnapshotPath` para o snapshot isolado de TEMP da rodada anterior, produzido pelo coletor às 13:07, sem minificação. Não houve nova coleta nem leitura de credenciais nesta rodada; esse sucesso anterior não prova o tratamento posterior de falhas do backend. O coordenador informou regressão em `validate_snapshot` para último sucesso anterior à última tentativa falha; depende de correção e nova regressão do backend.

Hashes SHA-256 da cópia/staging: `LLMUsage.ini` `F08CCC84B5CCA584FA4186A2E1778E75C8A895BA9217E0FB64FB78AD63EC81F1`; `main.lua` `4D8057B6CFC5F76FFAA6E18FF18420ABBDD62F5C0DD7BA0E1DFA9B004C36E75D`; `json.lua` `3287FA1513EB3363AE309E07D4E0107F32F6F67411D27EEC2020283FE8E1D1`.

| Achado | Resultado observado no Rainmeter |
| --- | --- |
| N1 | O snapshot real formatado original exibiu Claude, Codex e estados unsupported sem compactação. O fixture sintético formatado também carregou. |
| N2 | No primário, `X=400,Y=930/1030` produziu janela `211×187`, dentro da área útil vertical de 1920 px. No secundário, com `KeepOnScreen` desligado apenas na validação para alcançar as posições, `Y=930` mostrou três linhas e `Y=1030` mostrou título recolhido. A janela reportou **156 px de altura em ambos**: excede os 150 e 50 px restantes, respectivamente; a contenção da janela nativa ainda não está comprovada. |
| N3 | INI e Lua com BOM UTF-16 foram carregados; setas, `DADOS SINTÉTICOS`, `MÊS` e `USO DE IA (recolhido)` apareceram legíveis. A captura sintética é `artifacts/native-qa/revalidacao-demo-compact.png`. |
| N4 | Página 2 sintética mostra DeepSeek sem sobreposição com o nome, mas o texto aparece como `US$ 12.40 de...`, ocultando o orçamento. Ver `artifacts/native-qa/revalidacao-demo-dinheiro.png`; não afirmar que o valor completo está legível. |
| N5 | Compacta em posição segura, a janela caiu de `213×484` na rodada histórica para `211×187`. Com `KeepOnScreen=1`, pedido de `Y=930` foi limitado a `Y=893`, coerente com os 187 px; ao desativá-lo para o teste de borda a janela permaneceu com 156 px mesmo quando o corpo recolheu. Investigar os meters que mantêm a extensão. |

O comando `NextPage()` mostrou página 2 e um clique na seta anterior retornou à página 1. Clique na primeira linha abriu a gaveta com altura 499 px e outro clique voltou a 187 px; a prévia por hover foi observada, sem cronometrar o limiar de 400 ms. A roda foi acionada, mas a fixture disponível não permitiu comprovar mudança de item rolado. Alterar o nome sintético no arquivo sem refresh produziu `POLL QA` após 11 segundos; alteração de barra sintética de 51% para 90% com `RefreshSnapshot()` produziu amostras GDI de 22, 22, 25, 29 e 32 px, demonstrando quadros intermediários.

O log recente da janela Sobre exibiu notificações de refresh da validação, sem erro ou aviso de INI, Lua ou Shape visível na inspeção. Capturas guardadas são exclusivamente sintéticas; para elas, o fundo da cópia ficou temporariamente opaco e foi restaurado. Não foram capturadas respostas reais no repositório.

Ao final, fixture e variáveis da cópia foram restaurados ao staging, com `UseSyntheticFixture=0` e `SnapshotPath` isolado; `KeepOnScreen=1`, posição segura e Z normal foram restaurados e somente `LLMUsage-Validation` foi desativada. Os valores `Active` das skins illustro permaneceram iguais ao início. A suíte offline própria, repetida às 17:30, executou 32 testes com uma falha: `SnapshotPath` explícito ausente ainda recai silenciosamente no cache padrão, como documentado em `docs/revisao-integracao-regressoes.md`.

Pendências: corrigir/decidir fallback do caminho explícito, investigar altura nativa de 156 px e legibilidade do orçamento, repetir rolagem com mais itens e cronometrar hover, e executar regressão de backend após a correção do último sucesso. Não se alterou DPI, serviço, agendamento ou configuração de outros widgets.
