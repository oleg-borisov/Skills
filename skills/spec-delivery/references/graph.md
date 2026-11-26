# Реализация графа задач

Вход: `mode=graph`, BASE и каталог журнала уже зафиксированы по [SKILL.md](../SKILL.md).

Один writer на worktree. Только controller последовательно интегрирует ветки. Review/verifier получают неподвижный integration HEAD. INTEGRATED означает доступность для зависимых задач, не GREEN/approval/tracker completion. Сохраняй чужие изменения; новые worktrees создавай от фиксированного SHA. Reset существующего checkout/force-cleanup запрещены.

## Ledger

Дополнительно к общему state: `integration.{cwd,branch}`, parent, max_workers, `tasks.<ID>.{deps,write_scope,state,cwd,branch,base,head}`, текущий owner/liveness задачи и evidence завершённых prerequisites. Граф хранится один раз. Head запуска — integration HEAD.

## 0. План

1. Сверь criteria, test seams, статусы, комментарии и зависимости задач по spec и tracker. Циклы, неизвестные связи/статусы, конфликт источников или непроверяемый blocker → HUMAN_ATTENTION. У завершённых/внешних prerequisites нужен код в BASE или подтверждающее evidence: одного tracker-статуса недостаточно. Сохрани их evidence отдельно; в `tasks` и внутренних `deps` оставь только задачи, которые ещё нужно выполнить. Все задачи завершены → отчёт без workers и cleanup нетронутого журнала по протоколу.
2. По умолчанию `max_workers` равен максимальному числу исполнителей, которое поддерживают доступные слоты хоста и ресурсы. Если пользователь задал лимит, используй его в пределах этой ёмкости. Назначь write_scope задач по tickets/standards/notes, включая tests/fixtures/generated outputs. Сериализуй задачи с пересекающимися/неизвестными scopes или общими test resources через locks при dispatch. Подтверждённые особенности запуска checks сохрани один раз в plan/notes.
3. Host не адресует worktrees → BLOCKED_UNSUPPORTED_HOST. Цель merge (parent) — из аргументов либо текущая ветка исходного checkout. Создай integration worktree/ветку от BASE, имена по repo conventions/primary task ID; одним `ledger.py set` сохрани integration, parent, merge_target, max_workers и tasks в PENDING. Покажи graph/scopes/max_workers/integration/parent и работай без ожидания подтверждения; изменение требований/графа по ходу решает человек. Выполни условный Exploration по протоколу. Dispatch задаёт абсолютный cwd, branch, expected HEAD и назначение; все worker операции только в этом cwd.

## 1. Schedule → Implement → Integrate

Состояния `tasks.<ID>.state`: PENDING → RUNNING → READY_TO_INTEGRATE → INTEGRATED → REVIEWED. Неполный/blocked handoff state не продвигает. Frontier: PENDING с INTEGRATED/REVIEWED predecessors (`unblocked` в ответе `ledger.py integrate`), подтверждённо завершёнными внешними blockers и свободным write_scope. Предпочитай разблокирующие больше задач, затем ID/path; работающий независимый worker не задерживает ready задачу.

При первом dispatch и после каждой интеграции заполняй доступные slots задачами из frontier в пределах `max_workers`. До интеграции всех задач повторяй:

1. Примени directives, проверь blockers, создай task worktree/ветку от текущего integration HEAD; одним `ledger.py set` сохрани cwd/branch/base задачи, owner и RUNNING. Нет slots → событийное ожидание любого worker.
2. Tracker activation по протоколу. Fresh implementer получает spec_refs ticket/общих контрактов, `{base_sha: base, head_sha: base}` задачи, directives_path с write_scope и refs. Общий API/schema требует targeted checks затронутых consumers/fixtures, состав определяет worker.
3. Прими handoff: `ledger.py handoff --role implementer --task <ID>` сверяет cwd/head, ancestry base, чистоту и пути со scope. Успех → READY_TO_INTEGRATE; blocker возвращает RUNNING и блокирует интеграцию, включая conflict repair. Scope request — правила ниже/recovery.
4. Последовательно включай READY задачи: `ledger.py integrate --task <ID>` — обычный merge точного head задачи в чистый integration → INTEGRATED, новый head запуска; scope свободен. `conflict` → раздел ниже.
5. Немедленно пересчитай frontier. Базы работающих workers не меняй; синхронизируй только при конфликте. Нет gate/review на каждый ticket.

Frontier пуст, workers нет, PENDING остались → HUMAN_ATTENTION. Сообщение о продуктовой ошибке/нарушенном контракте → останови dispatch, безопасная остановка/recovery; известную поломку не распространяй.

### Расширение scope

До выхода за пути worker завершает turn с `blocker: {reason,paths}`, фактическим head/checks, сохраняя незавершённые правки без commit. Scope остаётся занят. Controller уточняет пути без вопроса, если criteria прежние и нет пересечений/неизвестных ресурсов: обнови write_scope задачи, докажи выход turn/subprocesses, продолжи того же implementer в том же cwd/HEAD с delta directives. Нет continuation → fresh worker со сменой владельца по recovery.

Пересечение/неизвестные границы → останови dispatch/merges, дождись writers. Разрешены последовательные интеграции уже завершённых задач в прежнем подтверждённом scope для освобождения locks; затем пересчитай locks. Неразрешённое пересечение → HUMAN_ATTENTION; новые требования/graph решает человек, спорный результат не интегрируй.

### Конфликт

`ledger.py integrate` сам прерывает merge и оставляет чистый integration tip. Заморозь merges/dispatch; другие workers могут закончить ветки. Fresh implementer в завершённом task worktree получает pinned integration tip, spec/standards затронутых задач, base/head задачи и directives: merge tip в task, product conflict repair, formatter/targeted checks/commit. Его handoff принимай с `--scope "*"`: merge приносит чужие пути; затем повтори `ledger.py integrate`. Две неудачные repair attempts задачи или конфликт требований → HUMAN_ATTENTION; иначе продолжи Schedule.

### Draft PR

После первой интеграции создай один draft PR, только если PR запрошен или обязателен repo/tracker workflow. Проверь существующий PR/base/head; closing refs — по tracker. Сохрани URL/result, не создавай повторно при recovery; прикрепи PR к диалогу, если host поддерживает. Draft не закрывает tickets и не становится ready до Done.

Все задачи INTEGRATED → перейди к общему Review в [SKILL.md](../SKILL.md). REVIEWED подтверждает покрытие ревью; итоговое качество и tracker completion требуют отдельного завершения.
