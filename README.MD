# Skills

Переиспользуемые agent assets для Claude Code, OpenCode, Codex, ZCode, Qoder, Devin и Antigravity:

- primary workflows /rr-loop, $rr-loop, /rr-cascade-loop-fast, $rr-cascade-loop-fast и /rr-parallel-loop, $rr-parallel-loop;
- leaf-agents implementer, verifier, standards-reviewer, spec-reviewer, reviser и опциональный scout;
- skills rr-loop, rr-cascade-loop-fast и rr-parallel-loop как source of truth своих controllers, локальный TDD skill в `skills/tdd/`, вспомогательный `skills/wait-what-ru/` и Markdown leaf-agents как source of truth для генерируемых профилей хостов.

`rr-parallel-loop` запускает готовые задачи графа в отдельных worktree и собирает
integration-ветку с draft PR, когда этого требует tracker или пользователь.
Review выполняется на объединённом результате. Он использует те же leaf-agents,
что последовательные workflows. Логические сценарии: [прогон контракта](docs/validation/rr-parallel-loop.md).

Во всех трёх workflows workers выполняют targeted checks; после review,
исправлений и разбора замечаний независимый verifier выполняет gate — финальную
проверку. В rr-loop это итог задачи, в cascade/parallel — всего плана. RED repair
проходит targeted checks → review → triage → повторный gate. Cascade
сохраняет промежуточные и покрывающие review. Решение: [ADR-0005](docs/adr/0005-final-gate-after-review.md).

Workers до handoff выполняют быстрый ярус проверок repo, повторное Spec review
ограничено diff исправления, замечания к неисполняемой документации идут одним
batch: [ADR-0006](docs/adr/0006-fast-tier-and-bounded-review.md).

На обычном пути запуск не останавливается на человеке: вызов навыка — согласие
на merge при quality GREEN, план показывается без подтверждения:
[ADR-0007](docs/adr/0007-run-without-human-stops.md). Механику ledger, handoff,
gate и интеграции выполняет `rr.py`; сверка хешей, снимок правок и захват
запуска убраны: [ADR-0008](docs/adr/0008-no-hash-snapshot-claim.md). Цена
запуска до и после: [эталонные сценарии](docs/validation/run-cost.md).

Синхронизация локальных окружений:

    .\link-codex.ps1

На macOS для OpenCode, ZCode, Devin и `~/.agents`:

    ./link-opencode.sh

Qoder и Antigravity:

    .\link-qoder.ps1
    .\link-gemini.ps1

Формат и зависимости описаны в AGENTS.md, генерация профилей и целевые каталоги hosts — в [docs/hosts.md](docs/hosts.md).
