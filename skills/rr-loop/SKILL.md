---
name: rr-loop
description: Запустить implement → review → revise → gate → merge в текущем primary-контексте.
disable-model-invocation: true
---

# RR Loop

Оставайся primary-controller. Сначала прочитай [общий протокол](references/protocol.md): роли, запуск без остановок, ledger и handoff обязательны для этого workflow. Его файлы фаз [review](references/review.md) и [verify](references/verify.md) читай при входе в фазу.

## Запуск

1. `RR init` по протоколу: текущий checkout, BASE = HEAD до правок. Текущая ветка не task-ветка → создай task-ветку по repo conventions/task ID, прежняя ветка — цель merge. Окружение сохраняется до reconciliation. Ledger: `.scratch/rr-loop/<branch>/`. Recovery продолжает сохранённую фазу, не новый Implement.
2. Прочитай spec: нужны проверяемые acceptance criteria и для кода — согласованные test seams; для docs достаточно наблюдаемой документальной цели. Неопределённость → HUMAN_ATTENTION с вопросами.
3. Выполни условный Exploration и tracker activation по протоколу. Следующее действие — fresh implementer с spec_refs и `{base_sha: BASE, head_sha: HEAD}`.

## Implement → Review → Triage

Прими handoff implementer через `RR handoff`, затем Review/Triage по протоколу. После каждого repair с новым commit — delta Review; gate только после разрешения findings. При unchanged HEAD не повторяй checks/review; неразрешённый вопрос передай человеку.

## Done

Coverage обеих осей актуально и OPEN findings нет → Verify, merge и завершение по [verify](references/verify.md); иначе Review/Triage.
