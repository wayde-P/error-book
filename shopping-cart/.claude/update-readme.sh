#!/bin/bash
# PostToolUse hook — runs after every Edit/Write.
# Reads the changed file path from stdin (JSON), then asks Claude to
# decide if the change warrants updating README.md.

set -euo pipefail

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only act on source files; skip the README itself and generated/config files
if [[ -z "$FILE" ]]; then exit 0; fi
if [[ "$FILE" == *README* ]]; then exit 0; fi
if [[ "$FILE" == *node_modules* || "$FILE" == *dist/* || "$FILE" == *.json || "$FILE" == *.yaml || "$FILE" == *.yml || "$FILE" == *.lock ]]; then exit 0; fi
if [[ ! "$FILE" =~ \.(py|jsx?|tsx?)$ ]]; then exit 0; fi

# Use the shopping-cart project root (the directory containing this script's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

README="$REPO_ROOT/README.md"
if [[ ! -f "$README" ]]; then exit 0; fi

# Emit an additionalContext message back to Claude asking it to update README
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "A source file was just modified: $FILE\n\nPlease review the current README.md at $README and decide if any section needs updating to reflect this change. Only update sections that are meaningfully affected (architecture, API endpoints, project structure, key design decisions). Do NOT update the README for trivial changes like adding a comment or fixing a typo. If an update is warranted, apply it now."
  }
}
EOF
