# Revisão de Design — Skin Rainmeter «Uso de IA»

**Data:** 12/11/2026  
**Autora:** Miiaq (UI/UX Designer)  
**Status:** Reconciliado com as decisões do coordenador e com a proposta de contrato v1 (`docs/contrato-coletor-proposta.md` e `docs/decisoes-coordenador.md`).

---

## 1. Resumo da Reconciliação

Esta revisão atualiza a especificação visual ([design-spec.md](file:///D:/code/llm-usage-widget/design/design-spec.md)) e o mockup navegável ([mockup.html](file:///D:/code/llm-usage-widget/design/mockup.html)) para alinhar totalmente a interface aos limites reais do coletor de dados, respeitando:
1. A estética das skins irmãs **illustro** (fundo escuro com contorno sutil, tipografia Trebuchet MS, barras finas de 1 px a 3 px).
2. O modelo de interação com atrasos calibrados (**hover de 400 ms** para prévia temporária, **troca em 250 ms**, **histerese de 450 ms** na saída e **clique para fixar**).
3. A escala semafórica de consumo em 5 níveis (**<25% folga**, **25–49% atenção leve**, **50–74% âmbar illustro**, **75–89% alto**, **≥90% crítico com pulso**).
4. O pedido direto do usuário de **ícones pequenos (12×12 px) à esquerda de cada LLM**, acompanhado de mecanismo de fallback para total extensibilidade.

---

## 2. Reconciliação dos Seis Conflitos do Contrato

### Conflito 1: Mais linhas que a tela e limitação à área útil disponível
- **Problema apontado no contrato:** A premissa de lista infinita ou densa sem controle de altura falha em telas de baixa resolução ou quando a skin fica perto do rodapé. Cinco contas por página **não garantem caber em toda tela e posição a 150% de escala**.
- **Decisão aplicada:** **Paginação explícita** + **delimitação dinâmica à área útil disponível**.
  - A skin define um limite fixo configurável por página (padrão: 5 contas), mas com **fallback explícito** para páginas menores (3 ou 4 contas) se a área útil vertical da tela (`#WORKAREAHEIGHT# - #WORKAREAY#`) for insuficiente.
  - Um controle discreto no topo exibe `‹ Pág 1/2 ›` com botões estáveis.
  - **Áreas de acerto 100% estáveis:** Como as linhas não se movem enquanto o cursor está sobre a página, o risco de laço abre/fecha (tremor de hover) é nulo.
  - **Gaveta:** A altura máxima da gaveta é limitada dinamicamente à área livre da tela. Se o detalhamento ultrapassar essa altura, a gaveta rola via roda do mouse (`MouseScrollUpAction`/`DownAction`), sem alterar a posição das linhas compactas.
  - **Limitação documentada (DPI):** Não se alega validação de DPI sem teste observado em execução real no Rainmeter; trata-se de cálculo geométrico em design que requer validação após a montagem da skin.

### Conflito 2: Reset desconhecido e interpretação de 0%
- **Problema apontado no contrato:** Fontes externas frequentemente omitem `reset_at` e `starts_at`. A spec anterior assumia que `0%` significava `não iniciada` e tentava calcular tempos até reset de forma especulativa.
- **Decisão aplicada:** Omissão estrita de contagem e marcador quando ausente; `0%` é puramente consumo nulo medido.
  - Se `reset_at` for nulo/ausente no contrato: a skin **omite** a contagem regressiva (`reinicia em...`). Na gaveta, o espaço exibe `reset não informado` ou permanece vazio.
  - O **marcador de ritmo** (traço de 1 px sobre a barra de 3 px) só é desenhado se `starts_at` e `reset_at` forem conhecidos e `starts_at < reset_at`. Caso contrário, o traço é omitido.
  - **`0%` de uso:** Mostra o número `0%` com a barra vazia. **Não** infere o texto `não iniciada`. O estado `não iniciada` só é desenhado se o plugin expressamente reportar essa situação no contrato.

### Conflito 3: Maior percentual por modelo em coluna fixa & Janelas extras
- **Problema apontado no contrato:** Cotas de modelos/grupos têm durações distintas. Comparar um modelo com limite semanal e colocá-lo na coluna `5H` geraria confusão conceitual. Além disso, provedores podem ter janelas atípicas (ex: limite de 24h ou rolling de 3 dias) que não cabem em 5h/semana/mês.
- **Decisão aplicada:** Equivalência estrita de janelas temporais + indicador de cota extra.
  - A coluna `5H` aceita **apenas janela comprovadamente equivalente a cinco horas** (`duration_seconds == 18000` ou rótulo/id inequívoco de 5 horas); **nunca ciclo curto genérico ou similar**. Qualquer janela de ciclo curto não equivalente a 5h (ex: 3h, 4h, 6h) é tratada como cota extra (`+N`).
  - As 3 colunas compactas representam estritamente:
    - Coluna 1: Janela comprovada de 5 horas (`5H`).
    - Coluna 2: Janela semanal (~604.800 s, `SEMANA`).
    - Coluna 3: Janela mensal (~2.592.000 s, `MÊS`).
  - O destaque do "maior percentual de uso" (com o ponto `tight-marker` de 3 px) ocorre **estritamente entre cotas comprovadamente equivalentes da mesma categoria temporal** (ex: limite semanal do modelo Fable só concorre na coluna `SEMANA`).
  - Ao passar o mouse sobre a célula com o ponto, a tooltip identifica o escopo: `Fable: 14% (Semana)`.
  - **Janelas extras/atípicas:** Cotas que não correspondem comprovadamente às 3 janelas padrão não são forçadas nas colunas compactas. A linha exibe uma tag sutil `+1` ao lado do nome da conta, e todas as cotas completas aparecem organizadas na gaveta expandida.

### Conflito 4: Orçamento como referência local (Contas em US$)
- **Problema apontado no contrato:** O orçamento (`budget`) é uma configuração do usuário na máquina local, não uma cota de consumo imposta pela API remota. Não possui "reset de API".
- **Decisão aplicada:** Identificação explícita de `Ref. local` e cálculo condicionado.
  - A barra e a porcentagem só são exibidas se houver gasto compatível na **mesma moeda, mesmo período e mesmo escopo**.
  - O término do ciclo é rotulado como `virada da ref. local em {t}`, nunca como reset da API.
  - Na gaveta, a seção é rotulada claramente como `Orçamento (ref. local)` para evitar que o usuário presuma que a API bloqueará requisições ao atingir 100%.
  - Se não houver gasto e orçamento compatíveis, os valores monetários são exibidos puramente em texto (`US$ 12,40 no mês · Orçamento: US$ 20,00`), sem barra percentual forçada.

### Conflito 5: Rodapé global versus frescor individual por provedor
- **Problema apontado no contrato:** Um único provedor atualizado às 14:05 não deve induzir o usuário a crer que todas as contas estão atualizadas naquele minuto.
- **Decisão aplicada:** Timestamp do instantâneo no rodapé + idade individual por provedor.
  - O rodapé passa a exibir `Instantâneo: {hh:mm}` (o horário de publicação do arquivo JSON pelo coletor).
  - O frescor é calculado e mostrado **individualmente** para cada provedor a partir de seu `last_success_at` (ex: `há 2 min`, `há 3 dias`, `nunca`), tanto no cabeçalho da gaveta quanto na linha compacta (em caso de dado antigo).
  - O contador de alertas (`1 alerta`, `2 alertas`) soma provedores com `error != null` ou `freshness.state == "stale"`.
  - Tentativa com erro recente (`last_attempt_result: "error"`), mas com dado anterior ainda fresco (`freshness.state: "fresh"`), mantém os valores normais na interface, registrando apenas diagnóstico na gaveta (`Última tentativa falhou às 14:05`).

### Conflito 6: Reset passado versus estado do provedor (Invalidação pontual da janela)
- **Problema apontado no contrato:** Se o reset de uma janela específica (ex: 5h) já passou, invalidar a conta inteira esconde desnecessariamente as demais janelas (ex: semanal) que continuam válidas.
- **Decisão aplicada:** Invalidação cirúrgica por janela.
  - Se `reset_at` de uma cota específica estiver no passado, **apenas aquela célula de janela** é marcada como `atualizando…` com barra tracejada/inativa.
  - As outras janelas da mesma conta continuam exibindo suas porcentagens e cores normais.
  - O provedor como um todo só entra no estado desatualizado (`stale`) quando seu `freshness.state` global expira (após `stale_after`).

---

## 3. Diretriz de Ícones e Identidade Visual

- **Preservação do Requisito:** Cada linha da conta conta com um ícone de **12×12 px** à esquerda do nome, conforme solicitado diretamente pelo usuário.
- **Nota sobre Autenticidade da Arte:** Os ícones presentes no mockup e previstos para os arquivos `@Resources\Icons\` são **representações estilizadas / aproximadas** para fins de diferenciação visual rápida na interface gráfica. **Não são rotulados nem apresentados como logotipos oficiais autenticados ou homologados pelas empresas detentoras das marcas** (Anthropic, OpenAI, Google, etc.).
- **Fallback Obrigatório (`default.png`):** Para garantir o princípio de provedores extensíveis, qualquer novo provedor adicionado no JSON que não possua um arquivo de ícone correspondente carrega automaticamente o ícone de fallback (uma centelha de IA translúcida). Nenhuma dependência visual rígida é imposta.

---

## 4. Matriz de Evidências e Limitações Técnicas

| Item | Implementação / Solução | Limitação / Evidência no Rainmeter |
|---|---|---|
| **DPI / Escala de Tela** | Coordenadas inteiras, largura 210 px. Paginação e gaveta limitadas à área útil (`#WORKAREAHEIGHT#`). | **Limitação documentada**: cinco contas por página não garantem caber em toda tela e posição a 150%; não se alega validação de DPI sem testes observados no runtime real do Rainmeter. Teste pendente após integração. |
| **Transições e Flickering** | Timers desacoplados (hover 400 ms, leave 450 ms). Posições $Y$ das linhas são constantes. | Testado no mockup: passar o cursor verticalmente entre as linhas não causa contração/expansão da lista, eliminando o tremor de layout. |
| **Valores Monetários** | Moeda ISO 4217, valores formatados em string (`US$ 12,40`). | Provedores em moedas distintas (ex: USD vs CNY) nunca são consolidados em um somatório geral na interface. |
| **Dados Ausentes / Desconexão** | Tratamento explícito de `null` em quotas, ausência de reset e erros com códigos normalizados (`missing_credential`, `auth_expired`, etc.). | Erro de conexão exibe texto seguro em pt-BR e preserva o último valor válido enquanto o frescor permitir. |
| **Rolagem da Gaveta** | `max-height: 260px` com overflow rolável via roda do mouse. | Rainmeter suporta rolagem através de Shape/Meter com ações de scroll incremental em Lua. |

---

## 5. Arquivos Atualizados

1. [docs/revisao-design.md](file:///D:/code/llm-usage-widget/docs/revisao-design.md): Este documento de síntese e conciliação técnica.
2. [design/design-spec.md](file:///D:/code/llm-usage-widget/design/design-spec.md): Especificação completa reescrita e refinada com as 6 decisões, paginação, janelas extras, tratamento de orçamento e notas de arte aproximada.
3. [design/mockup.html](file:///D:/code/llm-usage-widget/design/mockup.html): Mockup estático e interativo atualizado com os novos controles, paginação funcional, simulação de invalidação cirúrgica de reset, orçamento como ref. local e mostruário lado a lado.
