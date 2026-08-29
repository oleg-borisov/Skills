# Интеграция CodeBuddy

`link-codex.ps1` поддерживает CodeBuddy Code в user scope:

- `~/.codebuddy/skills/rr-loop` — junction на `skills/rr-loop`;
- `~/.codebuddy/agents` — junction на генерируемые `.codebuddy/agents`.

Не подключайте `agents/` напрямую: CodeBuddy требует у sub-agent обязательное поле `name` и использует свои `tools` и `permissionMode`. `sync-codebuddy-agents.ps1` адаптирует пять канонических leaf-agent contracts; исходники остаются в `agents/`.

Адаптеры ограничивают verifier и reviewers инструментами `Read, Glob, Grep, Bash` и режимом `plan`; implementer и reviser получают `Read, Write, Edit, Glob, Grep, Bash` с `acceptEdits`. Модель намеренно не фиксируется и наследуется из текущей конфигурации CodeBuddy.

После запуска синхронизации откройте новую сессию CodeBuddy либо выполните `/agents`, чтобы увидеть профили. `rr-loop` доступен как skill и вызывается из primary-контекста. Никакие hooks в CodeBuddy settings не включаются.

Источники: [Skills](https://www.codebuddy.ai/docs/cli/skills), [Sub-Agents](https://www.codebuddy.ai/docs/cli/sub-agents), [Creating Plugins](https://www.codebuddy.ai/docs/cli/plugins).
