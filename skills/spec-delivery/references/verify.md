# Verify и завершение

Часть [общего протокола](protocol.md); читай перед Verify.

## Verify

Вход: актуальное обязательное coverage, нет OPEN findings, весь план завершён по SKILL.md. Один gate итога, не каждого commit. HEAD/inputs неподвижны; dirty inputs/недостоверное evidence → HUMAN_ATTENTION.

Reuse полного GREEN (`RR gate --reuse`): тот же HEAD/inputs либо одинаковое Git tree при прежних требованиях/условиях. Diff только пояснений/инструкций допускает reuse, если controller по имеющимся diff/commands/логам доказывает неизменность code/tests/fixtures/resources/build/config inputs, существенной среды и достаточность команд; proof передай в `--reuse`. Для этого читает только изменённый текст docs; отдельный агент/check не нужен. Новые требования/inputs/условия или нужда в исследовании → verifier. Расширение файла/чистый merge не доказательство. Review coverage независимо.

Без применимого GREEN gate NOT_APPLICABLE (`RR gate --not-applicable <reason>`) лишь для всего непроверенного диапазона неисполняемого текста по worker evidence/repo config. Agent instructions, MDX, executable examples, configs/build inputs требуют gate; сомнение → verifier.

Иначе fresh verifier: `{base_sha: green.head или BASE, head_sha: HEAD, artifacts_dir: LEDGER_DIR, gate_path?}` и refs scope; его JSON — `RR gate`. RED → fresh reviser с gate_path и finding_ids: [] без review findings; targeted repair/commit → delta Review → Triage → новый gate с gate_path прежнего RED: verifier сначала повторяет только упавшие checks и идёт на полный проход лишь после их успеха. Unchanged HEAD после repair, `stop` в ответе CLI либо BLOCKED без доказанно устранимой технической причины → HUMAN_ATTENTION.

## Merge одной спеки

Граф завершается по [completion](completion.md).

1. Нужны quality GREEN и согласие на merge; отказ в согласии → вопрос, WAITING_FOR_HUMAN/pending_action. Rebase на актуальный tip цели; конфликт/ошибка → HUMAN_ATTENTION без автоматического retry.
2. Новый HEAD → `RR set head=<sha>` → необходимый delta Review → Triage → Verify с проверкой reuse GREEN.
3. При quality GREEN — fast-forward цели по repo workflow. Push task-ветки не означает merge; ошибка → HUMAN_ATTENTION.
4. После успешного merge — согласованные tracker/completion actions и cleanup созданного task-worktree. Успешные внешние действия не повторяй после recovery. Ошибка оставляет checkpoint.

## Завершение

COMPLETED только после успешного подтверждённого merge и согласованных completion actions. Сначала итог в диалог/разрешённый tracker: результат, SHA/PR, проверки, оставленные замечания (`left`), human dispositions/linked tasks и ограничения. Не ссылайся на удаляемые логи как доступный архив.

Затем `RR set status=COMPLETED` и `RR cleanup` без нового вопроса, чтения содержимого и архивации; writers нет. Ошибка cleanup → сохрани состояние/путь, сообщи. Worktrees удаляются отдельно по согласию; parent/default/shared сохраняется. Незавершённый/HUMAN_ATTENTION/STOP запуск не удаляй.
