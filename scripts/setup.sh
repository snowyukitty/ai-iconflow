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

# `skill install` owns every deployment path, so a wheel install and a checkout
# put the same files in the same places.
"$runner" -m iconflow skill install

printf '\n%s\n' "Done. Try:"
printf '%s\n' "  ./.venv/bin/python -m iconflow doctor"
printf '%s\n' "  ./.venv/bin/python -m iconflow demo --out iconflow-demo"
