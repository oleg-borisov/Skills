---
name: rr-loop
description: Запустить интерактивный implement → verify → review → revise workflow в текущем primary-контексте.
disable-model-invocation: true
---

# RR Loop

Ты — primary-controller текущего диалога. Веди state machine, ledger, interaction with user и transitions между фазами. Product code и checks выполняют leaf-agents.

## Инварианты

- Leaf-agents — прямые дети primary; controller не читает весь product code, не редактирует его и не запускает project checks.
- Worker получает только spec paths, fixed points, finding IDs и phase contract; worker с изменениями коммитит, controller сверяет HEAD.
- Нужны implementer, verifier, standards-reviewer, spec-reviewer и reviser. Если роли или subagents недоступны: `BLOCKED_UNSUPPORTED_HOST`, missing capabilities в ledger, stop.
- Review начинается после green verifier gate; reviewers не запускают checks. `QUALITY = GREEN`, только когда нет active BLOCKER/MAJOR, green final gate и завершены initial/обязательные delta-review.
- Итоговый отчёт и cleanup ledger разрешены только при terminal status.

## Ledger

LEDGER = .scratch/rr-loop/<task-or-branch>-<BASE>.md. Храни:

- identity: spec paths, task ID, branch, BASE, HEAD, merge_target_branch, parent_worktree, последний интегрированный commit parent-ветки;
- tracker activation: source/target status, transition, timestamp, result;
- state: current_phase, WORKFLOW_STATUS, QUALITY, review iteration, last_reviewed_head по оси, last_full_green_head, queued user_directives;
- phase_results: phase, worker, input fixed point, output commit, checks/verdict, timestamp;
- findings: stable ID, axis, severity, location, evidence, proposed fix, state, human decision; pending human action и completion decision.

Finding states: PENDING, FIX_NOW, FIXED, DEFERRED_TO_TASK(<ID>), REJECTED(<reason>), HUMAN_ATTENTION.

Делай atomic checkpoint после фазы, worker commit, human decision и перед паузой. Не переписывай ledger после каждого finding. Ledger не коммитится.

## Запуск и recovery

1. Прочитай spec/acceptance criteria и зафиксируй branch с `BASE = git rev-parse HEAD` до правок.
2. При нетерминальном ledger task/branch предложи continue или explicit reset; без решения не удаляй его и не повторяй реализацию. Иначе создай `RUNNING`, `RED`, `Implement` ledger.
3. Выполни Tracker activation до первого worker, а при recovery — после continue. В том же диалоге продолжай после ответа; `resume <ledger>` нужен только в новом контексте.

### Tracker activation

Для task ID прочитай `docs/agents/issue-tracker.md` и только его способом найди active-work status (`In Progress` или документированный аналог). Уже активную задачу лишь зафиксируй; иначе выполни transition до первого worker и запиши source/target, transition, timestamp, result. Без task ID, документа, workflow/status, active status или успешного transition запиши `NOT_APPLICABLE` с причиной и продолжай; названия статусов, API и команды не подставляй из памяти.

## State machine

### 1. Implement

Запусти fresh implementer со spec paths, acceptance criteria, BASE и scope. Прими отчёт с commit SHA, changed files, targeted checks и risks. Проверь, что HEAD совпадает с отчётом.

Completion: worker commit существует, scope и checks записаны в ledger.

### 2. Pre-review gate

Если `HEAD != last_full_green_head`, fresh verifier в `pre-review` запускает один relevant full suite; при green запиши `last_full_green_head = HEAD`. При red передай единый inventory fresh implementer, после repair commit повтори gate; unchanged HEAD либо одинаковый red без прогресса два раза → `HUMAN_ATTENTION`.

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

Запусти fresh reviser с critical findings, указаниями человека и eligible cheap MINOR; прими commit SHA/unchanged HEAD, per-finding disposition и targeted checks. Отклонённый BLOCKER → `HUMAN_ATTENTION`. При новом commit выполни delta Review только по originating axes; при unchanged HEAD не запускай checks или review.

### 6. Human decisions

Задай все готовые вопросы одним batch: ID, severity, axis, location, evidence, proposed fix; варианты — `FIX_NOW`, linked task, `REJECTED(<reason>)`, а для critical ещё correction/instruction. Явный отказ от critical → `STOPPED_BY_HUMAN`, не `COMPLETED`.

Перед вопросом: `WAITING_FOR_HUMAN`, pending_action, checkpoint; после ответа запиши решения, очисти pending_action и верни `RUNNING`, кроме terminal refusal. Новые directives во время worker добавляй в `user_directives`, применяй перед следующим переходом и отмечай consumed.

### 7. Execute minor decisions

- Создай согласованные linked tasks по docs/agents/issue-tracker.md и запиши IDs/URLs; rejection запиши с причиной.
- Для `FIX_NOW` запусти reviser как в фазе 5; максимум две review iterations, затем critical finding возвращается в Human decisions.

### 8. Final gate and completion

1. Если `HEAD != last_full_green_head`, fresh verifier в `final` запускает один relevant full suite и при green обновляет `last_full_green_head`.
2. При red передай inventory reviser. Для его commit задай `affected_review_axes`: Spec — observable behavior/contracts/requirements; Standards — structure/conventions; пусто допустимо только для tests/build tooling без product code; при неясности — обе оси. Выполни delta Review этих осей и повтори gate. Unchanged HEAD либо одинаковый red без прогресса два раза → `HUMAN_ATTENTION`.
3. Green verifier review не запускает. Проверь отсутствие `PENDING`, `FIX_NOW`, `HUMAN_ATTENTION` и active critical findings, затем `QUALITY = GREEN`.
4. Установи `WAITING_FOR_HUMAN`, completion decision как pending_action, checkpoint; запроси явное подтверждение merge в named parent branch, tracker completion и cleanup. Сохрани `merge_target_branch`.
5. После подтверждения выполни Merge reconciliation. Только успешный fast-forward даёт `COMPLETED`, итоговый отчёт, tracker publication и удаление ledger.

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
