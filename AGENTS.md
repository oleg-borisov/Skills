# AGENTS.md

Репозиторий содержит переиспользуемые agent assets для Claude Code, OpenCode, ZCode, Codex, Qoder, Devin, Antigravity и Mistral Vibe.

## Структура

| Каталог | Назначение |
| --- | --- |
| skills/spec-delivery/ | Primary skill для одной спецификации и графа задач. `references/` содержит протокол и фазы, `references/roles/` — контракты исполнителей, `scripts/rr.py` — CLI ledger. |
| skills/setup-agents/ | Установка именованных профилей ролей. `scripts/render.py` готовит файлы во временном каталоге `.tmp/`. |
| skills/tdd/, skills/wait-what-ru/ | Локальный TDD skill и вспомогательный user-invoked skill. |
| tests/ | unittest для `rr.py` и `render.py`. |
| docs/adr/, docs/validation/ | Решения и прогоны контрактов. Установка и её проверка — в [docs/hosts.md](docs/hosts.md). |

Порядок controller workflow задаёт `skills/spec-delivery/SKILL.md`. В `references/` файл `protocol.md` (роли, ledger, handoff) обязателен для primary-controller. `review.md` и `verify.md` читаются при входе в фазу, `graph.md`, `recovery.md` и `completion.md` — по условию. Leaf-agents работают по своим контрактам и читают controller protocol только как объект задачи на сами workflow assets. Термины — в `GLOSSARY.md`.

При запросе на подключение навыков прочитай [docs/hosts.md](docs/hosts.md). Для именованных профилей используй `setup-agents`.

## Зависимости

- Leaf-agents используют системные skills только по явным ссылкам в своих контрактах, например /tdd.
- Все workflow ожидают `docs/agents/issue-tracker.md` в продуктовом репозитории, когда нужны tracker operations.
- Controller вызывает `rr.py`: нужен Python 3.9+, только стандартная библиотека.
- Пять ролей обязательны, scout опционален. Для запуска используй именованный профиль роли, если он доступен, иначе универсального субагента. Когда хост не может запустить исполнителя обязательной роли или отсутствует Python 3.9+, workflow останавливается с BLOCKED_UNSUPPORTED_HOST. Недоступность scout даёт NOT_APPLICABLE Exploration.

## После правок

- `skills/spec-delivery/scripts/rr.py` или `skills/setup-agents/scripts/render.py` → `python -m unittest discover -s tests`. Renderer использует только стандартную библиотеку Python 3.9+.
- Новый user-invoked skill (`disable-model-invocation: true`) → добавь `agents/openai.yaml` с `policy.allow_implicit_invocation: false`: Codex первое поле не читает.
- Изменение поведения workflow фиксируй ADR в `docs/adr/`, если оно трудно обратимо и неочевидно.
