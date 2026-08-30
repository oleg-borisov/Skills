#!/usr/bin/env bash
#
# Синхронизирует rr-loop assets с macOS-хостами через symlink (аналог junction).
#
# Отличие от link-codex.ps1: на macOS всё (skills, agents, command) подключается
# симлинками — правки в репозитории подхватываются автоматически, повторная
# установка не нужна. Скрипт изменяет только известные rr-loop assets и
# сохраняет остальные пользовательские файлы.
#
# Сфера: OpenCode (~/.config/opencode) и канонический ~/.agents.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

AGENTS=('implementer' 'verifier' 'standards-reviewer' 'spec-reviewer' 'reviser')

REPO_SKILLS_PATH="$REPO_ROOT/skills"
RR_LOOP_SKILL_PATH="$REPO_SKILLS_PATH/rr-loop"
REPO_MARKDOWN_AGENTS_PATH="$REPO_ROOT/agents"
COMMAND_SOURCE_PATH="$REPO_ROOT/command/rr-loop.md"

USER_AGENTS_ROOT="$HOME/.agents"
OPENCODE_ROOT="$HOME/.config/opencode"

if [[ ! -d "$RR_LOOP_SKILL_PATH" ]]; then
    echo "Ошибка: отсутствует канонический skill: $RR_LOOP_SKILL_PATH" >&2
    exit 1
fi
if [[ ! -f "$COMMAND_SOURCE_PATH" ]]; then
    echo "Ошибка: отсутствует канонический command: $COMMAND_SOURCE_PATH" >&2
    exit 1
fi

# set_symlink <path> <target>
#  - Создаёт родительский каталог при необходимости.
#  - Если <path> уже симлинк — пересоздаёт его.
#  - Если <path> реальный file/dir — неявно не трогает, чтобы не удалить данные.
set_symlink() {
    local path="$1"
    local target="$2"

    if [[ ! -e "$target" ]]; then
        echo "Ошибка: цель отсутствует: $target" >&2
        exit 1
    fi

    local parent
    parent="$(dirname "$path")"
    if [[ ! -d "$parent" ]]; then
        mkdir -p "$parent"
    fi

    if [[ -L "$path" ]]; then
        rm -f "$path"
    elif [[ -e "$path" ]]; then
        echo "Пропускаю (реальный файл/каталог, не симлинк): $path" >&2
        return 1
    fi

    ln -s "$target" "$path"
    echo "Symlink: $path -> $target"
}

# Skill в каноническом ~/.agents (opencode читает его как agent-compatible skills).
set_symlink "$USER_AGENTS_ROOT/skills/rr-loop" "$RR_LOOP_SKILL_PATH"

# OpenCode: skills / agents / commands.
set_symlink "$OPENCODE_ROOT/skills/rr-loop" "$RR_LOOP_SKILL_PATH"

for name in "${AGENTS[@]}"; do
    set_symlink "$OPENCODE_ROOT/agents/$name.md" "$REPO_MARKDOWN_AGENTS_PATH/$name.md"
done

set_symlink "$OPENCODE_ROOT/commands/rr-loop.md" "$COMMAND_SOURCE_PATH"

echo "Agent assets synchronized."
