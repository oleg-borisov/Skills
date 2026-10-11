---
name: rr-parallel-loop
description: Реализовать готовый граф задач спецификации параллельными leaf-agents в отдельных worktree, собрать integration-ветку и пройти общий verify → review → revise до merge.
---

# RR Parallel Loop

Ты — primary-controller текущего диалога. Веди граф, integration-ветку, ledger и решения человека; product code и checks выполняют общие named leaf-agents. Этот workflow использует rolling frontier: запускает разблокированные задачи, пока другие workers ещё работают. Полный gate и review по умолчанию выполняются на собранной integration-ветке, не на каждом ticket.

## Инварианты

- Все workers — прямые дети primary. Обязательны implementer, verifier, standards-reviewer, spec-reviewer, reviser; scout опционален. Новых ролей и вложенных controller-agents нет.
- Controller читает spec, tickets, Git metadata, compact handoffs и ledger. Product code/patch читает и изменяет worker; project checks/formatter запускает worker. Если primary уже изменил product code вместо implementer → HUMAN_ATTENTION.
- Один writer на worktree. Implementers работают каждый в своей ветке; только controller последовательно интегрирует завершённые ветки. Verifier/reviewers получают неподвижный integration HEAD.
- INTEGRATED означает доступность кода для зависимых задач, не GREEN, review approval или tracker completion. Локально зелёные tests и чистый Git merge не доказывают корректность интеграции.
- QUALITY = GREEN требует актуального gate, полного spec coverage, обязательного Standards coverage и отсутствия OPEN findings. Новый HEAD инвалидирует итоговую QUALITY.
- Сохраняй чужие изменения. Создавай worktree от явно зафиксированного SHA; reset существующего checkout и force-cleanup не применяй.

## Контекст и общие агенты

Запускай fresh workers без истории controller, если host позволяет. Передавай context pointers с условием чтения, не копии spec/diff/логов: `spec_refs = [{path, sections, criterion_ids, hash}]`, standards_files, relevant notes_paths, findings_path + finding_ids, failure_inventory_path, directives_path, validation_plan_path. Пути должны быть доступны из назначенного worktree; изменяемые источники pin по hash. Для refs вне ветки используй доступный неизменяемый snapshot, а не копию в каждом prompt.

Execution envelope задаётся в dispatch: абсолютный cwd, branch, ожидаемый HEAD и назначение worker. Это контекст запуска, не новые поля JSON-контракта агента. Все Git/file/check операции worker выполняет в этом cwd; если host не способен обеспечить адресацию отдельных worktree, остановись с BLOCKED_UNSUPPORTED_HOST. Не подменяй named role универсальным агентом.

Используй существующие входы/выходы ролей:

| Роль | Вход помимо execution envelope | Выход |
| --- | --- | --- |
| implementer | spec_refs, base_sha, head_sha, changed_files; доступные context refs | commit/head, changed, standards_files, findings, checks, affected_review_axes, risks |
| verifier | base_sha, head_sha, changed_files, mode: pre-review или final; validation_plan_path | verdict/head, commands, failures, validation_plan |
| spec-reviewer | base_sha, head_sha, changed_files, spec_refs, review_mode; findings refs | head, verdict, findings, dispositions |
| standards-reviewer | base_sha, head_sha, changed_files, standards_files; findings refs | head, verdict, findings, dispositions |
| reviser | base_sha, head_sha, changed_files, spec_refs, standards_files, findings refs; repair/context refs | тот же формат, что implementer |

Пустые optional refs опускай; при repair только по inventory передавай reviser `finding_ids: []` и failure_inventory_path. Standards впервые определяет implementer, затем controller объединяет refs всех задач; при новом scope worker дополняет их. Changed_files controller вычисляет один раз на диапазон по Git metadata. Полные логи остаются по log_path; controller получает JSON, пути и решения, не пересказ работы. Не опрашивай workers ради пересказов статуса: жди завершения или сообщения о препятствии.

## Ledger и recovery

LEDGER_DIR = `.scratch/rr-parallel-loop/<integration-branch>/` в исходном checkout; workers получают абсолютные пути. Только controller пишет ledger. Source snapshots, handoffs, directives и inventory хранятся отдельно от checkpoint; spec и полные логи в checkpoint не дублируй.

### Claim работы

До создания integration branch, tracker actions и dispatch атомарно захвати claim: файл `<git-common-dir>/rr-parallel-loop-claims/<key>.json`, создаваемый exclusive create (ошибка, если существует). `<git-common-dir>` получи через Git; он общий для всех worktrees. key = SHA-256 UTF-8 канонического locator spec, при отсутствии spec — primary task locator. Локальный locator — нормализованный repo-relative путь, tracker locator — канонический URL; запиши locator/aliases, workflow, owner session ID, version = 1 и абсолютный ledger path; при transfer увеличивай version. Claim действует только внутри rr-parallel-loop. Если источники имеют разные aliases, сначала разреши их к одному spec locator; неоднозначность → HUMAN_ATTENTION.

Создание claim, проверка существования и запись owner не должны быть раздельными check-then-write. Существующий или неполностью записанный claim означает занятую работу, пока recovery не доказал обратное. При resume сохрани claim и owner; передачу ownership выполняй только после доказанного завершения предыдущего controller и workers. Неизвестная liveness → HUMAN_ATTENTION; возраст файла не доказывает устаревание. Reset/release допустим после подтверждённого отсутствия writers и решения о сохранении незавершённых данных. Claim освобождай после COMPLETED либо согласованного STOP/reset без активных writers; незавершённый ledger всё равно обнаруживается preflight. Ошибка exclusive create/недоступность общего каталога → остановка, не best-effort dispatch.

Все изменения claim, включая transfer/release/reset, сериализуй эксклюзивной OS-блокировкой по тому же key. Внутри критической секции перечитай owner/version и сравни с ожидаемыми перед записью; новый owner/version означает проигранную гонку, а не разрешение повторить transfer. Проверка завершения прежнего owner не заменяет этот compare-and-set. Освободи OS-блокировку после записи; она должна сниматься при смерти процесса. Если host не предоставляет такого примитива, recovery с передачей ownership останавливается до решения человека, автоматический захват не выполняется.

### Формат checkpoint

Перед первым checkpoint используй приведённые ниже структуры parallel ledger. Правила переходов заданы в этом skill.

- `null` означает отсутствие значения/evidence, `[]` — отсутствие записей.
  Заполни известные refs, SHA и абсолютные cwd; незаполненные обязательные данные
  блокируют соответствующее действие. Образец в `tasks` размножь по графу;
  `dependencies` содержит task IDs, `dependency_shas` — их интегрированные SHA.
  `graph` хранит связи и prerequisite evidence уже завершённых/внешних задач.
- `operations` — записи `{key, kind, task_id, intent, result}`; `kind` — dispatch,
  merge, tracker, PR или cleanup. Intent содержит точные входы операции; result
  остаётся null до наблюдаемого исхода. Историю операций сохраняй для recovery.
- `gate` и review `coverage` хранят HEAD/range, verdict/reason и evidence refs;
  counters сохраняют последовательные RED, review/repair iterations и retries.
  `open_findings` содержит `{id, seq}` последних OPEN records.
- Новый `findings.jsonl` создай пустым. Шаблон — форма одного события, а не готовое
  finding: заполни ID/refs/axis/severity/location/evidence/fix при обнаружении.
  `seq` строго возрастает; ID сохраняется во всех событиях одного finding.
  Изменение state/disposition добавляет строку, существующие строки сохраняются.
- Сначала сохрани handoff/finding events, затем атомарно замени state.json через
  временный файл того же каталога. До dispatch, merge, PR/transition/cleanup
  запиши intent с ключом операции; после действия — наблюдаемый result.
  Переход состояния фиксируй только по evidence.

#### state.json

```json
{
  "workflow": "rr-parallel-loop",
  "spec_refs": [],
  "primary_task": null,
  "BASE": null,
  "origin": { "cwd": null, "branch": null, "head": null },
  "integration": { "cwd": null, "branch": null, "head": null },
  "parent_target": { "branch": null, "head": null },
  "claim": { "path": null, "locator": null, "aliases": [], "owner_session_id": null, "version": null },
  "sources": [],
  "graph": [],
  "max_workers": 1,
  "tasks": [
    {
      "id": null,
      "spec_refs": [],
      "dependencies": [],
      "prerequisite_evidence": [],
      "write_scopes": [],
      "state": "PENDING",
      "task_base": null,
      "dependency_shas": {},
      "worktree": null,
      "branch": null,
      "head": null,
      "ownership": null,
      "worker_ids": [],
      "worker_liveness": null,
      "dirty_snapshot_ref": null,
      "handoff_refs": [],
      "standards_files": [],
      "inclusion_evidence": null,
      "repair_attempts": 0
    }
  ],
  "WORKFLOW_STATUS": "RUNNING",
  "QUALITY": "RED",
  "current_phase": "Preflight",
  "pending_action": null,
  "user_directives": [],
  "operations": [],
  "last_full_green_head": null,
  "gate": null,
  "last_reviewed_head": { "spec": null, "standards": null },
  "full_spec_reviewed_head": null,
  "coverage": { "spec": [], "standards": [] },
  "counters": {
    "consecutive_red": 0,
    "critical_repair_review_iterations": 0,
    "minor_repair_iterations": 0,
    "critical_no_progress": {},
    "parent_drift_retries": 0
  },
  "open_findings": [],
  "findings_seq": 0,
  "handoff_refs": [],
  "standards_files": [],
  "validation_plan_path": null,
  "failure_inventory_path": null,
  "directives_path": null,
  "notes": { "dir": null, "metadata_ref": null, "source_head": null, "relevant_paths": [], "paths": [] },
  "pr": null,
  "tracker_results": [],
  "merge_result": null,
  "cleanup_results": []
}
```

#### findings.jsonl

Одна строка на событие:

```jsonl
{"seq":1,"id":null,"task_refs":[],"axis":null,"severity":null,"head":null,"location":null,"evidence":null,"fix":null,"state":"OPEN","disposition":null}
```

### Возобновление

1. Для существующего нетерминального ledger предложи resume или явный reset. Без решения не удаляй данные и не запускай реализацию повторно. Сканируй ledgers rr-parallel-loop по task/spec и связанным branch/worktrees и его claim directory. Два активных владельца одной работы в этом workflow → HUMAN_ATTENTION. Reset не означает разрешение удалить незакоммиченный код.
2. Прочитай state.json, актуальные OPEN records и хвост после findings_seq. Старую историю читай только при расхождении. Неполная запись не доказывает действие.
3. Сверь spec/standards hashes, BASE, integration ancestry, task branches/cwd, реальный HEAD, worker liveness, PR/transition state и pending intents. Устаревшие notes переиспользуй только после сверки sources worker'ом. Изменение graph/requirements требует согласования нового плана, необъяснимый Git drift → HUMAN_ATTENTION.
4. RUNNING + живой worker → снова наблюдай его, не dispatch дубликата. Неизвестная liveness → HUMAN_ATTENTION. Завершившийся worker без checkpoint → восстанови результат по final handoff и branch HEAD. Если worker умер с dirty files/без handoff, сохрани worktree и запроси решение; не reset и не объявляй READY.
5. Merge intent без result: если точный source_sha уже ancestor integration tip и изменение tip объясняется этим merge, восстанови INTEGRATED, не merge повторно. Если merge ещё в процессе, при отсутствии живого writer прерви только собственную подтверждённую операцию и продолжи conflict path. Необъяснимые parents/другой tip → HUMAN_ATTENTION.
6. Внешнее действие без result сначала сверяй с tracker/PR/host. Неизвестный исход → HUMAN_ATTENTION, не слепой повтор. Успешные действия не повторяй. Gate/review evidence относится только к сохранённому HEAD и входам; после переписывания истории сбрось coverage и считай BASE для нового review от актуального parent tip, сохранив origin BASE отдельно.
7. Продолжай сохранённую фазу/counters/fixed points и pending_action после ответа, не возвращайся в Implement автоматически. Перед повторным dispatch докажи выход предыдущего writer. Обычно назначенный checkout должен быть чистым. Исключение — согласованное продолжение сохранённой незавершённой попытки: сохрани HEAD, inventory путей и hashes staged/unstaged/untracked содержимого без чтения product patch controller'ом, сверь отсутствие посторонних изменений и зафиксируй передачу ownership этих правок fresh implementer в directives_path. Перед первым изменением worker проверяет этот snapshot; расхождение → HUMAN_ATTENTION. При неизвестном происхождении dirty требуется решение человека. Это разрешает продолжить scope-expansion после согласования, но не разрешает dirty integration/Verify/Review.

### Остановка и указания человека

Указания во время работы сохраняй в user_directives, применяй перед dispatch/merge и помечай consumed. При scope/graph change останови новые dispatch/merges, дождись текущих workers, сохрани их результаты отдельно и перепланируй; ранее начатые результаты не включай автоматически в изменённую spec.

При HUMAN_ATTENTION/BLOCKED/ожидании решения прекрати новые dispatch/merges; текущим workers дай закончить локальные ветки, собери handoffs и затем зафиксируй checkpoint без активных writers. Если это невозможно, сохрани worker IDs/liveness и запрет повторного writer. При явном STOP немедленно прерви workers доступным механизмом и сохрани dirty состояние; невозможность остановить отрази явно. STOPPED_BY_HUMAN не удаляет worktrees/ledger автоматически. Нетерминальные ledger и notes сохраняются до recovery.

## 0. Preflight и план

1. До dispatch проверь нетерминальные ledgers `rr-parallel-loop` для этой spec/task/веток. Используй раздел «Ledger и recovery» выше. Другой активный controller этого workflow на той же работе → HUMAN_ATTENTION. Не удаляй ledger и не запускай дубликат.
2. Прочитай spec и готовые tickets с criteria, статусами, комментариями и зависимостями; tracker — только по `docs/agents/issue-tracker.md`. Нет готового графа → предложи rr-loop, не создавай tickets и не запускай его автоматически. Все tickets завершены → отчёт без workers. Неопределённые criteria, циклы, неизвестные связи/статусы, конфликт источников или непроверяемый внешний blocker → HUMAN_ATTENTION.
3. Сохрани исходный checkout, branch, BASE = HEAD и parent target. Зафиксируй незавершённые задачи и prerequisite evidence для уже завершённых: их код должен присутствовать в BASE или быть явно подтверждён источниками; одного tracker-статуса недостаточно. Для графа используй только существующие зависимости, не придумывай продуктовые решения.
4. Определи `max_workers` по доступным host slots и ресурсам checks. Сохрани write_scope каждой задачи из tickets/standards/notes. Пересекающиеся или неизвестные scopes запускай последовательно; это scheduling lock, не новая зависимость spec. Общие схемы/API, generated outputs и внешние test resources тоже требуют согласованной изоляции или сериализации. Если независимость нельзя установить по источникам, начни с одного worker.
5. Покажи план, зависимости, scopes, max_workers, integration/parent branches и режим `final gate + final review`. До запуска нужны подтверждённый план и согласованные test seams, если TDD их требует; уже данное явное согласование не спрашивай повторно. Сохрани WAITING_FOR_HUMAN/pending_action перед вопросом. Изменение требований или графа требует нового согласования.
6. После согласования создай отдельный integration worktree/ветку от BASE. Имена следуют repo conventions и primary task ID; используй свободные имена, не переиспользуй чужую ветку. Проверь named roles, worktree addressing и доступность refs. Нехватка обязательной capability → BLOCKED_UNSUPPORTED_HOST с checkpoint.

Exploration: один fresh scout только для конкретных вопросов, общих нескольким workers. Вход `{spec_refs, head_sha: BASE, questions, notes_dir}`; notes_dir вне repo, доступен workers. Сохрани metadata/source_head/relevant_paths, выдавай только нужные notes_paths. При отсутствии общих вопросов/scout/доступного notes_dir → NOT_APPLICABLE; локальные вопросы решает implementer.

## 1. Schedule → Implement → Integrate

Task states: `PENDING → RUNNING → READY_TO_INTEGRATE → INTEGRATED → REVIEWED`. ACTIVE в tracker не заменяет task state. Неполный/blocked handoff не продвигает задачу.

Frontier = PENDING задачи, у которых внутренние predecessors INTEGRATED/REVIEWED, внешние blockers подтверждённо завершены, write_scope не конфликтует с RUNNING/READY_TO_INTEGRATE. Среди доступных предпочитай разблокирующие больше зависимых задач, затем ID/path; не задерживай готовую задачу ради ещё работающего независимого worker.

Повторяй до интеграции всех задач:

1. Применяй сохранённые user_directives и проверь внешние blockers перед dispatch. Для ready ticket создай новый worktree/ветку от текущего integration HEAD, сохрани `task_base` и dependency SHAs. Если места заняты, жди завершения любого worker, без busy polling.
2. До первого worker активируй tracker task документированным transition; уже активный статус повторно не меняй. Отсутствие ID/интеграции или ошибка transition → NOT_APPLICABLE с причиной; это не разрешает пропускать получение tickets/blockers. Сохрани intent/result для recovery.
3. Сохрани dispatch intent, затем запусти fresh implementer: `{spec_refs: критерии ticket и общие контракты, base_sha: task_base, head_sha: task_base, changed_files: []}` и context refs. В directives_path задай write_scope и протокол расширения: до выхода за scope worker завершает текущую попытку финальным JSON с `risks` о требуемых путях/причине и фактическим commit/head/checks; незавершённый scope не коммитит, dirty сохраняет. Он не остаётся ждать ответа как RUNNING writer. Controller сначала решает scope, затем dispatch fresh worker после подтверждённого выхода предыдущего. Worker сохраняет чужие изменения, выполняет TDD где применимо, formatter и targeted checks, коммитит свой scope. Других workers и merge в integration он не запускает.
4. Прими финальный JSON. Сверь assigned branch/cwd, reported head с реальным tip, ancestry task_base, отсутствие незакоммиченных проверяемых входов, changed_files со scope и evidence targeted checks. HEAD/null commit, неожиданная ветка/правки или блокировка → останови новые dispatch, сохрани результаты и HUMAN_ATTENTION; пустой commit и повторную реализацию вслепую не делай. При запросе расширения scope останови dispatch, дождись writers и согласуй conflicts/dependencies; до решения не интегрируй результат с неподтверждённым scope.
5. READY_TO_INTEGRATE включай в integration последовательно. Перед merge проверь чистоту integration checkout, сохранённый target tip и точный source SHA. Сохрани intent `{task, source_sha, integration_before}`, выполни обычный merge без squash/rebase; после успеха запиши integration_after, inclusion evidence, INTEGRATED и освободи scope. Коммит worker должен оставаться предком integration HEAD.
6. После каждой интеграции немедленно пересчитай frontier и заполни свободные slots. Другим workers не рассылай новый tip: их база зафиксирована, синхронизация нужна только при конфликте. Никакого full-suite/review на каждый ticket по умолчанию.

Если frontier пуст, workers отсутствуют, а PENDING остались → HUMAN_ATTENTION с невыполненными prerequisites, не успешное завершение. При сообщении о продуктовой ошибке/нарушенном контракте останови новые dispatch и перейди к безопасной остановке из recovery; известную поломку не распространяй на новые задачи.

### Конфликт интеграции

Controller не разрешает product conflicts. Прерви только собственный начатый merge, восстановив чистый integration tip. Заморозь дальнейшие merges; другие workers могут закончить свои ветки. Fresh implementer в завершённом task worktree получает текущие spec_refs, task_base, task HEAD, changed_files и directives_path: merge фиксированного integration tip в task-ветку, разрешение конфликта в рамках spec, formatter, targeted checks и commit. Передай refs требований других задач, затронутых конфликтом. Это repair, не новая роль merger.

После handoff проверь наличие обоих родителей в ancestry и повтори интеграцию. После двух неудачных repair attempts одного ticket или при конфликте требований → HUMAN_ATTENTION. Лимит не разрешает потерю changes или автоматический выбор одной стороны. Во время заморозки новые задачи не запускай; после успешной интеграции продолжи Schedule.

### Черновик PR

После первой успешной интеграции создай один draft PR для integration-ветки, если пользователь запросил PR или tracker закрывает работу через PR. Сверь существующий PR, согласованные base/head и repo workflow; publication/push выполняй в пределах авторизации, иначе сохрани pending_action. Ссылки closing для spec/tickets добавляй только по правилам tracker. Draft не закрывает задачи; PR остаётся draft до Done. URL и результат сохраняй, при recovery повторно PR не создавай. На host с механизмом прикрепления PR прикрепи созданный PR к текущему диалогу.

## 2. Freeze → Verify

После INTEGRATED всех задач дождись выхода всех writers и зафиксируй integration HEAD. В этом checkout во время Verify/Review нет merge, formatter или другого writer. Если parent не изменялся, задача сборки integration завершена; теперь проверяется объединённый результат.

При `HEAD == last_full_green_head` и неизменных проверяемых входах используй сохранённый GREEN. Dirty inputs, неизвестный scope/evidence → HUMAN_ATTENTION. Иначе fresh verifier получает `{base_sha: last_full_green_head или BASE, head_sha: HEAD, changed_files, mode: pre-review, validation_plan_path}`. Он определяет обязательные full-suite commands по repo configuration и возвращает один inventory; controller сохраняет plan и log refs.

Docs-only gate = NOT_APPLICABLE допустим только для всего непроверенного диапазона неисполняемого текста по worker evidence/repo configuration. Agent instructions, MDX, executable examples, configs/build inputs требуют обычного gate; сомнение → verifier. Для NOT_APPLICABLE сохраняй range/reason, last_full_green_head не обновляй.

GREEN → сохрани HEAD/evidence, сбрось RED counter, Review. RED → один fresh implementer до первого review, иначе reviser; он исправляет общий failure inventory в integration worktree и делает targeted checks/commit. Новый commit → Verify; BLOCKED, unchanged HEAD или три последовательных RED → HUMAN_ATTENTION. Repair не увеличивает review counter и не помечает findings FIXED.

## 3. Review → Revise

Первый review собранной integration: Spec в режиме full-spec со всеми criteria, включая ранее завершённые задачи; Standards по объединённым standards_files. Нужные оси запускай параллельно на одном HEAD. Для каждой оси base_sha = last_reviewed_head этой оси или BASE. Spec обязателен; Standards = NOT_APPLICABLE только при доказанном отсутствии применимых документированных правил либо полном покрытии правилами успешных automated checks. Сохраняй range/reason; неизвестные standards не считай отсутствующими.

Принимай JSON named reviewers; неверный HEAD, NO_SPEC/BLOCKED_CONTEXT, неполные dispositions → HUMAN_ATTENTION без продвижения coverage. Назначай stable finding IDs и severity: wrong → BLOCKER; missing/partial/hard → MAJOR; judgement → MINOR. Сохраняй evidence обеих осей, не своди их в общий verdict. На каждую выполненную ось сохрани last_reviewed_head, на полный Spec — full_spec_reviewed_head.

Finding states: OPEN, FIXED только по explicit reviewer disposition, WONT_FIX только по решению человека с reason/linked task. ACCEPTED от worker и отсутствие finding в новом отчёте оставляют ID OPEN. Дубликаты объединяй с сохранением IDs и истории. Critical = BLOCKER/MAJOR; автоматический WONT_FIX запрещён.

- Есть critical → fresh reviser со всеми обязательными finding_ids, spec/standards refs и scope. Дешёвый MINOR можно включить: один файл, до 20 LOC, без API/schema/test-architecture/research. Остальные MINOR требуют решения человека.
- Нет critical, остались MINOR/спорные → одним batch спроси FIX_NOW, linked task или REJECTED(reason), приведя ID/axis/location/evidence/fix. MINOR >3 файлов, >100 LOC или меняющий test architecture — только linked task/rejection. Создавай linked task лишь по авторизации и документированному tracker workflow; до получения ID finding OPEN.
- Critical REJECTED агентом, противоречие spec/standards или тот же critical без прогресса два review подряд → HUMAN_ATTENTION. Четыре critical repair-review iterations либо две MINOR repair iterations — предел автоматического цикла; findings не закрывай по лимиту. После MINOR-предела предложи linked task/rejection. Явный отказ человека исправлять critical → STOPPED_BY_HUMAN, не COMPLETED.

После нового commit reviser: Verify → delta Review → triage. Проверяй union(originating axes OPEN IDs, affected_review_axes нового diff, ещё непокрытых обязательных осей); при сомнении обе. Delta Spec читает затронутые criteria и влияние на общее покрытие; при неясности повтори full-spec. Даже при пустом delta reviewer обязан дать dispositions переданных IDs. Unchanged HEAD → решения человека, без повторных checks/review.

## 4. Done

Все задачи интегрированы, актуальны gate/full-spec + последующие delta/Standards coverage, нет OPEN findings и pending decisions → задачи REVIEWED, QUALITY = GREEN. Выполненные gate/review на том же HEAD повторно не запускай. REVIEWED ещё не tracker completion.

Перед публикацией результата, финальным merge и cleanup прочитай [references/completion.md](references/completion.md). Выполни подтверждённый repo workflow: PR либо direct merge, с проверками при изменении HEAD. COMPLETED допустим только после подтверждённого merge и всех согласованных completion actions. До этого сохраняй ledger, branch/worktrees и draft как незавершённую работу.
