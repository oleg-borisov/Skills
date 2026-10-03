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
- Каждый worker получает только refs: spec_paths, fixed_point SHA, finding IDs, phase contract. НЕ вставляй содержимое spec, diff или историю. Worker читает сам.
- Worker, который меняет код, коммитит свою фазу. Controller проверяет новый HEAD.
- Review кодовых изменений начинается только после green verifier gate; документационные commits ревьюятся позже — следующим Review или make-up Review в final gate. Reviewers не запускают checks.
- QUALITY = GREEN: активных BLOCKER/MAJOR нет, final gate green либо final verifier пропущен по §5 п.2 как неприменимый, initial и обязательные delta-review завершены; для отложенных документационных задач их роль выполняет make-up Review в final gate.
- Итоговый отчёт разрешён после успешного final merge; cleanup ledger — только при terminal status.

## Token Budget Rule

Никогда не вставляй в промпт worker'a содержимое файлов. Передавай путь+SHA/диапазон. Diff вычисляй один раз и передавай {changed_files, range}.

## Leaf-agents

- implementer — реализует spec, делает targeted checks, коммитит.
- verifier — read-only gate; возвращает один failure inventory.
- standards-reviewer — проверяет documented standards.
- spec-reviewer — проверяет соответствие spec.
- reviser — исправляет заданные finding IDs, делает targeted checks, коммитит.

Все пять named leaf-agents являются обязательной capability host. Если хотя бы одна требуемая роль или механизм subagents недоступны, установи WORKFLOW_STATUS = BLOCKED_UNSUPPORTED_HOST, перечисли отсутствующие capabilities, сохрани ledger и остановись.

## Ledger

LEDGER = .scratch/rr-cascade-loop-fast/<branch>.md. Храни только: BASE, HEAD, last_full_green_head, last_reviewed_head, pending OPEN finding IDs, current_task. Текст spec/criteria не дублируй - только пути+хеши. Findings как JSONL append-only, не переписывай файл целиком. При recovery читай header + последние 50 строк.

Finding states: OPEN, FIXED, WONT_FIX(<reason>). AWAITING_REVIEW == OPEN до следующего Review. DEFERRED == WONT_FIX с linked task ID. Task states: PENDING, ACTIVE, AWAITING_REVIEW, REVIEWED; это не tracker completion. Отложенная документационная задача — OPEN с пометкой deferred: verify и review отложены до Review следующей кодовой задачи или final review каскада.

Делай atomic append checkpoint. Не переписывай ledger целиком. При recovery читай только YAML header + последние 50 строк. Findings храни как JSONL.

## Запуск и recovery

1. Определи branch и проверь нетерминальный ledger любого из rr-loop, rr-cascade-loop-fast для входной spec/task/branch до любых ранних выходов. Предложи продолжить его или явно сбросить; без решения не удаляй файл и не повторяй реализацию. При recovery сохрани BASE из ledger, сверь plan/sources, branch, HEAD, phase_results, task states (включая OPEN-deferred), last_reviewed_head осей и pending_action; подтверждённые фазы не повторяй, незаписанный worker commit сначала сверяй с handoff. Изменение состава, требований или порядка требует подтверждения нового плана; необъяснимое расхождение Git-state → HUMAN_ATTENTION. Продолжай сохранённый workflow/фазу, шаги нового запуска ниже не повторяй.
2. Прочитай вход: spec и/или каталог готовых tickets; для tracker — тело, комментарии, подзадачи и связи по `docs/agents/issue-tracker.md`. Найди исходную spec и acceptance criteria. Если все существующие подзадачи завершены — сообщи, что задач нет, и закончи без workers. Без готовой нарезки прочитай установленный `rr-loop/SKILL.md` и продолжай его обычный workflow в primary, без cascade ledger; самостоятельно `to-tickets` не запускай.
3. Зафиксируй BASE = git rev-parse HEAD до правок. Каскад работает в одной текущей ветке с одним финальным merge.
4. Составь plan из незавершённых готовых локальных tickets или подзадач tracker-spec. Для локальных tickets читай `Blocked by`, `Status`, acceptance criteria; порядок файлов — лишь tie-break. Объедини зависимости и порядок spec; независимые задачи упорядочь по spec, затем ID/path. Циклы, конфликт источников, неизвестные статусы/связи/spec → HUMAN_ATTENTION. Внешние задачи в plan автоматически не добавляй.
5. Проверь внешние blockers первой задачи; незавершённый или непроверяемый blocker останавливает запуск. План, явно допускающий red между задачами, также несовместим: green pre-review gate обязателен после каждой задачи, меняющей product code; для документационных задач верификация и review переносятся (§2, §3).
6. Покажи название spec, список задач и порядок с зависимостями. Сохрани plan и pending_action подтверждения запуска в ledger с WORKFLOW_STATUS = WAITING_FOR_HUMAN, QUALITY = RED; до подтверждения workers и tracker activation не выполняй.
7. После подтверждения установи RUNNING и выполни Task activation. В текущем диалоге продолжай сразу после ответа; resume <ledger> нужен только для recovery в новом контексте.

### Task activation

Перед каждой следующей задачей проверь внешние blockers; blocker или невозможность проверки → HUMAN_ATTENTION. Внутреннюю зависимость считай удовлетворённой по пройденному шагу ledger, включая допустимый перенос findings, без ожидания закрытия тикета. Применяй queued user_directives, установи current_task, task BASE = HEAD, state = ACTIVE, review iteration = 0; перенеси только BLOCKER IDs и выполни Tracker activation для текущего task ID. Checkpoint перед первым worker; затем Implement. При recovery продолжай сохранённую фазу, счётчики и fixed points не сбрасывай.

### Tracker activation

Для исполняемой задачи с `task ID` прочитай `docs/agents/issue-tracker.md` и используй только описанный там способ получения workflow и перехода. Найди статус, означающий начало активной работы: `In Progress` либо его документированный аналог. Если задача уже находится в таком статусе, переход не повторяй; зафиксируй это в ledger.

Иначе переведи задачу этим transition в найденный статус до первого worker. Запиши в ledger исходный/целевой статусы, transition, timestamp и результат. Не подставляй названия статусов, API или команды из памяти. Если документа нет, workflow/status недоступен, активный статус не определён или transition не проходит, запиши tracker activation как `NOT_APPLICABLE` с причиной и продолжай workflow. При отсутствии `task ID` также запиши tracker activation как `NOT_APPLICABLE` и продолжай workflow. Это послабление касается только смены статуса, не получения задач и проверки blockers.

## State machine

### 0. Preflight (30 сек, без агентов)

Controller сам проверяет: spec имеет Given/When/Then или acceptance criteria с цифрами/проверяемыми условиями? Можно ли написать тест до кода?
Если spec == "сделать красиво/быстро/лучше" без критериев -> WORKFLOW_STATUS=HUMAN_ATTENTION, не запускай implementer. Экономит весь цикл.

### 1. Implement

Запусти fresh implementer с {spec_paths текущей задачи, task BASE_SHA, range task BASE..HEAD, carried_ids: [только BLOCKER IDs]}. Переноси между задачами только BLOCKER. MAJOR фиксируй сразу в своей задаче или WONT_FIX(DEFERRED). Не передавай все findings в промпт следующей задачи - только IDs BLOCKER. Текст criteria и остальных findings НЕ передавай - только IDs. Worker читает нужное сам; eligible cheap MINOR разрешены попутно по правилам Triage, будущие задачи вне scope. Потребуй per-finding disposition дополнительно к commit SHA, changed files, targeted checks и risks; заявленные исправления отметь OPEN; output строго JSON как в implementer. Проверь, что HEAD совпадает с отчётом.

Completion: worker commit существует, scope и checks записаны в ledger.

### 2. Verify-if-dirty: if HEAD==last_full_green_head -> skip

Единый гейт verify-if-dirty: если HEAD == last_full_green_head -> GREEN skip. Для документационной задачи gate skip по определению §2. Иначе запусти fresh verifier в режиме pre-review с одним relevant full suite.

Документационная задача — все changed files её worker commit(-ов) — файлы документации (`.md`/`.mdx`/`.rst`, docs-каталоги); любой другой файл, включая конфиги и комментарии в коде, делает задачу обычной. Для документационной задачи verifier не запускай и `last_full_green_head` не обновляй; её review переносится (§3).

При green запиши `last_full_green_head = HEAD`. Final verifier в §5 использует этот же гейт.

При red gate передай единый failure inventory fresh implementer до первого review текущей задачи или reviser после review. Repair не увеличивает review iteration. При repair commit вернись к этому gate; при unchanged HEAD -> HUMAN_ATTENTION. При повторном red без прогресса -> retry; max 3 RED подряд -> HUMAN_ATTENTION, иначе авто WONT_FIX.

Completion: verifier вернул green с exact commands/results.

### 3. Review

Документационную задачу в её собственной фазе Review не ревьюи: отметь её OPEN с пометкой deferred и переходи как задачу без новых active critical findings. Незакрытые carried findings переносятся дальше и получают disposition в будущем покрывающем Review или в make-up Review (§5 п.1); на make-up Review запрет не распространяется. Когда fixed point Review кодовой задачи покрывает изменения отложенных задач, после завершения review без новых active critical findings отметь их REVIEWED; при новых active critical findings отложенная задача остаётся OPEN-deferred до следующего покрывающего Review.

Первый Review каждой задачи: вычисли changed_files = git diff task BASE..HEAD --stat. Условный Review:
- if changed_files == docs-only (.md/.mdx/.rst/docs/) -> verifier skip, standards-reviewer skip (только spec-reviewer если нужно)
- if changed_files == tests-only (*.test.*/__tests__/e2e) -> standards-reviewer skip
- иначе -> оба ревьюера параллельно как сейчас (spec + standards)
LOC не учитывай для решения какие оси запускать. fixed point каждой оси — её last_reviewed_head, для первого шага — общий BASE. Передавай только {fixed_point SHA, spec_paths, diff_range, carried_ids} - не текст findings. Будущие требования не считай missing. На последней задаче spec-reviewer дополнительно сверяет покрытие всей spec, включая ранее завершённые задачи.

Повторная итерация внутри той же задачи:

- fixed point — last_reviewed_head соответствующей оси;
- запускай только оси, породившие активные findings;
- если active findings есть в обеих осях, запусти обе параллельно.

Ревьюеры возвращают только {type, evidence, location} без severity. Controller мапит в BLOCKER/MAJOR/MINOR детерминированно как в rr-loop.

Потребуй evidence и disposition по каждому carried ID: FIXED либо остаётся открытым; отсутствие повторного finding не означает исправление. Сохраняй axis и evidence. Не мерджи две оси в один verdict. Объединяй дубликаты MINOR с сохранением IDs и истории. Completion: findings запущенных осей и dispositions записаны, last_reviewed_head обновлён; задачи с завершённым обязательным review без active critical findings отмечены REVIEWED.

Переход:

При переносе findings между задачами переноси только stable IDs, не тексты.

- Если текущая задача не последняя: тот же critical finding без прогресса в двух последовательных review сквозь задачи -> авто WONT_FIX(DEFERRED_TO_TASK); явный отказ человека исправлять critical → STOPPED_BY_HUMAN; неразрешённое противоречие поведения/design -> HUMAN_ATTENTION. Иначе перенеси только BLOCKER IDs, оставь текущую задачу с active critical findings в OPEN, сделай checkpoint и выполни Task activation следующей задачи. Следующий worker — fresh implementer.
- Если текущая задача последняя: установи current_phase = Triage и перейди к §4.

### 4. Triage (Decide) — только для последней задачи

Лимиты: max 2 Review итерации на задачу -> авто WONT_FIX(DEFERRED) для оставшихся MINOR. max 3 RED verifier подряд -> HUMAN_ATTENTION. 4 critical review iterations -> HUMAN_ATTENTION.

Входное условие: current_task — последняя задача plan. Если условие не выполнено, допустимый переход определяет §3 Review: Task activation следующей задачи с fresh implementer.

- Нет active BLOCKER/MAJOR → обработай MINOR/human items.
- Есть active critical findings → Revise.
- Тот же critical finding без прогресса в двух последовательных review -> авто WONT_FIX(DEFERRED_TO_TASK); превышение лимитов выше -> HUMAN_ATTENTION.

MINOR можно исправить попутно только если в той же Implement/Revise-фазе исправляется BLOCKER/MAJOR и MINOR однозначно дешёвый: один файл, до 20 LOC, без public API/schema/test-architecture/research. Иначе нужно решение человека. MINOR больше трёх файлов, 100 LOC или меняющий test architecture нельзя брать FIX_NOW: только linked task или rejection.

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
- Для FIX_NOW запусти fresh reviser. При новом commit выполни только originating review axis; при unchanged HEAD не запускай checks или review. Максимум две review iterations; critical finding после лимита возвращает workflow в Human decisions.

### 5. Done

1. Если остались задачи OPEN-deferred, выполни их Review по правилам §3 (с учетом условного Review: docs-only/tests-only -> только нужные оси, иначе обе), fixed point каждой оси — её last_reviewed_head, для ни разу не ревьюившейся оси — общий BASE; на этом Review spec-reviewer дополнительно сверяет покрытие всей spec. При active critical findings перейди в Triage/Revise и вернись к этому шагу после их закрытия; если отложенные задачи остались OPEN-deferred, повтори их Review с обновлёнными fixed points. Иначе отметь отложенные задачи REVIEWED, а некритические findings make-up Review передай в Human decisions (§4).
2. Выполни verify-if-dirty (§2). При GREEN skip.
3. Если gate red, передай inventory fresh reviser. Для repair commit запиши affected_review_axes: Spec для изменения observable behavior, contracts или requirements; Standards для изменения структуры или conventions; пустой список допустим только для tests/build tooling, не меняющих product code. При неясной классификации запускай обе оси.
4. После repair commit выполни delta-review только по affected_review_axes и повтори этот gate. При unchanged HEAD -> HUMAN_ATTENTION. При повторном red без прогресса -> retry; max 3 RED подряд -> HUMAN_ATTENTION, иначе авто WONT_FIX.
5. После шага 1 review не запускай - каждый commit уже прошел delta-review или make-up Review, verifier HEAD не меняет.
6. Проверь ledger всего каскада: все задачи реализованы и проверены; нет OPEN, HUMAN_ATTENTION и active critical findings. Все carried findings получили review disposition.
7. Установи QUALITY = GREEN.
8. Установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши completion decision как pending_action, сделай checkpoint и спроси, выполнять ли merge в явно названную parent-ветку, tracker completion и cleanup task-worktree, если он был создан для этой задачи. Сохрани `merge_target_branch` в ledger. Без явного подтверждения не выполняй эти действия.
9. После подтверждения выполни фазу Merge reconciliation (§6).
10. Только после успешного fast-forward merge сформируй итоговый отчёт, опубликуй его в tracker и выполни подтверждённое completion задач каскада и specification ID при их наличии; сохраняй результаты каждого действия для recovery и не повторяй успешные. При ошибке checkpoint → HUMAN_ATTENTION. После успешного completion установи WORKFLOW_STATUS = COMPLETED и удали ledger.

### 6. Merge reconciliation

Выполняется только для подтверждённого `merge_target_branch`; task-ветка и parent-ветка должны быть явно различны. Merge = git rebase parent_tip + git push. Сложный worktree/MERGE_HEAD/backoff цикл вынесен в отдельный опциональный скилл `rr-merge`. Если rebase не прошел или ff-merge не прошел -> HUMAN_ATTENTION, не крути цикл. Tracker completion и cleanup task-worktree разрешены только после успешного fast-forward merge; при cleanup удали только task-worktree, созданный для этой задачи, никогда не трогай parent/default worktree.

## Conflicts

Если оси противоречат, примени более высокую severity. Если противоречие меняет behavior/design и не разрешается явным repo standard или spec, установи HUMAN_ATTENTION только для BLOCKER, конфликта поведения/design, или превышения лимитов выше. Остальное -> авто WONT_FIX(DEFERRED_TO_TASK) без паузы.
