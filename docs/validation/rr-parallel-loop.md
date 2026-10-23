# Логический прогон rr-parallel-loop

Исторический прогон: порядок Verify → Review ниже заменён [ADR-0005](../adr/0005-final-gate-after-review.md). Проверка нового порядка трёх workflows описана в [final-gate-after-review.md](final-gate-after-review.md).

Дата: 2026-10-11. Проверен текст [skill](../../skills/rr-parallel-loop/SKILL.md),
[completion](../../skills/rr-parallel-loop/references/completion.md), общие
`agents/*.md`. Workflows запускаются независимо; взаимный recovery не предусмотрен.

Метод: независимые read-only прогоны переходов состояния и аудит совместимости,
исправление обнаруженных противоречий, повторный прогон изменённых веток.
Это проверка контракта, не end-to-end запуск на продукте: реальные workers,
конфликтующие Git-ветки, PR API и tracker transitions в сценариях не выполнялись.
Время и токены не измерялись.

## Основной граф

Fixture: A и B независимы; C зависит от A; D зависит от B и C.
Их write_scopes доказанно независимы, есть два worker slots.

```text
BASE S → A(S) || B(S)
A готова → merge A → I1 → C(I1), пока B ещё RUNNING
B готова → merge B → I2
C готова → merge C → I3 → D(I3)
D готова → merge D → I4 → Freeze
Verify(I4) GREEN → Spec full-spec || Standards → REVIEWED
QUALITY GREEN → подтверждённый final merge → completion
```

C не ждёт B. D получает обе prerequisites в своей базе. Каждый task commit
сохраняется в ancestry integration; INTEGRATED не закрывает tracker ticket.

## Сценарии

| Вход/событие | Проверенный переход и инвариант |
| --- | --- |
| Общий write_scope или неизвестные границы | Сериализация до освобождения scope; параллельность не угадывается по разным ticket IDs. |
| Цикл графа / неизвестный внешний blocker | Preflight HUMAN_ATTENTION до реализации. |
| PENDING остались, frontier пуст, workers отсутствуют | HUMAN_ATTENTION с prerequisites, не ложный Done. |
| Конфликт merge B в I1 | Abort только собственного merge; freeze dispatch/merges; fresh implementer синхронизирует B с pinned I1; targeted checks; обе ancestry; повторная интеграция. Две неудачные попытки останавливают цикл. |
| Final verifier RED | Inventory → implementer до первого review, иначе reviser → новый HEAD → Verify. Три RED подряд или BLOCKED/unchanged HEAD → HUMAN_ATTENTION. |
| Review MAJOR F1 | Reviser ACCEPTED оставляет F1 OPEN → Verify нового HEAD → reviewer explicit FIXED → coverage. |
| Новое изменение другой review-оси | Union originating/affected/uncovered axes; исправление не обходит обязательный review. |
| Неизменный GREEN HEAD | Повторный full suite не нужен при неизменных входах; OPEN findings всё равно требуют dispositions. |
| Обычный Markdown / agent instructions | Только неисполняемый текст допускает NOT_APPLICABLE; инструкции агентов идут через обычный gate. |
| Merge завершён, checkpoint result не записан | Intent + точный source ancestor + объяснимый новый tip восстанавливают INTEGRATED без повторного merge. |
| Worker жив при resume | Повторное наблюдение, не второй writer. Неизвестная liveness блокирует dispatch. |
| Scope expansion | Worker завершает turn JSON/risks, не ждёт controller. По уточнению 2026-10-14 свободные пути в прежних criteria допускают продолжение того же owner; передача другому worker требует snapshot. Integration и gate остаются clean. |
| Два новых controller | Exclusive create claim rr-parallel-loop допускает одного владельца. Незавершённая запись также блокирует второго. |
| Два concurrent resume | OS-lock сериализует передачу claim; повторная проверка owner/version внутри секции отклоняет проигравшего. |
| Parent продвинулся | Merge parent → новый integration HEAD → Verify/Review/triage. Повторный drift ограничен; старое GREEN не переносится. |
| PR ждёт человека, head/base меняется | Подтверждённая защита expected refs либо проверка кандидата очереди; без механизма PR остаётся draft. Слияние сторонним участником из других refs не даёт COMPLETED. |
| STOP при активных workers | Interrupt, сохранение IDs/liveness/dirty, STOPPED_BY_HUMAN; автоматического cleanup нет. |

## Исправления по результатам прогонов

1. Recovery ограничен ledger своего workflow. Межскилловые ссылки и routing удалены; claim rr-parallel-loop имеет отдельный namespace в общем Git directory.
2. Взаимное ожидание scope decision: blocked worker теперь завершает попытку;
   явно разрешена контролируемая передача сохранённых dirty правок.
3. Гонка первичного запуска и concurrent resume: atomic claim rr-parallel-loop, версия
   владельца и сериализация его изменений.
4. Гонка изменения PR base: expected head/base защищаются при фактическом merge;
   чтение refs перед запросом не считается достаточной гарантией.

JSON-контракты общих leaf-agents сохранены. Worktree/cwd задаётся dispatch envelope;
scope и continuation передаются через существующий directives_path, блокировка —
через risks в существующем handoff. Отдельная роль merger не добавлена.

## Распространение и формат ledger

В Windows выполнен `./link-codex.ps1` через PowerShell 7 (exit 0), включая
`sync-codex-agents.ps1`, `sync-zcode-agents.ps1`, `link-gemini.ps1` и
`sync-gemini-agents.ps1`. `rr-parallel-loop` входит в тот же список workflows,
что `rr-loop` и `rr-cascade-loop-fast`; отдельного пути установки у него нет.

После запуска проверены targets junction и SHA-256 копий: 196 успешных проверок,
включая все 17 Orca accounts с каталогом `home`:

- Skills в `~/.agents`, `~/.claude`, `~/.config/opencode` и Orca homes — junction
  на соответствующие каталоги репозитория; `.agents/skills` и `~/.codex/agents`
  также указывают на репозиторий.
- Commands и Markdown agents Claude/OpenCode, ZCode profiles, Gemini plugin
  agents и Codex TOML profiles в Orca совпадают с источниками по SHA-256.
- Skill с форматами ledger доступен через `~/.agents/skills/rr-parallel-loop`.

В `link-codex.ps1` и `link-opencode.sh` удалена очистка retired assets.
В трёх workflows удалены поиск, миграция и cleanup прежних Markdown ledgers;
recovery текущих `state.json`/`findings.jsonl` сохранён. Межскилловые ссылки, поиск чужих ledger и общий для workflows claim удалены; собственный claim rr-parallel-loop защищает его concurrent controllers.

Структуры `state.json` и события `findings.jsonl` определены JSON/JSONL-блоками в разделе «Ledger и recovery» основного [SKILL.md](../../skills/rr-parallel-loop/SKILL.md). Оба блока успешно разобраны; sample finding не считается событием запуска, новый журнал создаётся пустым. С 2026-10-14 детали возобновления вынесены в [recovery.md](../../skills/rr-parallel-loop/references/recovery.md), загружаемый при resume, сбое или передаче dirty worktree; claim и checkpoint остаются в основном skill.

## Оптимизация по сессии, 2026-10-14

Источник: чат `01a133ec-cdc0-7290-b261-7e0b56115bd4`, прочитаны обе страницы истории через `read_thread`. Подсчёт событий: 45 `subAgentActivity(kind=started)`, 319 `collabAgentToolCall(tool=wait)`, из запусков 8 verifier. Это количества событий, не измерение токенов или избыточной работы. В частности, новый HEAD после product repair требует нового общего gate.

Наблюдения и изменения общего workflow:

- SPO-544: дополнительный migration test builder вызвал передачу dirty, snapshot и fresh implementer. Уточнение свободных путей в прежних criteria теперь продолжает того же owner с delta directives; требования и граф этим не расширяются.
- SPO-553/SPO-549: capacity failures приводили к повторным запросам разрешения продолжить известные dirty-попытки. Теперь допустимы два технических продолжения при доказанном выходе writer/subprocesses и происхождении правок; неизвестная liveness по-прежнему блокирует восстановление.
- Verifier сравнил hash копии worktree с hash другого абсолютного источника (LF/CRLF). Контракт теперь связывает hash с сырыми байтами точного path; несовпадение нельзя обходить нормализацией текста.
- В истории многократно повторялись сообщения об ожидании handoff. Skill требует событийного ожидания и чтения только изменившихся результатов; обязательная частота сообщений host сохраняется.
- Общие роли возвращают финальный JSON; verifier read-only. Controller сохраняет JSON сам, отсутствие второй копии файла не становится причиной повторного gate. Для неполного evidence предусмотрено ограниченное восстановление отчёта.
- Смена схемы дошла до общего gate со старыми assertions. В dispatch уточнён выбор targeted checks по затронутым consumers/fixtures; список конкретных Android-тестов и runner относятся к проекту и в skill не перенесены.

Удалена дублирующая таблица входов/выходов ролей. JSON-схемы ledger и общих leaf-agents не менялись. Cleanup сохраняет evidence вне удаляемых каталогов. Claim, full gate, независимые review, finding dispositions и авторизация final merge сохранены.

Проверка изменённых веток контракта:

| Сценарий | Ожидаемое действие |
| --- | --- |
| Свободный fixture для прежнего criterion | Завершить turn, сохранить scope/intent, продолжить того же owner; не создавать snapshot без передачи ownership. |
| Путь занят другим RUNNING/READY worker | Приостановить dispatch/merges, дождаться writers; интегрировать завершённые задачи в подтверждённом scope, освободить их locks и проверить scope продолжения. |
| Capacity failure; owner и выход subprocesses подтверждены | Продолжить сохранённую попытку в пределах двух retries; fresh worker получает snapshot при передаче dirty. |
| Timeout ожидания или неизвестный subprocess | Не считать worker завершённым; не назначать второго writer. |
| JSON есть, handoff-файла нет | Controller сохраняет JSON; проверки результата обычные, новый gate не запускается из-за файла. |
| Commit есть, отчёт неполный | Восстановить evidence в той же роли; не повторять реализацию или успешные проверки без изменения входов. |
| BLOCKED до checks из-за неверной адресации | Исправить refs и продолжить verifier на тех же входах в пределах retries; это не product RED. |
| Test RED / новый HEAD после repair | Обычный inventory → repair → Verify; инфраструктурные retries не подменяют этот цикл. |
| GREEN HEAD без изменений | Переиспользовать gate evidence; OPEN findings всё равно требуют reviewer dispositions. |
| Evidence находится внутри удаляемого ledger | Сохранить evidence/рабочие ссылки снаружи либо оставить содержащий его каталог. |

Это логический прогон, не повтор продуктовой сессии. Фактическая экономия токенов и времени после изменений не измерена.

Размер текста (Unicode characters, LF, без внешних пробелов): основной SKILL.md 25 750 → 24 482 (−4,9%); весь skill с references 30 173 → 33 320 (+10,4%). Recovery загружается условно. Ожидаемая экономия выполнения связана с устранением fresh dispatch/повторного контекста/дублирующего handoff, а не с уменьшением суммарного объёма всех файлов.

Независимый read-only forward-test обнаружил и позволил исправить два перехода: freeze merges не позволял освободить scope завершившегося B; безусловное удаление ledger противоречило сохранению вложенного evidence. Для первого теперь разрешена интеграция завершённых задач в подтверждённом scope после выхода writers; для второго содержащие evidence каталоги остаются с отметкой COMPLETED.

Повторный независимый прогон этих двух исправлений не нашёл блокирующих противоречий.

Статические проверки: `git diff --check`, строгая UTF-8 декодировка без BOM, локальные Markdown-ссылки, разбор и сравнение JSON/JSONL checkpoint с HEAD — PASS. Frontmatter проверен как два plain scalar поля. Штатный `quick_validate.py` не запустился: в доступном bundled Python отсутствует PyYAML. Скрипты установки/генерации и общие agents не менялись.

## Границы результата

После изменений повторены `git diff --check` для staged/unstaged, PowerShell AST
parse всех корневых `.ps1`, `bash -n link-opencode.sh`, строгая UTF-8 декодировка
и проверка локальных Markdown-ссылок skill — успешны. Windows-синхронизация
выполнена и проверена выше. macOS-синхронизация на macOS не запускалась;
подтверждён только синтаксис Bash-скрипта.

При первоначальном логическом прогоне metadata/scaffold нового skill проверены;
штатный `quick_validate.py` не запустился из-за отсутствия PyYAML, frontmatter
проверен отдельно как YAML mapping из двух plain scalars.

- Выигрыш скорости предполагает независимые scopes, доступные worker slots и
  изолируемые checks. При сериализации графа ускорение ограничено.
- Экономия — один общий gate/review вместо gate/review каждого ticket и отсутствие
  merger-agent на чистом слиянии; repair может добавить запуски.
- Ошибки интеграции могут обнаружиться позднее, чем в rr-cascade-loop-fast.
- Worktree addressing, OS-lock, защита refs PR и test resources требуют проверки
  на выбранном host. Неподдерживаемая capability останавливает соответствующий
  переход; логический прогон не подтверждает наличие этих механизмов у хоста.
