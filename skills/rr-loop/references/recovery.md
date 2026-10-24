# Recovery rr-parallel-loop

Читай только при resume/неизвестном исходе/сбое worker/передаче dirty worktree. Общий snapshot ledger описан в [протоколе](protocol.md).

1. Существующий нетерминальный ledger/claim → resume либо явный reset; без решения не удаляй и не dispatch дубликат. Reset не разрешает потерю незакоммиченного кода. Ownership claim передавай по OS-lock/owner/version правилам SKILL.md.
2. Прочитай актуальный state и нужные refs; сверяй identity, sources, BASE/integration ancestry, branch/cwd/HEAD задач, liveness, PR/tracker state и pending intents. Изменение требований/graph требует согласования, необъяснимый drift → HUMAN_ATTENTION. Notes сверяет worker. Старый ledger восстанавливай по его фактическим полям без повторения подтверждённых действий; миграцию истории не строй.
3. Живой worker → наблюдай, не создавай второго writer. Неизвестная liveness → HUMAN_ATTENTION. Завершённый worker без checkpoint → сверь final handoff/branch HEAD и восстанови переход. Продолжай фазу/counters/fixed points/pending_action, не новый Implement.
4. Merge intent без result: точный source_sha уже ancestor integration tip и tip объясняется этим merge → восстанови INTEGRATED/inclusion evidence. Собственный зависший merge без живого writer прерви и продолжи conflict path. Необъяснимые parents/tip → HUMAN_ATTENTION. Внешний intent без result сверяй с сервисом; неизвестный исход не повторяй. Успешные результаты сохраняются до completion.
5. Перед новым writer докажи выход предыдущего worker/subprocesses. Dirty передача fresh worker: сохрани HEAD, inventory путей и hashes staged/unstaged/untracked, включая удаления, без чтения patch controller'ом. Проверь происхождение, запиши owner/snapshot ref в directives; worker сверяет snapshot до правок. Неизвестное происхождение/расхождение → HUMAN_ATTENTION. Для continuation того же owner без иных writers новый snapshot не нужен. Dirty integration/Review/Verify запрещены.
6. При HUMAN_ATTENTION/BLOCKED/ожидании прекрати dispatch/merges; дай workers закончить локальные ветки, собери результаты. Если выход не подтверждён, сохрани IDs/liveness и запрет нового writer. STOP немедленно прерывает workers доступным механизмом, сохраняет dirty/ledger; невозможность остановить укажи явно. STOP не удаляет worktrees/ledger автоматически.

## Техническая попытка

Capacity/transport failure с подтверждённым выходом, прежними требованиями и единственным известным owner → продолжи ту же попытку без нового разрешения. Предпочитай того же агента; иначе fresh той же named role с dirty передачей выше. Модель/роль не меняй. Неизвестный исход tool/check сначала сверяй.

Готовый commit/неполный JSON → восстанови только handoff по имеющемуся evidence; повторная реализация/успешные checks на тех же входах не нужны. Отсутствующее evidence не выдумывай. До двух автоматических continuations на task/phase, включая восстановление отчёта; текущий retry counter сохраняй в task, не dispatch history. Затем HUMAN_ATTENTION. Product RED/review counters независимы.

BLOCKED из-за refs/вызова checks можно продолжить после доказанного устранения причины на прежних входах; передай исправленный вызов/refs и сохранённые результаты. Неизвестная среда/liveness, чужие изменения или требования вне scope → HUMAN_ATTENTION. Восстановление handoff не заменяет gate/review.
