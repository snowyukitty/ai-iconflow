# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The packaged front door for agents that have no source checkout.

A foreign agent installs IconFlow as a wheel and then needs three things the
repository used to be the only source of: the design procedure (``SKILL.md``),
the reference documents the procedure cites (``docs/*.md``), and a way to put
that skill where its own client discovers skills. This module resolves all of
them out of the package, so ``iconflow docs`` and ``iconflow skill`` behave the
same from a clone, an editable install, and an isolated wheel.

It also owns the single resource resolver the rest of the CLI uses.
"""
from __future__ import annotations

import contextlib
import importlib.resources
import re
from pathlib import Path

# Packaged resource sets, mapped to where they live in the source checkout.
RESOURCE_DIRS: dict[str, tuple[str, ...]] = {
    "presets": ("templates", "presets"),
    "templates": ("templates",),
    "docs": ("docs",),
    "demo": ("demo",),
    "skill": ("skills", "iconflow"),
}
# Legacy top-level namespace packages, for source execution without an install.
_NAMESPACE_FALLBACK = {
    "presets": "templates.presets",
    "templates": "templates",
    "docs": "docs",
    "demo": "demo",
    "skill": "skills.iconflow",
}
# Every file `iconflow skill install` deploys, relative to the skill resource.
SKILL_FILES: tuple[str, ...] = ("SKILL.md", "LICENSE", "agents/openai.yaml")
# User-level skill discovery roots shared by current open Agent Skills clients.
SKILL_HOMES: tuple[tuple[str, ...], ...] = (
    (".claude", "skills"),
    (".agents", "skills"),
    (".copilot", "skills"),
)
# Codex reads `.agents`; a second copy under `.codex` is discovered twice
# because Codex does not merge same-named skills across roots.
LEGACY_SKILL_HOMES: tuple[tuple[str, ...], ...] = ((".codex", "skills"),)
# Files an older deployment wrote that the current skill package does not own.
STALE_SKILL_FILES: tuple[str, ...] = ("README.md",)


def checkout_root(candidate: Path | None = None) -> Path | None:
    """The IconFlow source checkout this package lives in, if it is one.

    On a wheel install the directory above ``iconflow/`` is ``site-packages``,
    where an unrelated distribution's top-level ``docs`` or ``templates``
    directory would otherwise shadow our packaged resources. Two markers only a
    real checkout has — this project's ``pyproject.toml`` beside the package
    source — make that impossible.

    ``candidate`` is for tests; production always asks about this file's own
    parent directory.
    """

    candidate = (
        Path(__file__).resolve().parent.parent if candidate is None else Path(candidate)
    )
    manifest = candidate / "pyproject.toml"
    if not manifest.is_file() or not (candidate / "iconflow" / "cli.py").is_file():
        return None
    try:
        if 'name = "iconflow"' not in manifest.read_text(encoding="utf-8"):
            return None
    except OSError:
        return None
    return candidate


def resource_root(package: str):
    """Return the root Traversable for one packaged resource set.

    Resolution order, most reliable first:

    1. The on-disk source tree next to this package — an editable install
       (``pip install -e .``), a plain checkout, or CI. A modern *strict*
       editable finder does not expose the ``package-dir``-remapped resource
       subpackages to ``importlib.resources`` (nor put the repo root on
       ``sys.path`` for the namespace fallback), so the checkout layout is the
       dependable source there. :func:`checkout_root` proves it *is* a checkout
       before this branch is trusted.
    2. The packaged ``iconflow.resources.*`` subpackage — a real wheel install,
       where there is no checkout so step 1 is skipped.
    3. The top-level namespace directories — legacy source execution.
    """

    subdir = RESOURCE_DIRS.get(package)
    checkout = checkout_root()
    if subdir is not None and checkout is not None:
        source = checkout.joinpath(*subdir)
        if source.is_dir():
            return source
    try:
        return importlib.resources.files(f"iconflow.resources.{package}")
    except ModuleNotFoundError:
        pass
    # `files(None)` resolves to this module's own package rather than failing,
    # so an unknown resource set has to be rejected before that call.
    fallback = _NAMESPACE_FALLBACK.get(package)
    try:
        if fallback is None:
            raise ModuleNotFoundError(package)
        return importlib.resources.files(fallback)
    except (ModuleNotFoundError, TypeError) as exc:
        # An incomplete install, not a bug in the caller: say which resource set
        # is missing and let the CLI report it as exit 2 rather than tracebacking.
        raise RuntimeError(
            f"packaged resource set {package!r} is missing from this install; "
            "reinstall iconflow"
        ) from exc


def resource(package: str, name: str):
    """Return one packaged resource path/Traversable by name.

    ``name`` is a resource-relative POSIX path. It is a library argument, not
    user input, but rejecting escapes here keeps a future caller from turning
    one into a read outside the resource set.
    """

    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts) or Path(name).is_absolute():
        raise ValueError(f"invalid resource name: {name!r}")
    subdir = RESOURCE_DIRS.get(package)
    checkout = checkout_root()
    if subdir is not None and checkout is not None:
        source = checkout.joinpath(*subdir, *parts)
        if source.is_file():
            return source
    return resource_root(package).joinpath(*parts)


def _read(traversable) -> str:
    return traversable.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# licensing


SPDX_COMMENT = re.compile(r"<!--\s*SPDX-License-Identifier:.*?-->\s*", re.DOTALL)


def strip_spdx_comment(text: str) -> str:
    """Remove the licence header before a scaffold is copied into a project.

    The dedication belongs on IconFlow's copy, not on the user's. Left in, it
    rides `master.svg` all the way into the `favicon.svg` they serve in
    production — an IconFlow URL embedded in their shipped asset, which is
    exactly the attribution LICENSES.md section 1 promises never to require.
    The CC0 grant is told to the person on the terminal instead.
    """

    return SPDX_COMMENT.sub("", text, count=1).lstrip()





# The tier map from LICENSES.md, in the form an agent can act on. Kept here
# rather than parsed out of the Markdown so `iconflow license` answers
# identically from a wheel with no checkout.
LICENSE_TIERS: tuple[dict[str, str], ...] = (
    {"tier": "0", "paths": "the icons you make with IconFlow",
     "license": "yours — no conditions",
     "what": "every master.svg, favicon, .ico, .icns, manifest, receipt and case "
             "file you create"},
    {"tier": "1", "paths": "iconflow/ scripts/ tests/", "license": "Apache-2.0",
     "what": "the engine and tooling"},
    {"tier": "1b", "paths": "templates/ (presets)", "license": "CC0-1.0",
     "what": "technique scaffolds and every file IconFlow writes into your project"},
    {"tier": "2", "paths": "docs/ casebook/ skills/", "license": "CC-BY-SA-4.0",
     "what": "the written methodology"},
    {"tier": "3a", "paths": "brand/ demo/ docs/assets/", "license": "CC-BY-4.0",
     "what": "IconFlow's product mark and packaged imagery, plus its trademark"},
    {"tier": "3b", "paths": "gallery/ showcase/ examples/ website/assets/",
     "license": "CC-BY-NC-ND-4.0",
     "what": "the published corpus: 137 archive studies and finished works"},
)

OUTPUT_GUARANTEE: tuple[str, ...] = (
    "No attribution required — you never have to credit IconFlow in your app.",
    "Commercial use unrestricted — ship it, sell it, trademark it.",
    "No copyleft and no share-alike reaches through the tool into your design.",
    "The scaffolds behind `iconflow new` are CC0 public domain, so an icon you "
    "evolve from one inherits nothing.",
    "Reading the playbook and applying it creates no obligation: copyright covers "
    "the prose, not the design methods it describes.",
    "Any IconFlow boilerplate embodied in a file the tool generates for you — a "
    "manifest, a head snippet, a receipt, the Review Lab HTML — is supplied under "
    "CC0, so nothing the toolkit wrote attaches a condition to what it produced.",
    "Not promised, because no licence can: that your icon is copyrightable, "
    "registrable, or clear of someone else's mark. Those remain yours to check.",
)

LICENSE_NOTES: tuple[str, ...] = (
    "The one exception: `iconflow demo` copies IconFlow's OWN product mark so you "
    "can watch the engine prove itself. Do not ship that as your identity.",
    "Full map and boundary cases: LICENSES.md. Trademark: TRADEMARKS.md.",
)


def license_summary() -> dict:
    """The licensing answer an agent needs, in one structure."""

    return {
        "headline": "The icons you make with IconFlow are yours.",
        "your_output": list(OUTPUT_GUARANTEE),
        "tiers": [dict(tier) for tier in LICENSE_TIERS],
        "notes": list(LICENSE_NOTES),
        "documents": {"map": "LICENSES.md", "trademark": "TRADEMARKS.md",
                      "provenance": "docs/PROVENANCE.md"},
    }


# ---------------------------------------------------------------------------
# docs


def doc_names() -> list[str]:
    """Every packaged reference document, without the ``.md`` suffix."""

    root = resource_root("docs")
    names = sorted(
        entry.name[:-3]
        for entry in root.iterdir()
        if entry.name.endswith(".md") and entry.is_file()
    )
    return names


def resolve_doc(name: str) -> str:
    """Map a user-typed document name to its exact packaged name.

    Accepts ``LEARNINGS``, ``learnings``, ``LEARNINGS.md``, and
    ``docs/LEARNINGS.md`` so an agent can quote whatever the prose it just read
    happened to use.
    """

    wanted = name.strip().replace("\\", "/").rsplit("/", 1)[-1]
    if wanted.lower().endswith(".md"):
        wanted = wanted[:-3]
    available = doc_names()
    for candidate in available:
        if candidate.lower() == wanted.lower():
            return candidate
    close = [c for c in available if wanted.lower() in c.lower()]
    hint = ", ".join(close or available)
    raise ValueError(f"unknown document {name!r}; available: {hint}")


def read_doc(name: str) -> str:
    """Return one packaged document's text, resolved leniently by name."""

    return _read(resource("docs", f"{resolve_doc(name)}.md"))


def doc_summary(name: str) -> str:
    """One-line description of a packaged document: its blockquote or subtitle.

    Falls back to the empty string rather than guessing, so the listing never
    invents a description a document does not carry.
    """

    try:
        text = read_doc(name)
    except (OSError, ValueError):
        return ""
    # Every document opens with an SPDX licence comment; it is provenance that
    # should travel with a copied file, but it is not the document's subject.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    paragraph: list[str] = []
    for line in text.splitlines()[:24]:
        stripped = line.strip()
        if stripped.startswith(">"):
            stripped = stripped[1:].strip()
        if not paragraph:
            if not stripped or _is_not_prose(stripped):
                continue
            paragraph.append(stripped)
            continue
        if not stripped:
            break
        paragraph.append(stripped)
    return _first_sentence(" ".join(paragraph))


def _is_not_prose(line: str) -> bool:
    """True for markdown furniture — headings, images, tables, list items, fences.

    ``**bold**`` opens a real sentence in several documents, so a bare ``*``
    prefix is not enough to reject a line; only a list marker is.
    """

    if line.startswith(("#", "!", "|", "```", ">")):
        return True
    return line[:2] in ("- ", "* ", "+ ")


def _first_sentence(text: str, limit: int = 84) -> str:
    """Trim a paragraph to one readable line without cutting a word in half."""

    cleaned = " ".join(text.replace("**", "").split())
    if not cleaned:
        return ""
    stop = cleaned.find(". ")
    if 0 < stop <= limit:
        return cleaned[:stop]
    if len(cleaned) <= limit:
        return cleaned.rstrip(".")
    head = cleaned[:limit].rsplit(" ", 1)[0].rstrip(",;:")
    return f"{head}…"


def export_docs(out_dir: Path, names: list[str] | None = None) -> list[Path]:
    """Write packaged documents into ``out_dir`` and return what was written.

    The images the documents reference come along, because an exemplar gallery
    the reader cannot see is the difference between a distinctive mark and
    another gradient tile. Names are resolved rather than trusted, so no caller
    can steer a write outside ``out_dir``.
    """

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    resolved = [resolve_doc(name) for name in names] if names else doc_names()
    written: list[Path] = []
    for name in resolved:
        target = out_dir / f"{name}.md"
        _write_file(target, read_doc(name))
        written.append(target)
    licence = resource("docs", "LICENSE")
    if licence.is_file():
        _write_file(out_dir / "LICENSE", _read(licence))
        written.append(out_dir / "LICENSE")
    written.extend(_export_doc_assets(out_dir))
    return written


def _export_doc_assets(out_dir: Path) -> list[Path]:
    """Copy `docs/assets/` beside the exported markdown so image links resolve."""

    try:
        assets = resource_root("docs").joinpath("assets")
        entries = sorted(assets.iterdir()) if assets.is_dir() else []
    except (OSError, RuntimeError, ModuleNotFoundError):
        return []
    written: list[Path] = []
    for entry in entries:
        if not entry.is_file():
            continue
        target = out_dir / "assets" / entry.name
        if target.is_symlink():
            raise OSError(f"refusing to write through a symlink: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(entry.read_bytes())
        written.append(target)
    return written


def _write_file(target: Path, text: str) -> None:
    """Write a deployed file, refusing to follow a symlink out of the target.

    These destinations come from the caller (``--out``, ``--dir``), so a
    pre-existing symlink at the path would otherwise let this overwrite a file
    somewhere else entirely.
    """

    if target.is_symlink():
        raise OSError(f"refusing to write through a symlink: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# skill


def skill_text() -> str:
    """The canonical ``SKILL.md`` this build carries."""

    return _read(resource("skill", "SKILL.md"))


def claude_plugin_dirs(home: Path | None = None) -> list[Path]:
    """Installed Claude Code plugin copies of IconFlow, if there are any.

    The plugin already supplies this skill. Writing a second copy into
    ``~/.claude/skills/`` would leave Claude Code holding two skills with the
    same name, so the installer looks here before choosing its roots.
    """

    base = Path.home() if home is None else Path(home)
    cache = base / ".claude" / "plugins" / "cache"
    if not cache.is_dir():
        return []
    return sorted(
        path for path in cache.glob("*/iconflow") if path.is_dir()
    )


def default_skill_roots(home: Path | None = None) -> list[Path]:
    """The user-level ``skills/`` roots this installer writes into.

    Drops the Claude Code root when its plugin already carries the skill; the
    caller reports that so a skipped root is never silent.
    """

    base = Path.home() if home is None else Path(home)
    roots = [base.joinpath(*parts) for parts in SKILL_HOMES]
    if claude_plugin_dirs(base):
        claude_root = base.joinpath(*SKILL_HOMES[0])
        roots = [root for root in roots if root != claude_root]
    return roots


def project_skill_roots(project: Path) -> list[Path]:
    """The same discovery roots, resolved inside one repository.

    A project-local skill travels with the repository, so a teammate's agent
    picks up the procedure by cloning rather than by installing anything.
    """

    project = Path(project)
    return [project.joinpath(*parts) for parts in SKILL_HOMES]


def legacy_skill_dirs(home: Path | None = None) -> list[Path]:
    """Deployment directories a previous IconFlow version created."""

    base = Path.home() if home is None else Path(home)
    return [base.joinpath(*parts, "iconflow") for parts in LEGACY_SKILL_HOMES]


def install_skill(roots: list[Path]) -> tuple[list[Path], list[Path]]:
    """Copy the packaged skill into each ``skills/`` root.

    Returns ``(installed skill directories, files removed)``. Every file comes
    from the package, so this works from an isolated wheel with no checkout
    anywhere on the machine.
    """

    # Read every file before touching a destination: a half-written skill
    # directory would shadow a working one, and an empty one would look
    # installed while teaching the agent nothing.
    payload = {}
    for name in SKILL_FILES:
        source = resource("skill", name)
        if not source.is_file():
            raise OSError(
                f"packaged skill file {name} is missing from this install; "
                "reinstall iconflow"
            )
        payload[name] = _read(source)

    installed: list[Path] = []
    removed: list[Path] = []
    for root in roots:
        destination = Path(root).expanduser().resolve() / "iconflow"
        destination.mkdir(parents=True, exist_ok=True)
        for name, text in payload.items():
            _write_file(destination.joinpath(*name.split("/")), text)
        for stale in STALE_SKILL_FILES:
            path = destination / stale
            if path.is_file() and not path.is_symlink():
                path.unlink()
                removed.append(path)
        installed.append(destination)
    return installed, removed


def remove_legacy_skills(home: Path | None = None) -> list[Path]:
    """Retire duplicate deployments from superseded discovery roots.

    This deletes only files IconFlow itself wrote — the ones in
    :data:`SKILL_FILES` and :data:`STALE_SKILL_FILES` — and then removes the
    directory only if nothing else is left in it. Anything the user added or
    edited by hand survives, and is reported back so the caller can say so.
    """

    removed: list[Path] = []
    for directory in legacy_skill_dirs(home):
        # Only ever a path this module itself composed, never caller input.
        if directory.name != "iconflow":  # pragma: no cover - defensive
            continue
        # A symlinked deployment must be unlinked, never walked: rmtree refuses
        # a symlink, and following it would delete whatever it points at.
        if directory.is_symlink():
            directory.unlink(missing_ok=True)
            removed.append(directory)
            continue
        if not directory.is_dir():
            continue
        for name in (*SKILL_FILES, *STALE_SKILL_FILES):
            path = directory.joinpath(*name.split("/"))
            if path.is_file() and not path.is_symlink():
                path.unlink()
        _prune_empty_dirs(directory)
        if not directory.exists():
            removed.append(directory)
    return removed


def _prune_empty_dirs(directory: Path) -> None:
    """Remove ``directory`` and its subdirectories, but only where empty."""

    for child in sorted(directory.rglob("*"), reverse=True):
        if child.is_dir() and not child.is_symlink() and not any(child.iterdir()):
            child.rmdir()
    with contextlib.suppress(OSError):
        directory.rmdir()
