# Recovery spec-delivery

Integration и task worktrees относятся к режиму graph. Читай при resume/неизвестном исходе/сбое worker/смене владельца незакоммиченных правок. Общий snapshot ledger описан в [протоколе](protocol.md).

1. Существующий запуск (отказ `ledger.py init`) → resume либо явный reset по решению человека; без решения не удаляй и не dispatch дубликат. Reset не разрешает потерю незакоммиченного кода.
   При resume используй сохранённый путь и `mode`; planning → продолжи выбор режима после init. Для старого ledger без mode: `workflow=rr-loop` → single, `workflow=rr-parallel-loop` → graph. Незавершённый каскад продолжай с навыком и протоколом из ревизии `c47fd72` репозитория Skills.
2. Прочитай актуальный state нужными `ledger.py get`; сверяй identity, sources, BASE/integration ancestry, branch/cwd/HEAD задач, liveness, PR/tracker state и pending intents. Изменение требований/graph решает человек, необъяснимый drift → HUMAN_ATTENTION. Notes сверяет worker.
3. Живой worker → наблюдай, не создавай второго writer. Неизвестная liveness → HUMAN_ATTENTION. Завершённый worker без checkpoint → передай его финальный JSON CLI. Если старый handoff уже применён и записан без cwd/scope, сверь сохранённый JSON, HEAD и исходный scope по plan/directives и Git; при подтверждении продолжай с имеющегося checkpoint, иначе HUMAN_ATTENTION. Продолжай фазу/counters/fixed points/pending_action.
4. При resume старого graph проверь последние handoffs задач READY_TO_INTEGRATE. Если handoff содержит blocker, верни задачу в RUNNING. Если на неё уже записан `integrating`, остановись с HUMAN_ATTENTION и сверь фактическое состояние до повторной попытки.
   Остальной `integrating` без результата → повтори `ledger.py integrate --task <ID>`: CLI восстановит INTEGRATED либо прервёт зависший merge; отказ → HUMAN_ATTENTION. Внешний intent без result сверяй с сервисом; неизвестный исход не повторяй. Успешные результаты сохраняются до completion.
   `candidate_intent` → сверь состояние Git и происхождение HEAD с записанными before/target: подтверждённый результат зафиксируй как кандидата по [Review](review.md); незавершённая операция/неизвестный исход → HUMAN_ATTENTION. Старый ledger без `review_target` до подтверждённого merge → сначала подготовь кандидата и заново установи coverage обеих осей.
   Старый GREEN до подтверждённого merge требует `ledger.py gate --reuse` с применимым сохранённым evidence. При ошибке reuse → Verify на актуальном кандидате. При активной merge queue сверь checkout и refs кандидата отдельно от PR head по [completion](completion.md).
5. Перед новым writer докажи выход предыдущего worker/subprocesses. Смена владельца: fresh worker той же роли получает HEAD и directive, что незакоммиченные правки в cwd — наследство прежнего исполнителя этой задачи. Происхождение правок неизвестно → HUMAN_ATTENTION. Dirty integration/Review/Verify запрещены.
6. При HUMAN_ATTENTION/BLOCKED/ожидании прекрати dispatch/merges; дай workers закончить локальные ветки, собери результаты. Если выход не подтверждён, сохрани IDs/liveness и запрет нового writer. STOP немедленно прерывает workers доступным механизмом, сохраняет dirty/ledger; невозможность остановить укажи явно. STOP не удаляет worktrees/ledger автоматически.

## Техническая попытка

Capacity/transport failure с подтверждённым выходом, прежними требованиями и единственным известным owner → продолжи ту же попытку без нового разрешения. Предпочитай того же агента, иначе запусти fresh worker той же роли по протоколу со сменой владельца выше. Неизвестный исход tool/check сначала сверяй.

Готовый commit/неполный JSON → восстанови только handoff по имеющемуся evidence; повторная реализация/успешные checks на тех же входах не нужны. Отсутствующее evidence не выдумывай. До двух автоматических continuations на task/phase, включая восстановление отчёта; текущий retry counter сохраняй в task, не dispatch history. Затем HUMAN_ATTENTION. Product RED/review counters независимы.

BLOCKED из-за refs/вызова checks можно продолжить после доказанного устранения причины на прежних входах; передай исправленный вызов/refs и сохранённые результаты. Неизвестная среда/liveness, чужие изменения или требования вне scope → HUMAN_ATTENTION. Восстановление handoff не заменяет gate/review.
