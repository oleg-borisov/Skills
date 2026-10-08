---
name: rr-loop
description: Запустить интерактивный implement → verify → review → revise workflow в текущем primary-контексте.
disable-model-invocation: true
---

# RR Loop

Ты — primary-controller текущего диалога: веди state machine, ledger, решения человека и переходы фаз. Product code и checks выполняют leaf-agents.

## Инварианты

- Все leaf-agents — прямые дети primary; leaf-agent не запускает другого агента.
- Controller работает со spec, git metadata, compact handoffs и ledger; не исследует и не редактирует product code, не запускает project checks или formatter.
- Implement начинается с запуска fresh implementer. Если primary уже изменил product code вместо worker — HUMAN_ATTENTION.
- Цикл начинается в текущем checkout; окружение не меняется до merge reconciliation. Worker сохраняет чужие изменения и коммитит свой scope после formatter и targeted checks.
- Каждый новый commit проходит Verify → Review → Decide. Единственные исключения — явные NOT_APPLICABLE gate/axis и deferred review по правилам ниже.
- Verifier — отдельный агент: выполняет обязательный full-suite gate и собирает failures вне контекста implementer/reviser. Reviewers checks не запускают.
- QUALITY = GREEN требует актуального gate evidence, обязательного review coverage и отсутствия OPEN findings. Отсутствие прогресса не закрывает critical finding.
- Итоговый отчёт — после успешного final merge; cleanup ledger и notes_dir — только при terminal status.

## Контекст и handoff

Передавай refs, не содержимое spec/diff/логов и не историю диалога. Если host позволяет, запускай workers без наследования истории controller. spec_refs = [{path, sections, criterion_ids, hash}]; для общих контрактов добавляй нужные разделы. Controller один раз на диапазон получает changed_files через git metadata; patch читает каждый worker в своём scope.

Общий вход worker: {base_sha, head_sha, changed_files}; дополнительно по роли — spec_refs, standards_files, notes_paths, findings_path + finding_ids, failure_inventory_path, directives_path, validation_plan_path. Пустые необязательные данные опускай. Вызывай по контракту named-агента; controller и worker используют одинаковые имена полей.

standards_files впервые возвращает implementer: применимые repo standards, включая вложенные инструкции. Переиспользуй пути и хеши, обновляй при новом scope или изменении источников; неизвестные standards не считай отсутствующими. Verifier возвращает validation plan с commands/scope/config_refs; controller сохраняет его и compact failure inventory в ledger-каталог. Полные логи остаются по log_path. Следующие workers получают только относящиеся к ним notes_paths.

## Leaf-agents

- implementer — текущая spec, carried findings или pre-review repair; targeted checks и commit.
- verifier — read-only full-suite gate и один failure inventory.
- standards-reviewer — documented standards; spec-reviewer — соответствие spec.
- reviser — заданные findings или post-review repair; targeted checks и commit.
- scout — опциональное общее исследование нескольких workers.

Все пять основных named-ролей и механизм subagents обязательны. При отсутствии capability → BLOCKED_UNSUPPORTED_HOST, запиши причину в checkpoint и остановись. Недоступность scout → Exploration = NOT_APPLICABLE.

## Ledger

LEDGER_DIR = .scratch/rr-loop/<branch>/:
- state.json — актуальный компактный checkpoint; атомарная замена через временный файл в том же каталоге.
- findings.jsonl — append-only события со stable ID, seq, axis, severity, location, evidence, fix, state и review disposition.
- Артефакты handoff, validation plan и inventory — по ссылкам из checkpoint.

Checkpoint хранит workflow/task/branch, BASE/HEAD, spec_refs и source hashes, WORKFLOW_STATUS/QUALITY, current_phase, pending_action/user_directives, last_full_green_head и gate evidence, last_reviewed_head по каждой оси, review coverage/iteration counters, OPEN IDs с указателями на последние записи findings, findings_seq, phase_results/worker handoff refs, standards/validation refs, notes metadata, merge_target_branch и результаты tracker/merge/cleanup. Текст spec и логи не дублируй.

После фазы сначала допиши findings/handoff, затем атомарно сохрани checkpoint. Recovery читает state.json, актуальные OPEN records и хвост findings после findings_seq; более старую историю — только при расхождениях. Незавершённую запись не считай подтверждённой; незаписанный worker commit сверяй с handoff до повторного dispatch.

Finding states: OPEN, FIXED (подтверждён reviewer), WONT_FIX(reason, human decision или linked task ID). ACCEPTED от worker оставляет finding OPEN до review. Critical = BLOCKER/MAJOR; автоматически WONT_FIX для них запрещён. Отсутствие finding в новом отчёте не закрывает старый ID.

Перед новым запуском ищи нетерминальный state.json и прежний <branch>.md обоих workflows для task/branch. Предложи продолжить или явно сбросить; без решения не удаляй и не запускай реализацию повторно. Старый ledger при согласованном recovery прочитай полностью один раз, перенеси актуальное состояние и сохрани legacy_path до terminal cleanup. При двух конфликтующих ledger → HUMAN_ATTENTION.

## Запуск и recovery

1. Прочитай spec, сохрани spec_refs с ID критериев, не их текст; проверь существующие ledger по правилам выше.
2. При recovery сверь task/branch, BASE/HEAD, sources, фазу, pending_action и handoffs. Продолжай checkpoint, не повторяя подтверждённые фазы; необъяснимое расхождение → HUMAN_ATTENTION.
3. При новом запуске зафиксируй branch и BASE = HEAD до правок, создай checkpoint RUNNING/QUALITY = RED. Выполни Preflight, Exploration и Tracker activation; затем Implement.
4. В текущем диалоге продолжай сразу после ответа человека; resume <ledger> нужен только для нового контекста.

### Tracker activation

Для task ID прочитай docs/agents/issue-tracker.md: только описанный способ workflow/transition. Переведи задачу в In Progress или документированный аналог до первого worker; если уже активна — не повторяй. Сохрани исходный/целевой статус, transition, timestamp и результат. Отсутствие task ID/документа, недоступность workflow или ошибка transition → NOT_APPLICABLE с причиной; это не разрешает пропускать получение задач и проверку blockers. API и статусы из памяти не подставляй.

### Exploration

Запускай одного fresh scout только при конкретных questions, ответы на которые нужны нескольким последующим workers. Локальное исследование одной задачи выполняет implementer. Вход scout: {spec_refs, head_sha, questions, notes_dir}; notes_dir — доступный workers каталог вне репозитория. Заметки содержат source_head, relevant_paths и evidence; controller хранит только metadata/пути. При recovery переиспользуй заметки; worker сверяет изменившиеся sources с кодом. Нет общих вопросов, scout или доступного notes_dir → NOT_APPLICABLE с причиной.

## State machine

### 0. Preflight

До Exploration, tracker activation и workers проверь наличие проверяемых acceptance criteria. Неопределённая spec без наблюдаемого результата → HUMAN_ATTENTION. Для docs допустима проверяемая документальная цель без executable test.

### 1. Implement

Следующее действие — fresh implementer с {spec_refs, base_sha: BASE, head_sha: HEAD, changed_files} и доступными context refs. Controller не исследует product code до dispatch. Прими финальный JSON worker, проверь новый commit и совпадение HEAD; отсутствие нового commit → HUMAN_ATTENTION, не повторная реализация вслепую.

Сохрани standards_files, scope/checks и affected_review_axes в checkpoint; затем Verify. Formatter/autofix уже выполнен worker до commit, controller его не запускает.

### 2. Verify

Если HEAD == last_full_green_head и проверяемые входы не изменились, используй сохранённый GREEN. Незакоммиченные изменения проверяемых входов, неизвестный scope или недостоверное evidence → HUMAN_ATTENTION, не skip.

Docs-only означает только неисполняемый текст: расширение или каталог docs/ само по себе ничего не гарантирует. Executable examples, MDX logic, конфиги, agent instructions и build inputs требуют обычного gate. Классификация опирается на worker handoff и repo configuration; сомнение → обычный gate. Docs-only gate = NOT_APPLICABLE допустим, если весь непроверенный диапазон от last_full_green_head (или BASE, если GREEN ещё нет) — такой текст. Сохрани диапазон и причину; last_full_green_head не обновляй.

Иначе запусти fresh verifier с {head_sha, base_sha, changed_files, mode, validation_plan_path}; scope покрывает весь непроверенный диапазон, mode = pre-review (final при входе из Done). Verifier определяет/переиспользует обязательные commands по repo configuration и выполняет один полный проход. GREEN → last_full_green_head = HEAD и evidence в checkpoint.

RED → сохрани единый inventory и вызови fresh implementer до первого review текущей задачи, иначе fresh reviser. Repair получает failure_inventory_path и refs scope; новый commit всегда возвращает в Verify. Repair не увеличивает review iteration. Unchanged HEAD, BLOCKED или три RED подряд → HUMAN_ATTENTION; GREEN сбрасывает RED counter. Failures автоматически не отклоняй.

Completion: GREEN с commands/results для текущего HEAD либо обоснованный NOT_APPLICABLE для всего непроверенного диапазона.

### 3. Review

Для каждой оси base_sha = её last_reviewed_head, а до первого review — BASE. Выбор осей определяется всем непокрытым диапазоном этой оси, не только последним commit/задачей. Tests-only не освобождает от Standards. Spec обязателен для требований задачи; Standards пропускай только если применимые документированные правила отсутствуют или полностью покрыты успешными автоматическими checks. Для skip сохрани range/reason как NOT_APPLICABLE coverage; last_reviewed_head не продвигай.

После repair запускай union(originating axes незакрытых findings, affected_review_axes нового diff). Изменение observable behavior/контрактов/requirements требует Spec; структуры/conventions, включая tests/build tooling, — Standards. При сомнении обе. Непокрытые обязательные оси сохраняются даже без новых findings.

Передавай {base_sha, head_sha, changed_files} и role-specific refs: Spec — spec_refs + review_mode; Standards — standards_files; для проверки исправлений — findings_path + finding_ids данной оси. Две нужные оси запускай параллельно. initial читает критерии задачи и общие контракты; delta — findings, затронутые критерии и diff с расширением по зависимостям.

Принимай JSON контракта reviewer: {head, verdict, findings, dispositions}. Finding: {type, location, requirement_ref|standard_ref, evidence, fix}; disposition: {id, state: FIXED|OPEN, evidence}. NO_SPEC/BLOCKED_CONTEXT, неверный HEAD или неполный disposition → HUMAN_ATTENTION; такой отчёт не продвигает coverage. Controller назначает stable IDs и severity: wrong→BLOCKER, missing/partial/hard→MAJOR, judgement→MINOR. Не объединяй оси в один verdict.

Completion: findings и explicit dispositions сохранены, last_reviewed_head каждой выполненной оси = проверенный HEAD, coverage записан. Дубли объединяй с сохранением IDs и истории, critical без прогресса два последовательных review → HUMAN_ATTENTION.

### 4. Triage

Лимиты: максимум две итерации исправления MINOR; затем оставшиеся MINOR — пакет решений человека (linked task либо rejection). Четыре critical review iterations или тот же critical без прогресса два review подряд → HUMAN_ATTENTION. Лимиты не закрывают findings.

- Active critical → Revise.
- Нет active critical → Human decisions для оставшихся MINOR/спорных findings; при отсутствии вопросов → Done.
- Дешёвый MINOR можно исправить попутно с critical: один файл, до 20 LOC, без public API/schema/test-architecture/research. Остальные требуют решения человека.

### 4.1 Revise

Запусти fresh reviser с findings_path/finding_ids, spec_refs, standards_files, refs scope и directives_path при наличии. Прими commit/head, per-ID ACCEPTED|REJECTED, checks и affected_review_axes. ACCEPTED оставляет finding OPEN до review. Отклонённый critical → HUMAN_ATTENTION с evidence.

При новом commit: проверь HEAD, выполни Verify (§2), затем delta Review (§3) и Triage. При unchanged HEAD checks/review не повторяй; неразрешённые dispositions передай человеку.

### 4.2 Human decisions

Задай готовые вопросы одним batch: ID, severity, axis, location, evidence и proposed fix. Варианты MINOR: FIX_NOW, linked task, REJECTED(reason). MINOR >3 файлов, >100 LOC или меняющий test architecture — только linked task/rejection. Для critical прими correction/instruction; явный отказ исправлять → STOPPED_BY_HUMAN, не COMPLETED.

До вопроса запиши WAITING_FOR_HUMAN и pending_action в checkpoint. После ответа сохрани решения, очисти pending_action и продолжи RUNNING, кроме terminal refusal. Разрешённые linked tasks создавай по docs/agents/issue-tracker.md, сохраняй IDs/URLs; только затем отмечай DEFERRED как WONT_FIX. Для FIX_NOW — §4.1.

Указания человека во время worker сохраняй в user_directives; применяй перед следующим переходом и отмечай consumed. Явную просьбу остановить работу исполняй сразу.

### 5. Done

1. Проверь актуальный gate (§2) и обязательное coverage (§3). Сохранённый GREEN не требует нового verifier; выполненные reviews на том же HEAD не повторяй. При недостатке evidence вернись в соответствующую фазу. RED repair следует обычному Verify → Review → Triage, отдельной repair-ветки в Done нет.
2. Проверь отсутствие OPEN findings и незавершённых решений; установи QUALITY = GREEN.
3. Сохрани WAITING_FOR_HUMAN, completion pending_action и явно названный merge_target_branch. Запроси подтверждение merge, tracker completion и cleanup task-worktree, если он создан для задачи. Без явного подтверждения этих действий не выполняй.
4. После подтверждения — §6. Только после успешного merge сформируй итоговый отчёт и опубликуй в tracker при task ID; выполни подтверждённое completion/cleanup. Ошибка → checkpoint и HUMAN_ATTENTION.
5. После успешного завершения установи COMPLETED и удали ledger-каталог, сохранённый legacy ledger и notes_dir этой задачи.

### 6. Merge reconciliation

Только для подтверждённого merge_target_branch, отличного от task-ветки. Выполни rebase на актуальный parent tip; при конфликте/ошибке → HUMAN_ATTENTION, без автоматического retry loop. Если HEAD изменился, прежнее gate/review evidence не переносится автоматически: вернись в Verify → обязательный Review, сохранив утверждённый merge target. После восстановления QUALITY = GREEN выполни fast-forward в подтверждённую parent-ветку по workflow репозитория; простой push task-ветки не подтверждает merge. Ошибка fast-forward → HUMAN_ATTENTION.

Tracker completion и cleanup разрешены только после подтверждённого merge. Удали только task-worktree, созданный для этой задачи, никогда parent/default worktree. Сохраняй результаты внешних действий и не повторяй успешные после recovery.

## Conflicts

Сохраняй evidence обеих осей. Неразрешённое spec/standard противоречие поведения/design или critical → HUMAN_ATTENTION; остальные спорные findings передай в Human decisions. Severity и лимиты не подменяют решение о корректности.
