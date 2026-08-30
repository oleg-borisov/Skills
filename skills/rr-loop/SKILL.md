---
name: rr-loop
description: Запустить интерактивный implement → verify → review → revise workflow в текущем primary-контексте.
disable-model-invocation: true
---

# RR Loop

Ты — primary-controller текущего диалога. Веди state machine, ledger, interaction with user и transitions между фазами. Product code и checks выполняют leaf-agents.

## Инварианты

- Все leaf-agents — прямые дети primary; leaf-agent не запускает другого агента.
- Controller не читает весь product code, не редактирует его и не запускает project checks. Ему достаточно spec, git metadata, compact handoffs и ledger.
- Каждый worker получает только spec paths, fixed points, finding IDs и свой phase contract. Не вставляй в prompt полную историю цикла.
- Worker, который меняет код, коммитит свою фазу. Controller проверяет новый HEAD.
- Review начинается только после green verifier gate. Reviewers не запускают checks.
- QUALITY = GREEN: активных BLOCKER/MAJOR нет, final gate green, initial и обязательные delta-review завершены.
- Итоговый отчёт и cleanup ledger разрешены только при terminal status.

## Leaf-agents

- implementer — реализует spec, делает targeted checks, коммитит.
- verifier — read-only gate; возвращает один failure inventory.
- standards-reviewer — проверяет documented standards и smell baseline.
- spec-reviewer — проверяет соответствие spec.
- reviser — исправляет заданные finding IDs, делает targeted checks, коммитит.

Все пять named leaf-agents являются обязательной capability host. Если хотя бы одна требуемая роль или механизм subagents недоступны, установи WORKFLOW_STATUS = BLOCKED_UNSUPPORTED_HOST, перечисли отсутствующие capabilities, сохрани ledger и остановись.

## Ledger

LEDGER = .scratch/rr-loop/<task-or-branch>-<BASE>.md. Храни:

- spec paths, task ID, branch, BASE, HEAD, merge_target_branch, parent_worktree и последний интегрированный commit parent-ветки;
- tracker activation: исходный и целевой статус, применённый transition, timestamp и результат;
- current_phase, WORKFLOW_STATUS, QUALITY;
- review iteration, last_reviewed_head по каждой оси, last_full_green_head;
- queued user_directives;
- phase_results: phase, worker, input fixed point, output commit, checks/verdict, timestamp;
- findings: stable ID, axis, severity, location, evidence, proposed fix, state, human decision;
- pending human action и completion decision.

Finding states: PENDING, FIX_NOW, FIXED, DEFERRED_TO_TASK(<ID>), REJECTED(<reason>), HUMAN_ATTENTION.

Делай atomic checkpoint после фазы, worker commit, human decision и перед паузой. Не переписывай ledger после каждого finding. Ledger не коммитится.

## Запуск и recovery

1. Прочитай spec и выпиши acceptance criteria.
2. Зафиксируй branch и BASE = git rev-parse HEAD до правок.
3. Если для task/branch есть нетерминальный ledger, предложи продолжить его или явно сбросить. Без решения не удаляй файл и не повторяй реализацию.
4. Иначе создай ledger с WORKFLOW_STATUS = RUNNING, QUALITY = RED, current_phase = Implement.
5. До запуска первого worker, а при recovery — сразу после решения продолжить, выполни Tracker activation.
6. В текущем диалоге продолжай сразу после ответа человека. resume <ledger> нужен только для recovery в новом контексте.

### Tracker activation

Для исполняемой задачи с `task ID` прочитай `docs/agents/issue-tracker.md` и используй только описанный там способ получения workflow и перехода. Найди статус, означающий начало активной работы: `In Progress` либо его документированный аналог. Если задача уже находится в таком статусе, переход не повторяй; зафиксируй это в ledger.

Иначе переведи задачу этим transition в найденный статус до первого worker. Запиши в ledger исходный/целевой статусы, transition, timestamp и результат. Не подставляй названия статусов, API или команды из памяти. Если документа нет, workflow/status недоступен, активный статус не определён или transition не проходит, запиши tracker activation как `NOT_APPLICABLE` с причиной и продолжай workflow. При отсутствии `task ID` также запиши tracker activation как `NOT_APPLICABLE` и продолжай workflow.

## State machine

### 1. Implement

Запусти fresh implementer со spec paths, acceptance criteria, BASE и scope. Прими отчёт с commit SHA, changed files, targeted checks и risks. Проверь, что HEAD совпадает с отчётом.

Completion: worker commit существует, scope и checks записаны в ledger.

### 2. Pre-review gate

Если `HEAD != last_full_green_head`, запусти fresh verifier в режиме pre-review с одним relevant full suite. Targeted checks уже выполнил implementer.

При green запиши `last_full_green_head = HEAD`. При `HEAD == last_full_green_head` gate уже закрыт.

При red gate передай единый failure inventory fresh implementer до первого review или reviser после review. Repair не увеличивает review iteration. При repair commit вернись к этому gate; при unchanged HEAD → HUMAN_ATTENTION. Одинаковый red gate без прогресса два раза → HUMAN_ATTENTION.

Completion: verifier вернул green с exact commands/results.

### 3. Review

Первая итерация: параллельно fresh standards-reviewer и fresh spec-reviewer против BASE...HEAD.

Повторная итерация:

- fixed point — last_reviewed_head соответствующей оси;
- запускай только оси, породившие активные findings;
- если active findings есть в обеих осях, запусти обе параллельно.

Нормализуй отчёты в stable IDs и severity:

- BLOCKER: security/data loss, broken mandatory contract, build/test impossibility, mandatory spec requirement missing;
- MAJOR: logic error, important edge case, material spec deviation, material performance/design defect;
- MINOR: local maintainability, naming, comments, cosmetic or deferred improvement.

Сохраняй axis и evidence. Не мерджи две оси в один verdict. Completion: findings запущенных осей записаны, last_reviewed_head обновлён.

### 4. Decide

- Нет active BLOCKER/MAJOR → обработай MINOR/human items.
- Есть active critical findings → Revise.
- Тот же critical finding без прогресса в двух последовательных review или четыре critical review iterations всего → HUMAN_ATTENTION.

MINOR можно исправить попутно только если в той же revise-фазе есть BLOCKER/MAJOR и MINOR однозначно дешёвый: один файл, до 20 LOC, без public API/schema/test-architecture/research. Иначе нужно решение человека. MINOR больше трёх файлов, 100 LOC или меняющий test architecture нельзя брать FIX_NOW: только linked task или rejection.

### 5. Revise

Запусти fresh reviser с critical findings, указаниями человека и eligible cheap MINOR. Прими commit SHA либо подтверждение unchanged HEAD, per-finding disposition и targeted checks. Отклонённый BLOCKER всегда переводи в HUMAN_ATTENTION.

При новом commit запусти delta Review только по originating axes. При unchanged HEAD не запускай checks или review.

### 6. Human decisions

Задай все готовые вопросы одним batch. Для каждого finding покажи ID, severity, axis, location, evidence и proposed fix.

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
4. При green gate не запускай review: каждый commit после initial Review уже прошёл обязательный delta-review, а verifier не меняет HEAD.
5. Проверь ledger: нет PENDING, FIX_NOW, HUMAN_ATTENTION и active critical findings.
6. Установи QUALITY = GREEN.
7. Установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши completion decision как pending_action, сделай checkpoint и спроси, выполнять ли merge в явно названную parent-ветку, tracker completion и cleanup current worktree. Сохрани `merge_target_branch` в ledger. Без явного подтверждения не выполняй эти действия.
8. После подтверждения выполни фазу Merge reconciliation.
9. Только после успешного fast-forward merge установи WORKFLOW_STATUS = COMPLETED, сформируй итоговый отчёт, опубликуй его в tracker при наличии task ID и удали ledger.

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

Записывай в ledger каждую попытку: `parent_worktree`, parent/task refs до и после pull, `parent_tip`, ожидания параллельных reconciliation, результат подмёржа, конфликтующие файлы, resolver/verifier handoff и SHA final fast-forward. После любого conflict-resolution commit QUALITY снова RED до green verifier; при успешном цикле верни QUALITY = GREEN. Tracker completion и cleanup разрешены только после SHA final fast-forward.

## Conflicts

Если оси противоречат, примени более высокую severity. Если противоречие меняет behavior/design и не разрешается явным repo standard или spec, установи HUMAN_ATTENTION.
