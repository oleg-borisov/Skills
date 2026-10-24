---
name: rr-parallel-loop
description: Реализовать готовый граф задач в отдельных worktree, собрать integration и пройти review → final gate → merge.
---

# RR Parallel Loop

Оставайся primary-controller. Сначала прочитай [общий протокол](../rr-loop/references/protocol.md): роли, ledger, handoff, Review/Triage, Verify и cleanup обязательны. Rolling frontier запускает готовые задачи, пока другие workers работают; общий review/gate — на собранной integration, не на каждом ticket.

Один writer на worktree. Только controller последовательно интегрирует ветки. Review/verifier получают неподвижный integration HEAD. INTEGRATED означает доступность для зависимых задач, не GREEN/approval/tracker completion. Сохраняй чужие изменения; новые worktrees создавай от фиксированного SHA. Reset существующего checkout/force-cleanup запрещены.

## Ledger и claim

LEDGER_DIR = `.scratch/rr-parallel-loop/<integration-branch>/` в исходном checkout. Дополнительно к общему state: origin/integration/parent cwd/branch/tips; claim ref/owner/version; согласованный graph/prerequisite evidence/max_workers; tasks с dependencies, task_base/dependency_shas, write_scope, state, cwd/branch/head, текущим owner/liveness, dirty_snapshot_ref при передаче, актуальными handoff/standards refs, inclusion evidence и retry counters. Граф хранится один раз; global standards — объединение refs задач, не вторая копия. Незавершённые операции и результаты внешних действий — по общему протоколу, без dispatch/merge history.

До создания integration branch, tracker actions и dispatch захвати claim через exclusive create: `<git-common-dir>/rr-parallel-loop-claims/<key>.json`. key = SHA-256 UTF-8 канонического locator spec или primary task: нормализованный repo-relative path либо канонический tracker URL. Разреши aliases до захвата; неоднозначность → HUMAN_ATTENTION. Claim содержит locator/aliases, owner session ID, version = 1 и абсолютный ledger path; общий Git dir получи через Git.

Существующий/неполный claim — занято, не check-then-write и не перезапись по возрасту. Transfer/release/reset сериализуй эксклюзивной OS-блокировкой по key, внутри перечитай и сравни ожидаемые owner/version; transfer увеличивает version. Нужны доказанный выход прежнего controller/workers и отсутствие writers; неизвестная liveness → HUMAN_ATTENTION. Нет безопасного примитива → остановка соответствующей операции, без best-effort захвата. Claim действует в этом workflow; освобождай после COMPLETED либо согласованного STOP/reset без writers. Незавершённый ledger сохраняется и обнаруживается preflight.

При resume, неизвестном исходе операции, сбое worker или dirty передаче прочитай [recovery](../rr-loop/references/recovery.md).

## 0. План

1. Проверь нетерминальные ledgers/claim по spec/task/веткам до ранних выходов. Не запускай дубликат.
2. Прочитай spec и готовые tickets: criteria, статусы, комментарии, зависимости; tracker по `docs/agents/issue-tracker.md`. Все завершены → отчёт без workers. Нет готового графа → предложи rr-loop, не создавай tickets/новый workflow автоматически. Неопределённость criteria, циклы, неизвестные связи/статусы, конфликт источников или непроверяемый blocker → HUMAN_ATTENTION.
3. Сохрани origin, BASE = HEAD и parent target. У завершённых/внешних prerequisites нужен код в BASE или подтверждающее evidence: одного tracker-статуса недостаточно. Не придумывай продуктовые зависимости.
4. Назначь write_scope задач по tickets/standards/notes, включая tests/fixtures/generated outputs; пересекающиеся/неизвестные scopes и общие test resources сериализуй. Это lock, не зависимость spec. max_workers ограничь host slots/ресурсами; неизвестна независимость → 1. Подтверждённые особенности запуска checks сохрани один раз в plan/notes.
5. Покажи graph/scopes/max_workers/integration/parent и final review → final gate. Нужны согласованный план и test seams, если их требует TDD; уже данное согласование не повторяй. До него WAITING_FOR_HUMAN/pending_action. Изменение требований/графа требует нового согласования.
6. После согласования и claim создай integration worktree/ветку от BASE, имена по repo conventions/primary task ID. Выполни условный Exploration по протоколу. Dispatch задаёт абсолютный cwd, branch, expected HEAD и назначение; все worker операции только в этом cwd. Host не адресует worktrees → BLOCKED_UNSUPPORTED_HOST.

## 1. Schedule → Implement → Integrate

States: PENDING → RUNNING → READY_TO_INTEGRATE → INTEGRATED → REVIEWED. Неполный/blocked handoff state не продвигает. Frontier: PENDING с INTEGRATED/REVIEWED predecessors, подтверждённо завершёнными внешними blockers и свободным write_scope. Предпочитай разблокирующие больше задач, затем ID/path; работающий независимый worker не задерживает ready задачу.

До интеграции всех задач повторяй:

1. Примени directives, проверь blockers, создай task worktree/ветку от текущего integration HEAD; сохрани task_base/dependency_shas. Нет slots → событийное ожидание любого worker.
2. Tracker activation по протоколу; сохрани текущий dispatch intent/owner. Fresh implementer получает spec_refs ticket/общих контрактов, `{base_sha: task_base, head_sha: task_base}`, directives_path с write_scope и refs. Общий API/schema требует targeted checks затронутых consumers/fixtures, состав определяет worker.
3. Прими handoff: сверь cwd/branch/head, ancestry task_base, чистоту inputs, фактические Git paths со scope и успешные targeted checks. Blocker/scope request — правила ниже/recovery; отсутствие нового commit или неожиданные правки → HUMAN_ATTENTION. Проверенный завершённый scope → READY_TO_INTEGRATE.
4. Последовательно включай READY ветки: чистый integration, ожидаемый tip и точный source SHA; checkpoint с intent `{task,source_sha,integration_before}` → обычный merge без squash/rebase → inclusion evidence/integration HEAD/INTEGRATED. Source commit остаётся ancestor integration. Освободи scope, сверни завершённую операцию в task inclusion evidence.
5. Немедленно пересчитай frontier и заполни slots. Базы работающих workers не меняй; синхронизируй только при конфликте. Нет full gate/review на каждый ticket.

Frontier пуст, workers нет, PENDING остались → HUMAN_ATTENTION. Сообщение о продуктовой ошибке/нарушенном контракте → останови dispatch, безопасная остановка/recovery; известную поломку не распространяй.

### Расширение scope

До выхода за пути worker завершает turn с `blocker: {reason,paths}`, фактическим head/checks, сохраняя незавершённые правки без commit. Scope остаётся занят. Controller уточняет пути без вопроса, если criteria прежние и нет пересечений/неизвестных ресурсов: сохрани scope/intent, докажи выход turn/subprocesses, продолжи того же implementer в том же cwd/HEAD с delta directives. Ownership сохраняется; snapshot не нужен без иных writers, worker сверяет свои правки. Нет continuation → fresh worker через recovery.

Пересечение/неизвестные границы → останови dispatch/merges, дождись writers. Разрешены последовательные интеграции уже завершённых задач в прежнем подтверждённом scope для освобождения locks; затем пересчитай locks. Неразрешённое пересечение → HUMAN_ATTENTION; новые требования/graph требуют согласования, спорный результат не интегрируй.

### Конфликт

Controller прерывает только свой merge и восстанавливает чистый integration tip. Заморозь merges/dispatch; другие workers могут закончить ветки. Fresh implementer в завершённом task worktree получает pinned integration tip, spec/standards затронутых задач, task_base/task HEAD и directives: merge tip в task, product conflict repair, formatter/targeted checks/commit. После handoff проверь ancestry обоих родителей и повтори интеграцию. Две неудачные repair attempts задачи или конфликт требований → HUMAN_ATTENTION; иначе продолжи Schedule.

### Draft PR

После первой интеграции создай один draft PR, только если PR запрошен или обязателен tracker workflow и publication/push авторизованы. Проверь существующий PR/base/head; closing refs — по tracker. Иначе pending_action. Сохрани URL/result, не создавай повторно при recovery; прикрепи PR к диалогу, если host поддерживает. Draft не закрывает tickets и не становится ready до Done.

## 2. Freeze → Review → Revise → Verify

Все INTEGRATED → дождись выхода writers, зафиксируй integration HEAD. Первый Spec — full-spec всей spec, включая ранее завершённые задачи; Standards — по объединённым refs. Review/Triage/repair/лимиты по общему протоколу. Два нужных reviewer параллельно; CODE/formatter/merge во время review/gate запрещены.

Все обязательные coverage актуальны, OPEN/pending нет → tasks REVIEWED → финальный Verify всего плана по протоколу. REVIEWED не означает GREEN/tracker completion. RED repair в integration получает общий inventory и refs затронутого scope; новый commit всегда проходит delta Review → Triage → новый gate, без нового Schedule. Для технического BLOCKED используй recovery; незавершённый gate не GREEN.

## 3. Done

Все задачи интегрированы/REVIEWED, актуальны full-spec + последующие delta/Standards, нет OPEN/pending и применим финальный GREEN/NOT_APPLICABLE → QUALITY = GREEN. Выполненные проверки/reviews на тех же входах не повторяй.

Далее прочитай [completion](../rr-loop/references/completion.md): авторизованный final merge, tracker actions, cleanup worktrees, отчёт, освобождение claim и удаление всего LEDGER_DIR без архивации. До успешного merge/согласованных actions COMPLETED запрещён.
