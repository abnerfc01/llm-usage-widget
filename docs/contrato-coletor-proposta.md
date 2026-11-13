# Proposta pendente de aprovação: contrato coletor → skin

**Estado:** proposta técnica para revisão; nenhum campo, comportamento ou caminho abaixo foi aprovado ou implementado.  
**Escopo:** instantâneo JSON local entre um coletor executado independentemente do processo Orca e uma skin dinâmica do Rainmeter. Esta proposta não afirma que qualquer provedor ofereça os dados do exemplo.

## Limites e responsabilidades propostos

- O coletor agenda tentativas por provedor, chama plugins e normaliza apenas dados que cada fonte realmente fornece. A skin lê um único instantâneo, não autentica, não chama APIs e não conhece nomes de provedores.
- A configuração define plugins, ordem, visibilidade e referências externas de credenciais. Um provedor novo exige um arquivo de plugin e uma entrada de configuração; a skin consome o mesmo contrato. Um plugin pode produzir cotas, valores monetários, ambos ou nenhum enquanto está indisponível.
- Nenhuma janela `diária`, `5h`, `semanal` ou `mensal` é presumida. Plugins emitem identificador e rótulo de cada janela efetivamente observada. A duração, o início e o reset são opcionais, pois a fonte pode não informá-los. `0%` significa uso medido em zero; ausência de janela significa que ela não foi informada; valor desconhecido não vira zero.
- O JSON contém só dados de exibição e diagnóstico seguro. Credenciais, cookies, tokens, cabeçalhos HTTP, respostas brutas, URLs autenticadas e caminhos de perfis não entram no arquivo, na configuração de exemplo ou em mensagens de erro.

## Envelope JSON v1 proposto

| Campo | Tipo e regra |
|---|---|
| `schema_version` | String `1.0`. Mudança incompatível exige versão principal nova; leitores rejeitam versão principal desconhecida e podem ignorar campos adicionais de v1. |
| `generated_at` | Instante ISO 8601 com fuso. Marca a publicação do arquivo, não uma coleta bem-sucedida. |
| `providers` | Array na ordem configurada, incluindo provedores com erro ou sem credencial. `id` estável e único; `display_name` é texto de apresentação, nunca chave de lógica. |

Cada objeto de `providers` contém `id`, `display_name`, `kind` (`quota`, `metered` ou `mixed`), `enabled`, `visible`, `collection_interval_seconds`, `last_attempt_at`, `last_attempt_result`, `last_success_at`, `freshness`, `error` e `data`. `last_attempt_at` e `last_success_at` são instantes ISO 8601 ou `null`; `last_attempt_result` é `success`, `error` ou `never`. Uma falha posterior não apaga `last_success_at` nem o último `data` válido. Para `never`, ambos os instantes são `null` e `data` é `null`. `enabled=false` impede coleta; `visible=false` só oculta a linha, sem alterar a posição relativa das demais.

`freshness` é calculado **por provedor** a partir do último sucesso: `state` vale `fresh`, `stale` ou `never`; `stale_after` é o instante limite ou `null`. A regra inicial proposta é `max(3 × collection_interval_seconds, 1800)` após `last_success_at`, compatível com a especificação de design; seu valor e eventual ajuste por provedor precisam de aprovação. Uma tentativa falha pode coexistir com `fresh`, pois erro de tentativa e idade do dado são fatos distintos. `generated_at` recente não torna um provedor fresco. Um `reset_at` já passado invalida aquela **janela** mesmo que o restante do provedor esteja fresco; a skin não exibe percentual antigo como atual.

`error` é `null` ou `{ "code": "...", "message_key": "..." }`. Códigos propostos: `missing_credential`, `auth_expired`, `network`, `timeout`, `provider_unavailable`, `unsupported`, `invalid_response`. A skin mapeia códigos conhecidos a textos pt-BR seguros; código desconhecido vira `Sem resposta`. `message_key` é opcional, de vocabulário fechado, sem texto livre oriundo do servidor. `next_attempt_at` pode aparecer no provedor quando houver agendamento conhecido; a skin omite a contagem regressiva se não houver. Diagnóstico detalhado, se necessário, fica fora deste contrato e deve ser saneado.

### `data.quotas`

`data.quotas` é um array, possivelmente vazio, de limites observados. Cada item contém:

| Campo | Tipo e significado |
|---|---|
| `id` | Identificador estável dentro do provedor, sem depender da posição no array. |
| `scope` | `{ "type": "account|model|model_group", "id": "...", "label": "..." }`. Permite vários modelos e grupos, com nomes vindos do plugin. |
| `window` | `{ "id": "...", "label": "..." }` e, somente quando conhecidos, `duration_seconds`, `starts_at`, `reset_at`. `id` descreve a janela do provedor; não precisa corresponder a uma coluna fixa. |
| `used_percent` | Número finito maior ou igual a zero quando a fonte fornece percentual comparável de uso da cota. Pode ultrapassar 100; a barra pode ser limitada visualmente, mas o número permanece real. Se a fonte fornece apenas unidades absolutas sem denominador, o plugin não inventa percentual e deve usar outro campo numa futura versão aprovada. |
| `observed_at` | Instante da observação, quando conhecido. Se omitido, usa-se `last_success_at` do provedor como referência de idade. |

`reset_at` desconhecido não autoriza a skin a mostrar `não iniciada`, um horário estimado, progresso temporal ou marcador de ritmo. `não iniciada` exige informação explícita de estado da fonte em evolução futura do contrato; `0%` sozinho não prova isso. O marcador de ritmo só é calculável quando `starts_at` e `reset_at` são conhecidos e `starts_at < reset_at`. A skin calcula o tempo restante a partir do relógio local somente para reset conhecido e futuro.

### `data.money`

`data.money`, quando presente, usa `currency` em código ISO 4217 e valores decimais **como strings** para evitar arredondamento binário. `balance` é opcional e representa saldo informado pelo provedor, sem sinal de consumo percentual. `spend` é um array de `{ period: { id, label, starts_at?, ends_at? }, amount, scope? }`; `scope` opcional usa o mesmo formato de `quotas` para gasto por modelo. Uma agregação por modelo não deve ser presumida completa nem somada automaticamente ao total da conta. A skin apresenta o símbolo e a formatação local a partir de `currency`; moedas diferentes nunca são somadas ou comparadas sem conversão explicitamente aprovada.

`budget`, se configurado, é `{ amount, currency, period: { id, label, starts_at?, ends_at? }, source: "local_config" }`, com `scope` opcional; a ausência de `scope` em gasto e orçamento significa conta inteira. É **referência local definida pelo usuário**, não limite contratual, saldo do provedor ou bloqueio garantido. O percentual de orçamento só pode ser calculado quando existe gasto da mesma moeda, escopo e período; se faltarem período ou gasto compatível, mostrar orçamento e gasto separadamente, sem barra percentual nem reset inventado. Um limiar monetário de alerta, como `US$ 1`, também requer configuração explícita e moeda correspondente; não é universal.

## Exemplo exclusivamente sintético

Os nomes, números e horários abaixo são inventados para exercitar o contrato. O primeiro provedor preservou um sucesso às 14:00 após erro às 14:05; `fresh` vale até 14:30. O segundo tem gasto mensal de USD 12.40 e orçamento local de USD 20.00, logo a referência consumida seria 62% no mesmo período.

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-11-11T14:06:00-03:00",
  "providers": [
    {
      "id": "demo_quota",
      "display_name": "Exemplo Cotas",
      "kind": "quota",
      "enabled": true,
      "visible": true,
      "collection_interval_seconds": 600,
      "last_attempt_at": "2026-11-11T14:05:00-03:00",
      "last_attempt_result": "error",
      "last_success_at": "2026-11-11T14:00:00-03:00",
      "freshness": {
        "state": "fresh",
        "stale_after": "2026-11-11T14:30:00-03:00"
      },
      "error": {
        "code": "auth_expired",
        "message_key": "auth_expired"
      },
      "data": {
        "quotas": [
          {
            "id": "account_5h",
            "scope": { "type": "account", "id": "account", "label": "Conta" },
            "window": {
              "id": "rolling_5h",
              "label": "5 horas",
              "duration_seconds": 18000,
              "starts_at": "2026-11-11T11:00:00-03:00",
              "reset_at": "2026-11-11T16:00:00-03:00"
            },
            "used_percent": 35
          },
          {
            "id": "account_week",
            "scope": { "type": "account", "id": "account", "label": "Conta" },
            "window": {
              "id": "week",
              "label": "Semana",
              "starts_at": "2026-11-09T00:00:00-03:00",
              "reset_at": "2026-11-16T00:00:00-03:00"
            },
            "used_percent": 15
          },
          {
            "id": "model_week",
            "scope": { "type": "model", "id": "demo_model", "label": "Modelo Exemplo" },
            "window": { "id": "week", "label": "Semana" },
            "used_percent": 14
          }
        ]
      }
    },
    {
      "id": "demo_metered",
      "display_name": "Exemplo API",
      "kind": "metered",
      "enabled": true,
      "visible": true,
      "collection_interval_seconds": 900,
      "last_attempt_at": "2026-11-11T14:04:00-03:00",
      "last_attempt_result": "success",
      "last_success_at": "2026-11-11T14:04:00-03:00",
      "freshness": {
        "state": "fresh",
        "stale_after": "2026-11-11T14:49:00-03:00"
      },
      "error": null,
      "data": {
        "quotas": [],
        "money": {
          "currency": "USD",
          "spend": [
            {
              "period": {
                "id": "2026-11",
                "label": "Novembro",
                "starts_at": "2026-11-01T00:00:00-03:00",
                "ends_at": "2026-12-01T00:00:00-03:00"
              },
              "amount": "12.40"
            }
          ],
          "budget": {
            "amount": "20.00",
            "currency": "USD",
            "period": {
              "id": "2026-11",
              "label": "Novembro",
              "starts_at": "2026-11-01T00:00:00-03:00",
              "ends_at": "2026-12-01T00:00:00-03:00"
            },
            "source": "local_config"
          }
        }
      }
    }
  ]
}
```

## Configuração e publicação propostas

Exemplo **sem segredos** de entrada de configuração: `{ "id": "demo_quota", "plugin": "demo_quota", "enabled": true, "visible": true, "order": 10, "credential_ref": "demo_quota_default" }`. `credential_ref` é só um identificador opaco para armazenamento externo de credenciais; o plugin recebe acesso por mecanismo local apropriado, nunca por valor serializado no instantâneo. A resolução de credenciais não deve depender do Orca aberto, e o coletor não deve renovar tokens nem alterar sessões de ferramentas oficiais. Se a credencial faltar ou expirar, publicar estado seguro e preservar dados anteriores.

Local proposto para dados e configuração: `%LOCALAPPDATA%\LLMUsageWidget\`, fora da pasta da skin sincronizada pelo OneDrive. O coletor grava o JSON completo em arquivo temporário **no mesmo diretório**, valida-o, força a gravação e substitui atomicamente o instantâneo anterior; a skin abre apenas o arquivo final e mantém o último instantâneo válido se a leitura falhar. Limitar permissões ao usuário local, não incluir dados sensíveis nos logs e não usar o JSON como canal de credenciais. A viabilidade exata da substituição atômica no Windows e do caminho configurável pela skin fica para implementação e teste posteriores.

## Problemas concretos na especificação visual, pendentes de decisão

1. **Mais linhas que a tela.** A seção 2 diz que a lista nunca rola, mas o modo denso e a rolagem só da gaveta não resolvem quando as próprias linhas excedem a altura útil. A configuração pode ocultar provedores, porém isso exige escolha manual e pode esconder erros. É preciso aprovar limite visível, paginação, lista rolável com áreas de acerto estáveis ou outro comportamento, inclusive em telas pequenas e escala de 150%.
2. **Reset desconhecido.** As seções 5, 9 e 10 descrevem tempo restante, tooltip, marcador de ritmo e `não iniciada` como se todo provedor informasse início/reset. Com `reset_at` ausente, a UI deve omitir esses elementos e dizer `reset desconhecido` somente se esse texto for aprovado. `0%` não determina se a janela começou.
3. **Pior limite por modelo em coluna fixa.** A seção 0 escolhe o maior percentual de conta/modelo/grupo para cada coluna, mas essa comparação só é válida entre janelas equivalentes. Um limite de modelo semanal não pode ocupar `5H`, e um provedor com janela diária ou irregular não cabe nas três colunas. Mesmo quando comparável, a célula deve identificar qual escopo gerou o valor e a gaveta deve conservar todos os limites; a regra de seleção e a representação de janelas extras precisam de aprovação.
4. **Orçamento é referência local.** A seção 2 trata orçamento como percentual na coluna mensal ou semanal e a seção 9 o mostra com reset. O orçamento não é cota imposta pelo provedor. Período, moeda e gasto compatíveis são pré-requisitos para percentual; `ends_at` do orçamento é virada da referência local, não reset da API. Texto, cor e alerta devem comunicar essa distinção.
5. **Rodapé global versus frescor individual.** `Atualizado às {hh:mm}` pode refletir só um provedor enquanto outro está antigo ou com erro. A skin deve usar `last_success_at` de cada linha e contar alertas por provedor, deixando claro o significado do horário global antes de aprovar o texto final.
6. **Reset passado versus estado do provedor.** A seção 6 marca a linha inteira como desatualizada quando qualquer reset passa. Isso pode esconder outras janelas ainda válidas. A proposta invalida a janela afetada e mantém o frescor do provedor separado; o comportamento visual precisa de decisão explícita.

**Decisão pendente:** aprovar ou ajustar este contrato e as regras de UI acima antes de implementar coletor, plugins ou skin.
