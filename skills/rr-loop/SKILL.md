---
name: rr-loop
description: Запустить implement → review → revise → final gate в текущем primary-контексте.
disable-model-invocation: true
---

# RR Loop

Оставайся primary-controller. Сначала прочитай [общий протокол](references/protocol.md): роли, компактный ledger, Review/Triage, Verify и cleanup обязательны для этого workflow.

## Запуск

1. Проверь существующий ledger по протоколу. Recovery продолжает сохранённую фазу, не новый Implement.
2. Прочитай spec: нужны проверяемые acceptance criteria; для docs достаточно наблюдаемой документальной цели. Неопределённость → HUMAN_ATTENTION.
3. Новый запуск: текущий checkout, BASE = HEAD до правок, RUNNING/RED; имена веток по repo conventions/task ID. Окружение сохраняется до reconciliation. Ledger: `.scratch/rr-loop/<branch>/`.
4. Выполни условный Exploration и tracker activation по протоколу. Следующее действие — fresh implementer с spec_refs и `{base_sha: BASE, head_sha: HEAD}`. Controller до dispatch product code не исследует. Если primary уже изменил product code вместо worker → HUMAN_ATTENTION.

## Implement → Review → Triage

Прими handoff implementer: новый head, успешные финальные targeted checks, standards refs и affected_review_axes. Сверь Git metadata; отсутствие нового commit без технически незавершённой попытки → HUMAN_ATTENTION.

Выполни Review/Triage по протоколу. После каждого repair с новым commit — delta Review; полный gate только после разрешения findings и решений человека. При unchanged HEAD не повторяй checks/review; неразрешённый вопрос передай человеку.

## Done → Verify → Merge

1. Проверь актуальное обязательное review coverage и отсутствие OPEN findings/pending decisions. Недостаток → Review/Triage; иначе финальный Verify по протоколу. Только применимый GREEN или обоснованный gate NOT_APPLICABLE даёт QUALITY = GREEN.
2. Зафиксируй merge_target_branch, отличную от task-ветки. Получи явную авторизацию merge и tracker completion/publication, а также удаления созданного task-worktree. Уже данную авторизацию не спрашивай повторно. До ответа — WAITING_FOR_HUMAN/pending_action.
3. Выполни rebase на актуальный parent tip. Конфликт/ошибка → HUMAN_ATTENTION без автоматического retry. Новый HEAD → необходимый delta Review → Triage → Verify с проверкой reuse GREEN. Сохраняй утверждённый target.
4. После QUALITY = GREEN выполни fast-forward в подтверждённую parent-ветку по repo workflow. Push task-ветки не означает merge; ошибка → HUMAN_ATTENTION.
5. Только после успешного merge выполни согласованные tracker/completion actions и cleanup созданного task-worktree. Успешные внешние действия не повторяй после recovery. Ошибка оставляет checkpoint.
6. Сформируй краткий итог: результат, финальный SHA, проверки, человеческие решения/linked tasks и ограничения. COMPLETED → cleanup всего каталога запуска по протоколу; архив evidence не нужен.
