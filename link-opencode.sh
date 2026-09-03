#!/usr/bin/env bash
#
# Синхронизирует rr-loop assets с macOS-хостами через symlink (аналог junction).
#
# Отличие от link-codex.ps1: на macOS всё (skills, agents, command) подключается
# симлинками — правки в репозитории подхватываются автоматически, повторная
# установка не нужна. Скрипт изменяет только известные rr-loop assets и
# сохраняет остальные пользовательские файлы.
#
# Сфера: OpenCode (~/.config/opencode), ZCode (~/.zcode) и канонический ~/.agents.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

AGENTS=('implementer' 'verifier' 'standards-reviewer' 'spec-reviewer' 'reviser')

REPO_SKILLS_PATH="$REPO_ROOT/skills"
REPO_MARKDOWN_AGENTS_PATH="$REPO_ROOT/agents"
REPO_ZCODE_AGENTS_PATH="$REPO_ROOT/.zcode/agents"
WORKFLOWS=('rr-loop' 'rr-cascade-loop')

USER_AGENTS_ROOT="$HOME/.agents"
OPENCODE_ROOT="$HOME/.config/opencode"
ZCODE_ROOT="$HOME/.zcode"

for workflow in "${WORKFLOWS[@]}"; do
    if [[ ! -f "$REPO_ROOT/command/$workflow.md" ]]; then
        echo "Ошибка: отсутствует канонический command: $REPO_ROOT/command/$workflow.md" >&2
        exit 1
    fi
done

bash "$REPO_ROOT/sync-zcode-agents.sh"

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

shopt -s nullglob
skill_entries=("$REPO_SKILLS_PATH"/*)
shopt -u nullglob

skill_paths=()
for skill_path in "${skill_entries[@]}"; do
    [[ -d "$skill_path" ]] && skill_paths+=("$skill_path")
done

if (( ${#skill_paths[@]} == 0 )); then
    echo "Ошибка: не найдены канонические skills: $REPO_SKILLS_PATH" >&2
    exit 1
fi

for skill_path in "${skill_paths[@]}"; do
    skill_name="$(basename "$skill_path")"
    if [[ ! -f "$skill_path/SKILL.md" ]]; then
        echo "Ошибка: отсутствует SKILL.md: $skill_path" >&2
        exit 1
    fi

    # ~/.agents — каноническая папка agent-compatible skills; OpenCode — host install.
    set_symlink "$USER_AGENTS_ROOT/skills/$skill_name" "$skill_path"
    set_symlink "$OPENCODE_ROOT/skills/$skill_name" "$skill_path"
done

# OpenCode: agents / commands.

for name in "${AGENTS[@]}"; do
    set_symlink "$OPENCODE_ROOT/agents/$name.md" "$REPO_MARKDOWN_AGENTS_PATH/$name.md"
    set_symlink "$ZCODE_ROOT/agents/$name.md" "$REPO_ZCODE_AGENTS_PATH/$name.md"
done

for workflow in "${WORKFLOWS[@]}"; do
    set_symlink "$OPENCODE_ROOT/commands/$workflow.md" "$REPO_ROOT/command/$workflow.md"
done

echo "Agent assets synchronized."
