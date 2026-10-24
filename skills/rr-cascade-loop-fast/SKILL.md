---
name: rr-cascade-loop-fast
description: Последовательно реализовать готовые задачи, исправляя findings в следующем Implement.
disable-model-invocation: true
---

# RR Cascade Loop Fast

Оставайся primary-controller. Сначала прочитай [общий протокол](../rr-loop/references/protocol.md): роли, ledger, handoff, Review/Triage, Verify и cleanup обязательны. Ниже — отличия каскада; перенос critical в следующий Implement заменяет немедленный Revise только для промежуточных задач.

## План и запуск

1. Проверь нетерминальный ledger до ранних выходов. Recovery сохраняет план, task states/BASE, counters, fixed points и текущую фазу. Изменение состава/требований/порядка требует нового согласования; необъяснимый Git drift → HUMAN_ATTENTION.
2. Прочитай spec и готовые tickets: criteria, тело/комментарии/подзадачи/связи tracker по `docs/agents/issue-tracker.md`; локальные Blocked by/Status. Все завершены → отчёт без workers. Нет готовой нарезки → [rr-loop](../rr-loop/SKILL.md), без cascade ledger и самостоятельного создания tickets.
3. Одна текущая ветка, BASE = HEAD до правок, один финальный merge; окружение до reconciliation не меняется. Ledger: `.scratch/rr-cascade-loop-fast/<branch>/`. Дополнительно к общему state: plan/dependencies, current_task, task BASE/state/deferred marker, deferred_code_count.
4. Планируй незавершённые задачи по зависимостям/порядку spec, затем ID/path. Внешние задачи в план не добавляй. Циклы, неизвестные статусы/связи, конфликт источников, непроверяемый blocker или непроверяемые criteria → HUMAN_ATTENTION. План с известными failures targeted checks до будущей задачи несовместим с каскадом.
5. Покажи plan/dependencies; нужны подтверждение запуска и test seams, если их требует TDD. Уже данное явное согласование не повторяй. До него — WAITING_FOR_HUMAN/pending_action, без tracker activation/workers. Затем RUNNING и условный Exploration по протоколу.

Task states: PENDING → ACTIVE → AWAITING_REVIEW → REVIEWED. REVIEWED означает coverage, не gate GREEN/tracker completion.

## Следующая задача → Implement

Проверь внешние blockers: незавершённый/непроверяемый → HUMAN_ATTENTION. Внутренние зависимости выполнены по ledger с разрешённым переносом findings, без ожидания tracker completion. Примени directives, current_task, task BASE = HEAD, ACTIVE, task review counter = 0; при recovery их не сбрасывай. Выполни tracker activation.

Следующее действие — fresh implementer с spec_refs задачи/общих контрактов и carried criteria, `{base_sha: task BASE, head_sha: HEAD}`, findings_path/IDs и context refs. Обязательны все OPEN BLOCKER/MAJOR и согласованные FIX_NOW; дешёвые MINOR — по протоколу. Будущие задачи вне scope; controller product code до dispatch не исследует.

Прими новый head, успешные targeted checks, rejected и affected_review_axes; сверь Git metadata. Нет нового commit → HUMAN_ATTENTION, кроме технически незавершённой попытки. Worker acceptance не закрывает findings. Затем Review либо допустимое отложение.

## Review или deferred

Собственный review задачи можно отложить:

- Только неисполняемый текст → AWAITING_REVIEW/deferred.
- Малая кодовая задача → AWAITING_REVIEW/deferred:batch: весь diff <100 строк и <10 файлов; нет public API/schema/контрактов/migrations/test-architecture; targeted checks успешны; задача не последняя; отложено <3 кодовых задач после последнего review. Docs-задачи счётчик не сбрасывают.
- Carried IDs, active critical, RED repair, reconciliation или явная user_directive запрещают отложение. Пороги меняются только явным решением человека.

Отложена не последняя → следующая задача; последняя docs-only → Done для покрывающего review, без повторного отложения. Иначе Review по общему протоколу: refs/Standards всех непокрытых задач каждой оси. После coverage/dispositions без critical покрытые задачи REVIEWED; иначе AWAITING_REVIEW.

Reviewer последней задачи — Spec full-spec всей spec, включая ранее завершённые задачи. Если review deferred, full-spec выполняется в Done. Сохраняй full_spec_reviewed_head; последующие Spec delta проверяют влияние на общее покрытие, при неясности full-spec.

После review промежуточной задачи все OPEN critical и FIX_NOW переходят в следующий Implement. Тот же critical без прогресса два review → HUMAN_ATTENTION. После последней задачи — Triage по всему каскаду: critical автоматически в отдельный ticket не откладывай; Revise/решения человека/лимиты по протоколу. Новый repair commit всегда проходит delta Review → Triage, без deferred и без возврата к выполненным tickets.

## Done → Verify → Merge

1. Покрой deferred задачи Review; при отсутствии полного spec coverage — full-spec. Новые findings/решения → Triage. Только все REVIEWED, актуальные full-spec + delta/Standards и отсутствие OPEN/pending допускают один финальный Verify всего плана по протоколу. Выполненное review/GREEN не повторяй.
2. После применимого GREEN/NOT_APPLICABLE установи QUALITY = GREEN. Зафиксируй merge_target_branch, отличную от task-ветки. Получи явную авторизацию merge, tracker completion/publication задач/spec и удаления созданного task-worktree; уже данную не повторяй.
3. Rebase на актуальный parent tip; конфликт/ошибка → HUMAN_ATTENTION без retry loop. Новый HEAD → необходимый delta Review → Triage → Verify с проверкой reuse, сохраняя утверждённый target. Затем fast-forward в parent по repo workflow; push task-ветки не означает merge.
4. После успешного merge — согласованные tracker/completion actions, cleanup task-worktree и краткий итог. Успешные внешние действия при recovery не повторяй. Ошибка сохраняет checkpoint. COMPLETED → удаление всего каталога запуска по протоколу без архивации.
