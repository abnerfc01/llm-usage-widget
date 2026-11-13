# Skin "Uso de IA" — especificação de design

Versão 2 (Reconciliada) · 12/11/2026 · Rainmeter 4.5.28 · Windows 11  
Mockup interativo: `design/mockup.html`  
Relatório de reconciliação: `docs/revisao-design.md`

A skin é uma "irmã" das illustro (Clock, System, Disk, Network). Tem a mesma largura de 210 px, o mesmo fundo escuro com faixa de título, a mesma fonte Trebuchet MS em negrito e as barras finas sobre trilho quase transparente. A diferença é que a barra muda de cor conforme o consumo (escala semafórica de 5 níveis).

---

## 0. Decisões principais

1. **Tabela com colunas fixas por categoria temporal estrita.** Cada conta ocupa uma linha com três colunas fixas: `5H`, `SEMANA` e `MÊS`. A coluna `5H` aceita **apenas janela comprovadamente equivalente a cinco horas** (`duration_seconds == 18000` ou identificador inequívoco comprovado de 5h). Ciclos curtos não equivalentes a 5h (ex: 3h, 4h, 6h) **nunca** entram na coluna 5H; são categorizados como janelas extras (`+N`) e detalhados na gaveta. A janela é identificada pela posição e pelo cabeçalho, nunca pela cor.
2. **Gaveta de detalhes abaixo da lista, não sanfona sob a linha.** Passar o mouse ou clicar abre os detalhes numa gaveta única no fim da lista. **As linhas da página nunca mudam de posição vertical**, impedindo que qualquer área de acerto se mova sob o cursor, o que elimina totalmente o risco de laço de abre/fecha (flickering). Apenas uma conta fica aberta por vez e somente a borda inferior da skin se expande.
3. **Limite por modelo restrito a janelas equivalentes.** Se uma cota específica de modelo ou grupo (ex: Fable no Claude) estiver mais consumida que a cota da conta, ela é destacada na coluna daquela mesma janela temporal com um ponto marcador (`tight-marker`). Uma cota semanal de modelo **nunca** ocupa a coluna de 5 horas. Janelas extras ou irregulares recebem uma tag sutil `+1` na linha e detalhamento completo na gaveta.
4. **Paginação explícita e limitação à área útil disponível.** Cinco contas por página **não garantem caber em toda tela e posição a 150%** (por exemplo, quando a skin estiver posicionada perto da borda inferior da tela ou em telas com altura útil reduzida, como 768p/1080p a 150%). Por isso, o número de contas visíveis e a altura da gaveta devem ser limitados dinamicamente à área útil de trabalho disponível (`#WORKAREAHEIGHT#` e `#WORKAREAY#`), com fallback explícito para páginas menores (ex: 3 ou 4 contas) e rolagem interna na gaveta. (Nota de metodologia: não se alega validação de DPI sem testes observados no runtime do Rainmeter; trata-se de especificação geométrica com limitações documentadas).
5. **Orçamento como referência local.** O orçamento (`budget`) em contas de API em dinheiro é tratado visualmente como **referência local definida pelo usuário** (`source: local_config`), e não como cota contratual imposta pela API. Barra percentual só é calculada se houver gasto compatível no mesmo período, moeda e escopo.
6. **Invalidação cirúrgica por janela vs. frescor do provedor.** Se o horário de reset de uma janela específica já passou, apenas aquela célula é marcada como `atualizando…` com barra tracejada. As outras janelas da conta que continuam válidas permanecem ativas e coloridas. O provedor como um todo só entra no estado desatualizado (`stale`) quando o prazo de frescor do coletor (`stale_after`) expira.
7. **Identificação com ícone da empresa + nome.** Cada conta exibe um ícone pequeno (12×12 px) à esquerda do nome. Para garantir extensibilidade, contas novas sem arquivo de arte utilizam automaticamente o ícone de fallback (`default.png`).  
   > [!NOTE]
   > Os ícones são representações estilizadas/aproximadas para diferenciação visual rápida na área de trabalho e não são rotulados como logotipos oficiais verificados das empresas detentoras das marcas.

---

## 1. Dimensões, grade e tipografia

Todas as medidas estão em px a 100% de escala do Windows. Em escalas de 125% ou 150%, multiplique as coordenadas pelo mesmo fator.

### Grade horizontal (largura total 210 px)

| Elemento | X inicial | X final | Largura | Alinhamento |
|---|---|---|---|---|
| Margem esquerda | 0 | 10 | 10 | — |
| Ícone da empresa | 10 | 22 | 12 | centralizado (12×12 px) |
| Respiro | 22 | 25 | 3 | — |
| Nome da conta / tag | 25 | 78 | 53 | esquerda, `ClipString=1` |
| Coluna 5H | 80 | 116 | 36 | número à direita em X=116 |
| Coluna SEMANA | 122 | 158 | 36 | número à direita em X=158 |
| Coluna MÊS | 164 | 200 | 36 | número à direita em X=200 |
| Margem direita | 200 | 210 | 10 | — |

### Ícones das empresas

- **Tamanho e formato**: PNG 12×12 px (ou 24×24 com `AntiAlias=1` e `ImageAlpha=230`), salvos em `@Resources\Icons\<provedor>.png`.
- **Provedores nativos**:
  - `claude.png`: centelha/asterisco em coral (`#D97757`).
  - `codex.png`: roseta geométrica OpenAI em verde (`#10A37F`).
  - `antigravity.png`: estrela de 4 pontas Gemini/Google em azul (`#7EA5F8`).
  - `opencode.png`: glifo hexagonal de código em ciano (`#38BDF8`).
  - `cursor.png`: cubo/seta isométrica em branco/prata (`#ECECF1`).
- **Fallback universal (`default.png`)**: glifo sutil de centelha de inteligência artificial em branco translúcido (alfa 150). Utilizado automaticamente quando o plugin do coletor reportar um `id` de provedor sem ícone dedicado.
- **Aviso de arte**: ícones são representações estilizadas funcionais para desktop, não marcas comerciais autenticadas.

### Grade vertical do estado compacto (K = contas visíveis na página, padrão 5)

| Elemento | Y | Altura |
|---|---|---|
| Faixa do título (fundo mais escuro) | 0 | 34 |
| Título `USO DE IA` (centro X=105) | 10 | 14 |
| Controles de paginação `‹ 1 / 2 ›` (X=145 a 200) | 10 | 14 |
| Cabeçalho das colunas (`5H · SEMANA · MÊS`) | 38 | 12 |
| Linha i (i = 0…K-1): topo `T = 54 + 22·i` | — | — |
| ↳ ícone da empresa | T+1 | 12 |
| ↳ nome e números | T | 14 |
| ↳ barras (trilho e preenchimento) | T+14 | 2 |
| ↳ área de acerto estável (0 a 210 px) | T-3 | 22 |
| Gaveta (0 quando fechada, max 260 px quando aberta) | `54 + 22·K + 2` | `G` (animada / rolável) |
| Rodapé | `58 + 22·K + G` | 14 |
| **Altura compacta (5 contas)** | — | **186 px** |

### Tipografia (Trebuchet MS, negrito, sombra illustro)

| Uso | Tamanho | Cor (RGBA) | Caixa |
|---|---|---|---|
| Título | 10 pt | 255,255,255,205 · sombra 0,0,0,50 | MAIÚSCULAS |
| Nome da conta, números de consumo | 8 pt | 255,255,255,205 (números na cor do nível) | normal |
| Rótulos de coluna, tempos, rodapé, tags | 7 pt | 255,255,255,150 (secundário) | colunas em MAIÚSCULAS |
| Sombra do texto | — | 0,0,0,20 (`StringEffect=Shadow`) | — |

---

## 2. Estado compacto e paginação

1. **Título e Paginação**: Título `USO DE IA` centralizado. Quando o número de provedores habilitados for maior que 5, aparecem no topo direito os controles `‹ 1 / 2 ›` para alternância imediata de páginas.
2. **Cabeçalho de Colunas**: `5H · SEMANA · MÊS` em 7 pt secundário alinhado à direita de cada coluna.
3. **Linha da Conta**:
   - Ícone (12×12 px) + Nome da conta (cortado em 53 px se necessário).
   - Se a conta possuir janelas adicionais não enquadradas nas 3 colunas (ex: cota de 24h ou rolling de 3 dias), exibe uma tag `+1` em 7 pt secundário ao lado do nome.
   - Cada coluna mostra o valor em porcentagem e uma barra de 2 px embaixo.
4. **Rodapé Global**:
   - À esquerda: `Instantâneo: {hh:mm}` (horário em que o coletor gerou o arquivo JSON local).
   - À direita: contador de alertas (`1 alerta`, `2 alertas`) se houver provedores com erro ativo ou dado desatualizado (`stale`).

### Regras de exibição na célula

- **Janela inexistente**: não desenha número nem trilho (célula vazia). Nunca desenha "0%" falso nem "—".
- **Janela com 0% medido**: mostra `0%` com o trilho vazio. Não infere texto `não iniciada` a menos que o contrato forneça essa indicação.
- **Preenchimento da barra**: `36 × min(%, 100) / 100`. Acima de 0%, tem no mínimo 1 px.
- **Acima de 100%**: a barra satura visualmente em 100% e o número reflete o valor real (ex: `114%`) na cor crítica do nível 5.
- **Limite por modelo mais restrito**: quando uma cota de modelo daquela mesma categoria temporal estiver mais alta que a da conta, exibe o número dessa cota com o ponto marcador de 3 px (`tight-marker`) e indica o escopo no tooltip.

### Linhas de API paga por uso (Valores monetários)

- **Saldo pré-pago sem orçamento**: exibe `US$ 4,20 restantes` ocupando as três colunas em 8 pt, sem barra.
- **Gasto pós-pago sem orçamento**: exibe `US$ 12,40 no mês`, sem barra.
- **Com orçamento configurado pelo usuário (`source: local_config`)**:
  - Exibe porcentagem na coluna correspondente (ex: `MÊS: 62%`) com barra colorida conforme a escala normal.
  - As outras colunas exibem `US$ 12,40 de 20` em 7 pt secundário.
  - **Condição estrita**: a barra e o percentual só existem se a moeda, o período e o escopo do gasto e do orçamento forem compatíveis. Se faltar correspondência, exibe apenas os valores monetários em texto puro.

---

## 3. Codificação e equivalência das janelas

| Coluna | Duração de referência | Regra de equivalência |
|---|---|---|
| `5H` | 5 horas comprovadas | Estritamente duração comprovada de 18.000 s (`duration_seconds == 18000`) ou identificador inequívoco comprovado de 5 horas. Ciclos curtos genéricos (ex: 3h, 4h, 6h) nunca são exibidos aqui; são tratados como cotas extras (+N). |
| `SEMANA` | 7 dias | Janelas semanais (~604.800 s) de conta ou de modelos. |
| `MÊS` | Mês corrente / 30 dias | Janelas mensais (~2.592.000 s) ou orçamentos locais mensais. |

- **Janelas Extras / Irregulares**: se um provedor fornecer cotas diárias de 24h, de 3 dias ou limites específicos que não pertençam às três categorias, elas **não** são forçadas em colunas erradas. O estado compacto exibe o indicador `+1` e todas as cotas aparecem detalhadas na gaveta.
- Na gaveta, as janelas da conta usam barras de **3 px**. As janelas de modelo/grupo usam barras de **2 px**.

---

## 4. Escala semafórica de cores (5 níveis)

Todas as cores possuem contraste mínimo de **4,5:1** sobre fundo preto translúcido (`rgba(0,0,0,0.784)`) mesmo em cima de papel de parede 100% branco.

| Nível | Faixa de uso | Significado | Cor RGB | Hex |
|---|---|---|---|---|
| **1** | < 25% | Folga | 92, 200, 140 | `#5CC88C` |
| **2** | 25 a 49% | Atenção leve | 190, 210, 70 | `#BED246` |
| **3** | 50 a 74% | Metade (âmbar illustro) | 235, 170, 0 | `#EBAA00` |
| **4** | 75 a 89% | Alto | 255, 135, 50 | `#FF8732` |
| **5** | ≥ 90% | Crítico (com pulso) | 255, 118, 110 | `#FF766E` |
| **Estado** | Erros, avisos e status | Alertas / Falhas | 140, 190, 255 | `#8CBEFF` |

---

## 5. Tempo até o reset e ritmo

Exibido na gaveta, em 7 pt secundário, abaixo de cada barra de janela.

| Situação | Exibição na gaveta |
|---|---|
| `reset_at` futuro conhecido | `reinicia em 4d 6h`, `reinicia em 2h 14min`, `reinicia em 38min` ou `reinicia em menos de 1min`. |
| `reset_at` no passado | `atualizando…`, e a barra dessa janela fica no estilo tracejado. |
| `reset_at` ausente / desconhecido | Omitir a linha de contagem (ou `reset não informado`). Não inventar estimativas. |
| Marcador de ritmo (traço de 1×7 px na barra) | **Apenas** quando `starts_at` e `reset_at` forem conhecidos e `starts_at < reset_at`. Indica visualmente a fração de tempo já transcorrida da janela. |

---

## 6. Estados de frescor, erro e invalidação pontual

### Invalidação pontual por janela (Cirúrgica)
Se o horário de reset de uma janela específica já expirou:
- **Apenas a célula afetada** exibe `…` ou `atualizando…` com a barra tracejada em alfa reduzido.
- **As demais janelas da mesma conta continuam ativas, com números e cores normais.** A conta inteira não é rebaixada para desatualizada se apenas um limite de 5h venceu enquanto o semanal segue válido.

### Estados do provedor (Frescor individual)
- **Normal (`fresh`)**: `freshness.state == "fresh"`. Exibe cores e barras plenas. Se a última tentativa falhou mas o dado anterior continua fresco, a skin exibe os dados salvos e registra um aviso leve na gaveta (`Última tentativa falhou às {hh:mm}`).
- **Desatualizado (`stale`)**: `freshness.state == "stale"` (passou do `stale_after`). Linha exibe `· {idade}` junto ao nome, números mudam para branco secundário (alfa 150) e as barras ficam tracejadas (`bar-dashed`).
- **Erro sem dado anterior (`never`)**: exibe ícone `!` e texto resumido ocupando as colunas (`Login expirado`, `Sem credencial`, `Sem conexão`, `Sem resposta`). Conta como alerta no rodapé.

---

## 7. Modelo de interação (Hover temporário + Clique fixador)

| Ação | Atraso | Comportamento |
|---|---|---|
| Cursor sobre uma linha | **400 ms** parado | Abre prévia temporária da conta na gaveta. |
| Cursor move para outra linha | **250 ms** sobre a nova | Troca rápida do conteúdo da gaveta sem mover nenhuma linha. |
| Cursor sai da skin | **450 ms** fora (histerese) | Fecha a gaveta se estiver em prévia. Se estiver fixada, nada acontece. |
| Clique esquerdo na linha | Imediato | **Fixa** a gaveta aberta (marcador lateral sólido e dica *"fixado · clique para soltar"*). |
| Clique na linha fixada ou no cabeçalho | Imediato | **Solta e fecha** a gaveta. |
| Roda do mouse na gaveta | Imediato | Rola o conteúdo verticalmente se ultrapassar 260 px. |
| Clique em `‹` ou `›` | Imediato | Alterna para a página anterior/seguinte. |

---

## 8. Conteúdo da gaveta por conta

Estrutura de cima para baixo:
1. **Cabeçalho**: ícone da empresa + Nome em MAIÚSCULAS à esquerda. À direita, idade do dado do provedor (`agora`, `há 2 min`, `há 3 dias`, `nunca`).
2. **Aviso de Estado**: exibido apenas se houver erro, dado antigo ou falha transitória de coleta.
3. **Janelas Principais da Conta** (blocos de 34 px):
   - Rótulo e número na cor de consumo.
   - Barra de 3 px com marcador de ritmo (quando disponível).
   - Texto de reset (`reinicia em...`) ou omitido se não informado.
4. **Janelas por Modelo / Grupo de Modelos**:
   - Rótulo de seção `POR MODELO` ou `POR GRUPO DE MODELOS`.
   - Barras de 2 px para cada modelo com escopo explícito.
5. **Seção de Orçamento (Ref. Local)** para APIs em US$:
   - Rótulo `Orçamento (ref. local)` com barra e `virada da ref. local em {t}`.
6. **Extras**: ex: créditos de reset do Codex (`2 créditos · expiram em 09/12`).
7. **Dica Inferior**: `clique para fixar` ou `fixado · clique para soltar`.

---

## 9. Textos exatos da interface (pt-BR)

| Onde | Texto |
|---|---|
| Título | `USO DE IA` |
| Paginação | `‹ {p} / {total} ›` |
| Cabeçalho das colunas | `5H` · `SEMANA` · `MÊS` |
| Rótulos das janelas | `5 horas` · `Semana` · `Mês` |
| Modelos e grupos | `POR MODELO` · `POR GRUPO DE MODELOS` |
| Reset | `reinicia em {t}` · `atualizando…` |
| Orçamento local | `Orçamento (ref. local)` · `virada da ref. local em {t}` |
| Idade do dado | `agora` · `há {n} min` · `há {n} h` · `há {n} dias` · `nunca` |
| Rodapé | `Instantâneo: {hh:mm}` · `1 alerta` · `{n} alertas` |
| Erros (linha) | `Login expirado` · `Sem credencial` · `Sem conexão` · `Sem resposta` |
| Erros (gaveta) | `Entre de novo na sua conta do {Provedor} para voltar a ver o consumo.` |
| Desatualizado (gaveta) | `Dado antigo` · `Sem atualização desde {dd/mm} às {hh:mm}. Abra o {Provedor} para renovar a sessão.` |
| Falha transitória | `Tentativa recente falhou às {hh:mm}. Exibindo dados anteriores.` |
