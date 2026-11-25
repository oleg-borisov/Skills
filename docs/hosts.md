# Генерация профилей и установка на hosts

Канон — `agents/*.md` и `skills/`; всё ниже описывает, как он попадает в Codex, ZCode, Devin, Qoder, Antigravity, Mistral Vibe, Claude Code и OpenCode.

## Генерация Codex profiles

    .\sync-codex-agents.ps1

Скрипт генерирует .codex/agents/*.toml из канонических Markdown agents. TOML-файлы вручную не редактировать.

Модели и reasoning effort leaf-agents задаются в `$profiles` этого скрипта.
Для primary-контроллера spec-delivery рекомендуется `gpt-6.1-sol` / `medium`, выбираемые
в текущем диалоге Codex; генератор и скрипт распространения primary не настраивают.

## Генерация ZCode profiles

    .\sync-zcode-agents.ps1

На macOS:

    bash ./sync-zcode-agents.sh

Скрипты генерируют `.zcode/agents/*.md` из канонических Markdown agents. ZCode-профили вручную не редактировать: они не задают `model`, поэтому наследуют дефолтную модель ZCode.

## Генерация Devin profiles

    .\sync-devin-agents.ps1

На macOS:

    bash ./sync-devin-agents.sh

Скрипты генерируют `.devin/agents/*.md` из канонических Markdown agents. Devin-профили вручную не редактировать: они не задают `model`, поэтому используют default subagent model Devin (`agent.subagent_model` или router), а не модель primary. Read-only роли (`verifier`, `standards-reviewer`, `spec-reviewer`) получают `allowed-tools: read, grep, glob, exec`; остальные — все tools. Запрет вложенных subagents у Devin действует по умолчанию (без `max-nesting`).

## Генерация Qoder profiles

    .\sync-qoder-agents.ps1

Скрипт генерирует `.qoder/agents/*.md` из канонических Markdown agents. Qoder-профили вручную не редактировать: они не задают `model`, поэтому наследуют модель текущей сессии Qoder. Read-only роли (`verifier`, `standards-reviewer`, `spec-reviewer`) получают `tools: Read, Grep, Glob, Bash`; остальные — `disallowedTools: Agent`, чтобы leaf не запускал других агентов. Температура берётся из канонического frontmatter.

## Генерация Vibe profiles

    .\sync-vibe-agents.ps1

Скрипт генерирует `.vibe/agents/*.toml` из канонических Markdown agents — это project-scope профили Mistral Vibe: сессия Vibe в доверенном клоне репозитория видит всех leaf-агентов без установки. Вручную не редактировать.

Профили не задают `active_model`, поэтому каждый субагент наследует модель сессии; `temperature` канонического frontmatter не переносится — у agent-файла Vibe нет per-agent температуры. Все профили — `agent_type = "subagent"` с запретом вложенного запуска (`disabled_tools = ["agents_spawn"]`); read-only роли (`verifier`, `standards-reviewer`, `spec-reviewer`) дополнительно получают `[tools.write_file]`/`[tools.edit]` с `permission = "never"` — bash остаётся у сессии, verifier запускает checks. Новая сессия подхватывает профили после перезапуска или `/reload`.

## Синхронизация окружений

    .\link-codex.ps1

Скрипт сначала генерирует Codex profiles, затем:

- подключает directory skill `spec-delivery` junction-ами;
- копирует flat Markdown agents и command в Claude Code/OpenCode;
- сохраняет ~/.codex/agents как junction на .codex/agents;
- копирует TOML leaf-agents и подключает skill во все Orca/codex-accounts/*/home;
- копирует генерируемые ZCode Markdown profiles в `~/.zcode/agents`;
- копирует генерируемые Devin Markdown profiles в `%APPDATA%\devin\agents`. Skills Devin читает из `~/.agents/skills`.

File symlinks не используются: целевые hosts их не подхватывают. Сторонние файлы в пользовательских каталогах сохраняются.

## Синхронизация Qoder

    .\link-qoder.ps1

Скрипт сначала генерирует Qoder profiles, затем:

- подключает junction-ами все каталоги `skills/` с `SKILL.md` в `~/.qoder/skills`;
- копирует генерируемые Markdown profiles в `~/.qoder/agents`.

Копия skill в `~/.qoder/skills` заменяется junction-ом только при совпадении содержимого с репозиторием (разница CRLF/LF допустима); иначе скрипт останавливается и сохраняет пользовательские файлы. Junction нужен потому, что Qoder отдаёт `~/.qoder/skills` приоритет над `~/.agents/skills`: установленная копия перекрывала бы правки репозитория.

Профили копируются поимённо, а не junction-ом на весь `~/.qoder/agents`, чтобы сохранить сторонние определения агентов пользователя. Slash-command adapters не устанавливаются: в Qoder skills вызываются напрямую через `/<name>`, поэтому `~/.qoder/commands` скрипт не трогает.

Реестр subagents Qoder инициализируется на старте сессии: после установки или правки профилей нужен новый task.

## Синхронизация Vibe

    .\link-vibe.ps1

Скрипт сначала генерирует Vibe profiles, затем:

- подключает junction-ами все каталоги `skills/` с `SKILL.md` в `~/.vibe/skills`;
- копирует генерируемые TOML profiles в `~/.vibe/agents`.

Каталог установки берётся из `VIBE_HOME`, по умолчанию `~/.vibe`. Копия skill в `~/.vibe/skills` заменяется junction-ом только при совпадении содержимого с репозиторием (разница CRLF/LF допустима); иначе скрипт останавливается и сохраняет пользовательские файлы. Профили копируются поимённо, чтобы сохранить сторонние определения агентов пользователя. Правки профилей подхватываются новой сессией Vibe или через `/reload`.

## Синхронизация Antigravity

    .\link-gemini.ps1

Скрипт вызывает `sync-gemini-agents.ps1`: тот собирает plugin `serenity-agents` в игнорируемом `.gemini/plugins/` (agents, skills/spec-delivery, rules). Затем plugin зеркалируется в `~/.gemini/config/plugins/serenity-agents` копированием: plugin discovery Antigravity не читает junction.

## Синхронизация на macOS (OpenCode + ZCode + Devin + ~/.agents)

    ./link-opencode.sh

macOS-аналог junction — это symlink; на macOS hosts корректно читают симлинки,
поэтому skills, OpenCode agents и command подключаются ссылками и повторная установка
после правок не нужна. Исключение — ZCode subagents в `~/.zcode/agents`:
симлинки subagent-профилей ZCode на macOS не читает, поэтому файлы копируются.
Точно так же изменяются только известные spec-delivery assets,
существующие пользовательские файлы (например остальные skills в ~/.agents) не трогаются.
Devin-профили копируются в `~/.config/devin/agents`.
Сфера ограничена OpenCode (~/.config/opencode), ZCode (~/.zcode), Devin (~/.config/devin) и каноническим ~/.agents.

## OpenCode models

Канонические `agents/*.md` не задают `model`, поэтому наследуют дефолтную модель
OpenCode. Никакой скрипт модели для OpenCode не устанавливает.

Ранее установленные overrides чистятся разово:

    pwsh -NoProfile -ExecutionPolicy Bypass -File .\remove-opencode-model-overrides.ps1

Скрипт удаляет только `agents.<name>.model` известных spec-delivery агентов
(`implementer`, `verifier`, `standards-reviewer`, `spec-reviewer`, `reviser`, `scout`),
пустые секции зачищает, остальной конфиг не трогает
(перед записью делает `.bak.*`).

Требует PowerShell 7+.

## Проверка

- Get-Item для ~/.codex/agents возвращает junction на .codex/agents этого репозитория.
- На Windows и macOS: `~/.zcode/agents/*.md` — копии `.zcode/agents/*.md` (ZCode subagent-профили симлинки не читают).
- Devin: `%APPDATA%\devin\agents\*.md` (Windows) или `~/.config/devin/agents/*.md` (macOS) — копии `.devin/agents/*.md`; новая сессия Devin видит шесть leaf-agents как subagent profiles.
- В Qoder: `~/.qoder/skills/<skill>` — junction на `skills/<skill>` этого репозитория для каждого skill с `SKILL.md`; `~/.qoder/agents/*.md` — копии `.qoder/agents/*.md`. Новый task Qoder видит все шесть leaf-agents как subagent types; read-only роли не имеют Write/Edit/Agent, остальные не имеют Agent.
- В Vibe: `~/.vibe/skills/<skill>` — junction на `skills/<skill>` этого репозитория для каждого skill с `SKILL.md`; `~/.vibe/agents/*.toml` — копии `.vibe/agents/*.toml`. Новая сессия Vibe видит шесть leaf-агентов как spawnable subagents; read-only роли имеют `never` на write_file/edit, все профили не запускают субагентов.
- На macOS: `~/.config/opencode/agents/*.md`, все `~/.config/opencode/skills/<skill>`, `spec-delivery.md` в `~/.config/opencode/commands` и все `~/.agents/skills/<skill>` — симлинки на этот репозиторий.
- В agent-каталогах присутствуют пять обязательных leaf-agents и опциональный scout; reviewer/custom-agent отсутствуют.
- `agents/*.md`, `.zcode/agents/*.md`, `.qoder/agents/*.md`, `.devin/agents/*.md`, `.vibe/agents/*.toml` и устанавливаемые OpenCode agents не содержат `model` и наследуют дефолтную модель хоста; `opencode.json` не содержит `agents.<name>.model`.
- Skills вызываются в primary-контексте через `/spec-delivery`, `$spec-delivery`, `/tdd` или `$tdd`.
- Минимальная версия Codex с custom agents и skills — 0.147.0.
- У `spec-delivery` и `wait-what-ru` есть `agents/openai.yaml` с `policy.allow_implicit_invocation: false`: Codex не читает `disable-model-invocation` и без этого файла показывает skill модели.

При обновлении старой установки удали оставшиеся ссылки и установленные копии
`rr-loop`, `rr-parallel-loop` и `rr-cascade-loop-fast` из каталогов skills и commands. Для Antigravity также очисти прежние копии в сгенерированном `.gemini/plugins/serenity-agents/skills/` перед синхронизацией.
Журналы запусков находятся в checkout продукта и нужны для resume.
