"""The casebook — the memory that makes the design system self-evolving.

Every shipped icon is recorded as one structured markdown case file in
`casebook/`. The engine can then aggregate them (`iconflow case stats`) and
tell the agent-designer *where the system is weak*:

  - which rubric axis chronically scores lowest on the first pass
    (→ the playbook section that needs strengthening),
  - which signature devices are being over-used
    (→ the toolkit is developing its own house cliché),
  - which lessons have not yet been distilled into the docs
    (→ run the distillation protocol in docs/EVOLUTION.md).

The files are the source of truth and are hand-editable; this module only
needs a forgiving line-based parser, not YAML.
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

AXES = ("legibility", "distinctiveness", "balance", "color", "scalability", "craft")

# stats() thresholds — when crossed, the report tells the agent to act.
DISTILL_THRESHOLD = 3       # undistilled lessons before "distill now"
HOUSE_CLICHE_SHARE = 0.5    # one signature device carrying > half of all cases
HOUSE_CLICHE_MIN_CASES = 4  # ...once there are enough cases to mean anything

_LESSON_RE = re.compile(r"^-\s*\[( |x|X)\]\s*(.+)$")
_KV_RE = re.compile(r"^([a-z_]+)\s*:\s*(.*)$")
_SCORE_RE = re.compile(r"([a-z_]+)\s*=\s*(\d+)")
_SCORE_ITEM_RE = re.compile(r"([a-z_]+)\s*=\s*(\d+)", re.I)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")

CASE_STATUSES = ("draft", "reviewed", "approved", "shipped", "archived")


@dataclass
class Case:
    slug: str
    path: Path
    date: str = ""
    project: str = ""
    targets: str = ""
    essence: str = ""
    style_family: str = ""
    signature_device: str = ""
    device_family: str = ""
    device_detail: str = ""
    concept_lens: str = ""
    status: str = ""
    cliche_avoided: str = ""
    scores_first: dict[str, int] = field(default_factory=dict)
    scores_final: dict[str, int] = field(default_factory=dict)
    iterations: int = 0
    lessons: list[tuple[bool, str]] = field(default_factory=list)  # (distilled, text)

    @property
    def undistilled(self) -> list[str]:
        return [text for distilled, text in self.lessons if not distilled]


@dataclass(frozen=True)
class LintIssue:
    path: Path
    message: str
    severity: str = "error"


def normalize_taxonomy(value: str) -> str:
    """Normalize a controlled vocabulary label without discarding Unicode."""

    return re.sub(r"[^\w]+", "-", value.strip().casefold(), flags=re.UNICODE).strip("-")


def normalize_detail(value: str) -> str:
    """Normalize human-readable detail while preserving its wording."""

    return " ".join(value.strip().split())


def parse_scores(raw: str) -> dict[str, int]:
    """Strictly parse comma/space-separated ``axis=score`` pairs.

    The old parser silently ignored typos, duplicate axes, and trailing text.
    Shipping metadata must fail closed instead.  ``parse_case`` retains a
    forgiving private parser so historical hand-edited cases still load.
    """

    raw = re.sub(r"\s*=\s*", "=", raw.strip())
    if not raw:
        return {}
    parts = re.split(r"[\s,]+", raw)
    scores: dict[str, int] = {}
    for part in parts:
        match = _SCORE_ITEM_RE.fullmatch(part)
        if not match:
            raise ValueError(
                f"invalid score token '{part}'; expected axis=1..5"
            )
        axis, value = match.group(1).lower(), int(match.group(2))
        if axis in scores:
            raise ValueError(f"duplicate rubric axis: {axis}")
        scores[axis] = value
    validate_scores(scores)
    return scores


def _parse_scores_loose(raw: str) -> dict[str, int]:
    """Backward-compatible parser for existing casebook markdown."""

    return {k.lower(): int(v) for k, v in _SCORE_RE.findall(raw.lower())}


def validate_scores(scores: dict[str, int]) -> None:
    unknown = sorted(set(scores) - set(AXES))
    if unknown:
        raise ValueError(
            f"unknown rubric axis: {', '.join(unknown)}. Axes: {', '.join(AXES)}"
        )
    bad = sorted(
        k for k, v in scores.items()
        if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 5
    )
    if bad:
        raise ValueError(f"scores must be 1..5: {', '.join(bad)}")


def validate_date(value: str) -> str:
    """Return a canonical ISO date, rejecting path-like or loose values."""

    if not _DATE_RE.fullmatch(value):
        raise ValueError("date must use YYYY-MM-DD")
    try:
        parsed = _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid calendar date: {value}") from exc
    canonical = parsed.isoformat()
    if canonical != value:
        raise ValueError("date must use canonical YYYY-MM-DD")
    return canonical


def default_casebook_dir() -> Path:
    """Return a writable, project-local casebook path.

    Package resources are immutable after wheel installation.  Keeping cases
    relative to the current project also makes them straightforward to review
    and commit.  ``ICONFLOW_CASEBOOK_DIR`` supports teams with a shared ledger.
    """

    override = os.environ.get("ICONFLOW_CASEBOOK_DIR")
    return Path(override).expanduser() if override else Path.cwd() / "casebook"


def parse_case(path: str | Path) -> Case:
    path = Path(path)
    case = Case(slug=path.stem, path=path)
    lines = path.read_text(encoding="utf-8").splitlines()

    in_front = False
    front_done = False
    in_lessons = False
    for line in lines:
        stripped = line.strip()
        if stripped == "---" and not front_done:
            if in_front:
                front_done = True
                in_front = False
            else:
                in_front = True
            continue
        if in_front:
            m = _KV_RE.match(stripped)
            if not m:
                continue
            key, value = m.group(1), m.group(2).strip()
            if key in ("scores_first", "scores_final"):
                setattr(case, key, _parse_scores_loose(value))
            elif key == "iterations":
                try:
                    case.iterations = int(value)
                except ValueError:
                    pass
            elif key in ("slug", "date", "project", "targets", "essence",
                         "style_family", "signature_device", "device_family",
                         "device_detail", "concept_lens", "status",
                         "cliche_avoided"):
                setattr(case, key, value)
            continue
        if stripped.lower().startswith("## lessons"):
            in_lessons = True
            continue
        if stripped.startswith("## "):
            in_lessons = False
            continue
        if in_lessons:
            m = _LESSON_RE.match(stripped)
            if m:
                case.lessons.append((m.group(1).lower() == "x", m.group(2).strip()))
    # New taxonomy fields are additive.  Historical free-text devices remain
    # valid detail, but we do not invent a family classification that the
    # original designer never chose.
    case.device_family = normalize_taxonomy(case.device_family)
    case.device_detail = normalize_detail(case.device_detail or case.signature_device)
    case.concept_lens = normalize_taxonomy(case.concept_lens)
    case.status = normalize_taxonomy(case.status) or "shipped"
    if not case.signature_device and case.device_detail:
        case.signature_device = case.device_detail
    return case


def load_casebook(directory: str | Path) -> list[Case]:
    directory = Path(directory)
    if not directory.is_dir():
        return []
    cases = [parse_case(p) for p in sorted(directory.glob("*.md"))
             if p.name.upper() != "README.MD"]
    return cases


_TEMPLATE = """---
slug: {slug}
date: {date}
project: {project}
targets: {targets}
essence: {essence}
style_family: {style_family}
signature_device: {signature_device}
device_family: {device_family}
device_detail: {device_detail}
concept_lens: {concept_lens}
cliche_avoided: {cliche_avoided}
status: {status}
scores_first: {scores_first}
scores_final: {scores_final}
iterations: {iterations}
---

## Summary
{summary}

## What failed first
<!-- What the earlier passes got wrong and which change fixed it. This is the
     raw material for future lessons — be specific (axis, size, shape). -->

## Lessons
<!-- One reusable rule per bullet. `- [ ]` = not yet distilled into the docs;
     flip to `- [x]` after promoting it (see docs/EVOLUTION.md). -->
{lessons}
"""


def _fmt_scores(scores: dict[str, int]) -> str:
    return " ".join(f"{k}={scores[k]}" for k in AXES if k in scores)


def new_case(directory: str | Path, slug: str, *, project: str = "",
             targets: str = "", essence: str = "", style_family: str = "",
             signature_device: str = "", cliche_avoided: str = "",
             device_family: str = "", device_detail: str = "",
             concept_lens: str = "", status: str = "shipped",
             scores_first: dict[str, int] | None = None,
             scores_final: dict[str, int] | None = None,
             iterations: int = 1, summary: str = "",
             lessons: list[str] | None = None, date: str = "") -> Path:
    """Scaffold a structured case file. Returns the created path."""
    slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    if not slug:
        raise ValueError("slug must contain at least one alphanumeric character")
    for scores in (scores_first, scores_final):
        if scores:
            validate_scores(scores)
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 1:
        raise ValueError("iterations must be an integer >= 1")
    directory = Path(directory).expanduser().resolve(strict=False)
    directory.mkdir(parents=True, exist_ok=True)
    date = validate_date(date or _dt.date.today().isoformat())
    status = normalize_taxonomy(status)
    if status not in CASE_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(CASE_STATUSES)}")
    device_detail = normalize_detail(device_detail or signature_device)
    signature_device = normalize_detail(signature_device or device_detail)
    device_family = normalize_taxonomy(device_family)
    concept_lens = normalize_taxonomy(concept_lens)
    # Front-matter values are single-line by design; rejecting line breaks
    # prevents accidental metadata injection in hand-composed CLI arguments.
    front_values = {
        "project": project, "targets": targets, "essence": essence,
        "style_family": style_family, "signature_device": signature_device,
        "device_family": device_family, "device_detail": device_detail,
        "concept_lens": concept_lens, "cliche_avoided": cliche_avoided,
    }
    multiline = [key for key, value in front_values.items() if "\n" in value or "\r" in value]
    if multiline:
        raise ValueError(f"front-matter fields must be single-line: {', '.join(multiline)}")
    path = (directory / f"{date}-{slug}.md").resolve(strict=False)
    try:
        path.relative_to(directory)
    except ValueError as exc:  # defense in depth if filename rules change later
        raise ValueError("case path escapes the selected casebook directory") from exc
    if path.exists():
        raise ValueError(f"case already exists: {path}")
    if any("\n" in text or "\r" in text for text in (lessons or [])):
        raise ValueError("each lesson must be a single line")
    lesson_lines = "\n".join(f"- [ ] {text}" for text in (lessons or [])) or "- [ ] "
    path.write_text(_TEMPLATE.format(
        slug=slug, date=date, project=project, targets=targets, essence=essence,
        style_family=style_family, signature_device=signature_device,
        device_family=device_family, device_detail=device_detail,
        concept_lens=concept_lens, status=status,
        cliche_avoided=cliche_avoided,
        scores_first=_fmt_scores(scores_first or {}),
        scores_final=_fmt_scores(scores_final or {}),
        iterations=iterations,
        summary=summary or "<!-- One paragraph: the brief, the winning concept, why it won. -->",
        lessons=lesson_lines,
    ), encoding="utf-8")
    return path


def lint_case(path: str | Path, *, root: str | Path | None = None) -> list[LintIssue]:
    """Validate one case strictly while keeping the normal loader forgiving."""

    path = Path(path)
    issues: list[LintIssue] = []
    if root is not None:
        root_path = Path(root).expanduser().resolve(strict=False)
        try:
            path.resolve(strict=False).relative_to(root_path)
        except ValueError:
            issues.append(LintIssue(path, "case path escapes the selected casebook directory"))
            return issues
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [LintIssue(path, f"cannot read UTF-8 case file: {exc}")]

    if not lines or lines[0].strip() != "---":
        return [LintIssue(path, "front matter must begin on line 1 with ---")]
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        return [LintIssue(path, "front matter has no closing ---")]

    metadata: dict[str, str] = {}
    for number, line in enumerate(lines[1:end], start=2):
        match = _KV_RE.fullmatch(line.strip())
        if not match:
            issues.append(LintIssue(path, f"line {number}: expected key: value"))
            continue
        key, value = match.group(1), match.group(2).strip()
        if key in metadata:
            issues.append(LintIssue(path, f"line {number}: duplicate key '{key}'"))
        metadata[key] = value

    for required in ("slug", "date", "scores_first", "scores_final", "iterations"):
        if required not in metadata:
            issues.append(LintIssue(path, f"missing front-matter key: {required}"))

    date = metadata.get("date", "")
    if date:
        try:
            validate_date(date)
        except ValueError as exc:
            issues.append(LintIssue(path, str(exc)))
        if not path.name.startswith(date + "-"):
            issues.append(LintIssue(path, "filename must start with the case date", "warning"))

    slug = metadata.get("slug", "")
    normalized_slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    if not normalized_slug:
        issues.append(LintIssue(path, "slug must contain an ASCII letter or number"))
    elif slug != normalized_slug:
        issues.append(LintIssue(path, f"slug is not canonical; use '{normalized_slug}'"))

    for score_key in ("scores_first", "scores_final"):
        if score_key not in metadata:
            continue
        try:
            parsed = parse_scores(metadata[score_key])
        except ValueError as exc:
            issues.append(LintIssue(path, f"{score_key}: {exc}"))
            continue
        if metadata.get("status", "shipped") == "shipped":
            missing = [axis for axis in AXES if axis not in parsed]
            if missing:
                issues.append(LintIssue(
                    path,
                    f"{score_key} is incomplete for a shipped case: {', '.join(missing)}",
                ))

    iterations = metadata.get("iterations")
    if iterations is not None:
        try:
            if int(iterations) < 1:
                raise ValueError
        except ValueError:
            issues.append(LintIssue(path, "iterations must be an integer >= 1"))

    status = normalize_taxonomy(metadata.get("status", "shipped"))
    if status not in CASE_STATUSES:
        issues.append(LintIssue(path, f"status must be one of: {', '.join(CASE_STATUSES)}"))

    # These warnings provide a safe migration path for historical cases: they
    # remain loadable and count in stats, while lint makes the missing taxonomy
    # explicit when a team is ready to normalize them.
    for key in ("device_family", "device_detail", "concept_lens", "status"):
        if key not in metadata:
            issues.append(LintIssue(path, f"legacy case is missing normalized key: {key}", "warning"))
    for key in ("device_family", "concept_lens"):
        value = metadata.get(key, "")
        if value and value != normalize_taxonomy(value):
            issues.append(LintIssue(
                path, f"{key} is not normalized; use '{normalize_taxonomy(value)}'", "warning"
            ))
    detail = metadata.get("device_detail", "")
    if detail and detail != normalize_detail(detail):
        issues.append(LintIssue(path, "device_detail contains irregular whitespace", "warning"))
    return issues


def lint_casebook(directory: str | Path) -> list[LintIssue]:
    """Lint all direct Markdown cases and reject symlink escapes."""

    directory = Path(directory).expanduser().resolve(strict=False)
    if not directory.exists():
        return [LintIssue(directory, "casebook directory does not exist")]
    if not directory.is_dir():
        return [LintIssue(directory, "casebook path is not a directory")]
    issues: list[LintIssue] = []
    for path in sorted(directory.glob("*.md")):
        if path.name.upper() == "README.MD":
            continue
        issues.extend(lint_case(path, root=directory))
    return issues


def _mean(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


def stats(cases: list[Case]) -> dict:
    """Aggregate the casebook into an actionable health report (as data)."""
    axis_first = {a: _mean([c.scores_first[a] for c in cases if a in c.scores_first])
                  for a in AXES}
    axis_final = {a: _mean([c.scores_final[a] for c in cases if a in c.scores_final])
                  for a in AXES}
    axis_counts_first = {a: sum(a in c.scores_first for c in cases) for a in AXES}
    axis_counts_final = {a: sum(a in c.scores_final for c in cases) for a in AXES}
    scored = {a: v for a, v in axis_first.items() if v is not None}
    weakest_axes: list[str] = []
    if scored:
        minimum = min(scored.values())
        weakest_axes = [axis for axis in AXES if axis in scored and abs(scored[axis] - minimum) < 1e-9]
    weakest_axis = weakest_axes[0] if weakest_axes else None

    devices: dict[str, int] = {}
    families: dict[str, int] = {}
    device_families: dict[str, int] = {}
    concept_lenses: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for c in cases:
        if c.signature_device:
            key = normalize_detail(c.signature_device).casefold()
            devices[key] = devices.get(key, 0) + 1
        if c.style_family:
            key = normalize_taxonomy(c.style_family)
            families[key] = families.get(key, 0) + 1
        if c.device_family:
            key = normalize_taxonomy(c.device_family)
            device_families[key] = device_families.get(key, 0) + 1
        if c.concept_lens:
            key = normalize_taxonomy(c.concept_lens)
            concept_lenses[key] = concept_lenses.get(key, 0) + 1
        key = normalize_taxonomy(c.status) or "shipped"
        statuses[key] = statuses.get(key, 0) + 1

    house_cliche = None
    # Family-level grouping catches conceptual repetition even when authors use
    # slightly different prose for each device detail.
    cliche_groups: dict[str, int] = {}
    for c in cases:
        if c.device_family:
            key = c.device_family
        elif c.signature_device:
            key = normalize_detail(c.signature_device).casefold()
        else:
            continue
        cliche_groups[key] = cliche_groups.get(key, 0) + 1
    if len(cases) >= HOUSE_CLICHE_MIN_CASES and cliche_groups:
        top_device, top_count = max(cliche_groups.items(), key=lambda kv: kv[1])
        if top_count / len(cases) > HOUSE_CLICHE_SHARE:
            house_cliche = (top_device, top_count)

    undistilled = [(c.path.name, text) for c in cases for text in c.undistilled]
    iterations = _mean([c.iterations for c in cases if c.iterations > 0])

    return {
        "cases": len(cases),
        "axis_first": axis_first,
        "axis_final": axis_final,
        "axis_counts_first": axis_counts_first,
        "axis_counts_final": axis_counts_final,
        "weakest_axis": weakest_axis,
        "weakest_axes": weakest_axes,
        "devices": devices,
        "families": families,
        "device_families": device_families,
        "concept_lenses": concept_lenses,
        "statuses": statuses,
        "house_cliche": house_cliche,
        "undistilled": undistilled,
        "mean_iterations": iterations,
    }


def format_stats(s: dict) -> list[str]:
    """Render stats() as the lines the CLI prints — written for an AI agent
    to act on, not just to read."""
    lines = [f"casebook: {s['cases']} case(s)"]
    if not s["cases"]:
        lines.append("Empty. After each shipped icon run: python -m iconflow case new --slug <slug> ...")
        return lines

    lines.append("first-pass rubric means (5 = never needs that fix):")
    for a in AXES:
        first, final = s["axis_first"][a], s["axis_final"][a]
        if first is None and final is None:
            continue
        fmt = lambda v: f"{v:.1f}" if v is not None else "-"
        first_n = s.get("axis_counts_first", {}).get(a, 0)
        final_n = s.get("axis_counts_final", {}).get(a, 0)
        lines.append(
            f"  {a:<16} first {fmt(first)} (n={first_n})   "
            f"final {fmt(final)} (n={final_n})"
        )
    weakest_axes = s.get("weakest_axes") or ([s["weakest_axis"]] if s["weakest_axis"] else [])
    if weakest_axes:
        label = ", ".join(f"'{axis}'" for axis in weakest_axes)
        lines.append(
            f"EVOLUTION TARGET: {label} "
            + ("are tied as the weakest first-pass axes — " if len(weakest_axes) > 1
               else "is the weakest first-pass axis — ")
            + "strengthen the playbook/concepting guidance that prevents those first-draft mistakes "
            "(protocol: docs/EVOLUTION.md §2)."
        )
    if s["mean_iterations"] is not None:
        lines.append(f"mean review iterations to ship: {s['mean_iterations']:.1f}"
                     + (" — above 3: first drafts are weak; distill harder rules."
                        if s["mean_iterations"] > 3 else ""))
    if s["devices"]:
        top = sorted(s["devices"].items(), key=lambda kv: -kv[1])
        lines.append("signature devices used: "
                     + ", ".join(f"{k} x{v}" for k, v in top))
    if s.get("device_families"):
        top = sorted(s["device_families"].items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append("device families: " + ", ".join(f"{k} x{v}" for k, v in top))
    if s.get("families"):
        top = sorted(s["families"].items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append("style families: " + ", ".join(f"{k} x{v}" for k, v in top))
    if s.get("concept_lenses"):
        top = sorted(s["concept_lenses"].items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append("concept lenses: " + ", ".join(f"{k} x{v}" for k, v in top))
    if s.get("statuses"):
        top = sorted(s["statuses"].items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append("case status: " + ", ".join(f"{k} x{v}" for k, v in top))
    if s["house_cliche"]:
        device, count = s["house_cliche"]
        lines.append(
            f"HOUSE-CLICHE WARNING: '{device}' used in {count}/{s['cases']} cases — the toolkit is "
            "developing its own cliche. Prefer a different signature device on the next brief."
        )
    if s["undistilled"]:
        lines.append(f"{len(s['undistilled'])} undistilled lesson(s):")
        for name, text in s["undistilled"]:
            lines.append(f"  [ ] ({name}) {text}")
        if len(s["undistilled"]) >= DISTILL_THRESHOLD:
            lines.append(
                "DISTILL NOW: promote recurring lessons into docs/LEARNINGS.md (and the playbook "
                "if load-bearing), then flip their checkboxes to [x]. Protocol: docs/EVOLUTION.md §3."
            )
    else:
        lines.append("no undistilled lessons — casebook and docs are in sync.")
    return lines


_ATLAS_STYLE = """
:root{color-scheme:dark;--ink:#f5f1e8;--muted:#a9abb4;--paper:#17181c;
--panel:#22242a;--line:#393b43;--signal:#ff5b3d;--good:#68d391;--bad:#ff7b72}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{width:min(1200px,calc(100% - 32px));margin:0 auto;padding:48px 0 72px}
h1,h2,h3,p{margin-top:0}h1{font-size:clamp(2rem,5vw,4rem);letter-spacing:-.045em;
margin-bottom:8px}h2{margin-top:40px;font-size:1.35rem}h3{font-size:1.05rem}
.eyebrow,.muted{color:var(--muted)}.eyebrow{text-transform:uppercase;letter-spacing:.16em;
font-size:.72rem}.metrics,.distributions,.cases{display:grid;gap:16px}
.metrics{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:28px 0}
.metric,.panel,.case,.empty{background:var(--panel);border:1px solid var(--line);border-radius:16px}
.metric{padding:18px}.metric strong{display:block;font-size:1.8rem}.panel{padding:20px}
.distributions{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}.cases{grid-template-columns:
repeat(auto-fit,minmax(min(100%,420px),1fr))}.case{padding:22px;overflow:hidden}
.case-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}
.tags{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}.tag{border:1px solid var(--line);
border-radius:999px;padding:3px 9px;color:var(--muted);font-size:.78rem}.tag.status{color:var(--ink)}
table{width:100%;border-collapse:separate;border-spacing:4px;font-variant-numeric:tabular-nums}
th,td{padding:7px 8px;text-align:center;border-radius:6px}th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-size:.73rem;text-transform:uppercase;letter-spacing:.07em}
.score-0{background:#303139;color:var(--muted)}.score-1{background:#592c31}.score-2{background:#714032}
.score-3{background:#725f35}.score-4{background:#315e4a}.score-5{background:#23705a}
.delta-up{color:var(--good)}.delta-down{color:var(--bad)}.delta-flat{color:var(--muted)}
.bar-row{display:grid;grid-template-columns:minmax(90px,1fr) 3fr auto;gap:10px;align-items:center;
margin:9px 0}.bar-track{height:8px;background:#303139;border-radius:99px;overflow:hidden}
.bar-fill{height:100%;width:var(--share);background:var(--signal);border-radius:inherit}
.bar-label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.lessons{padding-left:20px;margin-bottom:0}
.lessons li{margin:6px 0}.signal{border-left:3px solid var(--signal);padding:8px 0 8px 14px;
margin:10px 0}.empty{padding:40px;text-align:center;color:var(--muted)}.source{word-break:break-all}
@media(max-width:620px){main{width:min(100% - 20px,1200px);padding-top:28px}.case{padding:16px}
th,td{padding:6px 4px;font-size:.78rem}.bar-row{grid-template-columns:1fr}.bar-count{display:none}}
"""


def _h(value: object) -> str:
    """Escape every value originating in a hand-editable case file."""

    return _html.escape(str(value), quote=True)


def _score_cell(value: int | None) -> str:
    valid = value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5 else 0
    label = str(value) if value is not None else "—"
    return f'<td class="score-{valid}">{_h(label)}</td>'


def _delta_cell(first: int | None, final: int | None) -> str:
    if not isinstance(first, int) or not isinstance(final, int):
        return '<td class="delta-flat">—</td>'
    delta = final - first
    cls = "delta-up" if delta > 0 else "delta-down" if delta < 0 else "delta-flat"
    label = f"{delta:+d}" if delta else "0"
    return f'<td class="{cls}">{label}</td>'


def _distribution(title: str, values: dict[str, int]) -> str:
    if not values:
        rows = '<p class="muted">No classified cases yet.</p>'
    else:
        maximum = max(values.values())
        rendered = []
        for label, count in sorted(values.items(), key=lambda item: (-item[1], item[0])):
            share = 100 * count / maximum if maximum else 0
            rendered.append(
                '<div class="bar-row">'
                f'<span class="bar-label" title="{_h(label)}">{_h(label)}</span>'
                f'<span class="bar-track"><span class="bar-fill" style="--share:{share:.1f}%"></span></span>'
                f'<span class="bar-count">{count}</span></div>'
            )
        rows = "".join(rendered)
    return f'<section class="panel"><h3>{_h(title)}</h3>{rows}</section>'


def _axis_overview(report: dict) -> str:
    rows = []
    for axis in AXES:
        first = report["axis_first"][axis]
        final = report["axis_final"][axis]
        first_label = f"{first:.1f}" if first is not None else "—"
        final_label = f"{final:.1f}" if final is not None else "—"
        first_rounded = round(first) if first is not None else 0
        final_rounded = round(final) if final is not None else 0
        first_class = first_rounded if 1 <= first_rounded <= 5 else 0
        final_class = final_rounded if 1 <= final_rounded <= 5 else 0
        if first is None or final is None:
            delta = "—"
            delta_class = "delta-flat"
        else:
            change = final - first
            delta = f"{change:+.1f}" if change else "0.0"
            delta_class = "delta-up" if change > 0 else "delta-down" if change < 0 else "delta-flat"
        rows.append(
            f'<tr><td>{_h(axis)}</td><td class="score-{first_class}">{first_label}</td>'
            f'<td class="score-{final_class}">{final_label}</td>'
            f'<td class="{delta_class}">{delta}</td>'
            f'<td>{report["axis_counts_first"][axis]} → {report["axis_counts_final"][axis]}</td></tr>'
        )
    return (
        '<section class="panel"><h3>Six-axis movement</h3><table><thead><tr>'
        '<th>Axis</th><th>First</th><th>Final</th><th>Delta</th><th>Samples</th>'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></section>'
    )


def _case_card(case: Case) -> str:
    title = case.project or case.slug or case.path.stem
    tags = [
        ("status", case.status or "unknown"),
        ("", case.essence),
        ("", case.style_family),
        ("", case.device_family),
        ("", case.concept_lens),
    ]
    tag_html = "".join(
        f'<span class="tag {kind}">{_h(value)}</span>'
        for kind, value in tags if value
    )
    rows = []
    for axis in AXES:
        first = case.scores_first.get(axis)
        final = case.scores_final.get(axis)
        rows.append(
            f'<tr><td>{_h(axis)}</td>{_score_cell(first)}{_score_cell(final)}'
            f'{_delta_cell(first, final)}</tr>'
        )
    details = []
    if case.device_detail:
        details.append(f'<p><strong>Signature device</strong><br>{_h(case.device_detail)}</p>')
    if case.cliche_avoided:
        details.append(f'<p><strong>Cliché avoided</strong><br>{_h(case.cliche_avoided)}</p>')
    lessons = "".join(
        f'<li>{"✓" if distilled else "□"} {_h(text)}</li>'
        for distilled, text in case.lessons
    )
    lesson_block = (
        f'<h3>Lessons</h3><ul class="lessons">{lessons}</ul>' if lessons else ""
    )
    targets = f'<p class="muted">Targets: {_h(case.targets)}</p>' if case.targets else ""
    return (
        '<article class="case">'
        '<div class="case-head"><div>'
        f'<p class="eyebrow">{_h(case.date or "Undated")}</p><h3>{_h(title)}</h3>'
        f'</div><span class="muted">{_h(case.iterations or "—")} pass(es)</span></div>'
        f'<div class="tags">{tag_html}</div>{targets}'
        '<table><thead><tr><th>Axis</th><th>First</th><th>Final</th><th>Δ</th></tr></thead><tbody>'
        + "".join(rows) + '</tbody></table>' + "".join(details) + lesson_block
        + f'<p class="muted source">Source: {_h(case.path.name)}</p></article>'
    )


def atlas_html(cases: list[Case], *, title: str = "IconFlow Casebook Atlas") -> str:
    """Render a deterministic, dependency-free visual casebook report."""

    report = stats(cases)
    case_count = report["cases"]
    mean_iterations = report["mean_iterations"]
    iteration_label = f"{mean_iterations:.1f}" if mean_iterations is not None else "—"
    weakest = report.get("weakest_axes", [])
    weakest_label = ", ".join(weakest) if weakest else "not enough score data"

    signals = [
        f'<div class="signal"><strong>Evolution target</strong><br>{_h(weakest_label)}</div>',
        f'<div class="signal"><strong>Undistilled lessons</strong><br>{len(report["undistilled"])}</div>',
    ]
    if report["house_cliche"]:
        device, count = report["house_cliche"]
        signals.append(
            f'<div class="signal"><strong>House-cliché warning</strong><br>'
            f'{_h(device)} appears in {count}/{case_count} cases.</div>'
        )
    elif case_count:
        signals.append('<div class="signal"><strong>House cliché</strong><br>No dominant device family.</div>')
    if len(report["undistilled"]) >= DISTILL_THRESHOLD:
        signals.append('<div class="signal"><strong>DISTILL NOW</strong><br>Lesson threshold reached.</div>')

    lesson_items = "".join(
        f'<li><span class="muted">{_h(filename)}</span> — {_h(text)}</li>'
        for filename, text in report["undistilled"]
    )
    lessons = (
        f'<ul class="lessons">{lesson_items}</ul>'
        if lesson_items else '<p class="muted">Casebook and distilled guidance are in sync.</p>'
    )
    cards = "".join(_case_card(case) for case in cases)
    if not cards:
        cards = (
            '<section class="empty"><h3>No cases yet</h3>'
            '<p>Record a shipped design with <code>iconflow case new</code>, then regenerate this atlas.</p>'
            '</section>'
        )

    safe_title = _h(title)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{safe_title}</title><style>{_ATLAS_STYLE}</style></head><body><main>'
        f'<p class="eyebrow">Design memory · {case_count} case(s)</p><h1>{safe_title}</h1>'
        '<p class="muted">First-pass weaknesses, review gains, recurring devices, and lessons still waiting to become rules.</p>'
        '<section class="metrics">'
        f'<div class="metric"><span class="muted">Cases</span><strong>{case_count}</strong></div>'
        f'<div class="metric"><span class="muted">Mean passes</span><strong>{iteration_label}</strong></div>'
        f'<div class="metric"><span class="muted">Undistilled</span><strong>{len(report["undistilled"])}</strong></div>'
        f'<div class="metric"><span class="muted">Weakest first</span><strong>{_h(weakest_label)}</strong></div>'
        '</section><h2>Portfolio movement</h2><section class="distributions">'
        + _axis_overview(report)
        + f'<section class="panel"><h3>Evolution signals</h3>{"".join(signals)}</section></section>'
        '<h2>Taxonomy</h2><section class="distributions">'
        + _distribution("Device families", report["device_families"])
        + _distribution("Concept lenses", report["concept_lenses"])
        + _distribution("Case status", report["statuses"])
        + '</section><h2>Undistilled lessons</h2><section class="panel">' + lessons + '</section>'
        '<h2>Cases</h2><section class="cases">' + cards + '</section>'
        '</main></body></html>'
    )


def write_atlas(directory: str | Path, out: str | Path, *,
                cases: list[Case] | None = None) -> Path:
    """Write a self-contained visual atlas for ``directory`` and return it."""

    destination = Path(out).expanduser().resolve(strict=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    selected = load_casebook(directory) if cases is None else cases
    destination.write_text(atlas_html(selected), encoding="utf-8")
    return destination
