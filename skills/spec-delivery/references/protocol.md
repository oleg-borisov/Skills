# Протокол spec-delivery

Обязателен для primary-controller. Порядок фаз — в [SKILL.md](../SKILL.md).

## Роли и контекст

Workers — прямые дети primary. Обязательны implementer, verifier, spec-reviewer, standards-reviewer, reviser; scout опционален. Controller читает spec/Git metadata/ответы CLI; product code/checks/formatter — workers, до dispatch controller product code не исследует. Primary уже изменил product code вместо worker → HUMAN_ATTENTION.

Для каждой попытки передай исполнителю актуальные входы роли. При свежем запуске передай абсолютный путь к `roles/<роль>.md` относительно этого протокола и потребуй первым шагом прочитать файл и следовать контракту, включая ограничения и Output. Если файл нечитаем, исполнитель останавливается до действий по задаче и сообщает путь и ошибку. Вызови именованный профиль роли, если он доступен. Иначе используй встроенный универсальный тип субагента хоста. Если именованный профиль не запустился, сначала подтверди отсутствие живого исполнителя, затем используй универсальный тип. Если хост не может запустить универсального субагента и нужный профиль недоступен, остановись с BLOCKED_UNSUPPORTED_HOST. Фазы исполняются только в дочернем контексте.

Если исполнитель сообщил, что путь нечитаем, после подтверждения его выхода прочитай контракт и передай его полный текст свежему универсальному субагенту с теми же входами. Если файл недоступен контроллеру или универсальный тип недоступен, обработай сбой по recovery. На универсальном типе действуют текстовые ограничения контракта. Модель и reasoning effort задаёт хост.

Новая задача/фаза — fresh worker заданной роли без истории controller. Исключения описаны в [Review](review.md#продолжение-исполнителей), [Graph](graph.md) и [Recovery](recovery.md). Общие входы `{base_sha,head_sha}` и delta directives. Пути worker получает через Git. Spec refs `{path,sections,criterion_ids}` включают требования задачи, общие контракты продукта и согласованные test seams. Worker читает файлы из рабочего дерева, tracker spec сохрани snapshot-файлом под LEDGER_DIR. Standards — список путей, которые находит implementer, включая вложенные инструкции. CLI объединяет их в `standards`. Неизвестные standards не означают отсутствие правил.

Controller SKILL.md, protocol/recovery/completion остаются у controller и не передаются worker для исполнения. Если задача меняет или проверяет сами workflow assets, передавай нужные файлы/секции как объект задачи.

Handoff — один финальный JSON роли. Передай его CLI одним вызовом: `ledger.py handoff` (implementer, reviser, scout), `ledger.py review` (reviewers), `ledger.py gate` (verifier). Вызов проверяет контракт и Git metadata, сохраняет JSON и продвигает state; повтор того же JSON ничего не меняет. `stop` либо `problems` в ответе → HUMAN_ATTENTION с этой причиной, кроме технически незавершённой попытки по recovery. Worker acceptance не закрывает findings. Пересказы spec/diff, progress, копии файлов и полные логи в контекст не передавай. Жди завершения worker одним ожиданием с максимальным timeout, который допускает host; короткие повторные ожидания и чтение прогресса запрещены, timeout не доказывает сбой. Успешные checks/reviews на прежних входах не повторяй.

Exploration: один scout только для общих нескольким workers questions; локальные вопросы — implementer. Вход `{spec_refs,head_sha,questions,notes_dir}`, notes_dir под LEDGER_DIR. Нет questions или доступного субагента для scout → NOT_APPLICABLE с причиной. Handoff — refs notes, sources сверяет worker.

Tracker: API/статусы только из `docs/agents/issue-tracker.md`. До первого worker задачи активируй In Progress/аналог; уже активное не повторяй. Нет ID/интеграции/transition или ошибка activation → NOT_APPLICABLE с причиной; tickets/blockers всё равно проверяй.

## Запуск без остановок

Первое действие — `ledger.py init`, до чтения tickets и ранних выходов. Отказ из-за существующего запуска → предложи resume/reset; без решения не удаляй и не повторяй реализацию. Ранний выход без работы → `ledger.py cleanup` нетронутого журнала.

Вызов навыка — согласие человека на завершающие действия: merge в цель при quality GREEN по правилам выбранного режима, tracker completion и удаление созданных запуском worktrees. Отказ из аргументов сохрани при init (`consent.merge=false`, `consent.tracker=false`, `consent.worktrees=false`): такое действие требует вопроса в Done. Известную при init цель передай в `--target`, иначе запиши в `merge_target` до первого worker. Текущая ветка — task-ветка, если её имя содержит ID задачи запуска. Push и перевод PR в ready — только когда их требует repo workflow или tracker; слияние PR остаётся за человеком/CI. План и ход работы показывай без ожидания подтверждения; явная directive человека имеет приоритет над умолчаниями.

`status`: RUNNING; WAITING_FOR_HUMAN с pending_action — конкретный вопрос, после ответа RUNNING и продолжение в текущем диалоге; HUMAN_ATTENTION — остановка, которую controller не вправе снять сам: сообщи причину и вопросы; STOPPED_BY_HUMAN — STOP исполняй сразу; COMPLETED. HUMAN_ATTENTION и STOP сохраняют данные и запрещают новые writers. Неясность требований всегда решает человек, не controller.

## Snapshot ledger

State, handoffs и findings меняет только controller и только через CLI. Команды вида `ledger.py <команда>` запускай как `python3 "<каталог skill spec-delivery>/scripts/ledger.py" <команда>` (Windows: `python`). Нет Python 3.9+ → BLOCKED_UNSUPPORTED_HOST. Вывод — одна строка JSON; код 1 — отказ: причина в stderr либо `problems`/`stop` в JSON. state.json целиком не читай и вручную не правь. JSON worker передавай в stdin; в Windows PowerShell 5.1 — через `--file`: pipe портит не-ASCII.

- `ledger.py init --ledger <LEDGER_DIR> [--cwd <cwd>] [--target <ветка>] task=<ID> spec=<locator> [path=json…]` — новый запуск: base = head = HEAD, status RUNNING, цель в `merge_target`, `.scratch/` в Git exclude. Отказ при существующем ledger либо незавершённом запуске той же task/spec в любом worktree репозитория. Locator spec — repo-relative path либо tracker URL.
- `ledger.py get --ledger <dir> [path…]` и `ledger.py set --ledger <dir> path=json… [--delete path]` — нужные поля и атомарная запись; path через точку. `quality` (UNVERIFIED|GREEN) вычисляет CLI для текущего head; status COMPLETED требует GREEN; `head=<rev>` записывай после rebase/merge вне worker. Смена `review_target` или переход на HEAD вне истории прежнего кандидата сбрасывает coverage обеих осей. Зафиксированный `review_target` должен входить в историю нового HEAD.
- `ledger.py handoff --ledger <dir> --role implementer|reviser|scout [--task <ID>] [--ids F1,F2] [--scope <путь|glob>…]` — сверяет HEAD, чистоту, ancestry, новый commit и пути против write_scope; продвигает head запуска либо задачи, объединяет standards, по `--ids` reviser считает итерации repair. Blocker допускает отсутствие commit и dirty.
- `ledger.py review --ledger <dir> --prepare [--axis spec|standards]` — готовит входы reviewers и возвращает пути к временным файлам. State не меняет. Порядок работы с файлами — в [Review](review.md#review).
- `ledger.py review --ledger <dir> --role spec-reviewer|standards-reviewer [--ids F1,F2] [--full-spec]` — сверяет head, base от зафиксированной цели и ось IDs; атомарно: dispositions, repaired, новые IDs с severity, coverage оси; возвращает fixed/open/new/critical/quality. `ledger.py review --axis <spec|standards> --skip <reason>` — ось NOT_APPLICABLE. `ledger.py review --ledger <dir> --triage` — лимиты по итогам принятого раунда.
- `ledger.py gate --ledger <dir>` — verdict verifier, счётчик RED, последний полный GREEN; возвращает ref handoff для gate_path. `ledger.py gate --reuse [<proof>]` и `ledger.py gate --not-applicable <reason>` — решения controller по verify.
- `ledger.py finding --ledger <dir> list | severity <IDs> <BLOCKER|MAJOR|MINOR> | close <IDs> <reason> | leave <IDs>` — severity, закрытие с причиной, оставленные MINOR.
- `ledger.py integrate --ledger <dir> --task <ID>` — режим graph: merge READY задачи в integration.
- `ledger.py verify --cwd <cwd> --head <sha> [--base <sha>] [--new-commit] [--scope <путь|glob>…]` — сверка Git вне handoff.
- `ledger.py cleanup --ledger <dir>` — удаление каталога запуска при status COMPLETED либо нетронутого запуска.

Каталог ledger принадлежит одному запуску: handoffs, notes и управляемые логи — под ним, штатные build outputs — на своих местах; workers получают абсолютные пути. Лимиты итераций и RED ведёт CLI (`LIMITS` в ledger.py).

Своими path храни только актуальное: task/spec_refs/branch, current_phase, pending_action, действующие constraints и неприменённые directives, текущих workers с liveness, retries технических попыток. Внешнее действие: intent до вызова, result/ID после; успешные results сохраняй до конца запуска для защиты от повторов. Применённые указания удаляй тем же `ledger.py set`.

findings — map OPEN записей по stable ID `{axis,severity,location,requirement_ref|standard_ref,evidence,fix}`. Reviewers получают выборку через `review --prepare`. Для implementer и reviser передай абсолютные `ledger_cli`, `ledger_dir` и нужные `finding_ids`. Они используют read-only `ledger.py get` с `findings.<ID>` и при необходимости `repaired.<file>`; после `repaired.` передаётся буквальный путь с точками. FIXED ставит только reviewer через `ledger.py review`. `ledger.py finding close` — решение человека с reason/linked task ID либо дубль записи. `ledger.py finding leave` — оставленные MINOR для итога.

Resume, неизвестный исход операции, сбой worker или смена владельца незакоммиченных правок → прочитай [recovery](recovery.md).

## Фазы

При входе в Review → Triage → Revise прочитай [review](review.md); перед Verify и завершением — [verify](verify.md). Читай файл при входе в фазу, не заранее; после сжатия контекста перечитай файл текущей фазы.
