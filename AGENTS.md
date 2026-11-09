# AGENTS.md

Репозиторий содержит переиспользуемые agent assets для Claude Code, OpenCode, ZCode, Codex и Qoder.

## Структура

| Каталог | Назначение |
| --- | --- |
| agents/ | Канонические Markdown-контракты leaf-agents: implementer, verifier, standards-reviewer, spec-reviewer, reviser, scout (опциональный exploration-агент). |
| agents/skill.reference | Служебное происхождение prompts, адаптированных из внешних skills. Агенты этот файл не читают. |
| command/ | Primary slash-command adapters /rr-loop, /rr-cascade-loop-fast и /rr-parallel-loop для Claude Code и OpenCode. |
| skills/rr-loop/ | Канонический user-invoked primary skill с полным controller workflow. |
| skills/rr-cascade-loop-fast/ | Каскад с исправлением findings в Implement следующей задачи. |
| skills/rr-parallel-loop/ | Rolling frontier графа задач в отдельных worktree, общий gate/review и recovery. |
| skills/tdd/ | Канонический test-first workflow с независимым oracle и проверкой дефектов теста. |
| .codex/agents/ | Генерируемые TOML profiles только для leaf-agents. |
| .zcode/agents/ | Генерируемые Markdown profiles только для ZCode leaf-agents. |
| .qoder/agents/ | Генерируемые Markdown profiles только для Qoder leaf-agents. |
| docs/agents/ | Инструкции интеграций, например issue-tracker.md. |

Каждый `skills/rr-loop/SKILL.md`, `skills/rr-cascade-loop-fast/SKILL.md` и `skills/rr-parallel-loop/SKILL.md` задаёт порядок своего controller workflow. Общие контракты ledger, handoff, review/gate и cleanup — в `skills/rr-loop/references/protocol.md`, обязательном для primary-controller всех трёх skills. Leaf-agents работают по своим контрактам; controller protocol читают только как объект задачи на сами workflow assets. Отдельных custom controller-agents нет.

`skills/tdd/SKILL.md` — локальная версия одноимённого skill для TDD-задач в этом репозитории.

## Зависимости

- Leaf-agents используют доступные системные skills только по явным ссылкам в своих контрактах, например /tdd.
- Все workflow ожидают docs/agents/issue-tracker.md, когда нужны tracker operations.
- Все пять named leaf-agents обязательны; при отсутствии роли или механизма subagents workflow останавливается с BLOCKED_UNSUPPORTED_HOST. scout — опциональный шестой: его недоступность даёт NOT_APPLICABLE Exploration, а не BLOCKED.

## Генерация Codex profiles

    .\sync-codex-agents.ps1

Скрипт генерирует .codex/agents/*.toml из канонических Markdown agents. TOML-файлы вручную не редактировать.

Модели и reasoning effort leaf-agents задаются в `$profiles` этого скрипта.
Для primary-контроллера rr-loop рекомендуется `gpt-6.1-sol` / `medium`, выбираемые
в текущем диалоге Codex; генератор и скрипт распространения primary не настраивают.

## Генерация ZCode profiles

    .\sync-zcode-agents.ps1

На macOS:

    bash ./sync-zcode-agents.sh

Скрипты генерируют `.zcode/agents/*.md` из канонических Markdown agents. ZCode-профили вручную не редактировать: они не задают `model`, поэтому наследуют дефолтную модель ZCode.

## Генерация Qoder profiles

    .\sync-qoder-agents.ps1

Скрипт генерирует `.qoder/agents/*.md` из канонических Markdown agents. Qoder-профили вручную не редактировать: они не задают `model`, поэтому наследуют модель текущей сессии Qoder. Read-only роли (`verifier`, `standards-reviewer`, `spec-reviewer`) получают `tools: Read, Grep, Glob, Bash`; остальные — `disallowedTools: Agent`, чтобы leaf не запускал других агентов. Температура берётся из канонического frontmatter.

## Синхронизация окружений

    .\link-codex.ps1

Скрипт сначала генерирует Codex profiles, затем:

- подключает directory skills `rr-loop`, `rr-cascade-loop-fast` и `rr-parallel-loop` junction-ами;
- копирует flat Markdown agents и command в Claude Code/OpenCode;
- сохраняет ~/.codex/agents как junction на .codex/agents;
- копирует TOML leaf-agents и подключает skill во все Orca/codex-accounts/*/home;
- копирует генерируемые ZCode Markdown profiles в `~/.zcode/agents`.

File symlinks не используются: целевые hosts их не подхватывают. Сторонние файлы в пользовательских каталогах сохраняются.

## Синхронизация Qoder

    .\link-qoder.ps1

Скрипт сначала генерирует Qoder profiles, затем:

- подключает junction-ами все каталоги `skills/` с `SKILL.md` в `~/.qoder/skills`;
- копирует генерируемые Markdown profiles в `~/.qoder/agents`.

Копия skill в `~/.qoder/skills` заменяется junction-ом только при совпадении содержимого с репозиторием (разница CRLF/LF допустима); иначе скрипт останавливается и сохраняет пользовательские файлы. Junction нужен потому, что Qoder отдаёт `~/.qoder/skills` приоритет над `~/.agents/skills`: установленная копия перекрывала бы правки репозитория.

Профили копируются поимённо, а не junction-ом на весь `~/.qoder/agents`, чтобы сохранить сторонние определения агентов пользователя. Slash-command adapters не устанавливаются: в Qoder skills вызываются напрямую через `/<name>`, поэтому `~/.qoder/commands` скрипт не трогает.

Реестр subagents Qoder инициализируется на старте сессии: после установки или правки профилей нужен новый task.

## Синхронизация на macOS (OpenCode + ZCode + ~/.agents)

    ./link-opencode.sh

macOS-аналог junction — это symlink; на macOS hosts корректно читают симлинки,
поэтому skills, OpenCode agents и command подключаются ссылками и повторная установка
после правок не нужна. Исключение — ZCode subagents в `~/.zcode/agents`:
симлинки subagent-профилей ZCode на macOS не читает, поэтому файлы копируются.
Точно так же изменяются только известные rr-loop assets,
существующие пользовательские файлы (например остальные skills в ~/.agents) не трогаются.
Сфера ограничена OpenCode (~/.config/opencode), ZCode (~/.zcode) и каноническим ~/.agents.

## OpenCode models

Канонические `agents/*.md` не задают `model`, поэтому наследуют дефолтную модель
OpenCode. Никакой скрипт модели для OpenCode не устанавливает.

Ранее установленные overrides чистятся разово:

    pwsh -NoProfile -ExecutionPolicy Bypass -File .\remove-opencode-model-overrides.ps1

Скрипт удаляет только `agents.<name>.model` известных rr-loop агентов
(`implementer`, `verifier`, `standards-reviewer`, `spec-reviewer`, `reviser`, `scout`),
пустые секции зачищает, остальной конфиг не трогает
(перед записью делает `.bak.*`).

Требует PowerShell 7+.

## Проверка

- Get-Item для ~/.codex/agents возвращает junction на .codex/agents этого репозитория.
- На Windows и macOS: `~/.zcode/agents/*.md` — копии `.zcode/agents/*.md` (ZCode subagent-профили симлинки не читают).
- В Qoder: `~/.qoder/skills/<skill>` — junction на `skills/<skill>` этого репозитория для каждого skill с `SKILL.md`; `~/.qoder/agents/*.md` — копии `.qoder/agents/*.md`. Новый task Qoder видит все шесть leaf-agents как subagent types; read-only роли не имеют Write/Edit/Agent, остальные не имеют Agent.
- На macOS: `~/.config/opencode/agents/*.md`, все `~/.config/opencode/skills/<skill>`, commands `rr-loop.md`, `rr-cascade-loop-fast.md`, `rr-parallel-loop.md` в `~/.config/opencode/commands` и все `~/.agents/skills/<skill>` — симлинки на этот репозиторий.
- В agent-каталогах присутствуют пять обязательных leaf-agents и опциональный scout; reviewer/custom-agent rr-loop отсутствуют.
- `agents/*.md`, `.zcode/agents/*.md`, `.qoder/agents/*.md` и устанавливаемые OpenCode agents не содержат `model` и наследуют дефолтную модель хоста; `opencode.json` не содержит `agents.<rr-loop>.model`.
- Skills вызываются в primary-контексте через /rr-loop, $rr-loop, /rr-cascade-loop-fast, $rr-cascade-loop-fast, /rr-parallel-loop, $rr-parallel-loop, /tdd или $tdd.
- Минимальная версия Codex с custom agents и skills — 0.147.0.
