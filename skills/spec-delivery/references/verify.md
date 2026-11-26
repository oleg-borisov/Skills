# Verify и завершение

Часть [общего протокола](protocol.md); читай перед Verify.

## Verify

Вход: актуальное обязательное coverage, нет OPEN findings, весь план завершён по SKILL.md. Один gate итога, не каждого commit. HEAD/inputs неподвижны; dirty inputs/недостоверное evidence → HUMAN_ATTENTION.

Reuse полного GREEN (`ledger.py gate --reuse`): тот же HEAD/inputs либо одинаковое Git tree при прежних требованиях/условиях. Diff только пояснений/инструкций допускает reuse, если controller по имеющимся diff/commands/логам доказывает неизменность code/tests/fixtures/resources/build/config inputs, существенной среды и достаточность команд; proof передай в `--reuse`. Для этого читает только изменённый текст docs; отдельный агент/check не нужен. Новые требования/inputs/условия или нужда в исследовании → verifier. Расширение файла/чистый merge не доказательство. Review coverage независимо.

Без применимого GREEN gate NOT_APPLICABLE (`ledger.py gate --not-applicable <reason>`) лишь для всего непроверенного диапазона неисполняемого текста по worker evidence/repo config. Agent instructions, MDX, executable examples, configs/build inputs требуют gate; сомнение → verifier.

Иначе fresh verifier: `{base_sha: review_target, head_sha: HEAD, artifacts_dir: LEDGER_DIR, gate_path?}` и refs scope. Если из уже известных repo instructions/configuration следует одна команда полного gate для этого scope, передай `gate_command: {cmd, source}` с указателем на правило. JSON verifier — `ledger.py gate`. RED кандидата merge queue → [правила очереди](completion.md#merge-queue). Иначе RED → fresh reviser с `{ledger_cli, ledger_dir, gate_path, finding_ids: []}`; targeted repair/commit → delta Review → Triage → новый gate с gate_path прежнего RED. Unchanged HEAD после repair, `stop` в ответе CLI либо BLOCKED без доказанно устранимой технической причины → HUMAN_ATTENTION.

GREEN → [завершение](completion.md).

## Завершение

COMPLETED только после успешного подтверждённого merge и согласованных completion actions. Сначала итог в диалог/разрешённый tracker: результат, SHA/PR, проверки, оставленные замечания (`left`), human dispositions/linked tasks и ограничения. Не ссылайся на удаляемые логи как доступный архив.

Затем `ledger.py set status=COMPLETED` и `ledger.py cleanup` без нового вопроса, чтения содержимого и архивации; writers нет. Ошибка cleanup → сохрани состояние/путь, сообщи. Worktrees удаляются отдельно по согласию; parent/default/shared сохраняется. Незавершённый/HUMAN_ATTENTION/STOP запуск не удаляй.
