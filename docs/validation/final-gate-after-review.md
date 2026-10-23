# Финальный gate после review

Дата: 2026-10-17. Контракт: [ADR-0005](../adr/0005-final-gate-after-review.md).

Проверяются три канонических workflow, completion parallel, общий verifier и генерируемые профили. Это логический прогон инструкций и статическая проверка assets; продуктовые сборки, tracker transitions и merge API не выполняются. Выигрыш времени не измерен.

## Сценарии переходов

| Сценарий | Ожидаемый маршрут |
| --- | --- |
| Обычный rr-loop | Implement с targeted checks → Review → Triage/решения → полный Verify → Done/merge. |
| Несколько review repairs | Reviser с targeted checks → delta Review → Triage; полный gate только после разрешения findings и решений. |
| Cascade, промежуточный тикет | Targeted checks → review либо допустимое deferred:batch → следующая задача, без полного gate. Carried findings сохраняют прежние правила. |
| Cascade, deferred:batch | Успешные targeted checks заменяют требование полного GREEN первой попытки; пороги diff и лимит отложенных задач сохраняются. |
| Cascade, весь план — неисполняемый текст | Deferred задачи получают покрывающее/full-spec review в Done без повторного отложения; gate допускает обоснованный NOT_APPLICABLE для всего диапазона. |
| Parallel, независимые тикеты | Targeted checks → последовательная интеграция → общий full-spec/Standards review → repairs/triage → финальный gate. |
| Review завершён, gate ещё не запускался | REVIEWED не означает QUALITY = GREEN, tracker completion или разрешение final merge. |
| Финальный RED | Единый inventory → fresh reviser с targeted checks/commit → обязательный delta Review → Triage → новый полный gate. |
| Новый finding после RED repair | Обычный review repair/решения до следующего gate; RED counter не сбрасывается review. |
| Три RED подряд | HUMAN_ATTENTION; промежуточные review и worker repairs не сбрасывают RED counter, GREEN сбрасывает. |
| Новый HEAD после reconciliation/кандидат merge queue | Проверка review coverage, необходимые Review/triage; Verify сначала проверяет применимость полного GREEN к фактическому кандидату и запускает verifier только без доказанного reuse. |
| Неизменный HEAD с достоверным GREEN | Gate evidence переиспользуется; выполненное review не повторяется. |
| Standards полностью проверяются будущим gate | Это ещё не основание пропускать Standards reviewer; нужны уже успешные checks нужного scope или доказанное отсутствие правил. |
| Targeted handoff промежуточного тикета | Сохраняет свой SHA; актуальные review coverage и итоговый gate покрывают финальный HEAD. |
| Старый ledger | Миграция не вводится: по согласованной предпосылке старых незавершённых запусков нет. Recovery новых запусков сохраняется. |

Исторические прогоны [rr-parallel-loop](rr-parallel-loop.md) описывают прежний порядок Verify → Review. Их результаты не являются проверкой нового порядка.

## Результаты

- Независимый read-only forward-test трёх workflows и completion: PASS, actionable противоречий ADR-0005 не найдено. Проверены успешный путь, несколько review repairs, RED repair с новым finding, три RED подряд, docs-only cascade, reconciliation и cached GREEN.
- Статические проверки: `git diff --check`, строгая UTF-8 без BOM, локальные Markdown-ссылки, порядок фаз и ссылки §, JSON/JSONL checkpoint, разбор Codex TOML и равенство verifier body каноническому источнику в Codex/ZCode — PASS.
- Выполнены штатные `sync-codex-agents.ps1`, `sync-zcode-agents.ps1` и `link-codex.ps1` на Windows, включая генерацию/синхронизацию Gemini. Проверены 200 junction targets/SHA-256 копий, включая 17 Orca accounts — PASS.
- Реальный продуктовый цикл и macOS-синхронизация не запускались. Скорость нового порядка требует измерения на последующих задачах.

## Уточнение 2026-10-23: reuse GREEN

Прежнее безусловное повторение gate после смены HEAD заменено проверкой применимости evidence самим controller. Никаких новых subagents, fingerprints или project checks для решения о reuse не добавлено.

| Сценарий | Ожидаемое решение |
| --- | --- |
| Новый SHA, одинаковое дерево, прежние требования и условия проверок | Reuse полного GREEN; сохранить исходный SHA и привязку к текущему HEAD. |
| Только пояснения/инструкции, прежние успешные проверки удовлетворяют текущим требованиям | Reuse по имеющимся diff/plan/логам, без verifier. Review coverage проверяется отдельно. |
| Инструкция добавляет обязательный тест, меняет существенный runtime или прежних результатов недостаточно | Обычный gate, даже если production code не менялся. |
| Бесконфликтный merge меняет код, tests, fixtures/resources или build/config inputs | Обычный gate; отсутствие конфликтов не является evidence эквивалентности. |
| Markdown используется как build input или исполняемая инструкция | Расширение файла не даёт автоматический reuse/NOT_APPLICABLE. |
| Нет полного GREEN, scope/evidence неизвестны, dirty inputs | Reuse не разрешён; обычные Verify/recovery guardrails сохраняются. |
| Reuse уже подтверждён, затем изменился код | Сравнивать с SHA фактического полного прогона; прежнее доказательство не покрывает новое изменение. |
| Успешный reuse | last_full_green_head не подменяется новым SHA, фиктивный запуск verifier не записывается. |

Самопроверка переходов выполнена в primary без subagents. Реальный продуктовый gate не перезапускался.

Статические проверки UTF-8/BOM, локальных ссылок, JSON/JSONL, ссылок на фазы, совпадения reuse-правил трёх workflows и git diff --check — PASS. Повторная Git-проверка исходного случая Spoon подтвердила diff только AGENTS.md/TESTING.md. Выполнен link-codex.ps1; 12 проверок targets junction и SHA-256 обновлённых skills — PASS.
