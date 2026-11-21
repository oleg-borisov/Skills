# Review → Triage → Revise

Часть [общего протокола](protocol.md); читай при входе в фазу.

По оси base_sha = last_reviewed_head или BASE, scope = весь непокрытый диапазон. Spec обязателен для требований; Standards NOT_APPLICABLE лишь при доказанном отсутствии правил либо полном покрытии уже успешными automated checks нужного scope. Будущий gate/tests-only не освобождает от Standards. Для skip range/reason, fixed point не продвигай.

Две нужные оси — параллельно на одном HEAD. Spec получает spec_refs/review_mode, Standards — standards_files; repair — findings_path/IDs своей оси. initial: criteria/общие контракты; delta: dispositions заданных IDs и diff repair с затронутыми им criteria/прямыми зависимостями, новое вне diff reviewer помечает `scope: outside`; full-spec: вся spec, включая завершённые задачи.

Reviewer возвращает head/verdict и только непустые optional findings/dispositions. Неверный HEAD, NO_SPEC/BLOCKED_CONTEXT, неполный explicit FIXED|OPEN/evidence заданных IDs → HUMAN_ATTENTION без coverage. Severity назначает `RR review`: wrong → BLOCKER; missing/partial/hard → MAJOR; judgement → MINOR; delta finding `scope: outside`, кроме wrong → MINOR. Finding с пометкой docs_only понижай до MINOR через `RR finding severity`, если документ не назван criterion spec и не является agent instructions/executable example/config. Дубли внутри оси объединяй по stable ID; между осями сохраняй IDs/verdict отдельно. После repair Spec delta нужен при OPEN IDs оси, Spec в affected_review_axes либо непокрытом диапазоне; Standards delta — только при OPEN IDs оси или явном Standards в affected_review_axes. Иной непокрытый диапазон Standards закрывает одно покрывающее Standards review финального HEAD перед Verify. Успешное review одним `RR review` атомарно обновляет coverage/findings; no_progress каждого OPEN ведёт CLI, остальные counters — controller. Full-spec фиксирует full_spec_reviewed_head; последующие delta оценивают влияние на всё покрытие, неясность → full-spec.

- Critical BLOCKER/MAJOR → fresh reviser. Попутный дешёвый MINOR: один файл, до 20 LOC, без API/schema/test-architecture/research.
- Docs MINOR по умолчанию FIX_NOW одним batch после закрытия critical: один reviser, одно delta Review dispositions; оставшиеся OPEN → решение человека без новых итераций.
- Остальные MINOR/спорные → batch ID/axis/location/evidence/fix: FIX_NOW, linked task, REJECTED(reason). MINOR >3 файлов/>100 LOC/меняющий test architecture — только linked task/rejection. Создание task требует авторизации/tracker contract; до получения ID finding OPEN.
- Critical rejected worker'ом, конфликт spec/standards либо тот же critical без прогресса два review → HUMAN_ATTENTION. Предел: четыре critical repair-review iterations, две MINOR repair iterations; после MINOR-предела решения человека. Лимит findings не закрывает; отказ человека исправлять critical → STOPPED_BY_HUMAN.

Reviser получает IDs/inventory и refs/directives scope, включая записи repaired файлов своих IDs. Новый commit → delta Review → Triage; unchanged HEAD → решение человека без повторных checks/review. Targeted checks/быстрый ярус/formatter — worker до commit, FIXED — reviewer.
