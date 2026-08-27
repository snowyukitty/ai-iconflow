# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Check what is actually true about this project, and write it down.

IconFlow refuses to ship an icon on the strength of someone remembering that
it looked fine. It renders the pixels, binds the approval to a source hash,
and fails closed when the two stop agreeing.

The project's claims *about itself* had no such discipline. `LAUNCH_READINESS`
is a hand-ticked checklist, and on 2026-08-25 it still said the `iconflow` name
returned 404 on PyPI and was "still free" — three days after 0.5.0 was
published from this repository. Nobody lied. A human ticked a box, the world
moved, and the box stayed ticked. That is precisely the failure mode a review
receipt exists to prevent, running unopposed in the tool's own documentation.

So this asks the world instead:

* are the generated site artifacts current, or has something drifted;
* does PyPI carry the version this checkout claims, with resolvable
  attestations;
* does the repository look the way the docs say it looks;
* **does the deployed site still serve what the repository holds** — the one
  failure nothing else here can see, because a perfect commit and a stale
  Cloudflare deploy look identical from inside a checkout.

One rule governs the whole file: **a probe that could not run reports UNKNOWN,
never PASS.** An unreachable network, a missing `gh`, an API that changed shape
— every one of those produces "I do not know", because a green tick that means
"I could not check" is worse than no tick at all. That is the same reason
`ship` refuses a stale receipt rather than assuming the best.

Usage::

    python scripts/state.py                 # human report
    python scripts/state.py --write         # regenerate docs/STATE.md
    python scripts/state.py --json          # one JSON object on stdout
    python scripts/state.py --offline       # local checks only

Exit codes follow ``docs/AGENT_CONTRACT.md``: 0 clean, 1 something FAILED,
2 the checker itself broke. An open owner gate is reported, never a failure —
gates are decisions waiting on a person, not defects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SITE = ROOT / "website"
REPORT = ROOT / "docs" / "STATE.md"
ORIGIN = "https://ai-iconflow.com"
REPO = "snowyukitty/ai-iconflow"
PYPI = "iconflow"
TIMEOUT = 20

PASS, FAIL, GATE, UNKNOWN = "PASS", "FAIL", "GATE", "UNKNOWN"
MARK = {PASS: "PASS", FAIL: "FAIL", GATE: "OPEN", UNKNOWN: "????"}


@dataclass
class Check:
    """One question with one answer and the evidence behind it."""

    key: str
    title: str
    state: str
    detail: str
    section: str = ""
    evidence: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Probes


def http(url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "iconflow-state/1"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, response.read()


def digest(data: bytes) -> str:
    """Hash with newlines normalised.

    The repository stores LF; an edge or a checkout may serve CRLF. That
    difference is not drift, and reporting it as drift would train a reader to
    ignore this file — which is the only way a report like this ever fails.
    """
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def gh_json(*args: str):
    """Ask the GitHub CLI, or return None if it cannot answer."""
    try:
        result = subprocess.run(
            ["gh", *args], capture_output=True, text=True, timeout=TIMEOUT,
            check=False, encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Section 1 — generated artifacts, offline


def load_script(name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_generators() -> list[Check]:
    """Every generated site artifact, re-derived and compared.

    Each generator already knows how to verify itself; this only collects them
    behind one command, so "is the site current" stops being four commands a
    person has to remember in the right order.
    """
    checks: list[Check] = []

    def run(key: str, title: str, call) -> None:
        # The generators narrate to stdout. Under --json this report owes the
        # caller exactly one JSON object, so their chatter is swallowed rather
        # than allowed to corrupt the envelope.
        saved = sys.stdout
        try:
            with open(os.devnull, "w", encoding="utf-8") as silence:
                sys.stdout = silence
                ok, detail = call()
        except Exception as exc:  # a generator that cannot run is not a pass
            checks.append(Check(key, title, UNKNOWN,
                                f"generator raised {type(exc).__name__}: {exc}"))
            return
        finally:
            sys.stdout = saved
        checks.append(Check(key, title, PASS if ok else FAIL, detail))

    def i18n():
        module = load_script("build_i18n")
        code = module.verify()
        return code == 0, ("five-language build byte-identical to a fresh render"
                           if code == 0 else "run python scripts/build_i18n.py")

    def archive():
        module = load_script("build_archive")
        code = module.verify()
        return code == 0, ("137 directions, catalog and page agree"
                           if code == 0 else "run python scripts/build_archive.py")

    def reference():
        module = load_script("build_reference")
        published = (SITE / "reference" / "icon-sizes" / "index.html").read_text(encoding="utf-8")
        current = module.render() == published
        return current, ("icon-size tables match iconflow/build.py"
                         if current else "run python scripts/build_reference.py")

    def tray_reference():
        module = load_script("build_tray_reference")
        code = module.verify()
        return code == 0, (
            "tray guide and five evidence PNGs match assemble.to_template"
            if code == 0 else "run python scripts/build_tray_reference.py"
        )

    def adoption():
        module = load_script("build_adoption")
        return module.verify()

    run("generated.i18n", "Five-language site is current", i18n)
    run("generated.archive", "Living archive is current", archive)
    run("generated.reference", "Icon-size reference is current", reference)
    run("generated.tray_reference", "Tray-icon reference is current", tray_reference)
    run("generated.adoption", "First-proof commands are current", adoption)
    for check in checks:
        check.section = "Generated artifacts"
    return checks


# ---------------------------------------------------------------------------
# Section 2 — the deployed site


CONTRACT_FILES = (
    ("/robots.txt", "robots.txt"),
    ("/llms.txt", "llms.txt"),
    ("/sitemap.xml", "sitemap.xml"),
    ("/reference/icon-sizes/", "reference/icon-sizes/index.html"),
    ("/reference/tray-icons/", "reference/tray-icons/index.html"),
)

# A body can differ from the checkout without the deploy being stale: a CDN
# may rewrite HTML on its way out. Telling someone to redeploy in that case
# sends them to fix the one thing that is not broken, so the difference is
# named instead. Ordered most-specific first.
EDGE_REWRITES = (
    ("cloudflareinsights",
     "the edge injects a Cloudflare Web Analytics beacon. This site's CSP is "
     "script-src 'self', so every visitor's browser blocks it and logs a "
     "violation: the analytics collect nothing and the console is never clean. "
     "Turn off automatic injection in the Cloudflare dashboard (Web Analytics), "
     "or accept a third-party script on a site that advertises local-first."),
    ("__cf_email__",
     "the edge rewrote something that looks like an email address into a "
     "mailto link. On the icon-size reference that corrupts real filenames "
     "(128x128@2x.png). Disable Scrape Shield -> Email Address Obfuscation, or "
     "emit &#64; from the generator."),
    ("/cdn-cgi/",
     "the edge injected a /cdn-cgi/ asset that is not in the checkout."),
)


def check_deployment() -> list[Check]:
    """Does ai-iconflow.com serve what this checkout holds?

    Nothing else in the repository can answer this. Tests prove the tracked
    files are correct; CI proves they build. Neither notices that the last
    `wrangler pages deploy` was two commits ago, and a visitor reads the
    deploy, not the commit.
    """
    checks: list[Check] = []
    for route, tracked in CONTRACT_FILES:
        local = SITE / tracked
        title = f"Live site serves current {route}"
        key = f"deploy{route.rstrip('/').replace('/', '.') or '.root'}"
        if not local.is_file():
            checks.append(Check(key, title, UNKNOWN, f"{tracked} is not in this checkout"))
            continue
        try:
            status, body = http(ORIGIN + route)
        except urllib.error.HTTPError as exc:
            # A status code is an answer, not a failure to reach the site. 404
            # on a route the sitemap advertises is the worst result here, not
            # an unknown: it means search engines are being sent to nothing.
            checks.append(Check(
                key, title, FAIL,
                f"HTTP {exc.code} — the sitemap advertises this route"
                if exc.code == 404 else f"HTTP {exc.code}",
                evidence={"http_status": exc.code}))
            continue
        except (urllib.error.URLError, OSError, ValueError) as exc:
            checks.append(Check(key, title, UNKNOWN, f"unreachable: {exc}"))
            continue
        if status != 200:
            checks.append(Check(key, title, FAIL, f"HTTP {status}"))
            continue
        want, got = digest(local.read_bytes()), digest(body)
        if want == got:
            checks.append(Check(key, title, PASS, "byte-identical to the checkout",
                                evidence={"repo_sha256": want}))
            continue

        # Say *why* it differs. "Redeploy" is actively wrong advice when the
        # bytes left this repository intact and something rewrote them in
        # flight, and a report that gives wrong advice gets ignored.
        marker = next((m for m, _ in EDGE_REWRITES if m.encode() in body), "")
        if marker:
            reason = dict(EDGE_REWRITES)[marker]
            checks.append(Check(key, f"Live {route} is served unmodified", FAIL,
                                reason, evidence={"marker": marker}))
        else:
            checks.append(Check(
                key, title, FAIL,
                f"deployed copy differs (repo {want[:12]}, live {got[:12]}) — redeploy",
                evidence={"repo_sha256": want, "live_sha256": got}))
    for check in checks:
        check.section = "Deployed site"
    return checks


# ---------------------------------------------------------------------------
# Section 3 — the distribution


PYPI_STALE_MARKERS = (
    "not published on PyPI",
    "not on PyPI yet",
    "do not use `pip install iconflow`",
)


def pypi_description_problems(description: str) -> list[str]:
    """Return adoption claims that make a published package deny itself."""
    lowered = description.lower()
    problems = [f"contains stale pre-release claim: {marker!r}"
                for marker in PYPI_STALE_MARKERS if marker.lower() in lowered]
    if "pip install iconflow" not in description:
        problems.append("missing the released install command")
    if "iconflow demo" not in description:
        problems.append("missing the source-bound first-proof command")
    return problems


def check_distribution() -> list[Check]:
    import iconflow

    version = iconflow.__version__
    checks: list[Check] = []
    try:
        status, body = http(f"https://pypi.org/pypi/{PYPI}/json")
        data = json.loads(body)
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        checks.append(Check("dist.pypi", "PyPI carries this version", UNKNOWN,
                            f"PyPI unreachable: {exc}"))
        checks.append(Check("dist.description", "PyPI first-proof copy is truthful", UNKNOWN,
                            "not checked, because the project page could not be listed"))
        checks.append(Check("dist.attestations", "Release attestations resolve", UNKNOWN,
                            "not checked, because the release could not be listed"))
        for check in checks:
            check.section = "Distribution"
        return checks

    published = sorted(data.get("releases", {}))
    latest = data["info"]["version"]
    here = version in published
    checks.append(Check(
        "dist.pypi", "PyPI carries this version",
        PASS if here else FAIL,
        f"checkout is {version}; PyPI latest is {latest} "
        + ("(published)" if here else "— this version has never been uploaded"),
        evidence={"checkout": version, "pypi_latest": latest, "released": published},
    ))

    description_problems = pypi_description_problems(
        data.get("info", {}).get("description") or ""
    )
    checks.append(Check(
        "dist.description", "PyPI first-proof copy is truthful",
        FAIL if description_problems else PASS,
        (f"published {latest} long description " + "; ".join(description_problems)
         + " — corrected checkout needs a future release"
         if description_problems
         else "install and demo commands present; no stale pre-release warning"),
        evidence={"pypi_latest": latest, "problems": description_problems},
    ))

    # An unsigned artifact and a signed one are indistinguishable from the JSON
    # API, so ask the integrity endpoint that actually holds the bundle.
    if not here:
        checks.append(Check("dist.attestations", "Release attestations resolve", UNKNOWN,
                            "no matching release to check"))
    else:
        names = [f"{PYPI}-{version}-py3-none-any.whl", f"{PYPI}-{version}.tar.gz"]
        resolved, missing = [], []
        for name in names:
            try:
                status, _ = http(f"https://pypi.org/integrity/{PYPI}/{version}/{name}/provenance")
            except (urllib.error.URLError, OSError) as exc:
                missing.append(f"{name} ({exc})")
                continue
            (resolved if status == 200 else missing).append(name)
        if missing:
            state = UNKNOWN if len(missing) == len(names) else FAIL
            detail = "no provenance for " + ", ".join(missing)
        else:
            state, detail = PASS, f"signed provenance for {len(resolved)} artifacts"
        checks.append(Check("dist.attestations", "Release attestations resolve",
                            state, detail, evidence={"resolved": resolved}))

    for check in checks:
        check.section = "Distribution"
    return checks


# ---------------------------------------------------------------------------
# Section 4 — the repository, and the gates on it


def check_repository() -> list[Check]:
    fields = ("visibility,repositoryTopics,usesCustomOpenGraphImage,"
              "hasDiscussionsEnabled,licenseInfo,stargazerCount,forkCount")
    data = gh_json("repo", "view", REPO, "--json", fields)
    if data is None:
        unknown = "gh could not answer (not installed, not authenticated, or offline)"
        checks = [
            Check("repo.public", "Repository is public", UNKNOWN, unknown),
            Check("repo.topics", "Discovery topics are set", UNKNOWN, unknown),
            Check("repo.social", "Repository social preview is uploaded", UNKNOWN, unknown),
            Check("repo.discussions", "Discussions decision", UNKNOWN, unknown),
        ]
    else:
        topics = [t["name"] for t in data.get("repositoryTopics") or []]
        public = data.get("visibility", "").upper() == "PUBLIC"
        social = bool(data.get("usesCustomOpenGraphImage"))
        discussions = bool(data.get("hasDiscussionsEnabled"))
        checks = [
            Check("repo.public", "Repository is public",
                  PASS if public else FAIL,
                  f"visibility {data.get('visibility', '?').lower()}; "
                  + _count(data.get("stargazerCount", 0), "star")
                  + ", " + _count(data.get("forkCount", 0), "fork")),
            Check("repo.topics", "Discovery topics are set",
                  PASS if len(topics) >= 15 else GATE,
                  f"{len(topics)} of GitHub's 20 topic slots used",
                  evidence={"topics": topics}),
            # Not a defect — a link preview nobody has uploaded yet. But it is
            # the cheapest unclaimed impression the project has: every link to
            # the repo, in every chat and every post, renders a grey card.
            Check("repo.social", "Repository social preview is uploaded",
                  PASS if social else GATE,
                  "custom Open Graph image set" if social
                  else "still GitHub's generated card — Settings → General → "
                       "Social preview, upload docs/assets/social-preview.png"),
            Check("repo.discussions", "Discussions decision",
                  PASS if discussions else GATE,
                  "enabled" if discussions
                  else "not enabled — gh repo edit " + REPO + " --enable-discussions"),
        ]

    ci = gh_json("run", "list", "--repo", REPO, "--workflow", "ci.yml",
                 "--branch", "main", "--limit", "1",
                 "--json", "conclusion,status,headSha,displayTitle")
    if not ci:
        checks.append(Check("repo.ci", "CI is green on main", UNKNOWN,
                            "gh could not list workflow runs"))
    else:
        run = ci[0]
        conclusion = run.get("conclusion") or run.get("status") or "unknown"
        checks.append(Check(
            "repo.ci", "CI is green on main",
            PASS if conclusion == "success" else (UNKNOWN if conclusion in
                                                  {"in_progress", "queued", "pending"} else FAIL),
            f"latest main run: {conclusion} ({(run.get('headSha') or '')[:7]})",
            evidence={"conclusion": conclusion, "title": run.get("displayTitle")}))

    for check in checks:
        check.section = "Repository"
    return checks


# ---------------------------------------------------------------------------
# What no probe can settle


UNCHECKABLE = (
    ("Owner reads `LICENSES.md` end to end and confirms the tier boundaries",
     "A person has to agree with the boundaries; no request can observe that."),
    ("Owner enables a CLA signature check on pull requests",
     "The app is installed on an account, not recorded in the repository. "
     "Until then, check the signature line by hand on every outside PR."),
    ("Owner decides whether to register the IconFlow word mark",
     "`TRADEMARKS.md` asserts common-law rights, which are real but weaker "
     "and jurisdiction-dependent."),
    ("Owner verifies the site in Google Search Console and Bing Webmaster Tools",
     "Verification lives in those consoles. Without it, `docs/SEO.md`'s page "
     "queue is guesswork rather than demand."),
    ("Owner settles whether `/how-icons-are-made/` stays closed to training crawlers",
     "It is the most citable page on the site and currently blocked. That is a "
     "licensing decision, not an SEO one, and it should be decided rather than "
     "inherited."),
    ("Release tags are signed",
     "Signing is a local key policy; a tag's absence of a signature is "
     "observable, but the decision to adopt one is not."),
)


# ---------------------------------------------------------------------------
# Reporting


def collect(offline: bool) -> list[Check]:
    checks = check_generators()
    if offline:
        note = "skipped: --offline"
        checks += [
            Check("deploy", "Deployed site matches the checkout", UNKNOWN, note, "Deployed site"),
            Check("dist", "Distribution", UNKNOWN, note, "Distribution"),
            Check("repo", "Repository", UNKNOWN, note, "Repository"),
        ]
        return checks
    return checks + check_deployment() + check_distribution() + check_repository()


def summarise(checks: list[Check]) -> dict[str, int]:
    counts = {PASS: 0, FAIL: 0, GATE: 0, UNKNOWN: 0}
    for check in checks:
        counts[check.state] += 1
    return counts


def render_report(checks: list[Check], counts: dict[str, int], stamp: str) -> str:
    lines = [
        "<!-- SPDX-License-Identifier: CC-BY-SA-4.0",
        "     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com -->",
        "# Project state",
        "",
        "> **Generated file. Do not edit.** Regenerate with",
        "> `python scripts/state.py --write`. Every line below was observed, not",
        "> remembered — which is the whole point, because the checklist this",
        "> replaces spent three days insisting the PyPI name was still free.",
        "",
        f"Observed {stamp}.",
        "",
        f"`{counts[PASS]} pass · {counts[FAIL]} fail · {counts[GATE]} open gate"
        f"{'s' if counts[GATE] != 1 else ''} · {counts[UNKNOWN]} unknown`",
        "",
        "An **open gate** is a decision waiting on a person, not a defect, and",
        "never fails this report. **Unknown** means a probe could not run: it is",
        "deliberately not a pass, because a tick that means \"I could not check\"",
        "is worse than no tick at all.",
        "",
    ]
    section = None
    for check in checks:
        if check.section != section:
            # A table row followed straight by a heading is not a heading in
            # every Markdown renderer; the blank line is load-bearing.
            if section is not None:
                lines.append("")
            section = check.section
            lines += [f"## {section}", "",
                      "| | Check | Detail |", "|---|---|---|"]
        lines.append(f"| `{MARK[check.state]}` | {check.title} | {check.detail} |")
    lines.append("")
    lines += [
        "## Waiting on a person",
        "",
        "No probe can settle these, and inventing one that pretends otherwise",
        "would be the same mistake in a new costume.",
        "",
    ]
    for title, why in UNCHECKABLE:
        lines.append(f"- **{title}.** {why}")
    lines += [
        "",
        "---",
        "",
        "Related: [`LAUNCH_READINESS.md`](LAUNCH_READINESS.md) for how the launch",
        "was reached, [`SEO.md`](SEO.md) for what the open gates cost, and",
        "[`RELEASING.md`](RELEASING.md) for the steps that change these answers.",
        "",
    ]
    return "\n".join(lines)


def render_human(checks: list[Check], counts: dict[str, int]) -> str:
    width = max(len(check.title) for check in checks)
    lines, section = [], None
    for check in checks:
        if check.section != section:
            section = check.section
            lines.append(f"\n{section}")
        lines.append(f"  {MARK[check.state]}  {check.title.ljust(width)}  {check.detail}")
    lines.append(
        f"\n{counts[PASS]} pass, {counts[FAIL]} fail, {counts[GATE]} open gate(s), "
        f"{counts[UNKNOWN]} unknown."
    )
    if counts[GATE]:
        lines.append("Open gates are decisions, not defects. See docs/STATE.md.")
    return "\n".join(lines)


def main() -> int:
    # Same guard as iconflow.cli.main: a Windows console defaults to a legacy
    # codepage, and an arrow in a hint should never be the reason a status
    # report crashes.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate docs/STATE.md")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit one JSON object on stdout")
    parser.add_argument("--offline", action="store_true",
                        help="run only the checks that need no network")
    args = parser.parse_args()

    checks = collect(args.offline)
    counts = summarise(checks)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status = "blocked" if counts[FAIL] else "ok"
    code = 1 if counts[FAIL] else 0

    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(render_report(checks, counts, stamp), encoding="utf-8", newline="\n")

    if args.as_json:
        print(json.dumps({
            "schema": 1,
            "command": "state",
            "status": status,
            "exit_code": code,
            "warnings": [{"code": c.key, "message": c.detail}
                         for c in checks if c.state == FAIL],
            "advisories": [{"code": c.key, "message": c.detail}
                           for c in checks if c.state in (GATE, UNKNOWN)],
            "outputs": {
                "observed": stamp,
                "counts": {k.lower(): v for k, v in counts.items()},
                "checks": [{"key": c.key, "section": c.section, "title": c.title,
                            "state": c.state, "detail": c.detail, "evidence": c.evidence}
                           for c in checks],
                "report": str(REPORT) if args.write else None,
            },
            "errors": [],
        }, ensure_ascii=False, indent=2))
    else:
        print(render_human(checks, counts))
        if args.write:
            print(f"\nWrote {REPORT.relative_to(ROOT)}")
    return code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(2)
    except Exception as exc:  # the checker breaking is a 2, never a silent 0
        print(f"state: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
