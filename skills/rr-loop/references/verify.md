# Финальный Verify и завершение

Часть [общего протокола](protocol.md); читай перед финальным Verify.

## Verify

Вход: актуальное обязательное coverage, нет OPEN/pending, весь план завершён по SKILL.md. Один полный gate итога, не каждого commit. HEAD/inputs неподвижны; dirty inputs/недостоверное evidence → HUMAN_ATTENTION.

Reuse полного GREEN: тот же HEAD/inputs либо одинаковое Git tree при прежних требованиях/условиях. Diff только пояснений/инструкций допускает reuse, если controller по имеющимся diff/plan/логам доказывает неизменность code/tests/fixtures/resources/build/config inputs, существенной среды и достаточность команд. Для этого читает только изменённый текст docs; отдельный агент/check не нужен. Новые требования/inputs/условия или нужда в исследовании → verifier. Расширение файла/чистый merge не доказательство. Сохрани исходный SHA/ref GREEN, итоговый HEAD и proof; last_full_green_head остаётся SHA прогона. Review coverage независимо.

Без применимого GREEN gate NOT_APPLICABLE лишь для всего непроверенного диапазона неисполняемого текста по worker evidence/repo config. Agent instructions, MDX, executable examples, configs/build inputs требуют gate; сомнение → verifier. Запиши range/reason, last_full_green_head не меняй.

Иначе fresh verifier: `{base_sha: last_full_green_head или BASE,head_sha: HEAD,artifacts_dir: LEDGER_DIR,validation_plan_path?}` и refs scope. Один full-suite проход по repo config. validation_plan одновременно evidence команд/results, один inventory failures, логи по refs. GREEN → last_full_green_head = HEAD, green_ref = handoff, consecutive_red = 0. RED → fresh reviser с inventory/refs scope и finding_ids: [] без review findings; targeted repair/commit → delta Review → Triage → новый gate с failure_inventory_path прежнего RED: verifier сначала повторяет только упавшие checks и идёт на полный проход лишь после их успеха. Repair не расходует review counter, сам review расходует; RED counter review не сбрасывает. Unchanged HEAD после repair, три RED подряд или BLOCKED без доказанно устранимой технической причины → HUMAN_ATTENTION.

## Завершение

COMPLETED только после успешного подтверждённого merge и согласованных completion actions. Сначала итог в диалог/разрешённый tracker: SHA/PR, результаты проверок, human dispositions/ограничения. Не ссылайся на удаляемые логи как доступный архив.

После COMPLETED выполни `RR cleanup` без нового вопроса, чтения/редактирования содержимого и архивации; writers нет. CLI проверяет status и путь каталога запуска. Ошибка cleanup → сохрани состояние/путь, сообщи. Worktrees удаляются отдельно по авторизации; parent/default/shared сохраняется. Незавершённый/HUMAN_ATTENTION/STOP запуск не удаляй.
