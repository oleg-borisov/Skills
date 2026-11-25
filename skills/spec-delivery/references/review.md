# Review → Triage → Revise

Часть [общего протокола](protocol.md); читай при входе в фазу.

По оси base_sha = `axes.<ось>.last_reviewed_head` или BASE, scope = весь непокрытый диапазон. Spec обязателен для требований; Standards NOT_APPLICABLE (`RR review --axis standards --skip <reason>`) лишь при доказанном отсутствии правил либо полном покрытии уже успешными automated checks нужного scope. Будущий gate/tests-only не освобождает от Standards.

Две нужные оси — параллельно на одном HEAD. Spec получает spec_refs/review_mode, Standards — standards_files; repair — findings_path/IDs своей оси. initial: criteria/общие контракты; delta: dispositions заданных IDs и diff repair с затронутыми им criteria/прямыми зависимостями, новое вне diff reviewer помечает `scope: outside`; full-spec: вся spec, включая завершённые задачи.

JSON каждого reviewer — один `RR review` с `--ids` переданных ему IDs. Отказ CLI (чужой HEAD, BLOCKED_CONTEXT, нет explicit FIXED|OPEN заданных IDs) → HUMAN_ATTENTION без coverage. Severity назначает CLI: wrong → BLOCKER; missing/partial/hard → MAJOR; judgement и delta `scope: outside`, кроме wrong → MINOR. Finding с пометкой docs_only понижай до MINOR одним `RR finding severity <IDs> MINOR`, если документ не назван criterion spec и не является agent instructions/executable example/config. Дубль OPEN-записи той же оси закрывай `RR finding close <ID> "дубль <ID>"`. После repair Spec delta нужен всегда; Standards delta — только при OPEN IDs оси, иначе непокрытый диапазон Standards закрывает одно покрывающее Standards review финального HEAD перед Verify. Full-spec (`--full-spec`) фиксирует full_spec_reviewed_head; последующие delta оценивают влияние на всё покрытие, неясность → full-spec.

- Critical BLOCKER/MAJOR → fresh reviser. Попутно дешёвые MINOR к коду: один файл, до 20 LOC, без API/schema/test-architecture/research.
- Остальные MINOR и все docs MINOR — FIX_NOW batch после закрытия critical: один reviser, одно delta Review dispositions; повторяй, пока есть OPEN MINOR и CLI не вернул `minor_limit`. `minor_limit` либо MINOR >3 файлов/>100 LOC/меняющий test architecture → `RR finding leave <IDs>`: оставленные замечания идут в итог запуска без остановки.
- Critical rejected worker'ом, конфликт spec/standards либо `stop` в ответе CLI (critical без прогресса, предел critical-итераций) → HUMAN_ATTENTION. Лимит critical findings не закрывает; отказ человека исправлять critical → STOPPED_BY_HUMAN.

Reviser получает IDs/gate_path и refs/directives scope; его handoff — `RR handoff --role reviser --ids <IDs>`. Новый commit → delta Review → Triage; unchanged HEAD → решение человека без повторных checks/review. Targeted checks/быстрый ярус/formatter — worker до commit, FIXED — reviewer.
