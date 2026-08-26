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

- spec paths, task ID, branch, BASE, HEAD;
- current_phase, WORKFLOW_STATUS, QUALITY;
- review iteration, last_reviewed_head по каждой оси;
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
5. В текущем диалоге продолжай сразу после ответа человека. resume <ledger> нужен только для recovery в новом контексте.

## State machine

### 1. Implement

Запусти fresh implementer со spec paths, acceptance criteria, BASE и scope. Прими отчёт с commit SHA, changed files, targeted checks и risks. Проверь, что HEAD совпадает с отчётом.

Completion: worker commit существует, scope и checks записаны в ledger.

### 2. Pre-review gate

Запусти fresh verifier в режиме pre-review:

1. compile/typecheck affected source sets;
2. targeted tests для changed behavior;
3. один relevant full suite.

При red gate передай единый failure inventory fresh implementer до первого review или reviser после review. Repair не увеличивает review iteration. После repair commit запусти fresh verifier ещё раз. Одинаковый red gate без прогресса два раза → HUMAN_ATTENTION.

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

После commit: fresh verifier в targeted → delta Review только по originating axes. Полный suite повторится только в final gate.

### 6. Human decisions

Задай все готовые вопросы одним batch. Для каждого finding покажи ID, severity, axis, location, evidence и proposed fix.

Варианты: FIX_NOW, создать linked task, REJECTED(<reason>). Для critical finding также прими correction/instruction. Явный отказ исправлять critical finding → STOPPED_BY_HUMAN, не COMPLETED.

Перед вопросом установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши pending_action и сделай checkpoint. После ответа запиши решения, очисти pending_action и верни WORKFLOW_STATUS = RUNNING, кроме terminal refusal.

Новые указания человека во время активного worker добавляй в user_directives; worker не прерывай. Примени directives перед следующим переходом фазы и отметь их consumed.

### 7. Execute minor decisions

- Создай согласованные linked tasks по docs/agents/issue-tracker.md и запиши IDs/URLs.
- Запиши human rejection с причиной.
- Для FIX_NOW запусти fresh reviser, затем targeted verifier gate и только originating review axis. Максимум две review iterations; critical finding после лимита возвращает workflow в Human decisions.

### 8. Final gate and completion

1. Запусти fresh verifier в final: compile affected source sets, targeted tests, один final relevant full suite.
2. Если gate red, передай inventory fresh reviser. Для repair commit запиши affected_review_axes: Spec для изменения observable behavior, contracts или requirements; Standards для изменения структуры или conventions; пустой список допустим только для tests/build tooling, не меняющих product code. При неясной классификации запускай обе оси.
3. После repair commit запусти targeted verifier, затем delta-review только по affected_review_axes. Повтори final gate. Одинаковый red gate без прогресса два раза → HUMAN_ATTENTION.
4. При green gate не запускай review: каждый commit после initial Review уже прошёл обязательный delta-review, а verifier не меняет HEAD.
5. Проверь ledger: нет PENDING, FIX_NOW, HUMAN_ATTENTION и active critical findings.
6. Установи QUALITY = GREEN.
7. Установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши completion decision как pending_action, сделай checkpoint и спроси, выполнять ли merge, tracker completion и cleanup current worktree. Без явного подтверждения не выполняй эти действия.
8. После решения установи WORKFLOW_STATUS = COMPLETED, сформируй итоговый отчёт, опубликуй его в tracker при наличии task ID и удали ledger.

## Conflicts

Если оси противоречат, примени более высокую severity. Если противоречие меняет behavior/design и не разрешается явным repo standard или spec, установи HUMAN_ATTENTION.
