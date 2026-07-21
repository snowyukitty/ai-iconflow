# The `/iconflow` Claude Code skill

`SKILL.md` here is the canonical source of the `/iconflow` skill. It lives with
the toolkit it drives so the two version together — when the `iconflow` CLI or
its docs change, the skill changes in the same commit, instead of drifting as a
separate copy in a user profile.

## Install

`scripts/setup.ps1` copies it into `~/.claude/skills/iconflow/` as part of
one-time setup. To (re)install it on its own:

```powershell
$dst = "$env:USERPROFILE\.claude\skills\iconflow"
New-Item -ItemType Directory $dst -Force | Out-Null
Copy-Item .\skills\iconflow\SKILL.md "$dst\SKILL.md" -Force
```

## Editing

Edit `SKILL.md` here, not the installed copy — the installed copy is a
deployment, and a hand edit there is lost on the next setup. After editing,
re-run the install snippet above to deploy it.

The skill references the toolkit by resolving the workspace root (the
`AI_Projects` directory), never a fixed drive letter, so it works wherever the
checkout lives.
