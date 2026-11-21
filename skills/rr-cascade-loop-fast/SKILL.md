---
name: rr-cascade-loop-fast
description: Последовательно реализовать готовые задачи, исправляя findings в следующем Implement.
disable-model-invocation: true
---

# RR Cascade Loop Fast

Оставайся primary-controller. Сначала прочитай [общий протокол](../rr-loop/references/protocol.md): роли, запуск без остановок, ledger и handoff обязательны. Его файлы фаз [review](../rr-loop/references/review.md) и [verify](../rr-loop/references/verify.md) читай при входе в фазу. Ниже — отличия каскада; перенос critical в следующий Implement заменяет немедленный Revise только для промежуточных задач.

## План и запуск

1. `RR init` по протоколу: одна текущая ветка, BASE = HEAD до правок, один финальный merge; окружение до reconciliation не меняется. Ledger: `.scratch/rr-cascade-loop-fast/<branch>/`. Recovery сохраняет план, состояния задач, counters, fixed points и текущую фазу; необъяснимый Git drift → HUMAN_ATTENTION.
2. Прочитай spec и готовые tickets: criteria, test seams, тело/комментарии/подзадачи/связи tracker по `docs/agents/issue-tracker.md`; локальные Blocked by/Status. Все завершены → отчёт без workers. Нет готовой нарезки → [rr-loop](../rr-loop/SKILL.md), без самостоятельного создания tickets.
3. Планируй незавершённые задачи по зависимостям/порядку spec, затем ID/path. Внешние задачи в план не добавляй. Циклы, неизвестные статусы/связи, конфликт источников, непроверяемый blocker, непроверяемые criteria или отсутствие test seams для кода → HUMAN_ATTENTION. План с известными failures targeted checks до будущей задачи несовместим с каскадом.
4. Одним `RR set` сохрани план: порядок и `tasks.<ID>.{deps,state: PENDING}`. Покажи plan/dependencies и работай без ожидания подтверждения; изменение состава/требований/порядка по ходу решает человек. Затем условный Exploration по протоколу.

Состояния `tasks.<ID>.state`: PENDING → ACTIVE → AWAITING_REVIEW → REVIEWED. REVIEWED означает coverage, не GREEN/tracker completion. Дополнительно в state: current_task, `tasks.<ID>.{base,deferred}`, deferred_code_count.

## Следующая задача → Implement

Проверь внешние blockers: незавершённый/непроверяемый → HUMAN_ATTENTION. Внутренние зависимости выполнены по ledger с разрешённым переносом findings, без ожидания tracker completion. Одним `RR set` примени directives и запиши current_task, `tasks.<ID>.base` = HEAD, ACTIVE, `counters.critical_iterations=0`, `counters.minor_iterations=0`; при recovery их не сбрасывай. Выполни tracker activation.

Следующее действие — fresh implementer с spec_refs задачи/общих контрактов и carried criteria, `{base_sha: tasks.<ID>.base, head_sha: HEAD}`, findings_path/IDs и context refs. Обязательны все OPEN BLOCKER/MAJOR и MINOR, подлежащие FIX_NOW по протоколу. Будущие задачи вне scope.

Прими handoff через `RR handoff --role implementer`; dispositions carried IDs даёт следующий review. Затем Review либо допустимое отложение.

## Review или deferred

Собственный review задачи можно отложить:

- Только неисполняемый текст → AWAITING_REVIEW/deferred.
- Малая кодовая задача → AWAITING_REVIEW/deferred:batch: весь diff <100 строк и <10 файлов; нет public API/schema/контрактов/migrations/test-architecture; handoff без blocker; задача не последняя; отложено <3 кодовых задач после последнего review. Docs-задачи счётчик не сбрасывают.
- Carried IDs, active critical, RED repair, reconciliation или явная user_directive запрещают отложение. Пороги меняются только явным решением человека.

Отложена не последняя → следующая задача; последняя docs-only → Done для покрывающего review, без повторного отложения. Иначе Review по общему протоколу: refs/Standards всех непокрытых задач каждой оси. После coverage/dispositions без critical покрытые задачи REVIEWED; иначе AWAITING_REVIEW.

Reviewer последней задачи — Spec full-spec всей spec, включая ранее завершённые задачи. Если review deferred, full-spec выполняется в Done. Последующие Spec delta проверяют влияние на общее покрытие, при неясности full-spec.

После review промежуточной задачи все OPEN critical и FIX_NOW переходят в следующий Implement; `stop` в ответе CLI → HUMAN_ATTENTION. После последней задачи — Triage по всему каскаду по протоколу: critical автоматически в отдельный ticket не откладывай. Новый repair commit всегда проходит delta Review → Triage, без deferred и без возврата к выполненным tickets.

## Done

Покрой deferred задачи Review; при отсутствии полного spec coverage — full-spec. Новые findings → Triage. Только все REVIEWED, актуальные full-spec + delta/Standards и отсутствие OPEN findings допускают один Verify всего плана, затем merge и завершение по [verify](../rr-loop/references/verify.md); tracker completion — для задач и spec. Выполненное review/GREEN не повторяй.
