#!/usr/bin/env python3
"""Refuse a skill-content change that does not move the plugin version.

Claude Code installs this repository's skill through its plugin machinery, and
that machinery decides whether an installed copy is current by comparing
**version strings**. So a change under ``skills/`` that leaves
``skills/.claude-plugin/plugin.json`` alone does not reach anyone: every
machine keeps serving the copy it already has, ``claude plugin update`` answers
"already at the latest version", and it is telling the truth as it understands
it.

That is not hypothetical. On 2026-09-11 a host was found running the
2026-08-21 skill — three weeks and 37 commits behind this repository, missing a
step the procedure had since made mandatory — with every check green, because
the version had read ``0.5.0`` the whole time.

The plugin version is the version of the **skill tree**, not of the Python
package: they were introduced together and are free to diverge, because a
consumer polling the plugin manifest is asking a different question from one
pinning ``iconflow==x.y.z`` on PyPI.

Usage::

    python scripts/check_plugin_version.py            # HEAD~1..HEAD
    python scripts/check_plugin_version.py --base origin/main
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = "skills/.claude-plugin/plugin.json"
WATCHED = "skills/"


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"git {' '.join(arguments)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout


def _manifest_version(ref: str) -> str | None:
    """The plugin version recorded at ``ref``, or None when it has no manifest."""
    completed = subprocess.run(
        ["git", "show", f"{ref}:{MANIFEST}"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    try:
        return str(json.loads(completed.stdout)["version"])
    except (json.JSONDecodeError, KeyError) as error:
        raise SystemExit(f"{MANIFEST} at {ref} is not a plugin manifest: {error}")


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        digits = ""
        for character in piece:
            if not character.isdigit():
                break
            digits += character
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="HEAD~1", help="the ref to compare against")
    parser.add_argument("--head", default="HEAD", help="the ref being published")
    arguments = parser.parse_args()

    changed = [
        line
        for line in _git(
            "diff", "--name-only", f"{arguments.base}..{arguments.head}"
        ).splitlines()
        if line.startswith(WATCHED)
    ]
    content_changed = [line for line in changed if line != MANIFEST]
    if not content_changed:
        print(f"No {WATCHED} content changed between {arguments.base} and {arguments.head}.")
        return 0

    before = _manifest_version(arguments.base)
    after = _manifest_version(arguments.head)
    if after is None:
        print(f"{MANIFEST} is absent at {arguments.head}; a skill tree needs its manifest.")
        return 1
    if before is None:
        print(f"{MANIFEST} is new at {arguments.head} ({after}); nothing to compare.")
        return 0

    listing = "\n  ".join(content_changed)
    if before == after:
        print(
            f"Skill content changed while the plugin version stayed {after}:\n"
            f"  {listing}\n\n"
            f"Every machine that already installed {after} will keep serving the copy it\n"
            "has: the plugin updater compares versions, not content, and will report the\n"
            "stale copy as up to date. Bump the version in "
            f"{MANIFEST}\n(and say what changed in CHANGELOG.md) in this same change.",
        )
        return 1
    if _version_tuple(after) <= _version_tuple(before):
        print(
            f"The plugin version went backwards or sideways: {before} -> {after}.\n"
            "A consumer decides it is current by comparing versions, so the new one must\n"
            "be strictly greater."
        )
        return 1

    print(f"Skill content changed and the plugin version moved {before} -> {after}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
