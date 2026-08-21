---
description: Install and verify the IconFlow toolchain, then prove it with the packaged demo
argument-hint: "[--demo]"
---

<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
Get the IconFlow toolchain working in this environment, then prove it. Report
what you did in three or four lines — do not narrate every command.

This installs the **Python toolkit**. The design procedure itself already came
with this plugin, so do not deploy a second copy of the skill for Claude Code.

1. **Is it already here?** Run `iconflow --version`. If that answers, skip to
   step 3.

2. **Install it.** IconFlow is a Python 3.10+ package with two dependencies and
   no API key.

   - `uv tool install iconflow`
   - `pipx install iconflow`
   - a project venv: `python -m venv .venv` then
     `.venv/bin/python -m pip install iconflow` (`.venv\Scripts\python.exe`
     on Windows) — that interpreter is then the runner in place of `iconflow`.

   Or, from a source checkout the user already has, its `scripts/setup.ps1` or
   `scripts/setup.sh`.

   If the user has none of `uv`, `pipx`, or a usable `python`, say so and stop;
   do not install a language runtime without asking.

3. **Fetch the Chromium renderer:** `iconflow setup`. This is the only step that
   uses the network. Rendering and builds are local afterwards.

4. **Prove it:** `iconflow doctor`. Every check must be PASS; each FAIL prints a
   `fix` command you can paste. Then, if `$ARGUMENTS` contains `--demo`, run
   `iconflow demo --out iconflow-demo` and read the review sheet it writes —
   that materializes an already-reviewed family and runs check → review → ship
   against its receipt, so a green run proves the whole engine end to end.

5. **Only if the user also works in Codex or Copilot**, deploy the skill for
   those clients with `iconflow skill install`. It writes into
   `~/.agents/skills/` and `~/.copilot/skills/` and deliberately skips
   `~/.claude/skills/`, because this plugin already provides the same skill to
   Claude Code and a second copy would show up twice. Skip this step entirely
   for a Claude-Code-only user.

Finish by telling the user the runner to use (`iconflow`, or the venv
interpreter path) and that `/iconflow:icon` designs an icon.
