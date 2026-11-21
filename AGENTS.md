# AGENTS.md

Репозиторий содержит переиспользуемые agent assets для Claude Code, OpenCode, ZCode, Codex, Qoder, Devin и Antigravity.

## Структура

| Каталог | Назначение |
| --- | --- |
| agents/ | Канонические Markdown-контракты leaf-agents: implementer, verifier, standards-reviewer, spec-reviewer, reviser, опциональный scout. |
| skills/rr-loop/ | Primary skill с controller workflow; `references/` — общий протокол и файлы фаз всех трёх rr skills, `scripts/rr.py` — CLI ledger. |
| skills/rr-cascade-loop-fast/, skills/rr-parallel-loop/ | Каскад и параллельный граф задач; используют протокол и CLI rr-loop. |
| skills/tdd/, skills/wait-what-ru/ | Локальный TDD skill и вспомогательный user-invoked skill. |
| command/ | Slash-command adapters трёх rr skills для Claude Code и OpenCode. |
| .codex/, .zcode/, .qoder/, .devin/ agents | Генерируемые профили leaf-agents. Вручную не редактировать. |
| tests/ | unittest для `rr.py`. |
| docs/adr/, docs/validation/ | Решения и прогоны контрактов; [docs/hosts.md](docs/hosts.md) — генерация профилей, установка на hosts и её проверка. |

Порядок controller workflow задаёт SKILL.md каждого rr skill. Общие контракты — в `skills/rr-loop/references/`: `protocol.md` (роли, ledger, handoff) обязателен для primary-controller, `review.md` и `verify.md` читаются при входе в фазу, `recovery.md` и `completion.md` — по условию. Leaf-agents работают по своим контрактам; controller protocol читают только как объект задачи на сами workflow assets. Отдельных custom controller-agents нет. Термины — в `GLOSSARY.md`.

## Зависимости

- Leaf-agents используют системные skills только по явным ссылкам в своих контрактах, например /tdd.
- Все workflow ожидают `docs/agents/issue-tracker.md` в продуктовом репозитории, когда нужны tracker operations.
- Controller вызывает `rr.py`: нужен Python 3.9+, только стандартная библиотека.
- Пять named leaf-agents обязательны; без роли, механизма subagents или Python workflow останавливается с BLOCKED_UNSUPPORTED_HOST. Недоступность scout даёт NOT_APPLICABLE Exploration.

## После правок

- `agents/*.md` → перегенерируй профили: `.\sync-codex-agents.ps1`, `.\sync-zcode-agents.ps1`, `.\sync-qoder-agents.ps1`, `.\sync-devin-agents.ps1`. Канонические agents и Markdown-профили не задают `model`; модели Codex — в `$profiles` генератора.
- `skills/rr-loop/scripts/rr.py` → `python -m unittest discover -s tests`.
- Новый user-invoked skill (`disable-model-invocation: true`) → добавь `agents/openai.yaml` с `policy.allow_implicit_invocation: false`: Codex первое поле не читает.
- Установка на hosts — `link-*` скрипты по [docs/hosts.md](docs/hosts.md); skills подключены ссылками, профили agents копируются.
- Изменение поведения workflow фиксируй ADR в `docs/adr/`, если оно трудно обратимо и неочевидно.
