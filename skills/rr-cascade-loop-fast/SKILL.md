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
- Каждый worker получает только refs: spec_paths, fixed_point SHA, finding IDs, пути заметок scout'а, phase contract. НЕ вставляй в prompt содержимое spec, diff или историю цикла.
- Worker, который меняет код, коммитит свою фазу. Controller проверяет новый HEAD.
- Review кодовых изменений начинается только после green verifier gate. Reviewers не запускают checks.
- QUALITY = GREEN: активных BLOCKER/MAJOR нет, final gate green, initial и обязательные delta-review завершены. Final verifier может быть пропущен как неприменимый (§2); для отложенных задач их роль выполняет покрывающее Review в final gate.
- Итоговый отчёт разрешён только после успешного final merge; cleanup ledger и notes_dir — только при terminal status.

## Token Budget Rule

Никогда не вставляй в промпт worker'a содержимое файлов. Передавай только путь + SHA/диапазон. Worker читает сам нужный фрагмент. Diff вычисляй один раз в controller и передавай changed_files + range.

## Leaf-agents

- implementer — реализует spec, делает targeted checks, коммитит.
- verifier — read-only gate; возвращает один failure inventory.
- standards-reviewer — проверяет documented standards.
- spec-reviewer — проверяет соответствие spec.
- reviser — исправляет заданные finding IDs, делает targeted checks, коммитит.
- scout — опциональный exploration-агент: пишет заметки в notes_dir, код и checks не трогает. Недоступность scout — Exploration = NOT_APPLICABLE с причиной, не BLOCKED.

Все пять named leaf-agents являются обязательной capability host. Если хотя бы одна требуемая роль или механизм subagents недоступны, установи WORKFLOW_STATUS = BLOCKED_UNSUPPORTED_HOST, перечисли отсутствующие capabilities, сохрани ledger и остановись.

## Ledger

LEDGER = .scratch/rr-cascade-loop-fast/<branch>.md. Храни только: BASE, HEAD, last_full_green_head, last_reviewed_head, pending OPEN finding IDs, current_task, пометки задач deferred/deferred:batch, путь и список файлов заметок scout'а. Текст spec/criteria не дублируй - только пути+хеши. Findings как JSONL append-only; ledger целиком не переписывай. При recovery читай header + последние 50 строк.

Finding states: OPEN, FIXED, WONT_FIX(<reason>). AWAITING_REVIEW == OPEN до следующего Review. DEFERRED == WONT_FIX с linked task ID. Task states: PENDING, ACTIVE, AWAITING_REVIEW, REVIEWED; это не tracker completion. Отложенная документационная задача — OPEN с пометкой deferred: verify и review отложены до покрывающего Review. Кодовая задача с критериями отложения (§3) — OPEN с пометкой deferred:batch: verifier gate обязателен, review отложено.

Делай atomic append checkpoint после фазы; заметки scout'а храни без содержимого.

## Запуск и recovery

1. Определи branch и проверь нетерминальный ledger любого из rr-loop, rr-cascade-loop-fast для входной spec/task/branch до любых ранних выходов. Предложи продолжить его или явно сбросить; без решения не удаляй файл и не повторяй реализацию. При recovery сохрани BASE из ledger, сверь plan/sources, branch, HEAD, phase_results, task states (включая OPEN-deferred), last_reviewed_head осей и pending_action; подтверждённые фазы не повторяй, незаписанный worker commit сначала сверяй с handoff. Изменение состава, требований или порядка требует подтверждения нового плана; необъяснимое расхождение Git-state → HUMAN_ATTENTION. Продолжай сохранённый workflow/фазу, шаги нового запуска ниже не повторяй.
2. Прочитай вход: spec и/или каталог готовых tickets; для tracker — тело, комментарии, подзадачи и связи по `docs/agents/issue-tracker.md`. Найди исходную spec и acceptance criteria. Если все существующие подзадачи завершены — сообщи, что задач нет, и закончи без workers. Без готовой нарезки прочитай установленный `rr-loop/SKILL.md` и продолжай его обычный workflow в primary, без cascade ledger; самостоятельно `to-tickets` не запускай.
3. Зафиксируй BASE = git rev-parse HEAD до правок. Каскад работает в одной текущей ветке с одним финальным merge.
4. Составь plan из незавершённых готовых локальных tickets или подзадач tracker-spec. Для локальных tickets читай `Blocked by`, `Status`, acceptance criteria; порядок файлов — лишь tie-break. Объедини зависимости и порядок spec; независимые задачи упорядочь по spec, затем ID/path. Циклы, конфликт источников, неизвестные статусы/связи/spec → HUMAN_ATTENTION. Внешние задачи в plan автоматически не добавляй.
5. Проверь внешние blockers первой задачи; незавершённый или непроверяемый blocker останавливает запуск. План, явно допускающий red между задачами, также несовместим: green pre-review gate обязателен после каждой задачи, меняющей product code; для документационных задач верификация и review переносятся, для кодовых задач с критериями §3 переносится только review.
6. Покажи название spec, список задач и порядок с зависимостями. Сохрани plan и pending_action подтверждения запуска в ledger с WORKFLOW_STATUS = WAITING_FOR_HUMAN, QUALITY = RED; до подтверждения workers и tracker activation не выполняй.
7. После подтверждения установи RUNNING, выполни Exploration и Task activation. В текущем диалоге продолжай сразу после ответа; resume <ledger> нужен только для recovery в новом контексте.

### Task activation

Перед каждой следующей задачей проверь внешние blockers; blocker или невозможность проверки → HUMAN_ATTENTION. Внутреннюю зависимость считай удовлетворённой по пройденному шагу ledger, включая допустимый перенос findings, без ожидания закрытия тикета. Применяй queued user_directives, установи current_task, task BASE = HEAD, state = ACTIVE, review iteration = 0; перенеси только BLOCKER IDs и выполни Tracker activation для текущего task ID. Checkpoint перед первым worker; затем Implement. При recovery продолжай сохранённую фазу, счётчики и fixed points не сбрасывай.

### Tracker activation

Для исполняемой задачи с `task ID` прочитай `docs/agents/issue-tracker.md` и используй только описанный там способ получения workflow и перехода. Найди статус, означающий начало активной работы: `In Progress` либо его документированный аналог. Если задача уже находится в таком статусе, переход не повторяй; зафиксируй это в ledger.

Иначе переведи задачу этим transition в найденный статус до первого worker. Запиши в ledger исходный/целевой статусы, transition, timestamp и результат. Не подставляй названия статусов, API или команды из памяти. Если документа нет, workflow/status недоступен, активный статус не определён или transition не проходит, запиши tracker activation как `NOT_APPLICABLE` с причиной и продолжай workflow. При отсутствии `task ID` также запиши tracker activation как `NOT_APPLICABLE` и продолжай workflow. Это послабление касается только смены статуса, не получения задач и проверки blockers.

### Exploration

Если план требует исследования кода — неизвестные conventions, точки интеграции, внешние доки, открытые вопросы в spec — запусти до первого worker'а одного fresh scout'а с {spec_paths, questions[], notes_dir}. scout пишет заметки append-only файлами в notes_dir (одна тема — один файл); код, tests и конфигурацию не меняет, checks не запускает, других агентов не порождает. notes_dir выбирает controller вне репозитория — каталог, доступный для записи всем workers на этом хосте, например временный каталог хоста; путь и список файлов заметок запиши в ledger. Все дальнейшие workers получают пути заметок по Token Budget Rule, не содержимое. При recovery переиспользуй заметки по пути из ledger, не исследуй заново. При расхождении заметок с кодом worker доверяет коду. Exploration не нужен, роль scout недоступна, заметки уже записаны или запись в notes_dir невозможна — запиши Exploration = NOT_APPLICABLE с причиной и продолжай.

## State machine

### 0. Preflight (30 сек, без агентов)

Controller сам проверяет: spec имеет Given/When/Then или acceptance criteria с цифрами/проверяемыми условиями? Можно ли написать тест до кода?
Если spec == "сделать красиво/быстро/лучше" без критериев -> WORKFLOW_STATUS=HUMAN_ATTENTION, не запускай implementer. Экономит весь цикл.

### 1. Implement

Запусти fresh implementer с {spec_paths текущей задачи, task BASE_SHA, range task BASE..HEAD, carried_ids: [только BLOCKER IDs]}. Refs — по Token Budget Rule: текст criteria и остальных findings не передавай, worker читает нужное сам. Переноси между задачами только BLOCKER; MAJOR фиксируй сразу в своей задаче или WONT_FIX(DEFERRED); eligible cheap MINOR разрешены попутно по правилам Triage, будущие задачи вне scope. Прими отчёт с commit SHA, changed files, targeted checks и risks; заявленные исправления отметь OPEN; output — строго JSON контракта implementer. Проверь, что HEAD совпадает с отчётом; HEAD без нового worker commit → HUMAN_ATTENTION. После commit implementer контроллер запускает fmt/lint (ruff format/prettier/go fmt) детерминированно, без LLM. 30% standards findings - это пробелы/импорты.

Completion: worker commit существует, scope и checks записаны в ledger.

### 2. Verify-if-dirty: if HEAD==last_full_green_head -> skip

Единый гейт verify-if-dirty: если HEAD == last_full_green_head -> GREEN skip. Для документационной задачи gate skip по определению §2. Иначе запусти fresh verifier в режиме pre-review с одним relevant full suite.

Документационная задача — все changed files её worker commit(-ов) — файлы документации (`.md`/`.mdx`/`.rst`, docs-каталоги); любой другой файл, включая конфиги и комментарии в коде, делает задачу обычной. Для документационной задачи verifier не запускай и `last_full_green_head` не обновляй; её review переносится (§3).

При green запиши `last_full_green_head = HEAD`. Final verifier в §5 использует этот же гейт.

При red gate передай единый failure inventory fresh implementer до первого review текущей задачи или reviser после review. Repair не увеличивает review iteration. При repair commit вернись к этому gate; при unchanged HEAD -> HUMAN_ATTENTION. При повторном red без прогресса -> retry; max 3 RED подряд -> HUMAN_ATTENTION, иначе авто WONT_FIX.

Completion: verifier вернул green с exact commands/results.

### 3. Review

Задачу не ревьюят в её собственной фазе Review, если:
- документационная задача (§2) — отметь её OPEN с пометкой deferred и переходи как задачу без новых active critical findings;
- кодовая задача проходит все критерии отложения (ниже) — отметь её OPEN с пометкой deferred:batch.

Критерии отложения ревью кодовой задачи (deferred:batch): суммарный worker diff < 100 строк и < 10 файлов; нет public API, schema, контрактов, migrations, test-architecture; verifier gate green с первой попытки; задача не последняя; с момента последнего состоявшегося Review отложено менее трёх задач с deferred:batch — документационные задачи счёт не сбрасывают. Явная user_directive форсирует Review любой отложенной задачи; числа критериев переопределяет явное решение человека при подтверждении плана, зафиксируй их в ledger.

Покрывающее Review: когда Review кодовой задачи покрывает изменения отложенных задач, его fixed point — last_reviewed_head оси, а для оси, не ревьюившейся с отложения, — BASE первой непокрытой задачи. После review без новых active critical findings отметь отложенные задачи REVIEWED. При новых active critical findings отложенная задача остаётся OPEN-deferred: её BLOCKER переносится в следующий Implement; MAJOR остаётся активным до следующего покрывающего Review, а на последней задаче закрывается Triage/Revise. Задача не REVIEWED до закрытия её critical findings.

Первый Review каждой задачи: вычисли changed_files = git diff task BASE..HEAD --stat. Условный Review:
- if changed_files == docs-only (.md/.mdx/.rst/docs/) -> verifier skip, standards-reviewer skip (только spec-reviewer если нужно)
- if changed_files == tests-only (*.test.*/__tests__/e2e) -> standards-reviewer skip
- иначе -> оба ревьюера параллельно как сейчас (spec + standards)
LOC не учитывай для решения какие оси запускать. fixed point каждой оси — её last_reviewed_head, для первого шага — общий BASE. Передавай refs по Token Budget Rule: {fixed_point SHA, spec_paths, diff_range}; переносимые findings — как carried_ids [только BLOCKER IDs]. Будущие требования не считай missing. На последней задаче spec-reviewer дополнительно сверяет покрытие всей spec, включая ранее завершённые задачи.

Повторная итерация внутри той же задачи:

- fixed point — last_reviewed_head соответствующей оси;
- запускай только оси, породившие активные findings;
- если active findings есть в обеих осях, запусти обе параллельно.

Ревьюеры возвращают только {type, evidence, location} без severity. Controller мапит type детерминированно: spec-ось — wrong→BLOCKER, missing→MAJOR, partial→MAJOR; standards-ось — hard→MAJOR, judgement→MINOR. Не мерджи две оси в один verdict.

Потребуй evidence и disposition по каждому carried ID: FIXED либо остаётся открытым; отсутствие повторного finding не означает исправление. Сохраняй axis и evidence. Объединяй дубликаты MINOR с сохранением IDs и истории. Completion: findings запущенных осей и dispositions записаны, last_reviewed_head обновлён; задачи с завершённым обязательным review без active critical findings отмечены REVIEWED.

Переход:

- Если текущая задача не последняя: тот же critical finding без прогресса в двух последовательных review сквозь задачи -> авто WONT_FIX(DEFERRED_TO_TASK); явный отказ человека исправлять critical → STOPPED_BY_HUMAN; неразрешённое противоречие поведения/design -> HUMAN_ATTENTION. Иначе перенеси только BLOCKER IDs (refs по Token Budget Rule), оставь текущую задачу с active critical findings в OPEN, сделай checkpoint и выполни Task activation следующей задачи. Следующий worker — fresh implementer.
- Если текущая задача последняя: установи current_phase = Triage и перейди к §4.

### 4. Triage (Decide) — только для последней задачи

Лимиты: max 2 Review итерации на задачу -> авто WONT_FIX(DEFERRED) для оставшихся MINOR. 4 critical review iterations -> HUMAN_ATTENTION.

Входное условие: current_task — последняя задача plan. Если условие не выполнено, допустимый переход определяет §3 Review: Task activation следующей задачи с fresh implementer.

- Нет active BLOCKER/MAJOR → обработай MINOR/human items.
- Есть active critical findings → Revise.
- Тот же critical finding без прогресса в двух последовательных review -> авто WONT_FIX(DEFERRED_TO_TASK); превышение лимитов выше -> HUMAN_ATTENTION.

MINOR можно исправить попутно только если в той же фазе исправляется BLOCKER/MAJOR и MINOR однозначно дешёвый: один файл, до 20 LOC, без public API/schema/test-architecture/research. Иначе нужно решение человека. MINOR больше трёх файлов, 100 LOC или меняющий test architecture нельзя брать FIX_NOW: только linked task или rejection.

### 4.1 Revise

Запусти fresh reviser с critical findings, указаниями человека и eligible cheap MINOR. Прими commit SHA либо подтверждение unchanged HEAD, per-finding disposition и targeted checks. Отклонённый BLOCKER всегда переводи в HUMAN_ATTENTION.

При новом commit запусти delta Review только по originating axes. При unchanged HEAD не запускай checks или review.

### 4.2 Human decisions

Задай все готовые вопросы одним batch по актуальным findings всего каскада. Для каждого finding покажи ID, severity, axis, location, evidence и proposed fix.

Варианты: FIX_NOW, создать linked task, REJECTED(<reason>). Для critical finding также прими correction/instruction. Явный отказ исправлять critical finding → STOPPED_BY_HUMAN, не COMPLETED.

Перед вопросом установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши pending_action и сделай checkpoint. После ответа запиши решения, очисти pending_action и верни WORKFLOW_STATUS = RUNNING, кроме terminal refusal.

Новые указания человека во время активного worker добавляй в user_directives; worker не прерывай. Примени directives перед следующим переходом фазы и отметь их consumed.

### 4.3 Execute minor decisions

- Создай согласованные linked tasks по docs/agents/issue-tracker.md и запиши IDs/URLs.
- Запиши human rejection с причиной.
- Для FIX_NOW запусти fresh reviser по §4.1. Максимум две review iterations; critical finding после лимита возвращает workflow в Human decisions.

### 5. Done

1. Если остались задачи OPEN-deferred (deferred или deferred:batch), выполни их покрывающее Review по правилам §3: условные оси и fixed points как там; spec-reviewer дополнительно сверяет покрытие всей spec. При active critical findings перейди в Triage/Revise и вернись к этому шагу после их закрытия. Иначе отметь отложенные задачи REVIEWED, а некритические findings покрывающего Review передай в Human decisions (§4).
2. Выполни verify-if-dirty (§2). При GREEN не запускай review.
3. Если gate red, передай inventory fresh reviser. Для repair commit запиши affected_review_axes: Spec для изменения observable behavior, contracts или requirements; Standards для изменения структуры или conventions; пустой список допустим только для tests/build tooling, не меняющих product code. При неясной классификации запускай обе оси.
4. После repair commit выполни delta-review только по affected_review_axes и повтори этот gate. При unchanged HEAD -> HUMAN_ATTENTION. При повторном red — retry по лимитам §2.
5. При green gate не запускай review: каждый commit уже прошёл обязательный review или delta-review, а verifier HEAD не меняет.
6. Проверь ledger всего каскада: все задачи реализованы и проверены; нет OPEN, HUMAN_ATTENTION и active critical findings. Все carried findings получили review disposition.
7. Установи QUALITY = GREEN.
8. Установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши completion decision как pending_action, сделай checkpoint и спроси, выполнять ли merge в явно названную parent-ветку, tracker completion и cleanup task-worktree, если он был создан для этой задачи. Сохрани `merge_target_branch` в ledger. Без явного подтверждения не выполняй эти действия.
9. После подтверждения выполни фазу Merge reconciliation (§6).
10. Только после успешного fast-forward merge сформируй итоговый отчёт, опубликуй его в tracker при наличии task ID. Затем выполни подтверждённое completion задач каскада и specification ID при их наличии; сохраняй результаты каждого действия для recovery и не повторяй успешные. При ошибке checkpoint → HUMAN_ATTENTION. После успешного completion установи WORKFLOW_STATUS = COMPLETED и удали ledger и notes_dir.

### 6. Merge reconciliation

Выполняется только для подтверждённого `merge_target_branch`; task-ветка и parent-ветка должны быть явно различны. Merge = git rebase parent_tip + git push. Сложный worktree/MERGE_HEAD/backoff цикл вынесен в отдельный опциональный скилл `rr-merge`. Если rebase не прошел или ff-merge не прошел -> HUMAN_ATTENTION, не крути цикл. Tracker completion и cleanup task-worktree разрешены только после успешного fast-forward merge; при cleanup удали только task-worktree, созданный для этой задачи, никогда не трогай parent/default worktree.

## Conflicts

Если оси противоречат, примени более высокую severity. Если противоречие меняет behavior/design и не разрешается явным repo standard или spec, установи HUMAN_ATTENTION только для BLOCKER, конфликта поведения/design, или превышения лимитов выше. Остальное -> авто WONT_FIX(DEFERRED_TO_TASK) без паузы.
