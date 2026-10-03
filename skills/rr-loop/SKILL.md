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
- Цикл начинается в текущем checkout; рабочее окружение не меняется до merge reconciliation.
- Каждый worker получает только refs: spec_paths, fixed_point SHA, finding IDs, phase contract. НЕ вставляй в prompt содержимое spec, diff или историю цикла.
- Worker, который меняет код, коммитит свою фазу. Controller проверяет новый HEAD.
- Review начинается только после green verifier gate. Reviewers не запускают checks.
- QUALITY = GREEN: активных BLOCKER/MAJOR нет, final gate green, initial и обязательные delta-review завершены.
- Итоговый отчёт и cleanup ledger разрешены только при terminal status.

## Token Budget Rule

Никогда не вставляй в промпт worker'a содержимое файлов. Передавай только путь + SHA/диапазон. Worker читает сам нужный фрагмент. Diff вычисляй один раз в controller и передавай changed_files + range.

## Leaf-agents

- implementer — реализует spec, делает targeted checks, коммитит.
- verifier — read-only gate; возвращает один failure inventory.
- standards-reviewer — проверяет documented standards.
- spec-reviewer — проверяет соответствие spec.
- reviser — исправляет заданные finding IDs, делает targeted checks, коммитит.

Все пять named leaf-agents являются обязательной capability host. Если хотя бы одна требуемая роль или механизм subagents недоступны, установи WORKFLOW_STATUS = BLOCKED_UNSUPPORTED_HOST, перечисли отсутствующие capabilities, сохрани ledger и остановись.

## Ledger

LEDGER = .scratch/rr-loop/<branch>.md. Храни только: BASE, HEAD, last_full_green_head, last_reviewed_head, pending OPEN finding IDs. Текст spec/criteria не дублируй - только пути+хеши. Findings как JSONL append-only, не переписывай файл целиком. При recovery читай header + последние 50 строк.

Finding states: OPEN, FIXED, WONT_FIX(<reason>). AWAITING_REVIEW == OPEN до следующего Review. DEFERRED == WONT_FIX с linked task ID.

Делай atomic append checkpoint после фазы. Не переписывай ledger целиком. При recovery читай только YAML header + последние 50 строк лога.

## Запуск и recovery

1. Прочитай spec paths, выпиши только пути + ID критериев, не текст. Spec читает worker сам.
2. Зафиксируй branch и BASE = git rev-parse HEAD до правок.
3. Если для task/branch есть нетерминальный ledger, предложи продолжить его или явно сбросить. Без решения не удаляй файл и не повторяй реализацию.
4. Иначе создай ledger с WORKFLOW_STATUS = RUNNING, QUALITY = RED, current_phase = Implement.
5. До запуска первого worker, а при recovery — сразу после решения продолжить, выполни Tracker activation.
6. В текущем диалоге продолжай сразу после ответа человека. resume <ledger> нужен только для recovery в новом контексте.

### Tracker activation

Для исполняемой задачи с `task ID` прочитай `docs/agents/issue-tracker.md` и используй только описанный там способ получения workflow и перехода. Найди статус, означающий начало активной работы: `In Progress` либо его документированный аналог. Если задача уже находится в таком статусе, переход не повторяй; зафиксируй это в ledger.

Иначе переведи задачу этим transition в найденный статус до первого worker. Запиши в ledger исходный/целевой статусы, transition, timestamp и результат. Не подставляй названия статусов, API или команды из памяти. Если документа нет, workflow/status недоступен, активный статус не определён или transition не проходит, запиши tracker activation как `NOT_APPLICABLE` с причиной и продолжай workflow. При отсутствии `task ID` также запиши tracker activation как `NOT_APPLICABLE` и продолжай workflow.

## State machine

### 0. Preflight (30 сек, без агентов)

Controller сам проверяет: spec имеет Given/When/Then или acceptance criteria с цифрами/проверяемыми условиями? Можно ли написать тест до кода?
Если spec == "сделать красиво/быстро/лучше" без критериев -> WORKFLOW_STATUS=HUMAN_ATTENTION, не запускай implementer. Экономит весь цикл.

### 1. Implement

Запусти fresh implementer с {spec_paths, BASE_SHA, range BASE..HEAD, changed_files}. Текст acceptance criteria НЕ передавай - worker прочитает spec сам по пути. Прими отчёт с commit SHA, changed files, targeted checks и risks. Проверь, что HEAD совпадает с отчётом. После commit implementer контроллер запускает fmt/lint (ruff format/prettier/go fmt) детерминированно, без LLM. 30% standards findings - это пробелы/импорты.

Completion: worker commit существует, scope и checks записаны в ledger.

### 2. Verify-if-dirty: if HEAD==last_full_green_head -> skip

Единый гейт verify-if-dirty: если HEAD == last_full_green_head -> GREEN skip. Иначе запусти fresh verifier в режиме pre-review с одним relevant full suite.

При green запиши `last_full_green_head = HEAD`.

При red gate передай единый failure inventory fresh implementer до первого review или reviser после review. Repair не увеличивает review iteration. При repair commit вернись к этому gate; при unchanged HEAD -> HUMAN_ATTENTION. При повторном red без прогресса -> retry; max 3 RED подряд -> HUMAN_ATTENTION, иначе авто WONT_FIX.

Completion: verifier вернул green с exact commands/results.

### 3. Review

Условный Review:
- if changed_files == docs-only (.md/.mdx/.rst/docs/) -> verifier skip, standards-reviewer skip (только spec-reviewer если нужно)
- if changed_files == tests-only (*.test.*/__tests__/e2e) -> standards-reviewer skip
- иначе -> оба ревьюера параллельно как сейчас (spec + standards)
LOC не учитывай для решения какие оси запускать.

fixed point каждой оси — её last_reviewed_head, для первого шага — общий BASE. Controller передает worker'у {fixed_point SHA, spec_paths, diff_range}.

Повторная итерация:

- fixed point — last_reviewed_head соответствующей оси;
- запускай только оси, породившие активные findings;
- если active findings есть в обеих осях, запусти обе параллельно.

Ревьюеры возвращают только {type, evidence, location} без severity. Controller сам мапит type -> BLOCKER/MAJOR/MINOR детерминированно.

Сохраняй axis и evidence. Не мерджи две оси в один verdict. Completion: findings запущенных осей записаны, last_reviewed_head обновлён.

### 4. Triage (Decide)

Лимиты: max 2 Review итерации на задачу -> авто WONT_FIX(DEFERRED) для оставшихся MINOR. max 3 RED verifier подряд -> HUMAN_ATTENTION. 4 critical review iterations -> HUMAN_ATTENTION.

- Нет active BLOCKER/MAJOR → обработай MINOR/human items.
- Есть active critical findings → Revise.
- Тот же critical finding без прогресса в двух последовательных review -> авто WONT_FIX(DEFERRED_TO_TASK); превышение лимитов выше -> HUMAN_ATTENTION.

MINOR можно исправить попутно только если в той же revise-фазе есть BLOCKER/MAJOR и MINOR однозначно дешёвый: один файл, до 20 LOC, без public API/schema/test-architecture/research. Иначе нужно решение человека. MINOR больше трёх файлов, 100 LOC или меняющий test architecture нельзя брать FIX_NOW: только linked task или rejection.

### 4.1 Revise

Запусти fresh reviser с critical findings, указаниями человека и eligible cheap MINOR. Прими commit SHA либо подтверждение unchanged HEAD, per-finding disposition и targeted checks. Отклонённый BLOCKER всегда переводи в HUMAN_ATTENTION.

При новом commit запусти delta Review только по originating axes. При unchanged HEAD не запускай checks или review.

### 4.2 Human decisions

Задай все готовые вопросы одним batch. Для каждого finding покажи ID, severity, axis, location, evidence и proposed fix.

Варианты: FIX_NOW, создать linked task, REJECTED(<reason>). Для critical finding также прими correction/instruction. Явный отказ исправлять critical finding → STOPPED_BY_HUMAN, не COMPLETED.

Перед вопросом установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши pending_action и сделай checkpoint. После ответа запиши решения, очисти pending_action и верни WORKFLOW_STATUS = RUNNING, кроме terminal refusal.

Новые указания человека во время активного worker добавляй в user_directives; worker не прерывай. Примени directives перед следующим переходом фазы и отметь их consumed.

### 4.3 Execute minor decisions

- Создай согласованные linked tasks по docs/agents/issue-tracker.md и запиши IDs/URLs.
- Запиши human rejection с причиной.
- Для FIX_NOW запусти fresh reviser. При новом commit выполни только originating review axis; при unchanged HEAD не запускай checks или review. Максимум две review iterations; critical finding после лимита возвращает workflow в Human decisions.

### 5. Done

1. Выполни verify-if-dirty (см §2). При GREEN не запускай review.
2. Если gate red, передай inventory fresh reviser. Для repair commit запиши affected_review_axes: Spec для изменения observable behavior, contracts или requirements; Standards для изменения структуры или conventions; пустой список допустим только для tests/build tooling, не меняющих product code. При неясной классификации запускай обе оси.
3. После repair commit выполни delta-review только по affected_review_axes и повтори этот gate. При unchanged HEAD -> HUMAN_ATTENTION. При повторном red без прогресса -> retry; max 3 RED подряд -> HUMAN_ATTENTION, иначе авто WONT_FIX.
4. При green gate не запускай review: каждый commit после initial Review уже прошёл обязательный delta-review, а verifier не меняет HEAD.
5. Проверь ledger: нет OPEN, HUMAN_ATTENTION и active critical findings.
6. Установи QUALITY = GREEN.
7. Установи WORKFLOW_STATUS = WAITING_FOR_HUMAN, запиши completion decision как pending_action, сделай checkpoint и спроси, выполнять ли merge в явно названную parent-ветку, tracker completion и cleanup task-worktree, если он был создан для этой задачи. Сохрани `merge_target_branch` в ledger. Без явного подтверждения не выполняй эти действия.
8. После подтверждения выполни фазу Merge reconciliation (§6).
9. Только после успешного fast-forward merge установи WORKFLOW_STATUS = COMPLETED, сформируй итоговый отчёт, опубликуй его в tracker при наличии task ID и удали ledger.

### 6. Merge reconciliation

Выполняется только для подтверждённого `merge_target_branch`; task-ветка и parent-ветка должны быть явно различны. Merge = git rebase parent_tip + git push. Сложный worktree/MERGE_HEAD/backoff цикл вынесен в отдельный опциональный скилл `rr-merge`. Если rebase не прошел или ff-merge не прошел -> HUMAN_ATTENTION, не крути цикл. Tracker completion и cleanup task-worktree разрешены только после успешного fast-forward merge; при cleanup удали только task-worktree, созданный для этой задачи, никогда не трогай parent/default worktree.

## Conflicts

Если оси противоречат, примени более высокую severity. Если противоречие меняет behavior/design и не разрешается явным repo standard или spec, установи HUMAN_ATTENTION только для BLOCKER, конфликта поведения/design, или превышения лимитов выше. Остальное -> авто WONT_FIX(DEFERRED_TO_TASK) без паузы.
