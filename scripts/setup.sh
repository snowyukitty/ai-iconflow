#!/bin/sh
# One-time setup for IconFlow on macOS and Linux.
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(dirname -- "$script_dir")
runner="$repo_root/.venv/bin/python"

if [ ! -x "$runner" ]; then
    printf '%s\n' "Creating virtual environment..."
    python3 -m venv "$repo_root/.venv"
fi

"$runner" -m pip install -e "$repo_root"
"$runner" -m iconflow setup

skill_src="$repo_root/skills/iconflow"
if [ -f "$skill_src/SKILL.md" ]; then
    for skill_parent in \
        "$HOME/.codex/skills" \
        "$HOME/.claude/skills" \
        "$HOME/.agents/skills" \
        "$HOME/.copilot/skills"
    do
        skill_dst="$skill_parent/iconflow"
        mkdir -p "$skill_dst"
        cp -R "$skill_src/." "$skill_dst/"
        rm -f "$skill_dst/README.md"
        printf '%s\n' "Installed IconFlow skill to $skill_dst"
    done
fi

printf '\n%s\n' "Done. Try:"
printf '%s\n' "  ./.venv/bin/python -m iconflow new gradient-glow --out master.svg"
printf '%s\n' "  ./.venv/bin/python -m iconflow review master.svg"
