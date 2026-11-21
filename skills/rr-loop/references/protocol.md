# Общий протокол rr workflows

Обязателен для primary-controller всех трёх rr skills. Порядок задач/интеграции — в вызывающем SKILL.md.

## Роли и контекст

Workers — прямые дети primary. Обязательны implementer, verifier, spec-reviewer, standards-reviewer, reviser; scout опционален. Нет named role/subagents → BLOCKED_UNSUPPORTED_HOST, без подмены роли. Controller читает spec/Git metadata/ответы CLI; product code/checks/formatter — workers, до dispatch controller product code не исследует. Primary уже изменил product code вместо worker → HUMAN_ATTENTION.

Используй установленного агента нужной роли. Явно указанная человеком модель имеет приоритет над моделью профиля; при её смене сохраняй полный контракт роли, ограничения и Output. Если host не поддерживает override модели установленного профиля, controller передаёт полный текст установленного leaf-контракта fresh subagent запрошенной модели. Это адаптация только для явно выбранной модели, а не замена отсутствующего агента. Имя задачи, пересказ роли и ссылка на controller skill/protocol полный контракт не заменяют.

Новая задача/фаза — fresh worker заданной роли без истории controller. Передавай только входы роли, refs и delta directives. Общие входы `{base_sha,head_sha}`; paths worker получает через Git. Spec refs `{path,sections,criterion_ids}` включают требования задачи, общие контракты продукта и согласованные test seams; worker читает файлы из рабочего дерева, tracker spec сохрани snapshot-файлом под LEDGER_DIR. Standards — список путей: их находит implementer, включая вложенные инструкции, CLI объединяет в `standards`. Неизвестные standards не означают отсутствие правил.

Controller SKILL.md, protocol/recovery/completion остаются у controller и не передаются worker для исполнения. Если задача меняет или проверяет сами workflow assets, передавай нужные файлы/секции как объект задачи.

Handoff — один финальный JSON роли. Передай его CLI одним вызовом: `RR handoff` (implementer, reviser, scout), `RR review` (reviewers), `RR gate` (verifier). Вызов проверяет контракт и Git metadata, сохраняет JSON и продвигает state; повтор того же JSON ничего не меняет. `stop` либо `problems` в ответе → HUMAN_ATTENTION с этой причиной, кроме технически незавершённой попытки по recovery. Worker acceptance не закрывает findings. Пересказы spec/diff, progress, копии файлов и полные логи в контекст не передавай. Жди завершения worker одним ожиданием с максимальным timeout, который допускает host; короткие повторные ожидания и чтение прогресса запрещены, timeout не доказывает сбой. Успешные checks/reviews на прежних входах не повторяй.

Exploration: один scout только для общих нескольким workers questions; локальные вопросы — implementer. Вход `{spec_refs,head_sha,questions,notes_dir}`, notes_dir под LEDGER_DIR. Нет questions/scout/доступа → NOT_APPLICABLE с причиной. Handoff — refs notes, sources сверяет worker.

Tracker: API/статусы только из `docs/agents/issue-tracker.md`. До первого worker задачи активируй In Progress/аналог; уже активное не повторяй. Нет ID/интеграции/transition или ошибка activation → NOT_APPLICABLE с причиной; tickets/blockers всё равно проверяй.

## Запуск без остановок

Первое действие — `RR init`, до чтения tickets и ранних выходов. Отказ из-за существующего запуска → предложи resume/reset; без решения не удаляй и не повторяй реализацию. Ранний выход без работы → `RR cleanup` нетронутого журнала.

Вызов навыка — согласие человека на завершающие действия: merge в цель при quality GREEN и чистом rebase, tracker completion и удаление созданных запуском worktrees. Отказ из аргументов сохрани при init (`consent.merge=false`, `consent.tracker=false`, `consent.worktrees=false`): такое действие требует вопроса в Done. Цель merge передай в `--target`: из аргументов либо ветка, от которой controller сам создал task-ветку. Текущая ветка — task-ветка, если её имя содержит ID задачи запуска; цель при этом не названа → один вопрос до первого worker. Push и перевод PR в ready — только когда их требует repo workflow или tracker; слияние PR остаётся за человеком/CI. План и ход работы показывай без ожидания подтверждения; явная directive человека имеет приоритет над умолчаниями.

`status`: RUNNING; WAITING_FOR_HUMAN с pending_action — конкретный вопрос, после ответа RUNNING и продолжение в текущем диалоге; HUMAN_ATTENTION — остановка, которую controller не вправе снять сам: сообщи причину и вопросы; STOPPED_BY_HUMAN — STOP исполняй сразу; COMPLETED. HUMAN_ATTENTION и STOP сохраняют данные и запрещают новые writers. Неясность требований всегда решает человек, не controller.

## Snapshot ledger

State, handoffs и findings меняет только controller и только через CLI: RR = `python3 <каталог skill rr-loop>/scripts/rr.py` (Windows: `python`). Нет Python 3.9+ → BLOCKED_UNSUPPORTED_HOST. Вывод — одна строка JSON; код 1 — отказ: причина в stderr либо `problems`/`stop` в JSON. state.json целиком не читай и вручную не правь. JSON worker передавай в stdin; в Windows PowerShell 5.1 — через `--file`: pipe портит не-ASCII.

- `RR init --ledger <LEDGER_DIR> [--cwd <cwd>] [--target <ветка>] task=<ID> spec=<locator> [path=json…]` — новый запуск: base = head = HEAD, status RUNNING, цель в `merge_target`, `.scratch/` в Git exclude. Отказ при существующем ledger либо незавершённом запуске той же task/spec в любом worktree репозитория. Locator spec — repo-relative path либо tracker URL.
- `RR get --ledger <dir> [path…]` и `RR set --ledger <dir> path=json… [--delete path]` — нужные поля и атомарная запись; path через точку. `quality` (UNVERIFIED|GREEN) вычисляет CLI для текущего head; status COMPLETED требует GREEN; `head=<rev>` записывай после rebase/merge вне worker.
- `RR handoff --ledger <dir> --role implementer|reviser|scout [--task <ID>] [--ids F1,F2] [--scope <путь|glob>…]` — сверяет HEAD, чистоту, ancestry, новый commit и пути против write_scope; продвигает head запуска либо задачи, объединяет standards, по `--ids` reviser считает итерации repair. Blocker допускает отсутствие commit и dirty.
- `RR review --ledger <dir> --role spec-reviewer|standards-reviewer [--ids F1,F2] [--full-spec]` — сверяет head и ось IDs; атомарно: dispositions, repaired, новые IDs с severity, coverage оси; возвращает fixed/open/new/critical/quality. `RR review --axis <spec|standards> --skip <reason>` — ось NOT_APPLICABLE для текущего head.
- `RR gate --ledger <dir>` — verdict verifier, счётчик RED, последний полный GREEN; возвращает ref handoff для gate_path. `RR gate --reuse [<proof>]` и `RR gate --not-applicable <reason>` — решения controller по verify.
- `RR finding --ledger <dir> list | severity <IDs> <BLOCKER|MAJOR|MINOR> | close <IDs> <reason> | leave <IDs>` — severity, закрытие с причиной, оставленные MINOR.
- `RR integrate --ledger <dir> --task <ID>` — rr-parallel-loop: merge READY задачи в integration.
- `RR verify --cwd <cwd> --head <sha> [--base <sha>] [--new-commit] [--scope <путь|glob>…]` — сверка Git вне handoff.
- `RR cleanup --ledger <dir>` — удаление каталога запуска при status COMPLETED либо нетронутого запуска.

LEDGER_DIR = `<checkout>/.scratch/<workflow>/<run>`, run — имя ветки с `-` вместо `/`. Каталог принадлежит одному запуску: handoffs, notes и управляемые логи — под ним, штатные build outputs — на своих местах; workers получают абсолютные пути. Лимиты итераций и RED ведёт CLI (`LIMITS` в rr.py).

Своими path храни только актуальное: task/spec_refs/branch, current_phase, pending_action, действующие constraints и неприменённые directives, текущих workers с liveness, retries технических попыток. Внешнее действие: intent до вызова, result/ID после; успешные results сохраняй до конца запуска для защиты от повторов. Применённые указания удаляй тем же `RR set`.

findings — map OPEN записей по stable ID `{axis,severity,location,requirement_ref|standard_ref,evidence,fix}`. findings_path = абсолютный state.json: worker читает заданные IDs и map repaired своих файлов. FIXED ставит только reviewer через `RR review`. `RR finding close` — решение человека с reason/linked task ID либо дубль записи; `RR finding leave` — оставленные MINOR для итога.

Resume, неизвестный исход операции, сбой worker или смена владельца незакоммиченных правок → прочитай [recovery](recovery.md).

## Фазы

При входе в Review → Triage → Revise прочитай [review](review.md); перед Verify и завершением — [verify](verify.md). Читай файл при входе в фазу, не заранее; после сжатия контекста перечитай файл текущей фазы.
