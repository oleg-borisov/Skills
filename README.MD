# Skills

Переиспользуемые agent assets для Claude Code, OpenCode, Codex, ZCode, Qoder, Devin и Antigravity:

- единый primary workflow `/rr-loop` или `$rr-loop`;
- leaf-agents implementer, verifier, standards-reviewer, spec-reviewer, reviser и опциональный scout;
- `skills/rr-loop/` как контракт контроллера, локальный TDD skill в `skills/tdd/`, вспомогательный `skills/wait-what-ru/` и Markdown-контракты leaf-agents для генерации профилей хостов.

`rr-loop` реализует одну спецификацию в текущем checkout. Готовые задачи графа
выполняются в отдельных worktree и собираются на integration-ветке. Параллелизм
ограничен зависимостями, областями записи и ёмкостью хоста.
[Решение об объединении](docs/adr/0009-unified-rr-loop.md).

Workers выполняют targeted checks. После реализации всего плана следует общее
ревью, разбор замечаний и финальная проверка независимым verifier. RED repair
проходит targeted checks → review → triage → повторный gate.

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
