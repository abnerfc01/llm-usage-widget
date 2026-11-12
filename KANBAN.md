# Kanban: skin de consumo de LLM no Rainmeter

Atualizado em: 2026-11-11 23:15 (pelo coordenador, a cada hora)
Run do Orca: `run_e29986923056`

## Equipe

| Nome | Papel | Modelo | Onde roda |
|---|---|---|---|
| Coordenador | Coordenação, síntese, kanban | Claude Fable 5 | Chat principal |
| Miiaq | Design de UI/UX | Claude Opus 5.5 | Worker do Orca |
| Jayla | Backend (coletor de dados) | gpt-6-sol, esforço alto | Worker do Orca (Codex) |
| Revisor | QA, contesta de propósito | Claude Sonnet 5.5 | Worker do Orca nas próximas rodadas |

## Fazendo

- **Miiaq: design da skin** (`task_1b21e239d721`). Especificação visual e mockup HTML em `design/`, com prévia ao passar o mouse e clique para fixar.
- **Jayla: coleta de uso sem o Orca** (`task_6b2a9665319e`). Investiga como consultar cada provedor diretamente e faz uma chamada de teste por provedor.

## A fazer

- Coordenador: juntar design, relatório da Jayla e objeções do revisor num desenho único e apresentar ao usuário para aprovação.
- Usuário: decidir qual login do Claude vale (ver "Pendências do usuário").
- Revisor: segunda rodada, contestando o desenho consolidado.
- Coordenador: escrever a especificação final e o plano de implementação.
- Jayla: implementar o coletor.
- Implementar a skin do Rainmeter (meters, Lua, animações).
- Revisor: testar a skin instalada.
- Coordenador: escrever o manual de uso (`MANUAL.md`): instalação, leitura das barras e cores, passar o mouse e clicar, estados de erro, como refazer logins, solução de problemas.
- Publicar no GitHub. Bloqueado: `gh` não está logado nesta máquina. Até lá, tudo é versionado em git local nesta pasta.

## Feito

- Coordenador: levantamento do contexto. Skins illustro ativas (Clock, Disk, System, Network), Rainmeter 4.5.28, dados de uso disponíveis por conta.
- Usuário: requisitos definidos. Detalhes ao passar o mouse e ao clicar; sem depender do Orca aberto; equipe em modo orquestração com kanban.
- Revisor: primeira rodada de objeções concluída. Principais achados:
  - A credencial do Claude em `~/.claude` está expirada; a válida está no perfil gerenciado pelo Orca.
  - O coletor não deve renovar tokens, só ler, para não deslogar as ferramentas oficiais.
  - O arquivo de dados não pode ficar na pasta de skins, que é sincronizada pelo OneDrive.
  - Cursor está com login expirado e não entrega dados hoje.
  - Passar o mouse numa skin que muda de altura exige atraso para não tremular.

## Requisitos acrescentados

- Provedores extensíveis: incluir novos serviços (DeepSeek, GLM, MiniMax, a definir) deve ser criar um arquivo de provedor e uma entrada de configuração, sem mexer na skin. Enviado a Jayla (arquitetura do coletor) e Miiaq (lista dinâmica e linha de saldo para APIs pagas por uso).

## Pendências do usuário

- Refazer o login do Cursor (`cursor-agent login`) para que ele tenha dados.
- Dizer qual login do Claude é o principal: o do perfil do Orca ou o de `~/.claude` (hoje expirado).

## Bloqueios

- Nenhum no momento.
