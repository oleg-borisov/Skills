# Завершение графа задач

Одна спека завершается по [verify](verify.md).

Вход: quality GREEN, writers нет. Цель (parent) зафиксирована при init и отлична от integration. Согласие на final merge, tracker completion и удаление созданных worktrees дано вызовом навыка; при отказе в аргументах — вопрос, WAITING_FOR_HUMAN/pending_action. Удаление LEDGER_DIR после COMPLETED согласия и архива не требует.

## Reconciliation

1. Получи актуальный parent tip разрешённым способом; затрагиваемые checkout чистые. Сохрани текущие intent/tips. Parent прежний → существующее evidence integration HEAD.
2. Parent изменился → обычный merge parent в integration, сохраняя ticket ancestry, затем `RR set head=<sha>`. Controller выполняет только чистый Git merge. Конфликт → прерви свой merge и передай fresh implementer единоличное владение integration cwd: pinned parent SHA, вся spec/standards, conflict repair, formatter/targeted checks/commit. Две неудачные attempts/неразрешимый конфликт → HUMAN_ATTENTION.
3. Новый integration HEAD → необходимый delta Review → Triage → Verify с проверкой reuse GREEN по общему протоколу. Spec delta оценивает влияние parent на всю spec; неясность → full-spec. Parent уже содержит spec/изменился graph → решение человека, не пустая реализация.
4. Сверь parent перед merge. Сдвинулся → reconciliation; два последовательных сдвига во время completion → HUMAN_ATTENTION.

## PR / direct merge

- PR: push проверенного integration HEAD в существующую head-ветку без force. До ready зафиксируй expected head/base SHA и механизм запрета merge при смене любого ref: атомарная проверка обоих либо merge queue с проверкой фактического кандидата. Одного чтения refs/проверки head недостаточно; нет механизма → draft/HUMAN_ATTENTION. Новому кандидату нужны актуальные review coverage и gate/reuse; queue checks не заменяют Spec автоматически. После GREEN — ready. Merge человеком/CI → WAITING_FOR_HUMAN с URL/refs, без tracker completion/cleanup до подтверждения. Squash/rebase допустим только по repo workflow с evidence проверенных refs и merged result SHA. Другие фактические refs → HUMAN_ATTENTION без GREEN/COMPLETED.
- Direct: fast-forward parent до проверенного integration HEAD с атомарным сравнением expected parent tip либо эксклюзивной блокировкой writers. Ошибка/drift/другой target → HUMAN_ATTENTION. Push integration сам по себе не merge.

## Завершение

После подтверждённого merge выполни ещё не выполненные согласованные tracker transitions/publication: проверь автоматическое закрытие tickets. Внешние действия имеют текущие intent/result; успешные после recovery не повторяй. Ошибка → HUMAN_ATTENTION/checkpoint.

Удаляй только созданные этим запуском зарегистрированные worktrees по согласию, без writers/dirty, с доказанной сохранностью commits в integration/parent. Для squash/rebase ancestry заменяет merged PR evidence. Origin/parent/shared worktree сохраняй; ветки — только по отдельному разрешению.

После merge и всех согласованных действий — итог и COMPLETED по [verify](verify.md) с перечнем tasks, затем удаление всего LEDGER_DIR. При отказе от merge работа остаётся незавершённой; явное прекращение → STOPPED_BY_HUMAN, данные сохраняются.
