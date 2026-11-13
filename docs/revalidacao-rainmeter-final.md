# Revalidação nativa final — 12/11/2026

**Resultado: não aprovado integralmente.** A geometria se ajusta após refresh, mas a movimentação sem refresh manteve uma janela de 187 px em posições com 150 e 50 px disponíveis. Outros cenários pedidos permanecem sem comprovação nesta rodada, indicados abaixo. O teste usou exclusivamente fixture sintética; não foi executado coletor, acesso a contas ou rede, e não se afirma coleta atual ponta a ponta.

## Ambiente e hashes

Rainmeter 4.5.28 existente, PID 46832; `SkinPath=C:\Users\Abner\OneDrive\Documentos\Rainmeter\Skins\`. Cópia própria `LLMUsage-Validation`, inativa no início, comparada com staging antes da execução; arquivos de produto coincidentes, sem necessidade de copiar. Backup de variáveis e fixture em `%TEMP%\llm-finalqa-20261112-175851`. Somente a cópia foi ativada, movida e configurada; fundo opaco temporário para capturas sintéticas. `KeepOnScreen=0` somente na cópia para teste das bordas.

SHA-256 staging e cópia no início: `LLMUsage.ini` F08CCC84B5CCA584FA4186A2E1778E75C8A895BA9217E0FB64FB78AD63EC81F1; `main.lua` D06039692B357F38108C02EE0E5960B48911BDE1E41BC16A22870A2A1B7C4D66; `json.lua` 3287FA1513EB3363AE309E07D4E0107F32F6F67411D27E57EC2020283FE8E1D1; `Variables.inc` FFFFE0452D095D6BA82568774E49C10E0C7CADCAC4203C945992A7DDB213F792; fixture BADF20ED462EC033BB409DDB8CC92D548058EFAD5F693BF5D3346C8EEE6A87EC.

## Resultados N1–N5

- **N1 — parcial:** fixture JSON formatada, com `null` e quebras de linha, carregou sem minificação; vide `artifacts/native-qa/final-demo-compact.png`. Trocando via `!SetVariable` da origem sintética válida para caminho explícito ausente, seguido de `RefreshSnapshot()`, a tela ficou vazia, sem reter a conta anterior (`final-demo-origem-ausente.png`). O cache padrão não foi lido nem manipulado nesta rodada; portanto não se comprova nativamente o caso em que ele contém dados, nem a troca entre duas origens válidas distintas. A imagem do estado vazio não contém dados reais.
- **N2 — falha ao mover:** com `KeepOnScreen=0`, ao mover de posição segura para X=1400,Y=930, a janela manteve 211×187 px após três segundos e continuou assim após `!Update` e mais dois segundos; em Y=1030 ainda media 211×187 após três segundos. Assim excedeu as áreas disponíveis de 150 e 50 px no movimento observado. Executando `!Refresh` em cada posição, passou a 211×137 e 211×35, respectivamente, dentro das áreas disponíveis; corpos esperados 136 e 34 com um pixel adicional na janela nativa. Evidências `final-demo-150.png` e `final-demo-50.png` são posteriores ao refresh. Não foi determinado se polling posterior pode ajustar a geometria sem intervenção; não afirmar atualização imediata ao arrastar.
- **N3 — aprovado no visual observado:** `DADOS SINTÉTICOS`, `MÊS`, setas e textos acentuados legíveis em 96 dpi; capturas sintéticas. Outras configurações de DPI não foram testadas.
- **N4 — parcial:** página 2 mostrou DeepSeek, `US$ 12,40` e `62%` sem sobreposição nem truncamento visível (`final-demo-dinheiro.png`). Gaveta fixa mostrou `Gasto US$ 12,40 de orçamento US$ 20,00 (mês)` (`final-demo-gaveta-orcamento.png`): valores legíveis, porém a fixture especifica período `Novembro` e a gaveta exibe apenas `mês`. Tooltip não foi comprovado; não afirmar apresentação completa do período específico.
- **N5 — condicionado:** com refresh, janelas 137/35 px cabem em 150/50 px; compacta segura 211×187 px. Sem refresh, 187 px persistiram como descrito em N2; não declarar contenção geral garantida.

## Interações e limites

Hover sobre a primeira linha abriu gaveta aproximadamente 488 ms após movimento do ponteiro (amostragem do retângulo nativo a cada 20 ms, não medição precisa do evento interno). Clique em linha abriu e fixou a gaveta após saída do cursor; segundo clique fechou, de 499 para 187 px. Paginação para 2/2 foi executada por `NextPage()` e observada; nesta rodada o retorno por clique não foi retestado. Fixture ampliada somente na cópia gerou oito detalhes: roda passou de 1–4 de 8 para 2–5 de 8, com capturas `final-demo-scroll-antes.png` e `final-demo-scroll-depois.png`. Alteração do nome para `POLL QA` no arquivo apareceu após espera de 12 segundos sem refresh. Tentativa de amostragem de animação por pixel não foi conclusiva; quadros intermediários não são reivindicados nesta rodada.

O coordenador informou **32/32 testes Lua** e, após correção temporal do backend, **43/43 testes Python**; não foram reexecutados por este QA. Esses resultados são distintos da observação nativa acima. Fontes anteriormente classificadas unsupported não foram consultadas nesta rodada e nenhum estado atual é afirmado.

## Restauração

Apenas `LLMUsage-Validation` foi desativada; sua posição voltou a X=1400,Y=120, `KeepOnScreen=1`, variáveis e fixture restauradas byte a byte (hashes idênticos ao backup). As seis seções illustro do `Rainmeter.ini` coincidem integralmente com o estado inicial, incluindo Active e posições. O processo original 46832 permanece ativo. Nenhum serviço, DPI global, agendamento, produto ou teste foi alterado.

Pendências: resolver/avaliar atualização de geometria durante movimentação e repetir N2; verificar tooltip e período Novembro; comprovar isolamento com cache padrão sintético controlado e duas origens válidas; validar retorno de página por clique e animação nativa com quadros intermediários; executar coleta atual apenas se necessária e autorizada, sempre sem expor dados reais.
