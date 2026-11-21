# Общий протокол rr workflows

Обязателен для primary-controller всех трёх rr skills. Порядок задач/интеграции — в вызывающем SKILL.md.

## Роли и контекст

Workers — прямые дети primary. Обязательны implementer, verifier, spec-reviewer, standards-reviewer, reviser; scout опционален. Нет named role/subagents → BLOCKED_UNSUPPORTED_HOST, без подмены роли. Controller читает spec/Git metadata/handoffs; product code/checks/formatter — workers. Primary уже изменил product code вместо worker → HUMAN_ATTENTION.

Используй установленного агента нужной роли. Явно указанная человеком модель имеет приоритет над моделью профиля; при её смене сохраняй полный контракт роли, ограничения и Output. Если host не поддерживает override модели установленного профиля, controller передаёт полный текст установленного leaf-контракта fresh subagent запрошенной модели. Это адаптация только для явно выбранной модели, а не замена отсутствующего агента. Имя задачи, пересказ роли и ссылка на controller skill/protocol полный контракт не заменяют.

Новая задача/фаза — fresh worker заданной роли без истории controller. Передавай только входы роли, refs и delta directives. Общие входы `{base_sha,head_sha}`; optional changed_files_path — один manifest на диапазон. Без него worker получает paths через Git. Spec refs `{path,sections,criterion_ids,source_sha?|hash?}`: source_sha закрепляет файл в Git tree, hash сырых байтов — изменяемый/внешний источник; tracker spec фиксируй snapshot. Product files/PNG отдельно не хешируй. Standards находит implementer, включая вложенные инструкции; переиспользуй refs, дополняй для нового scope. Неизвестные standards не означают отсутствие правил.

Workers получают контракт роли и входы задачи; spec_refs содержат требования задачи и общие контракты продукта. Controller SKILL.md, protocol/recovery/completion остаются у controller и не передаются worker для исполнения. Если задача меняет или проверяет сами workflow assets, передавай нужные файлы/секции как объект задачи.

Handoff — один JSON роли; controller сохраняет его один раз через `RR handoff`, state содержит ref/поля перехода. Сначала handoff, затем `RR set`/`RR review`, затем удаление ненужного прежнего файла: crash не должен менять evidence старого checkpoint. Git metadata handoff сверяй одним `RR verify`. Пересказы spec/diff, progress, пустые optional поля, копии файлов и полные логи в контекст не передавай. Читай только изменившийся результат/нужные поля state. Жди завершения worker одним ожиданием с максимальным timeout, который допускает host; короткие повторные ожидания и чтение прогресса запрещены, timeout не доказывает сбой. Workers не присылают промежуточных сообщений: единственный результат — финальный JSON. Успешные checks на прежних входах не повторяй.

Exploration: один scout только для общих нескольким workers questions; локальные вопросы — implementer. Вход `{spec_refs,head_sha,questions,notes_dir}`, notes_dir под LEDGER_DIR. Нет questions/scout/доступа → NOT_APPLICABLE с причиной. Handoff — refs notes, sources сверяет worker.

Tracker: API/статусы только из `docs/agents/issue-tracker.md`. До первого worker задачи активируй In Progress/аналог; уже активное не повторяй. Нет ID/интеграции/transition или ошибка activation → NOT_APPLICABLE с причиной; tickets/blockers всё равно проверяй.

## Snapshot ledger

State, handoffs и findings меняет только controller и только через CLI: RR = `python3 <каталог skill rr-loop>/scripts/rr.py` (Windows: `python`). Нет Python 3.9+ → BLOCKED_UNSUPPORTED_HOST. Вывод — одна строка JSON; код 1 — отказ с причиной в stderr. state.json целиком не читай и вручную не правь.

- `RR init --ledger <LEDGER_DIR> [--cwd <cwd>] [path=json…]` — новый запуск: base = head = HEAD, status RUNNING, quality UNVERIFIED, `.scratch/` в Git exclude. Отказ при существующем ledger → resume/reset.
- `RR get --ledger <dir> [path…]` и `RR set --ledger <dir> path=json… [--delete path]` — нужные поля и атомарная запись; path через точку.
- `RR handoff --ledger <dir> --role <роль> --name <имя>` с финальным JSON worker в stdin — проверка контракта роли, сохранение, сводка с ref. Отказ → восстановление handoff по recovery либо HUMAN_ATTENTION.
- `RR verify --cwd <cwd> --head <sha> [--base <sha>] [--new-commit] [--scope <путь|glob>…]` — HEAD, чистота, ancestry, изменённые пути против write_scope.
- `RR review --ledger <dir> --handoff <имя> [--ids F1,F2] [--full-spec]` — атомарно: dispositions заданных IDs, repaired, новые IDs с severity, coverage оси; возвращает fixed/open/new/critical.
- `RR finding --ledger <dir> list | severity <ID> <BLOCKER|MAJOR|MINOR> | close <ID> <reason>` — изменение severity и закрытие по решению человека.
- `RR cleanup --ledger <dir>` — удаление каталога запуска при status COMPLETED.

Поля CLI: status, quality, base, head, findings, next_finding_id, repaired, axes.<spec|standards>.{last_reviewed_head,full_spec_reviewed_head}, human_dispositions; остальное состояние храни своими path. Handoffs/refs/manifests/notes/inventory и управляемые логи — под LEDGER_DIR, штатные build outputs — на своих местах. Каталог принадлежит одному запуску; workers получают абсолютные пути.

Храни только актуальное состояние:

- workflow/task, cwd/branch, BASE/HEAD, source/standards refs, merge target. HEAD актуален; прошлые SHA — только у своего evidence.
- WORKFLOW_STATUS/QUALITY (UNVERIFIED|GREEN)/current_phase, pending_action, действующие согласования/constraints, неприменённые directives. Применённые указания удаляй, сохраняй лишь продолжающие действовать constraints.
- Текущие workers/ownership, pending operations, нужные handoff/validation refs. Внешнее действие: intent до вызова, result/ID после; успешные results сохраняй до конца для защиты от повторов. Завершённая dispatch history/interim/phase_results не нужна.
- По осям: last_reviewed_head и актуальное coverage (range/reason для NOT_APPLICABLE), full_spec_reviewed_head, текущий gate ref/verdict. last_full_green_head и отдельный green_ref сохраняют последний полный GREEN с plan/log evidence даже после RED; proof reuse связывает его с новым HEAD. Coverage сворачивай до покрытого диапазона, не истории итераций.
- Counters: consecutive_red, critical/minor repair iterations, no_progress каждого OPEN critical (в записи finding); retries конкретного workflow.
- findings: map OPEN записей по stable ID `{axis,severity,head,location,requirement_ref|standard_ref,evidence,fix}`; при необходимости worker rejection/решение. findings_path = абсолютный state.json, worker читает только заданные IDs. IDs назначает `RR review`.
- Компактные human dispositions/linked task IDs для итога. Reviewer FIXED удаляет запись атомарно с coverage и оставляет `{id,fix}` в map repaired по файлу location до конца запуска — это делает `RR review`. WONT_FIX закрывай `RR finding close` только после решения человека с reason/созданным linked task ID. Worker acceptance/отсутствие повторного finding ID не закрывают.

Закрытые findings, JSONL/seq, старые inputs/interim, checks поверх handoff, product hashes, история фаз и пустые optional поля не нужны. Устаревшие файлы удаляй без чтения после checkpoint; evidence активных refs сохраняй.

До нового запуска ищи нетерминальный ledger workflow по task/spec/связанным веткам/worktrees. Предложи resume/reset; без решения не удаляй/не повторяй реализацию. Конфликт владельцев/ledger → HUMAN_ATTENTION. Recovery сверяет identity/sources/BASE/HEAD/phase/pending_action/liveness и операции; затем продолжает checkpoint. Неизвестный исход сверяй с сервисом, успешное не повторяй; commit без checkpoint — с handoff. Необъяснимый drift → HUMAN_ATTENTION. Старый формат при resume сведи к текущему snapshot OPEN/coverage/counters/refs, без повторения подтверждённых действий и архива истории.

До вопроса WAITING_FOR_HUMAN/pending_action; после ответа RUNNING и продолжение в текущем диалоге. STOP исполняй сразу; HUMAN_ATTENTION/STOP сохраняют данные и запрещают новые writers.

## Фазы

При входе в Review → Triage → Revise прочитай [review](review.md); перед финальным Verify и завершением — [verify](verify.md). Читай файл при входе в фазу, не заранее; после сжатия контекста перечитай файл текущей фазы.
