# Рекомендации по моделям

Снимок на 2026-11-26. `render.py` читает таблицу как источник умолчаний для новой установки. ID моделей Codex перенесены из прежних профилей. Claude Code использует алиасы семейств, Qoder и Antigravity используют алиасы хоста. `inherit` оставляет выбор хосту. Для OpenCode и Vibe конкретный ID или алиас зависит от настроенного провайдера.

| Хост | strong | cheap |
| --- | --- | --- |
| codex | `gpt-6.2-sol` | `gpt-6-luna` |
| claude | `sonnet` | `haiku` |
| qoder | `performance` | `efficient` |
| antigravity | `pro` | `flash` |
| devin | `inherit` | `inherit` |
| opencode | `inherit` | `inherit` |
| vibe | `inherit` | `inherit` |
| zcode | `inherit` | `inherit` |

Обновляя таблицу, проверь ID и доступность на целевом хосте. Reasoning effort берётся из метаданных роли для Codex, Claude Code и ZCode. В ZCode это поле действует при закреплённой модели. Vibe использует настройки `thinking` выбранного алиаса из конфигурации моделей.
