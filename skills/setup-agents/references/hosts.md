# Установка именованных профилей

Пути ниже пользовательские. `~` — домашний каталог. `render.py options` показывает конечные пути и модели, `render.py render` создаёт файлы UTF-8 без BOM. В профиле записывается абсолютный путь к контракту после разрешения symlink и junction.

| Хост | Windows | macOS | Формат и ограничения |
| --- | --- | --- | --- |
| Codex | `~/.codex/agents` | `~/.codex/agents` | TOML, `model`, `model_reasoning_effort`, `sandbox_mode` read-only для verifier и reviewers, workspace-write для остальных |
| Claude Code | `~/.claude/agents` | `~/.claude/agents` | Markdown, `model`, `effort`, allowlist Read/Grep/Glob/Bash для read-only ролей, запрет Agent у остальных |
| OpenCode | `~/.config/opencode/agents` | `~/.config/opencode/agents` | Markdown, `mode: subagent`, опциональный `model`, разрешён bash, `permission.edit` по роли, `task: deny` |
| Devin | `%APPDATA%/devin/agents` | `~/.config/devin/agents` | Markdown, опциональный `model`, `allowed-tools: read, grep, glob, exec` для read-only ролей, вложенность ограничивает хост |
| Qoder | `~/.qoder/agents` | `~/.qoder/agents` | Markdown, `model`, `temperature`, Read/Grep/Glob/Bash для read-only ролей, `disallowedTools: Agent` у остальных |
| ZCode | `~/.zcode/agents` | `~/.zcode/agents` | Markdown, `model`, `thoughtLevel` при закреплённой модели, Read/Grep/Glob/Bash для read-only ролей |
| Mistral Vibe | `~/.vibe/agents` | `~/.vibe/agents` | TOML, `agent_type = "subagent"`, опциональный `active_model`, запрет `agents_spawn`, для read-only ролей запрет `write_file` и `edit` |
| Antigravity | `~/.gemini/config/plugins/serenity-agents/agents` | `~/.gemini/config/plugins/serenity-agents/agents` | Markdown, `subagent: true`, `mainAgent: false`, `model` принимает `inherit`, `pro`, `flash`. Для read-only ролей `view_file`, `grep_search`, `run_command` |

Allowlist файловых инструментов и поле sandbox зависят от версии хоста. Shell доступен для проверок. Ограничения контракта действуют на всех хостах.

## Особенности установки

- **Codex.** Используй пользовательский каталог (`$CODEX_HOME/agents`, если задан). У project-scope профилей наблюдался отказ spawn при видимой роли. Старая версия `link-codex.ps1` делала junction `~/.codex/agents` на `.codex/agents` checkout. Если назначение — этот junction, сначала прочитай модели из него, если файлы ещё доступны. После согласия проверь его цель, убери только сам junction через `(Get-Item -LiteralPath <каталог> -Force).Delete()` без рекурсии и создай обычный каталог. Для неизвестной ссылки уточни реальный пользовательский каталог. Orca даёт каждому аккаунту отдельный `%APPDATA%/orca/codex-accounts/<аккаунт>/home/agents`. Укажи этот путь в `--install-dir` и повтори для каждого выбранного аккаунта. При `inherit` профиль опускает `model`.
- **Qoder.** Начни новый task для инициализации реестра. В версиях с `/agents reload` можно обновить его этой командой. [Документация Qoder](https://docs.qoder.com/cli/subagent)
- **ZCode.** На macOS копируй профили обычными файлами. Используй новую сессию. Документация описывает встроенный `general-purpose`; доступность запуска проверяй в текущей версии и тарифе. [Документация ZCode](https://www.zcode.network/en/docs/subagents/)
- **Devin.** Custom subagents могут требовать включения экспериментальной функции. При отсутствии `model` выбор делает конфигурация Devin. [Документация Devin](https://docs.devin.ai/cli/subagents.md)
- **Vibe.** Учитывается `VIBE_HOME`. Значение `active_model` должно существовать в конфигурации Vibe. После установки начни новую сессию или используй `/reload`. [Исходный код профилей Vibe](https://github.com/mistralai/mistral-vibe/blob/main/vibe/core/agents/models.py)
- **Antigravity.** Plugin discovery ожидает обычные каталоги. Сначала установи plugin со skill через `link-gemini.ps1` на Windows или скопируй каталоги обоих навыков и создай `plugin.json` с `{"name":"serenity-agents"}` в корне plugin на macOS. Запускай renderer из checkout, чтобы профили ссылались на канонический контракт. Из старого plugin убери прежнее генерируемое правило `rules/AGENTS.md` про обязательный `invoke_subagent` типа `self`, если оно осталось и целиком относится к старой установке. В новой сессии проверь доступность профилей. Встроенный тип для прямого вызова с контрактом — `self`. [Документация Antigravity](https://antigravity.google/docs/subagents?tab=cli)
- **Claude Code и OpenCode.** Старые профили, установленные как симлинки, заменяй обычными файлами. Начни новую сессию. [Claude Code](https://code.claude.com/docs/en/sub-agents) · [OpenCode](https://opencode.ai/docs/agents/)

## Разовая очистка OpenCode

Если `opencode.json` содержит старые `agents.<name>.model`, сначала сделай резервную копию и затем убери только эти поля у `implementer`, `verifier`, `standards-reviewer`, `spec-reviewer`, `reviser` и `scout`. Пустые определения можно удалить. Проверь пользовательский и текущий проектный конфиг, включая `opencode.jsonc`. Сохрани остальные поля.
