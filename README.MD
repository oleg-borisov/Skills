# Skills

Переиспользуемые agent assets для Claude Code, OpenCode, Codex, ZCode, Qoder, Devin, Antigravity и Mistral Vibe.

- единый primary workflow `spec-delivery`;
- контракты implementer, verifier, standards-reviewer, spec-reviewer, reviser и опционального scout в `skills/spec-delivery/references/roles/`;
- `setup-agents` для установки именованных профилей, локальный `tdd` и вспомогательный `wait-what-ru`.

В Claude Code используй `/spec-delivery`, в Codex — `$spec-delivery`, в OpenCode —
`@spec-delivery`. [Claude Code](https://code.claude.com/docs/en/skills) · [OpenCode](https://opencode.ai/docs/skills)

`spec-delivery` реализует одну спецификацию в текущем checkout. Готовые задачи графа
выполняются в отдельных worktree и собираются на integration-ветке. Параллелизм
ограничен зависимостями, областями записи и ёмкостью хоста.
[Решение об объединении](docs/adr/0009-unified-rr-loop.md).

Каждый исполнитель читает контракт роли из навыка по абсолютному пути.
Контроллер использует именованный профиль, если он доступен, или универсальный
тип субагента хоста. [ADR-0010](docs/adr/0010-role-contracts-in-skill.md).

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

Чтобы подключить набор навыков, открой checkout в агенте и попроси его установить
навыки для нужного хоста. Можно назвать конкретные навыки. Агент определит активное
окружение и способ подключения по [инструкции](docs/hosts.md).
