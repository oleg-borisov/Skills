# AGENTS.md

Репозиторий содержит переиспользуемые agent assets для Claude Code, OpenCode, ZCode и Codex.

## Структура

| Каталог | Назначение |
| --- | --- |
| agents/ | Канонические Markdown-контракты leaf-agents: implementer, verifier, standards-reviewer, spec-reviewer, reviser. |
| agents/skill.reference | Служебное происхождение prompts, адаптированных из внешних skills. Агенты этот файл не читают. |
| command/ | Primary slash-command adapters /rr-loop и /rr-cascade-loop для Claude Code и OpenCode. |
| skills/rr-loop/ | Канонический user-invoked primary skill с полным controller workflow. |
| skills/rr-cascade-loop/ | Каскад готовых задач спецификации с совмещённым review. |
| .codex/agents/ | Генерируемые TOML profiles только для leaf-agents. |
| .zcode/agents/ | Генерируемые Markdown profiles только для ZCode leaf-agents. |
| docs/agents/ | Инструкции интеграций, например issue-tracker.md. |

Каждый `skills/rr-loop/SKILL.md` и `skills/rr-cascade-loop/SKILL.md` — source of truth своего controller workflow. Отдельных custom controller-agents нет.

## Зависимости

- Leaf-agents используют доступные системные skills только по явным ссылкам в своих контрактах, например /tdd.
- Оба workflow ожидают docs/agents/issue-tracker.md, когда нужны tracker operations.
- Все пять named leaf-agents обязательны; при отсутствии роли или механизма subagents workflow останавливается с BLOCKED_UNSUPPORTED_HOST.

## Генерация Codex profiles

    .\sync-codex-agents.ps1

Скрипт генерирует .codex/agents/*.toml из канонических Markdown agents. TOML-файлы вручную не редактировать.

## Генерация ZCode profiles

    .\sync-zcode-agents.ps1

На macOS:

    bash ./sync-zcode-agents.sh

Скрипты генерируют `.zcode/agents/*.md` из канонических Markdown agents. ZCode-профили вручную не редактировать: они не задают `model`, поэтому наследуют дефолтную модель ZCode.

## Синхронизация окружений

    .\link-codex.ps1

Скрипт сначала генерирует Codex profiles, затем:

- подключает directory skills `rr-loop` и `rr-cascade-loop` junction-ами;
- копирует flat Markdown agents и command в Claude Code/OpenCode;
- сохраняет ~/.codex/agents как junction на .codex/agents;
- копирует TOML leaf-agents и подключает skill во все Orca/codex-accounts/*/home;
- копирует генерируемые ZCode Markdown profiles в `~/.zcode/agents`.

File symlinks не используются: целевые hosts их не подхватывают. Сторонние файлы в пользовательских каталогах сохраняются.

## Синхронизация на macOS (OpenCode + ZCode + ~/.agents)

    ./link-opencode.sh

macOS-аналог junction — это symlink; на macOS hosts корректно читают симлинки,
поэтому всё (skills, agents, command) подключается ссылками и повторная установка
после правок не нужна. ZCode subagents в `~/.zcode/agents` также подключаются
симлинками. Точно так же изменяются только известные rr-loop assets,
существующие пользовательские файлы (например остальные skills в ~/.agents) не трогаются.
Сфера ограничена OpenCode (~/.config/opencode), ZCode (~/.zcode) и каноническим ~/.agents.

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
- На Windows: `~/.zcode/agents/*.md` — копии `.zcode/agents/*.md`.
- На macOS: `~/.config/opencode/agents/*.md`, `~/.zcode/agents/*.md`, все `~/.config/opencode/skills/<skill>`, `~/.config/opencode/commands/rr-loop.md`, `~/.config/opencode/commands/rr-cascade-loop.md` и все `~/.agents/skills/<skill>` — симлинки на этот репозиторий.
- В agent-каталогах присутствуют пять leaf-agents и отсутствуют reviewer/custom-agent rr-loop.
- Skills вызываются в primary-контексте через /rr-loop, $rr-loop, /rr-cascade-loop или $rr-cascade-loop.
- Минимальная версия Codex с custom agents и skills — 0.147.0.
