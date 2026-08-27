# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Bind IconFlow's public first-proof commands to one source.

The wheel already carries a reviewed demo family and a source-bound receipt.
The public surfaces drifted anyway: PyPI said the package was not published,
while the website still sent a new user through a source checkout and a manual
brand ``ship``. This generator owns the commands that answer the first adoption
question: "Can I install the release and watch its real quality gate pass?"

Run from the repository root::

    python scripts/build_adoption.py
    python scripts/build_adoption.py --check
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PORTABLE = """```bash
pip install iconflow          # or: uv tool install iconflow / pipx install iconflow
iconflow demo --setup --out iconflow-demo
```"""

WINDOWS = r"""python -m venv .venv
.\.venv\Scripts\python.exe -m pip install iconflow
.\.venv\Scripts\python.exe -m iconflow demo --setup `
  --out iconflow-demo"""

POSIX = """python3 -m venv .venv
./.venv/bin/python -m pip install iconflow
./.venv/bin/python -m iconflow demo --setup \\
  --out iconflow-demo"""


@dataclass(frozen=True)
class Binding:
    path: str
    name: str
    body: str

    @property
    def start(self) -> str:
        return f"<!-- adoption:{self.name}:start -->"

    @property
    def end(self) -> str:
        return f"<!-- adoption:{self.name}:end -->"


BINDINGS = (
    Binding("README.md", "portable", PORTABLE),
    Binding("website/index.html", "windows", WINDOWS),
    Binding("website/getting-started/index.html", "windows", WINDOWS),
    Binding("website/getting-started/index.html", "posix", POSIX),
)


def render_binding(text: str, binding: Binding) -> str:
    pattern = re.compile(
        re.escape(binding.start) + r"\n.*?\n" + re.escape(binding.end),
        re.DOTALL,
    )
    replacement = f"{binding.start}\n{binding.body}\n{binding.end}"
    rendered, count = pattern.subn(lambda _: replacement, text)
    if count != 1:
        raise ValueError(
            f"{binding.path}: expected one {binding.name!r} adoption block, found {count}"
        )
    return rendered


def expected_files() -> dict[Path, str]:
    rendered: dict[Path, str] = {}
    for binding in BINDINGS:
        path = ROOT / binding.path
        text = rendered.get(path)
        if text is None:
            text = path.read_text(encoding="utf-8")
        rendered[path] = render_binding(text, binding)
    return rendered


def verify() -> tuple[bool, str]:
    try:
        expected = expected_files()
    except (OSError, ValueError) as exc:
        return False, str(exc)
    stale = [str(path.relative_to(ROOT)) for path, text in expected.items()
             if path.read_text(encoding="utf-8") != text]
    if stale:
        return False, "first-proof commands drifted in " + ", ".join(stale)
    return True, "README and site first-proof commands share one install-and-demo contract"


def build() -> list[str]:
    changed = []
    for path, text in expected_files().items():
        if path.read_text(encoding="utf-8") == text:
            continue
        path.write_text(text, encoding="utf-8", newline="\n")
        changed.append(str(path.relative_to(ROOT)))
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args()
    if args.check:
        ok, detail = verify()
        print(detail)
        return 0 if ok else 1
    changed = build()
    print("Updated " + ", ".join(changed) if changed else "Adoption contract already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
