---
name: rr-cascade-loop-fast
description: Последовательно реализовать задачи спецификации, исправляя замечания review в Implement следующей задачи.
disable-model-invocation: true
---

# RR Cascade Loop Fast

Ты — primary-controller текущего диалога. Веди state machine, ledger, interaction with user и transitions между фазами. Product code и checks выполняют leaf-agents.

## Инварианты

- Все leaf-agents — прямые дети primary; leaf-agent не запускает другого агента.
- Controller не читает весь product code, не редактирует его и не запускает project checks. Ему достаточно spec, git metadata, compact handoffs и ledger.
- Цикл начинается в текущем checkout; рабочее окружение не меняется до merge reconciliation.
- Каждый worker получает только spec paths, fixed points, finding IDs и свой phase contract. Не вставляй в prompt полную историю цикла.
- Worker, который меняет код, коммитит свою фазу. Controller проверяет новый HEAD.
- Review начинается только после green verifier gate. Reviewers не запускают checks.
- QUALITY = GREEN: активных BLOCKER/MAJOR нет, final gate green, initial и обязательные delta-review завершены.
- Итоговый отчёт разрешён после успешного final merge; cleanup ledger — только при terminal status.

## Leaf-agents

- implementer — реализует spec, делает targeted checks, коммитит.
- verifier — read-only gate; возвращает один failure inventory.
- standards-reviewer — проверяет documented standards и smell baseline.
- spec-reviewer — проверяет соответствие spec.
- reviser — исправляет заданные finding IDs, делает targeted checks, коммитит.

Все пять named leaf-agents являются обязательной capability host. Если хотя бы одна требуемая роль или механизм subagents недоступны, установи WORKFLOW_STATUS = BLOCKED_UNSUPPORTED_HOST, перечисли отсутствующие capabilities, сохрани ledger и остановись.

## Ledger

LEDGER = .scratch/rr-cascade-loop-fast/<branch>.md. Храни:

- spec paths, specification ID, branch, BASE, HEAD, merge_target_branch, parent_worktree и последний интегрированный commit parent-ветки;
- подтверждённый plan: название, sources с versions/hashes, task IDs/paths, acceptance criteria, dependencies, порядок, внешние blockers и результат проверки, timestamp подтверждения;
- current_task, task BASE/HEAD, task state, review iteration и phase_results по задачам, carried finding IDs; общий BASE и last_reviewed_head при смене задачи сохраняются;
- tracker activation: исходный и целевой статус, применённый transition, timestamp и результат;
- current_phase, WORKFLOW_STATUS, QUALITY;
- last_reviewed_head по каждой оси, last_full_green_head;
- queued user_directives;
- phase_results: phase, worker, input fixed point, output commit, checks/verdict, timestamp;
- findings: stable ID, originating task, axis, severity, location, evidence, proposed fix, state, human decision; при объединении MINOR сохраняй исходные IDs и историю;
- pending human action и completion decision.

Finding states: PENDING, FIX_NOW, AWAITING_REVIEW, FIXED, DEFERRED_TO_TASK(<ID>), REJECTED(<reason>), HUMAN_ATTENTION. AWAITING_REVIEW означает заявленное worker исправление; FIXED ставится только после подтверждения reviewer. Task states: PENDING, ACTIVE, AWAITING_REVIEW, REVIEWED; это не tracker completion.

Делай atomic checkpoint после фазы, worker commit, human decision и перед паузой. Не переписывай ledger после каждого finding. Ledger не коммитится.

## Запуск и recovery

1. Определи branch и проверь нетерминальный ledger любого из rr-loop, rr-cascade-loop-fast для входной spec/task/branch до любых ранних выходов. Предложи продолжить его или явно сбросить; без решения не удаляй файл и не повторяй реализацию. При recovery сохрани BASE из ledger, сверь plan/sources, branch, HEAD, phase_results и pending_action; подтверждённые фазы не повторяй, незаписанный worker commit сначала сверяй с handoff. Изменение состава, требований или порядка требует подтверждения нового плана; необъяснимое расхождение Git-state → HUMAN_ATTENTION. Продолжай сохранённый workflow/фазу, шаги нового запуска ниже не повторяй.
2. Прочитай вход: spec и/или каталог готовых tickets; для tracker — тело, комментарии, подзадачи и связи по `docs/agents/issue-tracker.md`. Найди исходную spec и acceptance criteria. Если все существующие подзадачи завершены — сообщи, что задач нет, и закончи без workers. Без готовой нарезки прочитай установленный `rr-loop/SKILL.md` и продолжай его обычный workflow в primary, без cascade ledger; самостоятельно `to-tickets` не запускай.
3. Зафиксируй BASE = git rev-parse HEAD до правок. Каскад работает в одной текущей ветке с одним финальным merge.
4. Составь plan из незавершённых готовых локальных tickets или подзадач tracker-spec. Для локальных tickets читай `Blocked by`, `Status`, acceptance criteria; порядок файлов — лишь tie-break. Объедини зависимости и порядок spec; независимые задачи упорядочь по spec, затем ID/path. Циклы, конфликт источников, неизвестные статусы/связи/spec → HUMAN_ATTENTION. Внешние задачи в plan автоматически не добавляй.
5. Проверь внешние blockers первой задачи; незавершённый или непроверяемый blocker останавливает запуск. План, явно допускающий red между задачами, также несовместим: green pre-review gate обязателен после каждой задачи.
6. Покажи название spec, список задач и порядок с зависимостями. Сохрани plan и pending_action подтверждения запуска в ledger с WORKFLOW_STATUS = WAITING_FOR_HUMAN, QUALITY = RED; до подтверждения workers и tracker activation не выполняй.
7. После подтверждения установи RUNNING и выполни Task activation. В текущем диалоге продолжай сразу после ответа; resume <ledger> нужен только для recovery в новом контексте.

### Task activation

Перед каждой следующей задачей проверь внешние blockers; blocker или невозможность проверки → HUMAN_ATTENTION. Внутреннюю зависимость считай удовлетворённой по пройденному шагу ledger, включая допустимый перенос findings, без ожидания закрытия тикета. Применяй queued user_directives, установи current_task, task BASE = HEAD, state = ACTIVE, review iteration = 0; перенеси незакрытые findings и выполни Tracker activation для текущего task ID. Checkpoint перед первым worker; затем Implement. При recovery продолжай сохранённую фазу, счётчики и fixed points не сбрасывай.

### Tracker activation

Для исполняемой задачи с `task ID` прочитай `docs/agents/issue-tracker.md` и используй только описанный там способ получения workflow и перехода. Найди статус, означающий начало активной работы: `In Progress` либо его документированный аналог. Если задача уже находится в таком статусе, переход не повторяй; зафиксируй это в ledger.

Иначе переведи задачу этим transition в найденный статус до первого worker. Запиши в ledger исходный/целевой статусы, transition, timestamp и результат. Не подставляй названия статусов, API или команды из памяти. Если документа нет, workflow/status недоступен, активный статус не определён или transition не проходит, запиши tracker activation как `NOT_APPLICABLE` с причиной и продолжай workflow. При отсутствии `task ID` также запиши tracker activation как `NOT_APPLICABLE` и продолжай workflow. Это послабление касается только смены статуса, не получения задач и проверки blockers.

## State machine

### 1. Implement

Запусти fresh implementer со spec paths, acceptance criteria текущей задачи, task BASE и scope: текущая задача плюс неустранённые carried BLOCKER/MAJOR и human FIX_NOW, с IDs. Остальные findings передай для контекста; eligible cheap MINOR разрешены попутно по правилам Decide, будущие задачи вне scope. Потребуй per-finding disposition дополнительно к commit SHA, changed files, targeted checks и risks; заявленные исправления отметь AWAITING_REVIEW. Проверь, что HEAD совпадает с отчётом.

Completion: worker commit существует, scope и checks записаны в ledger.

### 2. Pre-review gate

Если `HEAD != last_full_green_head`, запусти fresh verifier в режиме pre-review с одним relevant full suite. Targeted checks уже выполнил implementer.

При green запиши `last_full_green_head = HEAD`. При `HEAD == last_full_green_head` gate уже закрыт.

При red gate передай единый failure inventory fresh implementer до первого review текущей задачи или reviser после review. Repair не увеличивает review iteration. При repair commit вернись к этому gate; при unchanged HEAD → HUMAN_ATTENTION. Одинаковый red gate без прогресса два раза → HUMAN_ATTENTION.

Completion: verifier вернул green с exact commands/results.

### 3. Review

Первый Review каждой задачи: параллельно fresh standards-reviewer и fresh spec-reviewer; fixed point каждой оси — её last_reviewed_head, для первого шага — общий BASE. Передай текущий scope, требования реализованной части spec и carried findings, включая ожидающие подтверждения исправлений и MINOR. Будущие требования не считай missing. На последней задаче spec-reviewer дополнительно сверяет покрытие всей spec, включая ранее завершённые задачи.

Повторная итерация внутри той же задачи:

- fixed point — last_reviewed_head соответствующей оси;
- запускай только оси, породившие активные findings;
- если active findings есть в обеих осях, запусти обе параллельно.

Нормализуй отчёты в stable IDs и severity:

- BLOCKER: security/data loss, broken mandatory contract, build/test impossibility, mandatory spec requirement missing;
- MAJOR: logic error, important edge case, material spec deviation, material performance/design defect;
- MINOR: local maintainability, naming, comments, cosmetic or deferred improvement.

Потребуй evidence и disposition по каждому carried ID: FIXED либо остаётся открытым; отсутствие повторного finding не означает исправление. Сохраняй axis и evidence. Не мерджи две оси в один verdict. Объединяй дубликаты MINOR с сохранением IDs и истории. Completion: findings запущенных осей и dispositions записаны, last_reviewed_head обновлён; задачи с завершённым обязательным review без active critical findings отмечены REVIEWED.

Переход:

- Если текущая задача не последняя: тот же critical finding без прогресса в двух последовательных review сквозь задачи → HUMAN_ATTENTION; явный отказ человека исправлять critical → STOPPED_BY_HUMAN; неразрешённое противоречие → HUMAN_ATTENTION. Иначе перенеси незакрытые findings, оставь текущую задачу с active critical findings в AWAITING_REVIEW, сделай checkpoint и выполни Task activation следующей задачи. Следующий worker — fresh implementer.
- Если текущая задача последняя: установи current_phase = Decide и перейди к §4.

### 4. Decide — только для последней задачи

Входное условие: current_task — последняя задача plan. Если условие не выполнено, допустимый переход определяет §3 Review: Task activation следующей задачи с fresh implementer.

- Нет active BLOCKER/MAJOR → обработай MINOR/human items.
- Есть active critical findings → Revise.
- Тот же critical finding без прогресса в двух последовательных review или четыре critical review iterations текущей задачи → HUMAN_ATTENTION.

MINOR можно исправить попутно только если в той же Implement/Revise-фазе исправляется BLOCKER/MAJOR и MINOR однозначно дешёвый: один файл, до 20 LOC, без public API/schema/test-architecture/research. Иначе нужно решение человека. MINOR больше трёх файлов, 100 LOC или меняющий test architecture нельзя брать FIX_NOW: только linked task или rejection.

### 5. Revise

Запусти fresh reviser с critical findings, указаниями человека и eligible cheap MINOR. Прими commit SHA либо подтверждение unchanged HEAD, per-finding disposition и targeted checks. Отклонённый BLOCKER всегда переводи в HUMAN_ATTENTION.

При новом commit запусти delta Review только по originating axes. При unchanged HEAD не запускай checks или review.

### 6. Human decisions

Задай все готовые вопросы одним batch по актуальным findings всего каскада. Для каждого finding покажи ID, severity, axis, location, evidence и proposed fix.

Варианты: FIX_NOW, создать linked task, REJECTED(<reason>). Для critical finding также прими correction/instruction. Явный отказ исправлять critical finding → STOPPED_BY_HUMAN, не COMPLETED.

Перед вопросом установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши pending_action и сделай checkpoint. После ответа запиши решения, очисти pending_action и верни WORKFLOW_STATUS = RUNNING, кроме terminal refusal.

Новые указания человека во время активного worker добавляй в user_directives; worker не прерывай. Примени directives перед следующим переходом фазы и отметь их consumed.

### 7. Execute minor decisions

- Создай согласованные linked tasks по docs/agents/issue-tracker.md и запиши IDs/URLs.
- Запиши human rejection с причиной.
- Для FIX_NOW запусти fresh reviser. При новом commit выполни только originating review axis; при unchanged HEAD не запускай checks или review. Максимум две review iterations; critical finding после лимита возвращает workflow в Human decisions.

### 8. Final gate and completion

1. Если `HEAD != last_full_green_head`, запусти fresh verifier в final с одним relevant full suite; при green запиши `last_full_green_head = HEAD`.
2. Если gate red, передай inventory fresh reviser. Для repair commit запиши affected_review_axes: Spec для изменения observable behavior, contracts или requirements; Standards для изменения структуры или conventions; пустой список допустим только для tests/build tooling, не меняющих product code. При неясной классификации запускай обе оси.
3. После repair commit выполни delta-review только по affected_review_axes и повтори этот gate. При unchanged HEAD → HUMAN_ATTENTION. Одинаковый red gate без прогресса два раза → HUMAN_ATTENTION.
4. При green gate не запускай review: каждый commit после initial Review уже прошёл обязательный delta-review или совмещённый Review следующей задачи, а verifier не меняет HEAD.
5. Проверь ledger всего каскада: все задачи реализованы и проверены; нет PENDING, FIX_NOW, AWAITING_REVIEW, HUMAN_ATTENTION и active critical findings. Все carried findings получили review disposition.
6. Установи QUALITY = GREEN.
7. Установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши completion decision как pending_action, сделай checkpoint и спроси, выполнять ли merge в явно названную parent-ветку, tracker completion и cleanup task-worktree, если он был создан для этой задачи. Сохрани `merge_target_branch` в ledger. Без явного подтверждения не выполняй эти действия.
8. После подтверждения выполни фазу Merge reconciliation.
9. Только после успешного fast-forward merge сформируй итоговый отчёт, опубликуй его в tracker и выполни подтверждённое completion задач каскада и specification ID при их наличии; сохраняй результаты каждого действия для recovery и не повторяй успешные. При ошибке checkpoint → HUMAN_ATTENTION. После успешного completion установи WORKFLOW_STATUS = COMPLETED и удали ledger.

### 9. Merge reconciliation

Эта фаза выполняется только для подтверждённого `merge_target_branch`; task-ветка и parent-ветка должны быть явно различны. Через `git worktree list --porcelain` найди `parent_worktree`, где checkout parent-ветки, либо явно выбранный чистый integration worktree. Все операции с parent-веткой выполняй только там; task-worktree остаётся на task-ветке. Перед действиями проверь чистоту обоих worktree, исключая только учтённый в ledger файл самого ledger. Чужие или неучтённые изменения — `HUMAN_ATTENTION`; не прячь, не stash и не удаляй их.

Если `parent_worktree` занят параллельным reconciliation другой task-ветки — активен merge (`MERGE_HEAD`) либо Git сообщает lock/index/ref contention — не меняй этот worktree. Дождись завершения или отмены того мёрджа, запиши в ledger ожидаемую ветку, наблюдаемое состояние и результат ожидания, затем начни цикл с шага 1. Используй ожидание task/thread, когда известен владелец; иначе проверяй Git-state с backoff. Не продолжай с зафиксированным до ожидания `parent_tip`.

Повторяй цикл до успешного final merge:

1. В `parent_worktree` выполни `git pull --ff-only` parent-ветки. Если она занята параллельным reconciliation, дождись его по правилу выше и начни этот шаг заново. Иную ошибку pull сохрани с точным выводом в ledger и остановись в `HUMAN_ATTENTION`.
2. Запиши полученный HEAD parent-ветки как `parent_tip`; в task-worktree выполни `git merge <parent_tip>`.
3. При конфликте запусти fresh reviser только с конфликтующими файлами, `parent_tip` и указанием разрешить текущий merge без потери ни одного из двух изменений. Он разрешает конфликт, выполняет релевантные targeted checks и коммитит merge resolution. Затем запусти fresh verifier для изменённых конфликтом областей и delta-review обеих осей. Red gate или active critical finding возвращает в обычный repair path; после green gate и закрытых findings продолжи этот цикл с шага 1, так как parent-ветка могла сдвинуться.
4. При merge без конфликта в `parent_worktree` непосредственно перед final merge снова выполни `git pull --ff-only`. При занятом parent-worktree дождись другого reconciliation и вернись к шагу 1.
5. Если HEAD parent-ветки отличается от `parent_tip`, вернись к шагу 2: task-ветка должна включать именно свежий tip parent-ветки.
6. Если tips совпадают, в `parent_worktree` выполни `git merge --ff-only <task-branch>` в parent-ветку. Это единственный final merge. При lock/contention или признаках незавершённого reconciliation другой ветки дождись его завершения либо отмены и вернись к шагу 1. Если fast-forward не проходит, не создавай merge commit: checkpoint, зафиксируй фактические refs и начни цикл заново с шага 1; после обновления parent-ветки снова выполни подмёрж, устранение конфликтов и новую попытку.

Записывай в ledger каждую попытку: `parent_worktree`, parent/task refs до и после pull, `parent_tip`, ожидания параллельных reconciliation, результат подмёржа, конфликтующие файлы, resolver/verifier handoff и SHA final fast-forward. После любого conflict-resolution commit QUALITY снова RED до green verifier; при успешном цикле верни QUALITY = GREEN. Tracker completion и cleanup разрешены только после SHA final fast-forward. При подтверждённом cleanup удали только task-worktree, созданный для этой задачи; никогда не удаляй parent/default worktree.

## Conflicts

Если оси противоречат, примени более высокую severity. Если противоречие меняет behavior/design и не разрешается явным repo standard или spec, установи HUMAN_ATTENTION.
