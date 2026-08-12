# AGENTS.md

Репозиторий содержит переиспользуемые агентные активы, общие для нескольких инструментов (Claude Code, opencode, Codex CLI).

## Что здесь лежит

| Каталог | Назначение |
| --- | --- |
| `agents/` | Агенты в markdown-формате: `reviewer` (ревью BLOCKER/MAJOR/MINOR), `reviser` (правки по ревью), `rr-loop` (оркестратор цикла implement → review → revise). |
| `command/` | Слash-команда `/rr-loop` (Claude Code / opencode). |
| `skills/` | Скиллы. Сейчас: `deferred-review` (ручная обработка отложенных замечаний после rr-loop). |
| `.codex/agents/` | Те же агенты в TOML-формате Codex CLI (reviewer, reviser, rr-loop). |
| `docs/agents/` | Документация для агентов (например, `issue-tracker.md` — описание трекера). |

## Связи и зависимости

- `rr-loop` (и `deferred-review`) зависят от скилла `code-review`, установленного в `~/.agents/skills/code-review`.
- `rr-loop` и `deferred-review` ожидают `docs/agents/issue-tracker.md` для публикации отчётов в трекер.
- Агенты и скиллы ожидают наличие `reviewer` и `reviser` в окружении агента, где они выполняются.

## Синхронизация с Codex CLI

Каталоги не копируются, а связываются junction-ами (Windows). Запуск:

```powershell
.\link-codex.ps1
```

Скрипт создаёт:
- `~\.codex\agents` → `.codex\agents` (custom agents Codex CLI, user-уровень)
- `~\.agents\skills\deferred-review` → `skills\deferred-review` (скилл Codex CLI, user-уровень)
- `.\agents\skills` → `skills` (скиллы Codex CLI, уровень репозитория)

Codex сканирует скиллы в `~/.agents/skills` и `.agents/skills` (от CWD до корня репозитория). Каталог `~/.codex/skills` НЕ сканируется. Скиллы также можно вызвать в сессии явно: `/skills` или `$deferred-review`. Custom agents живут в `~/.codex/agents` и `.codex/agents` — их спавнит главная модель по имени.

Повторный запуск безопасен: уже существующие junction-ы пересоздаются.

## Проверка после изменений

- Junction-ы: `Get-Item "$HOME\.codex\agents" | Select LinkType, Target` — должно быть `Junction` с целью на этот репозиторий.
- Агенты: `codex exec "Перечисли доступные custom agents"` из корня репозитория (или начать сессию и спросить). Custom agents не запускаются напрямую из CLI — их спавнит главная модель по имени.
- Скиллы: `codex exec "Доступен ли скилл <name>?"` — или начать сессию и спросить, доступен ли скилл.
- Версии: `codex --version` (минимум 0.147.0 для поддержки custom agents и skills).
