# Skills

Переиспользуемые agent assets для Claude Code, OpenCode и Codex:

- primary workflows /rr-loop, $rr-loop, /rr-cascade-loop-fast, $rr-cascade-loop-fast и /rr-parallel-loop, $rr-parallel-loop;
- leaf-agents implementer, verifier, standards-reviewer, spec-reviewer, reviser;
- skills rr-loop, rr-cascade-loop-fast и rr-parallel-loop как source of truth своих controllers, локальный TDD skill в `skills/tdd/` и Markdown leaf-agents как source of truth для генерируемых Codex TOML profiles.

`rr-parallel-loop` запускает готовые задачи графа в отдельных worktree и собирает
integration-ветку с draft PR, когда этого требует tracker или пользователь.
Review выполняется на объединённом результате. Он использует те же leaf-agents,
что последовательные workflows. Логические сценарии: [прогон контракта](docs/validation/rr-parallel-loop.md).

Во всех трёх workflows workers выполняют targeted checks; после review,
исправлений и решений человека независимый verifier выполняет полный финальный
gate. В rr-loop это итог задачи, в cascade/parallel — всего плана. RED repair
проходит targeted checks → review → triage → повторный полный gate. Cascade
сохраняет промежуточные и покрывающие review. Решение: [ADR-0005](docs/adr/0005-final-gate-after-review.md).

Синхронизация локальных окружений:

    .\link-codex.ps1

На macOS для OpenCode и `~/.agents`:

    ./link-opencode.sh

Формат, зависимости и целевые каталоги описаны в AGENTS.md.
