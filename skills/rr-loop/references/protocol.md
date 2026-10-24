# Общий протокол rr workflows

Обязателен для primary-controller всех трёх rr skills. Порядок задач/интеграции — в вызывающем SKILL.md.

## Роли и контекст

Workers — прямые дети primary. Обязательны implementer, verifier, spec-reviewer, standards-reviewer, reviser; scout опционален. Нет named role/subagents → BLOCKED_UNSUPPORTED_HOST, без подмены роли. Controller читает spec/Git metadata/handoffs; product code/checks/formatter — workers. Primary уже изменил product code вместо worker → HUMAN_ATTENTION.

Используй установленного агента нужной роли. Явно указанная человеком модель имеет приоритет над моделью профиля; при её смене сохраняй полный контракт роли, ограничения и Output. Если host не поддерживает override модели установленного профиля, controller передаёт полный текст установленного leaf-контракта fresh subagent запрошенной модели. Это адаптация только для явно выбранной модели, а не замена отсутствующего агента. Имя задачи, пересказ роли и ссылка на controller skill/protocol полный контракт не заменяют.

Новая задача/фаза — fresh worker заданной роли без истории controller. Передавай только входы роли, refs и delta directives. Общие входы `{base_sha,head_sha}`; optional changed_files_path — один manifest на диапазон. Без него worker получает paths через Git. Spec refs `{path,sections,criterion_ids,source_sha?|hash?}`: source_sha закрепляет файл в Git tree, hash сырых байтов — изменяемый/внешний источник; tracker spec фиксируй snapshot. Product files/PNG отдельно не хешируй. Standards находит implementer, включая вложенные инструкции; переиспользуй refs, дополняй для нового scope. Неизвестные standards не означают отсутствие правил.

Workers получают контракт роли и входы задачи; spec_refs содержат требования задачи и общие контракты продукта. Controller SKILL.md, protocol/recovery/completion остаются у controller и не передаются worker для исполнения. Если задача меняет или проверяет сами workflow assets, передавай нужные файлы/секции как объект задачи.

Handoff — один JSON роли; controller сохраняет его один раз, state содержит ref/поля перехода. Новый файл сначала запиши отдельно, атомарно переключи state, затем удаляй ненужный прежний: crash не должен менять evidence старого checkpoint. Пересказы spec/diff, progress, пустые optional поля, копии файлов и полные логи в контекст не передавай. Читай только изменившийся результат/нужные поля state. Жди события завершения host без busy polling; timeout не доказывает сбой. Успешные checks на прежних входах не повторяй.

Exploration: один scout только для общих нескольким workers questions; локальные вопросы — implementer. Вход `{spec_refs,head_sha,questions,notes_dir}`, notes_dir под LEDGER_DIR. Нет questions/scout/доступа → NOT_APPLICABLE с причиной. Handoff — refs notes, sources сверяет worker.

Tracker: API/статусы только из `docs/agents/issue-tracker.md`. До первого worker задачи активируй In Progress/аналог; уже активное не повторяй. Нет ID/интеграции/transition или ошибка activation → NOT_APPLICABLE с причиной; tickets/blockers всё равно проверяй.

## Snapshot ledger

Только controller атомарно заменяет LEDGER_DIR/state.json через temporary file того же каталога. Handoffs/refs/manifests/notes/inventory и управляемые логи — под LEDGER_DIR, штатные build outputs — на своих местах. Каталог принадлежит одному запуску; workers получают абсолютные пути.

Храни только актуальное состояние:

- workflow/task, cwd/branch, BASE/HEAD, source/standards refs, merge target. HEAD актуален; прошлые SHA — только у своего evidence.
- WORKFLOW_STATUS/QUALITY/current_phase, pending_action, действующие согласования/constraints, неприменённые directives. Применённые указания удаляй, сохраняй лишь продолжающие действовать constraints.
- Текущие workers/ownership, pending operations, нужные handoff/validation refs. Внешнее действие: intent до вызова, result/ID после; успешные results сохраняй до конца для защиты от повторов. Завершённая dispatch history/interim/phase_results не нужна.
- По осям: last_reviewed_head и актуальное coverage (range/reason для NOT_APPLICABLE), full_spec_reviewed_head, текущий gate ref/verdict. last_full_green_head и отдельный green_ref сохраняют последний полный GREEN с plan/log evidence даже после RED; proof reuse связывает его с новым HEAD. Coverage сворачивай до покрытого диапазона, не истории итераций.
- Counters: consecutive_red, critical/minor repair iterations, последний progress/consecutive_no_progress каждого OPEN critical; retries конкретного workflow.
- findings: map OPEN записей по stable ID `{axis,severity,head,location,requirement_ref|standard_ref,evidence,fix}`; при необходимости worker rejection/решение. findings_path = абсолютный state.json, worker читает только заданные IDs. next_finding_id предотвращает повтор ID.
- Компактные human dispositions/linked task IDs для итога. Reviewer FIXED удаляет запись атомарно с coverage/counters. WONT_FIX удаляет только после решения человека с reason/созданным linked task ID. Worker acceptance/отсутствие повторного finding ID не закрывают.

Закрытые findings, JSONL/seq, старые inputs/interim, checks поверх handoff, product hashes, история фаз и пустые optional поля не нужны. Устаревшие файлы удаляй без чтения после checkpoint; evidence активных refs сохраняй.

До нового запуска ищи нетерминальный ledger workflow по task/spec/связанным веткам/worktrees. Предложи resume/reset; без решения не удаляй/не повторяй реализацию. Конфликт владельцев/ledger → HUMAN_ATTENTION. Recovery сверяет identity/sources/BASE/HEAD/phase/pending_action/liveness и операции; затем продолжает checkpoint. Неизвестный исход сверяй с сервисом, успешное не повторяй; commit без checkpoint — с handoff. Необъяснимый drift → HUMAN_ATTENTION. Старый формат при resume сведи к текущему snapshot OPEN/coverage/counters/refs, без повторения подтверждённых действий и архива истории.

До вопроса WAITING_FOR_HUMAN/pending_action; после ответа RUNNING и продолжение в текущем диалоге. STOP исполняй сразу; HUMAN_ATTENTION/STOP сохраняют данные и запрещают новые writers.

## Review → Triage → Revise

По оси base_sha = last_reviewed_head или BASE, scope = весь непокрытый диапазон. Spec обязателен для требований; Standards NOT_APPLICABLE лишь при доказанном отсутствии правил либо полном покрытии уже успешными automated checks нужного scope. Будущий gate/tests-only не освобождает от Standards. Для skip range/reason, fixed point не продвигай.

Две нужные оси — параллельно на одном HEAD. Spec получает spec_refs/review_mode, Standards — standards_files; repair — findings_path/IDs своей оси. initial: criteria/общие контракты; delta: findings/затронутые criteria с расширением по зависимостям; full-spec: вся spec, включая завершённые задачи.

Reviewer возвращает head/verdict и только непустые optional findings/dispositions. Неверный HEAD, NO_SPEC/BLOCKED_CONTEXT, неполный explicit FIXED|OPEN/evidence заданных IDs → HUMAN_ATTENTION без coverage. Severity controller: wrong → BLOCKER; missing/partial/hard → MAJOR; judgement → MINOR. Дубли внутри оси объединяй по stable ID; между осями сохраняй IDs/verdict отдельно. После repair нужны union(оси OPEN IDs, affected_review_axes, непокрытые обязательные оси): поведение/requirements/контракты — Spec; структура/conventions/tests/tooling — Standards; сомнение — обе. Успешное review атомарно обновляет coverage/findings/counters. Full-spec фиксирует full_spec_reviewed_head; последующие delta оценивают влияние на всё покрытие, неясность → full-spec.

- Critical BLOCKER/MAJOR → fresh reviser. Попутный дешёвый MINOR: один файл, до 20 LOC, без API/schema/test-architecture/research.
- Остальные MINOR/спорные → batch ID/axis/location/evidence/fix: FIX_NOW, linked task, REJECTED(reason). MINOR >3 файлов/>100 LOC/меняющий test architecture — только linked task/rejection. Создание task требует авторизации/tracker contract; до получения ID finding OPEN.
- Critical rejected worker'ом, конфликт spec/standards либо тот же critical без прогресса два review → HUMAN_ATTENTION. Предел: четыре critical repair-review iterations, две MINOR repair iterations; после MINOR-предела решения человека. Лимит findings не закрывает; отказ человека исправлять critical → STOPPED_BY_HUMAN.

Reviser получает IDs/inventory и refs/directives scope. Новый commit → delta Review → Triage; unchanged HEAD → решение человека без повторных checks/review. Targeted checks/formatter — worker до commit, FIXED — reviewer.

## Финальный Verify

Вход: актуальное обязательное coverage, нет OPEN/pending, весь план завершён по SKILL.md. Один полный gate итога, не каждого commit. HEAD/inputs неподвижны; dirty inputs/недостоверное evidence → HUMAN_ATTENTION.

Reuse полного GREEN: тот же HEAD/inputs либо одинаковое Git tree при прежних требованиях/условиях. Diff только пояснений/инструкций допускает reuse, если controller по имеющимся diff/plan/логам доказывает неизменность code/tests/fixtures/resources/build/config inputs, существенной среды и достаточность команд. Для этого читает только изменённый текст docs; отдельный агент/check не нужен. Новые требования/inputs/условия или нужда в исследовании → verifier. Расширение файла/чистый merge не доказательство. Сохрани исходный SHA/ref GREEN, итоговый HEAD и proof; last_full_green_head остаётся SHA прогона. Review coverage независимо.

Без применимого GREEN gate NOT_APPLICABLE лишь для всего непроверенного диапазона неисполняемого текста по worker evidence/repo config. Agent instructions, MDX, executable examples, configs/build inputs требуют gate; сомнение → verifier. Запиши range/reason, last_full_green_head не меняй.

Иначе fresh verifier: `{base_sha: last_full_green_head или BASE,head_sha: HEAD,artifacts_dir: LEDGER_DIR,validation_plan_path?}` и refs scope. Один full-suite проход по repo config. validation_plan одновременно evidence команд/results, один inventory failures, логи по refs. GREEN → last_full_green_head = HEAD, green_ref = handoff, consecutive_red = 0. RED → fresh reviser с inventory/refs scope и finding_ids: [] без review findings; targeted repair/commit → delta Review → Triage → новый gate. Repair не расходует review counter, сам review расходует; RED counter review не сбрасывает. Unchanged HEAD после repair, три RED подряд или BLOCKED без доказанно устранимой технической причины → HUMAN_ATTENTION.

## Завершение

COMPLETED только после успешного подтверждённого merge и согласованных completion actions. Сначала итог в диалог/разрешённый tracker: SHA/PR, результаты проверок, human dispositions/ограничения. Не ссылайся на удаляемые логи как доступный архив.

После COMPLETED удали LEDGER_DIR целиком одной рекурсивной операцией без нового вопроса, чтения/редактирования содержимого и архивации. Проверь resolved absolute path: каталог данного запуска строго внутри `<исходный checkout>/.scratch/<workflow>/`, не сам корень workflow/.scratch, без symlink/junction компонентов; writers нет. Windows: `Remove-Item -LiteralPath <проверенный LEDGER_DIR> -Recurse -Force`; POSIX: `rm -rf -- <проверенный LEDGER_DIR>`. Ошибка cleanup → сохрани состояние/путь, сообщи. Worktrees удаляются отдельно по авторизации; parent/default/shared сохраняется. Незавершённый/HUMAN_ATTENTION/STOP запуск не удаляй.
