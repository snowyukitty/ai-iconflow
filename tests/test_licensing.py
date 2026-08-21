# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Fail-closed contracts for the three-tier licence split.

The point of the split is that IconFlow's methodology and finished artwork are
protected while **the icons a user makes with the tool stay entirely theirs**.
That second half is the fragile one: it breaks silently the moment a
restrictive tier leaks into something the toolkit copies or generates into a
consuming project. These tests exist to make that leak loud.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from iconflow import agentkit
from iconflow.cli import DEMO_NOTICE, main


ROOT = Path(__file__).resolve().parents[1]
LICENSES = ROOT / "LICENSES.md"
NOTICE = ROOT / "NOTICE"

# Directory -> the SPDX identifier every file in it must declare.
TIERS = {
    "templates": "CC0-1.0",
    "docs": "CC-BY-SA-4.0",
    "casebook": "CC-BY-SA-4.0",
    "skills": "CC-BY-SA-4.0",
    # Packaged with the wheel, so these have to stay free-licensed.
    "brand": "CC-BY-4.0",
    "demo": "CC-BY-4.0",
    "showcase": "CC-BY-NC-ND-4.0",
    "gallery": "CC-BY-NC-ND-4.0",
    "examples": "CC-BY-NC-ND-4.0",
    "docs/assets": "CC-BY-4.0",
    "website/assets": "CC-BY-NC-ND-4.0",
}
# Files the toolkit copies or generates INTO a user's project. Every one of
# these must be unencumbered, or a user's own logo inherits obligations.
USER_FACING_RESOURCES = ("presets", "templates")
SPDX = re.compile(r"SPDX-License-Identifier:\s*(\S+)")


def spdx_of(path: Path, limit: int = 1400) -> str | None:
    try:
        match = SPDX.search(path.read_text(encoding="utf-8")[:limit])
    except (OSError, UnicodeDecodeError):
        return None
    return match.group(1) if match else None


class TierMapTest(unittest.TestCase):
    def test_every_tier_directory_declares_its_licence(self):
        for directory, spdx in TIERS.items():
            with self.subTest(directory=directory):
                licence = ROOT / directory / "LICENSE"
                self.assertTrue(licence.is_file(), f"{directory}/LICENSE missing")
                self.assertEqual(spdx, spdx_of(licence), directory)

    def test_the_full_licence_texts_are_vendored(self):
        for name in ("CC0-1.0", "CC-BY-SA-4.0", "CC-BY-NC-ND-4.0"):
            with self.subTest(licence=name):
                text = (ROOT / "licenses" / f"{name}.txt").read_text(encoding="utf-8")
                self.assertGreater(len(text), 5000, "truncated licence text")
        self.assertIn("Apache License", (ROOT / "LICENSE").read_text(encoding="utf-8"))

    def test_the_map_names_every_tier_and_leads_with_user_ownership(self):
        text = LICENSES.read_text(encoding="utf-8")
        headline = text.index("The icons you make with IconFlow are yours")
        self.assertLess(headline, text.index("## 2. The tier map"),
                        "the ownership guarantee must come before the tier table")
        for spdx in ("Apache-2.0", "CC0-1.0", "CC-BY-SA-4.0", "CC-BY-NC-ND-4.0"):
            self.assertIn(spdx, text)

    def test_notice_carries_attribution_and_the_ownership_carve_out(self):
        # Apache-2.0 4(d) forces every redistributor to reproduce this file, so
        # it is the one attribution a fork cannot quietly drop.
        text = NOTICE.read_text(encoding="utf-8")
        self.assertIn("snowyukitty", text)
        self.assertIn("ICONS YOU MAKE WITH ICONFLOW ARE YOURS", text)
        self.assertIn("TRADEMARKS.md", text)
        for spdx in ("CC0-1.0", "CC-BY-SA-4.0", "CC-BY-NC-ND-4.0"):
            self.assertIn(spdx, text)


class SpdxHeaderTest(unittest.TestCase):
    """Per-file headers, so provenance survives a copied file.

    Enforced where the maintainer authors stable material. `casebook/` relies on
    its directory `LICENSE` instead, so a contributed case is not rejected for a
    missing header.
    """

    def test_methodology_documents_declare_cc_by_sa(self):
        for document in sorted((ROOT / "docs").glob("*.md")):
            with self.subTest(document=document.name):
                self.assertEqual("CC-BY-SA-4.0", spdx_of(document))

    def test_the_agent_procedure_declares_cc_by_sa(self):
        for document in sorted((ROOT / "skills").rglob("*.md")):
            with self.subTest(document=str(document.relative_to(ROOT))):
                self.assertEqual("CC-BY-SA-4.0", spdx_of(document))
        self.assertEqual("CC-BY-SA-4.0", spdx_of(ROOT / "AGENTS.md"))

    def test_frontmatter_still_comes_first_in_every_skill_document(self):
        # An SPDX comment above the YAML would stop clients recognising it.
        for document in sorted((ROOT / "skills").rglob("*.md")):
            with self.subTest(document=str(document.relative_to(ROOT))):
                self.assertTrue(
                    document.read_text(encoding="utf-8").startswith("---\n"),
                    "frontmatter must be the first thing in the file",
                )


class UserOutputIsUnencumberedTest(unittest.TestCase):
    """The guarantee in LICENSES.md section 1, checked rather than promised."""

    def test_every_scaffold_a_user_starts_from_is_public_domain(self):
        scaffolds = sorted((ROOT / "templates").rglob("*.svg"))
        self.assertGreaterEqual(len(scaffolds), 20)
        for scaffold in scaffolds:
            with self.subTest(scaffold=scaffold.name):
                # Apache-2.0 here would make a user's finished logo a derivative
                # work owing attribution and a licence copy. CC0 breaks the chain.
                self.assertEqual("CC0-1.0", spdx_of(scaffold))

    def test_the_packaged_scaffolds_are_public_domain_too(self):
        """A wheel user gets the same dedication a checkout user does."""
        for preset in ("flat-geometric", "gradient-glow"):
            with self.subTest(preset=preset):
                text = agentkit.resource("presets", f"{preset}.svg").read_text(
                    encoding="utf-8"
                )
                self.assertIn("SPDX-License-Identifier: CC0-1.0", text)

    def test_a_new_scaffold_arrives_without_any_iconflow_notice(self):
        """The copy `iconflow new` writes must be clean.

        The repository scaffold carries a CC0 header; carried into the user's
        copy it rides master.svg into the favicon.svg they serve in production.
        An IconFlow URL in someone's shipped asset is the attribution
        LICENSES.md section 1 promises never to require.
        """
        import contextlib
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a.svg"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(0, main(["new", "flat-geometric", "--out", str(target)]))
            copied = target.read_text(encoding="utf-8")
            self.assertNotIn("SPDX-License-Identifier", copied)
            self.assertNotIn("ai-iconflow.com", copied)
            self.assertTrue(copied.startswith("<svg"), copied[:60])
            # The dedication is told to the person instead.
            self.assertIn("CC0", out.getvalue())
            self.assertIn("yours", out.getvalue())

    def test_the_contributor_fixture_is_free_to_copy(self):
        # examples/ is no-derivatives, but community-case exists to be adapted.
        self.assertEqual(
            "CC0-1.0", spdx_of(ROOT / "examples" / "community-case" / "LICENSE")
        )

    def test_no_restrictive_tier_reaches_a_consuming_project(self):
        for package in USER_FACING_RESOURCES:
            for entry in agentkit.resource_root(package).iterdir():
                if not entry.name.endswith(".svg"):
                    continue
                with self.subTest(resource=f"{package}/{entry.name}"):
                    text = entry.read_text(encoding="utf-8")
                    for restrictive in ("CC-BY-SA-4.0", "CC-BY-NC-ND-4.0"):
                        self.assertNotIn(restrictive, text)

    def test_a_full_build_from_a_user_svg_leaks_nothing(self):
        """Every generator, checked at once instead of read one by one.

        `build` writes the manifest, the head snippet, the icon ladder and the
        favicons a user actually serves. If any of them carried an IconFlow
        notice, URL, or SPDX tag, LICENSES.md section 1 would be false in the
        one place a visitor could see it.
        """
        import tempfile

        leaks = ("SPDX-License-Identifier", "ai-iconflow.com", "snowyukitty",
                 "Apache-2.0", "CC-BY", "CC0-1.0", "Copyright")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            master = project / "master.svg"
            self.assertEqual(0, main(["new", "flat-geometric", "--out", str(master)]))
            code = main([
                "build", str(master), "--out", str(project / "out"),
                "--targets", "web", "--name", "My App",
            ])
            self.assertEqual(0, code)
            produced = [p for p in (project / "out").rglob("*") if p.is_file()]
            self.assertTrue(produced, "build produced nothing to check")
            for path in produced:
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue  # binary icon data carries no notice
                for leak in leaks:
                    with self.subTest(file=path.name, leak=leak):
                        self.assertNotIn(leak, text)

    def test_the_cli_can_state_the_guarantee_without_a_lawyer(self):
        import contextlib
        import io

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(0, main(["license"]))
        text = out.getvalue()
        self.assertIn("are yours", text)
        self.assertIn("No attribution required", text)

        payload = io.StringIO()
        with contextlib.redirect_stdout(payload):
            self.assertEqual(0, main(["license", "--json"]))
        summary = json.loads(payload.getvalue())
        self.assertIn("yours", summary["headline"])
        self.assertTrue(any("Commercial use" in line for line in summary["your_output"]))
        self.assertEqual(
            {"0", "1", "1b", "2", "3a", "3b"},
            {tier["tier"] for tier in summary["tiers"]},
        )


class SourceAttributionTest(unittest.TestCase):
    """Per-file notices, because NOTICE alone does not travel with a file.

    The engine is Apache-2.0, so a modified closed fork is permitted. What is
    *not* permitted is dropping the attribution (Apache-2.0 §4(c)/§4(d)) — and
    that is only detectable if every file carried a notice to begin with.
    """

    def test_every_python_source_file_carries_its_licence(self):
        roots = (ROOT / "iconflow", ROOT / "scripts", ROOT / "tests")
        modules = [
            path
            for root in roots
            for path in sorted(root.rglob("*.py"))
            if "__pycache__" not in path.parts
        ]
        self.assertGreaterEqual(len(modules), 30)
        for path in modules:
            with self.subTest(module=str(path.relative_to(ROOT))):
                head = path.read_text(encoding="utf-8")[:400]
                self.assertIn("SPDX-License-Identifier: Apache-2.0", head)
                self.assertIn("snowyukitty", head)

    def test_a_shebang_still_comes_first(self):
        script = ROOT / "scripts" / "proof_receipt.py"
        self.assertTrue(script.read_text(encoding="utf-8").startswith("#!"))

    def test_the_contributor_agreement_keeps_relicensing_possible(self):
        cla = (ROOT / "CLA.md").read_text(encoding="utf-8")
        self.assertIn("relicense", cla.lower())
        # A CLA that quietly took ownership would be a different, worse thing.
        self.assertIn("not an assignment", cla)
        self.assertIn("You keep the copyright", cla)
        for referrer in ("CONTRIBUTING.md", "LICENSES.md",
                         ".github/pull_request_template.md"):
            with self.subTest(document=referrer):
                self.assertIn("CLA.md", (ROOT / referrer).read_text(encoding="utf-8"))

    def test_provenance_states_what_apache_actually_requires(self):
        text = (ROOT / "docs" / "PROVENANCE.md").read_text(encoding="utf-8")
        for needle in ("§4(d)", "receipt-stale-source", "closed commercial product"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)


class BrandLeakTest(unittest.TestCase):
    """`demo` is the one command that puts IconFlow's own identity in a user directory."""

    def test_the_demo_notice_says_what_the_directory_holds(self):
        self.assertIn("IconFlow's own product mark", DEMO_NOTICE)
        self.assertIn("not a starting point", DEMO_NOTICE)
        self.assertIn("CC BY 4.0", DEMO_NOTICE)
        # The built .ico/.png beside it are the same mark; say so.
        self.assertIn(".icns", DEMO_NOTICE)
        self.assertIn("trademark", DEMO_NOTICE)
        self.assertIn("iconflow new", DEMO_NOTICE)

    def test_the_skill_tells_the_agent_to_pass_ownership_on(self):
        skill = (ROOT / "skills" / "iconflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Who owns what", skill)
        self.assertIn("the icon is theirs", skill)
        self.assertIn("iconflow license", skill)


class PublishedCorpusTest(unittest.TestCase):
    """What makes a copy of the published artwork self-identifying."""

    def test_every_published_study_carries_provenance_metadata(self):
        catalog = json.loads(
            (ROOT / "website" / "assets" / "archive" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        entries = catalog["entries"]
        self.assertGreaterEqual(len(entries), 100)
        for entry in entries:
            path = ROOT / "website" / entry["svg"].lstrip("/")
            with self.subTest(entry=entry["id"]):
                text = path.read_text(encoding="utf-8")
                self.assertIn("iconflow:provenance", text)
                self.assertIn("creativecommons.org/licenses/by-nc-nd/4.0/", text)
                self.assertIn("snowyukitty", text)

    def test_terms_for_ai_readers_are_published_and_honest(self):
        llms = (ROOT / "website" / "llms.txt").read_text(encoding="utf-8")
        self.assertIn("are yours", llms)
        for spdx in ("CC BY-SA 4.0", "CC BY-NC-ND 4.0"):
            self.assertIn(spdx, llms)
        self.assertIn("honoured voluntarily", llms)

        robots = (ROOT / "website" / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("/llms.txt", robots)
        for crawler in ("GPTBot", "ClaudeBot", "CCBot", "Google-Extended"):
            with self.subTest(crawler=crawler):
                self.assertIn(f"User-agent: {crawler}", robots)
        for corpus in ("/archive/", "/gallery/", "/how-icons-are-made/"):
            self.assertIn(f"Disallow: {corpus}", robots)
        # The discovery path this project depends on must stay open.
        self.assertIn("Allow: /getting-started/", robots)

    def test_provenance_admits_what_it_cannot_do(self):
        text = (ROOT / "docs" / "PROVENANCE.md").read_text(encoding="utf-8")
        self.assertIn("cannot", text)
        self.assertIn("monogram trap", text)
        self.assertIn("Software Heritage", text)


if __name__ == "__main__":
    unittest.main()
