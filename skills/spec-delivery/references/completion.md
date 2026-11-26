# Merge и завершение

Вход для single и graph: quality GREEN, writers нет. Цель — `merge_target`, источник — task-ветка либо integration. Зафиксируй проверенный SHA кандидата. При отказе от согласованного по умолчанию merge, tracker completion или удаления созданных worktrees — вопрос и WAITING_FOR_HUMAN/pending_action для соответствующего действия.

Вне активной merge queue сверяй актуальный tip цели с `review_target` и HEAD источника с проверенным SHA. Сдвиг цели → подготовка кандидата по [Review](review.md); для graph два последовательных сдвига во время completion → HUMAN_ATTENTION. Необъяснимый сдвиг источника → HUMAN_ATTENTION. Цель уже содержит spec/изменился graph → решение человека.

## PR / direct merge

- PR (по запросу или когда его требует repo/tracker workflow): найди существующий PR по head/base и сверь сохранённый intent/result. Push проверенного SHA в head-ветку без force; non-fast-forward → HUMAN_ATTENTION. Если PR ещё нет, создай один draft с проверенными head/base и closing refs по tracker. До ready зафиксируй expected head/base SHA и механизм запрета merge при смене любого ref: атомарная проверка обоих либо merge queue с обязательной проверкой её фактического кандидата. Одного чтения refs/проверки head недостаточно; нет механизма → draft/HUMAN_ATTENTION. После GREEN источника — ready при наличии этого механизма. Merge человеком/CI → WAITING_FOR_HUMAN с URL/refs до подтверждения. Squash/rebase допустим только по repo workflow с evidence проверенных refs и merged result SHA. Другие фактические refs → HUMAN_ATTENTION без GREEN/COMPLETED.
- Direct (если PR не нужен): fast-forward цели до проверенного SHA с атомарным сравнением ожидаемого tip либо эксклюзивной блокировкой writers. Ошибка/drift/другой target → HUMAN_ATTENTION.

### Merge queue

Храни исходные PR head и tip цели отдельно от проверяемого queue-кандидата. Когда очередь предоставит фактический head и подтверждённую базу (цель и предшествующие изменения очереди), создай и зарегистрируй отдельный worktree кандидата в том же Git-репозитории. Одним `ledger.py set` запиши `queue.source_head`, `queue.target_tip`, `candidate_cwd`, `head` и `review_target`. Выполни Review по собственному patch от базы очереди и Verify либо доказанный reuse. Checks очереди не заменяют Spec.

При возврате к completion в активной очереди сверь сохранённый PR head и фактические refs кандидата через провайдер. Очередь владеет временным кандидатом: writers туда не dispatch, SHA не пушь в PR head. Findings/RED → зафиксируй evidence, останови продвижение кандидата; применимый repair выполняй на исходной ветке после выхода из очереди, иначе HUMAN_ATTENTION. Новый кандидат → новый Review/Verify, неизвестная база → HUMAN_ATTENTION. Заверши запуск по evidence, что влит именно проверенный кандидат. При выходе из очереди восстанови сохранённые source head/target tip и очисти `candidate_cwd` и `queue` одной записью, затем подготовь кандидата из task/integration.

## Завершение

После подтверждённого merge выполни ещё не выполненные согласованные tracker transitions/publication: проверь автоматическое закрытие tickets. Внешние действия имеют текущие intent/result; успешные после recovery не повторяй. Ошибка → HUMAN_ATTENTION/checkpoint.

Удаляй только созданные этим запуском зарегистрированные worktrees по согласию, без writers/dirty, с доказанной сохранностью commits. Для squash/rebase ancestry заменяет merged PR evidence. Origin/parent/shared worktree сохраняй; ветки — только по отдельному разрешению.

После merge и всех согласованных действий — итог и COMPLETED по [verify](verify.md), для graph добавь перечень tasks. При отказе от merge работа остаётся незавершённой; явное прекращение → STOPPED_BY_HUMAN, данные сохраняются.
