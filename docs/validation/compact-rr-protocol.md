# Компактный rr protocol

Дата: 2026-10-25. Пользователь разрешил удалить историю ledger и лишние handoff-данные, а после завершения удалять каталог запуска целиком без архивации.

## Изменение

Три entrypoints используют один обязательный `skills/rr-loop/references/protocol.md`. Ledger — атомарный snapshot с OPEN findings, текущими fixed points/counters, refs evidence и результатами внешних действий для recovery. JSONL/seq, закрытые findings, phase history/interim и повтор handoff/checks не требуются. Worker передаёт head вместо head+commit, новые standards refs, только rejected IDs вместо ACCEPTED для каждого ID. Verifier возвращает один plan с результатами вместо повторов commands/scope. Scout передаёт refs notes без копии ответов.

COMPLETED требует merge и согласованные completion actions. После итога каталог данного запуска удаляется целиком без чтения файлов и архивации; незавершённый запуск сохраняется. Product worktrees требуют отдельной авторизации. Реальные ledger Spoon/SmartPhotoOrganizer этой правкой не изменялись.

## Размер

Unicode characters, UTF-8 → LF, trim; это размер текста, не измерение tokenizer или времени. Для новой базовой загрузки учтены entrypoint и общий protocol; условные parallel recovery/completion не включены ни до, ни после.

| Workflow | До | После | Сокращение |
| --- | ---: | ---: | ---: |
| rr-loop | 16 835 | 13 176 | 21,7% |
| rr-cascade-loop-fast | 20 990 | 15 956 | 24,0% |
| rr-parallel-loop | 26 742 | 19 674 | 26,4% |

Шесть канонических agent-контрактов: 10 920 → 10 346 characters. Основное сокращение handoff относится к результатам запуска и повторным передачам данных, не только к размеру prompt.

## Проверка

- Независимый read-only forward-test: critical/RED repairs, новый finding после RED, deferred cascade с docs-only последней задачей, carried critical, parallel locks/scope expansion, transport/dirty transfer, crash merge/transition, reconciliation и GREEN reuse. Найденный consumer `dispositions` исправлен на `rejected`; последний GREEN ref сохраняется отдельно от текущего RED. Atomic handoff → checkpoint → удаление obsolete refs проверен отдельным проходом.
- UTF-8 без BOM, local Markdown links и frontmatter трёх skills — PASS. 18 generated Codex/ZCode/Gemini profiles совпадают с каноническими bodies; Codex TOML разбирается стандартным tomllib.
- Штатный `link-codex.ps1` — PASS. 193 проверки junction targets/копий/generated references, включая 17 Orca accounts и установленный Gemini plugin — PASS. Генератор Gemini теперь рекурсивно распространяет references.
- `git diff --check` и PowerShell AST изменённого генератора — PASS.
- `skill-creator/scripts/quick_validate.py` недоступен из-за отсутствующего PyYAML; frontmatter проверен отдельно для используемых plain scalar полей.

Продуктовые builds/полные rr runs, macOS и ускорение wall-clock не проверялись.

Все references трёх workflows собраны в `skills/rr-loop/references/`: protocol, recovery и completion. Ссылки обновлены; генератор Gemini удаляет прежние известные копии из rr-parallel-loop.
