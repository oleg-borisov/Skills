# AGENTS.md

Репозиторий содержит переиспользуемые agent assets для Claude Code, OpenCode и Codex.

## Структура

| Каталог | Назначение |
| --- | --- |
| agents/ | Канонические Markdown-контракты leaf-agents: implementer, verifier, standards-reviewer, spec-reviewer, reviser. |
| agents/skill.reference | Служебное происхождение prompts, адаптированных из внешних skills. Агенты этот файл не читают. |
| command/ | Primary slash-command adapter /rr-loop для Claude Code и OpenCode. |
| skills/rr-loop/ | Канонический user-invoked primary skill с полным controller workflow. |
| .codex/agents/ | Генерируемые TOML profiles только для leaf-agents. |
| docs/agents/ | Инструкции интеграций, например issue-tracker.md. |

skills/rr-loop/SKILL.md — единственный source of truth controller. Отдельного custom-agent rr-loop нет.

## Зависимости

- Leaf-agents используют доступные системные skills только по явным ссылкам в своих контрактах, например /tdd.
- rr-loop ожидает docs/agents/issue-tracker.md, когда нужны tracker operations.
- Все пять named leaf-agents обязательны; при отсутствии роли или механизма subagents workflow останавливается с BLOCKED_UNSUPPORTED_HOST.

## Генерация Codex profiles

    .\sync-codex-agents.ps1

Скрипт генерирует .codex/agents/*.toml из канонических Markdown agents. TOML-файлы вручную не редактировать.

## Синхронизация окружений

    .\link-codex.ps1

Скрипт сначала генерирует Codex profiles, затем:

- подключает directory skills rr-loop junction-ами;
- копирует flat Markdown agents и command в Claude Code/OpenCode;
- сохраняет ~/.codex/agents как junction на .codex/agents;
- копирует TOML leaf-agents и подключает skill во все Orca/codex-accounts/*/home;

File symlinks не используются: целевые hosts их не подхватывают. Сторонние файлы в пользовательских каталогах сохраняются.

## Синхронизация на macOS (OpenCode + ~/.agents)

    ./link-opencode.sh

macOS-аналог junction — это symlink; на macOS hosts корректно читают симлинки,
поэтому всё (skills, agents, command) подключается ссылками и повторная установка
после правок не нужна. Точно так же изменяются только известные rr-loop assets,
существующие пользовательские файлы (например остальные skills в ~/.agents) не трогаются.
Сфера ограничена OpenCode (~/.config/opencode) и каноническим ~/.agents.

## OpenCode model overrides

    pwsh -NoProfile -ExecutionPolicy Bypass -File .\install-opencode-model-overrides.ps1

Канонические `agents/*.md` остаются без модели. Скрипт мержит в
`~/.config/opencode/opencode.json` только `agents.<name>.model`, не трогая
остальной конфиг (перед записью делает `.bak.*`):

| Agent | Model |
| --- | --- |
| implementer, reviser, verifier | `omniroute/coder` |
| standards-reviewer, spec-reviewer | `omniroute/architector` |

Требует PowerShell 7+.

## Проверка

- Get-Item для ~/.codex/agents возвращает junction на .codex/agents этого репозитория.
- На macOS: `~/.config/opencode/agents/*.md`, `~/.config/opencode/skills/rr-loop`, `~/.config/opencode/commands/rr-loop.md` и `~/.agents/skills/rr-loop` — симлинки на этот репозиторий.
- В agent-каталогах присутствуют пять leaf-agents и отсутствуют reviewer/custom-agent rr-loop.
- Skill rr-loop вызывается в primary-контексте через /rr-loop или $rr-loop.
- Минимальная версия Codex с custom agents и skills — 0.147.0.
