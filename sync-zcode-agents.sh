#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$REPO_ROOT/agents"
OUTPUT_ROOT="$REPO_ROOT/.zcode/agents"
AGENTS=('implementer' 'verifier' 'standards-reviewer' 'spec-reviewer' 'reviser')

mkdir -p "$OUTPUT_ROOT"

for agent_name in "${AGENTS[@]}"; do
    source_path="$SOURCE_ROOT/$agent_name.md"
    output_path="$OUTPUT_ROOT/$agent_name.md"

    if [[ ! -f "$source_path" ]]; then
        echo "Ошибка: отсутствует канонический агент: $source_path" >&2
        exit 1
    fi

    description="$(awk '/^description:[[:space:]]*/ { sub(/^description:[[:space:]]*/, ""); print; exit }' "$source_path")"
    if [[ -z "$description" ]]; then
        echo "Ошибка: в $source_path отсутствует description" >&2
        exit 1
    fi

    {
        printf '%s\n' '---' "name: $agent_name" "description: $description"
        case "$agent_name" in
            verifier|standards-reviewer|spec-reviewer)
                printf '%s\n' 'tools:' '  - Read' '  - Grep' '  - Glob' '  - Bash'
                ;;
        esac
        printf '%s\n' '---'
        awk 'BEGIN { delimiters = 0 } /^---$/ { delimiters++; next } delimiters >= 2 { print }' "$source_path" \
            | sed '${/^$/d;}'
    } > "$output_path"
done

echo "Generated ${#AGENTS[@]} ZCode agent profiles."
