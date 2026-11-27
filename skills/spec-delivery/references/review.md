# Review → Triage → Revise

Часть [общего протокола](protocol.md); читай при входе в фазу.

## Merge-кандидат

До первого Review получи актуальный tip согласованной цели разрешённым способом. Дождись выхода writers и проверь чистоту checkout. Для graph BASE должен входить в историю цели; для single подтверждай по Git metadata, что в историю кандидата сверх цели входят только коммиты task-ветки этой задачи. Переписанная история ранее зафиксированной цели либо неизвестное происхождение коммитов → HUMAN_ATTENTION. Tip уже предок HEAD → используй HEAD. Иначе зафиксируй `candidate_intent` с исходным HEAD и точным SHA цели до операции:

- Single: rebase task-ветки на этот SHA. Для уже опубликованной head-ветки PR используй merge цели, если repo workflow разрешает merge-коммиты, чтобы сохранить возможность обычного push. Если нужна линейная история и rebase потребует force-push, остановись до переписывания. Конфликт/ошибка → HUMAN_ATTENTION без автоматического retry.
- Graph: обычный merge этого SHA в integration с сохранением ticket ancestry. Конфликт → прерви свой merge и передай fresh implementer единоличное владение integration cwd, pinned tip цели, всю spec/standards и directive на conflict repair с formatter/targeted checks/commit. Две неудачные попытки или неразрешимый конфликт → HUMAN_ATTENTION.

Сохрани одним `ledger.py set head=<candidate> review_target=<tip> --delete candidate_intent`. `review_target` — предок кандидата. Смена tip сбрасывает coverage обеих осей, сохраняя OPEN findings. При сдвиге цели перед merge повтори подготовку, Review → Triage → Verify с проверкой reuse GREEN. Если цель уже содержит spec и свой diff пуст, сверяй состояние задачи с человеком.

## Review

При смене цели заново проверь весь собственный patch (для графа Spec снова `full-spec`) и запроси dispositions оставшихся OPEN IDs. Код из цели разрешено читать как контекст для оценки кандидата. Standards учитывает актуальные применимые правила; если цель меняла инструкции, уточни их пути для собственного patch.

Spec обязателен для требований; Standards NOT_APPLICABLE (`ledger.py review --axis standards --skip <reason>`) лишь при доказанном отсутствии правил либо полном покрытии уже успешными automated checks нужного scope. Будущий gate/tests-only не освобождает от Standards.

Один `ledger.py review --ledger <dir> --prepare` готовит обе оси. Для одной оси добавь `--axis spec|standards`. CLI один раз сверяет фактический HEAD, берёт base каждой оси из её последнего coverage или `review_target` и выгружает один diff на каждый уникальный диапазон. Для OPEN IDs формирует выборку своей оси. Ошибка подготовки → HUMAN_ATTENTION.

Передай каждой роли её `inputs.<ось>` из ответа. Spec также получает spec_refs/review_mode, Standards — standards_files. Initial: criteria/общие контракты; delta: затронутые criteria/прямые зависимости; full-spec: вся spec, включая завершённые задачи. Две нужные оси запускай параллельно на одном HEAD.

Если требуется `--file` для передачи результата CLI, используй возвращённый `artifacts_dir`. После приёма результатов и выхода всех использующих эти файлы reviewers удали этот временный каталог. При прерывании он восстанавливается через `--prepare` после сверки живых исполнителей.

### Продолжение исполнителей

В повторных раундах Review → Triage → Revise предпочитай продолжение последней сессии каждой роли (`spec-reviewer`, `standards-reviewer`, `reviser`). Используй механизм хоста, который начинает новый turn в той же сессии с сохранённой историей. Прими предыдущий handoff и подтверди завершение turn перед продолжением. Перед запуском reviser дождись также выхода предыдущего writer и его subprocesses.

Продолжай в пределах того же запуска, роли и checkout при неизменных `review_target`, требованиях, применимых standards и контракте роли. Новый HEAD должен быть потомком предыдущего кандидата в этом цикле. При входе в Verify перестань использовать эти сессии для новых раундов. Если условия изменились, сессия недоступна или хост не поддерживает продолжение с нужной параллельностью, используй свежего исполнителя по протоколу. При неизвестном исходе вызова или liveness сначала примени [Recovery](recovery.md).

На новый turn передай актуальные входы роли, включая `{base_sha,head_sha}`, пути из текущего `review --prepare` для reviewer и текущие IDs замечаний. Укажи, что входы и directives этого turn заменяют прежние. Прими новый handoff обычной командой CLI.

### Приём результатов

JSON каждого reviewer — один `ledger.py review` с `--ids` переданных ему IDs. Отказ CLI (чужой HEAD, BLOCKED_CONTEXT, нет explicit FIXED|OPEN заданных IDs) → HUMAN_ATTENTION без coverage. Severity назначает CLI: wrong → BLOCKER; missing/partial/hard → MAJOR; judgement и delta `scope: outside`, кроме wrong → MINOR. Finding с пометкой docs_only понижай до MINOR одним `ledger.py finding severity <IDs> MINOR`, если документ не назван criterion spec и не является agent instructions/executable example/config. Дубль OPEN-записи той же оси закрывай `ledger.py finding close <ID> "дубль <ID>"`. После приёма всех ожидаемых результатов раунда и этих правок severity/дублей, если остаются OPEN findings, получи лимиты через `ledger.py review --ledger <dir> --triage`. После repair Spec delta нужен всегда; Standards delta — только при OPEN IDs оси, иначе непокрытый диапазон Standards закрывает одно покрывающее Standards review финального HEAD перед Verify. Full-spec (`--full-spec`) фиксирует full_spec_reviewed_head; последующие delta оценивают влияние на всё покрытие, неясность → full-spec.

- Critical BLOCKER/MAJOR → reviser по правилам продолжения выше. Попутно дешёвые MINOR к коду: один файл, до 20 LOC, без API/schema/test-architecture/research.
- Остальные MINOR и все docs MINOR — FIX_NOW batch после закрытия critical: один reviser, одно delta Review dispositions; повторяй, пока есть OPEN MINOR и CLI не вернул `minor_limit`. `minor_limit` либо MINOR >3 файлов/>100 LOC/меняющий test architecture → `ledger.py finding leave <IDs>`: оставленные замечания идут в итог запуска без остановки.
- Critical rejected worker'ом, конфликт spec/standards либо `stop` в ответе CLI (critical без прогресса, предел critical-итераций) → HUMAN_ATTENTION. Лимит critical findings не закрывает; отказ человека исправлять critical → STOPPED_BY_HUMAN.

Для findings у кандидата merge queue сначала примени [правила очереди](completion.md#merge-queue). Reviser всегда получает `ledger_cli`, `ledger_dir` и finding_ids; передай применимые refs/directives scope и gate_path. Его handoff — `ledger.py handoff --role reviser --ids <IDs>`. Новый commit → delta Review → Triage; unchanged HEAD → решение человека без повторных checks/review. Targeted checks/быстрый ярус/formatter — worker до commit, FIXED — reviewer.
