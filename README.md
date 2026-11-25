# LLM Usage Widget

<p align="left">
  <a href="https://github.com/abnerfc01/llm-usage-widget/releases"><img alt="Release" src="https://img.shields.io/github/v/release/abnerfc01/llm-usage-widget?include_prereleases&style=flat-square&color=1a7f37"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.8%2B-1a7f37?style=flat-square&logo=python&logoColor=white">
  <img alt="Status" src="https://img.shields.io/badge/status-em%20desenvolvimento-orange?style=flat-square">
  <a href="https://github.com/abnerfc01/llm-usage-widget/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/abnerfc01/llm-usage-widget?style=flat-square&color=1a7f37"></a>
</p>

Widget estilo **Rainmeter** para acompanhar, direto na área de trabalho, o **uso e os limites das suas contas de LLM** (Claude, Codex, OpenCode, Agy e outras) — sem precisar abrir cada painel manualmente.

## O que ele faz

- Coleta localmente o consumo/percentual de uso de cada provedor configurado.
- Mostra tudo numa skin leve do Rainmeter, com atualização automática.
- Configuração guiada por menu (`Configurar-provedores.cmd`), sem precisar editar JSON na mão.

## Começando

Veja o **[Manual de uso completo](MANUAL.md)** para configurar as contas e instalar a skin.

## Estrutura do projeto

| Pasta | Conteúdo |
|---|---|
| `collector/` | Coletor Python que lê as credenciais locais e calcula o uso por provedor |
| `skin/` | Skin do Rainmeter (exibição) |
| `scripts/` | Utilitários de configuração |
| `examples/` | Exemplos de configuração de provedores |
| `tests/` | Testes automatizados |
| `docs/` | Documentação técnica adicional |

## Status

Projeto em desenvolvimento ativo — acompanhe o progresso em [KANBAN.md](KANBAN.md).
