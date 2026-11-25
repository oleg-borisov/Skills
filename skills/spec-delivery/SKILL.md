---
name: spec-delivery
description: Реализовать одну спецификацию или граф задач, пройти общее ревью, финальную проверку и merge.
disable-model-invocation: true
---

# Spec Delivery

Оставайся primary-controller. Сначала прочитай [протокол](references/protocol.md). При resume прочитай [recovery](references/recovery.md) и продолжи сохранённый режим и фазу. Для незавершённой реализации графа прочитай [реализацию графа](references/graph.md).

## Запуск

1. `RR init` по протоколу в текущем checkout с `mode=planning`: BASE = HEAD до правок. Ledger в исходном checkout, `.scratch/spec-delivery/<run>/`; run — имя рабочей ветки запуска по repo conventions/task ID с заменой `/` на `-`. Для одной спеки используй текущую task-ветку либо имя планируемой task-ветки; для явно заданного графа — имя планируемой integration-ветки. Сохраняй путь при выборе режима.
2. Прочитай spec и явно связанные задачи по tracker protocol. Нужны проверяемые acceptance criteria и для кода — согласованные test seams; для docs достаточно наблюдаемой документальной цели. Неясные требования, связи или blockers → HUMAN_ATTENTION. Явно заданный граф либо готовая нарезка в spec/трекере → сохрани `mode=graph` и прочитай [реализацию графа](references/graph.md). Спека без нарезки → сохрани `mode=single` и выполни шаг ниже. Новые записи в трекере из спеки не создавай.
3. Одна спека считается одной задачей. Работай в текущем checkout: если текущая ветка не task-ветка, создай task-ветку по repo conventions/task ID, прежняя ветка — цель merge. Для текущей task-ветки цель возьми из аргументов либо уточни по протоколу. Сохрани ветку и цель merge в ledger, окружение сохраняй до reconciliation. Выполни условный Exploration и tracker activation. Следующее действие — fresh implementer с spec_refs и `{base_sha: BASE, head_sha: BASE}`. Прими его handoff через `RR handoff`.

## Implement → Review → Triage

После handoff одиночной задачи либо интеграции всех задач графа дождись выхода writers. Зафиксируй HEAD и прочитай [review](references/review.md). Проведи общее ревью результата: Spec по всей spec (для графа включая ранее завершённые задачи, `--full-spec`), Standards по правилам запуска. Сохраняй HEAD и входы неподвижными во время review и gate. После repair с новым commit — delta Review и Triage. При unchanged HEAD не повторяй checks/review; неразрешённый вопрос передай человеку.

## Done

Coverage обеих осей актуально и OPEN findings нет → для графа одним `RR set` отметь все выполненные задачи REVIEWED. Прочитай [verify](references/verify.md) и проверь весь результат. RED repair графа выполняется в integration с refs затронутой области и без возврата к планировщику. После GREEN: одна спека → merge по verify; граф → прочитай [завершение графа](references/completion.md).
