# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Contracts for the packaged agent front door.

A foreign agent reaches IconFlow through three surfaces: `iconflow docs` for the
reference documents, `iconflow skill` for the procedure itself, and the Claude
Code plugin manifests that install both in one command. Each of them has to keep
working from an isolated wheel, with no checkout and no assumption about the
maintainer's workspace layout — the assumptions this file exists to prevent.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from iconflow import __version__, agentkit
from iconflow.cli import main


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "iconflow" / "SKILL.md"
PLUGIN = ROOT / "skills" / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
# Marketplace names Anthropic reserves for official use.
RESERVED_MARKETPLACES = {
    "claude-code-marketplace", "claude-code-plugins", "claude-plugins-official",
    "claude-plugins-community", "claude-community", "anthropic-marketplace",
    "anthropic-plugins", "agent-skills", "anthropic-agent-skills",
    "knowledge-work-plugins", "life-sciences", "claude-for-legal",
    "claude-for-financial-services", "financial-services-plugins",
    "first-party-plugins", "healthcare",
}


def run(*argv: str) -> tuple[int, str, str]:
    """Invoke the CLI in-process and capture both streams."""

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class PackagedDocsTest(unittest.TestCase):
    def test_lists_every_reference_document(self):
        on_disk = sorted(path.stem for path in (ROOT / "docs").glob("*.md"))
        self.assertEqual(on_disk, agentkit.doc_names())
        self.assertIn("DESIGN_PLAYBOOK", on_disk)

    def test_resolves_a_document_name_the_way_prose_writes_it(self):
        for spelling in ("LEARNINGS", "learnings", "Learnings.md", "docs/LEARNINGS.md"):
            with self.subTest(spelling=spelling):
                self.assertEqual("LEARNINGS", agentkit.resolve_doc(spelling))

    def test_unknown_document_names_the_alternatives(self):
        with self.assertRaisesRegex(ValueError, "DESIGN_PLAYBOOK"):
            agentkit.resolve_doc("nonexistent")
        code, _, err = run("docs", "nonexistent")
        self.assertEqual(2, code)
        self.assertIn("unknown document", err)

    def test_summaries_are_one_trimmed_line(self):
        for name in agentkit.doc_names():
            with self.subTest(doc=name):
                summary = agentkit.doc_summary(name)
                self.assertNotIn("\n", summary)
                self.assertLessEqual(len(summary), 90)
                # "<" catches the SPDX licence comment every document now opens with.
                self.assertFalse(summary.startswith(("#", "-", "|", ">", "<")))

    def test_listing_and_printing_are_separable(self):
        code, listing, _ = run("docs")
        self.assertEqual(0, code)
        for name in agentkit.doc_names():
            self.assertIn(name, listing)

        code, body, _ = run("docs", "REVIEW_CHECKLIST")
        self.assertEqual(0, code)
        self.assertIn("legibility", body.lower())

        code, path, _ = run("docs", "REVIEW_CHECKLIST", "--path")
        self.assertEqual(0, code)
        self.assertTrue(Path(path.strip()).is_file())

    def test_export_writes_every_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = run("docs", "--out", tmp)
            self.assertEqual(0, code)
            written = sorted(path.stem for path in Path(tmp).glob("*.md"))
            self.assertEqual(agentkit.doc_names(), written)

    def test_export_brings_the_images_the_documents_reference(self):
        """Prose without the exemplar gallery is how a generic mark ships.

        The playbook's images live in `docs/assets/`; a markdown export that
        drops them leaves every relative image link broken.
        """
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = run("docs", "--out", tmp)
            self.assertEqual(0, code)
            out = Path(tmp)
            referenced = set()
            for document in out.glob("*.md"):
                text = document.read_text(encoding="utf-8")
                referenced.update(re.findall(r"!\[[^\]]*\]\((assets/[^)\s]+)\)", text))
            self.assertTrue(referenced, "expected at least one image link to check")
            for link in sorted(referenced):
                with self.subTest(link=link):
                    self.assertTrue((out / link).is_file(), link)

    def test_json_listing_carries_names_and_summaries(self):
        code, payload, _ = run("docs", "--json")
        self.assertEqual(0, code)
        entries = json.loads(payload)
        self.assertEqual(agentkit.doc_names(), [entry["name"] for entry in entries])
        self.assertTrue(all("summary" in entry for entry in entries))


class ResourceResolutionTest(unittest.TestCase):
    """Where resources come from, and what must never be mistaken for a checkout."""

    def test_recognizes_this_checkout(self):
        self.assertEqual(ROOT, agentkit.checkout_root())
        self.assertEqual(ROOT, agentkit.checkout_root(ROOT))

    def test_site_packages_is_never_mistaken_for_a_checkout(self):
        """`site-packages/docs` from an unrelated project must not win.

        On a wheel install the directory above `iconflow/` is `site-packages`.
        Trusting it because it happens to contain `docs/` would let any other
        distribution shadow the packaged playbook.
        """
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site-packages"
            (site / "docs").mkdir(parents=True)
            (site / "iconflow").mkdir()
            self.assertIsNone(agentkit.checkout_root(site))

            # A foreign project's manifest is not ours.
            (site / "iconflow" / "cli.py").write_text("", encoding="utf-8")
            (site / "pyproject.toml").write_text(
                'name = "something-else"', encoding="utf-8"
            )
            self.assertIsNone(agentkit.checkout_root(site))

            (site / "pyproject.toml").write_text(
                'name = "ai-iconflow"', encoding="utf-8"
            )
            self.assertEqual(site, agentkit.checkout_root(site))

    def test_resource_names_cannot_escape_their_resource_set(self):
        for name in ("../pyproject.toml", "a/../../x", "/etc/passwd", ""):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    agentkit.resource("docs", name)

    def test_a_missing_resource_set_reports_the_install_not_a_traceback(self):
        with self.assertRaisesRegex(RuntimeError, "reinstall ai-iconflow"):
            agentkit.resource_root("no-such-resource-set")


class PackagedSkillTest(unittest.TestCase):
    def test_print_matches_the_canonical_source(self):
        code, printed, _ = run("skill", "print")
        self.assertEqual(0, code)
        self.assertEqual(SKILL.read_text(encoding="utf-8").strip(), printed.strip())

    def test_install_deploys_every_packaged_file_and_repeats_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            for attempt in (1, 2):
                with self.subTest(attempt=attempt):
                    code, _, _ = run("skill", "install", "--dir", tmp)
                    self.assertEqual(0, code)
                    destination = Path(tmp) / "iconflow"
                    for name in agentkit.SKILL_FILES:
                        self.assertTrue(destination.joinpath(*name.split("/")).is_file(), name)

    def test_install_removes_a_stale_file_from_an_older_deployment(self):
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "iconflow" / "README.md"
            stale.parent.mkdir(parents=True)
            stale.write_text("from an older IconFlow", encoding="utf-8")
            code, _, _ = run("skill", "install", "--dir", tmp)
            self.assertEqual(0, code)
            self.assertFalse(stale.exists())

    def test_explicit_directories_never_touch_the_user_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            code, _, _ = run("skill", "install", "--dir", str(Path(tmp) / "target"))
            self.assertEqual(0, code)
            self.assertFalse(fake_home.exists())
            self.assertTrue((Path(tmp) / "target" / "iconflow" / "SKILL.md").is_file())

    def test_refuses_to_write_a_deployed_file_through_a_symlink(self):
        """A pre-planted symlink must not redirect the write out of --dir."""
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside.md"
            outside.write_text("untouched", encoding="utf-8")
            destination = Path(tmp) / "root" / "iconflow"
            destination.mkdir(parents=True)
            try:
                (destination / "SKILL.md").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("this platform does not allow creating symlinks here")
            code, _, err = run("skill", "install", "--dir", str(Path(tmp) / "root"))
            self.assertEqual(2, code)
            self.assertIn("symlink", err)
            self.assertEqual("untouched", outside.read_text(encoding="utf-8"))

    def test_skips_the_claude_root_when_its_plugin_already_carries_the_skill(self):
        """Otherwise Claude Code holds two skills both named `iconflow`."""
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.assertEqual([], agentkit.claude_plugin_dirs(home))
            self.assertEqual(3, len(agentkit.default_skill_roots(home)))

            plugin = home / ".claude" / "plugins" / "cache" / "iconflow" / "iconflow"
            plugin.mkdir(parents=True)
            self.assertEqual([plugin], agentkit.claude_plugin_dirs(home))
            roots = agentkit.default_skill_roots(home)
            self.assertNotIn(home / ".claude" / "skills", roots)
            self.assertIn(home / ".agents" / "skills", roots)
            self.assertIn(home / ".copilot" / "skills", roots)

    def test_legacy_removal_only_ever_targets_the_iconflow_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            for directory in agentkit.legacy_skill_dirs(home):
                self.assertEqual("iconflow", directory.name)
                directory.mkdir(parents=True)
            removed = agentkit.remove_legacy_skills(home)
            self.assertEqual(agentkit.legacy_skill_dirs(home), removed)
            # A sibling skill from another toolkit must survive.
            self.assertTrue(all(path.parent.exists() for path in removed))


class SkillProcedureTest(unittest.TestCase):
    """The skill has to read the same in someone else's repository."""

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_frontmatter_declares_this_version(self):
        self.assertTrue(self.text.startswith("---\nname: iconflow\n"))
        self.assertIn("license: CC-BY-SA-4.0", self.text)
        self.assertIn("compatibility:", self.text)
        self.assertIn(f'version: "{__version__}"', self.text)

    def test_never_assumes_the_maintainers_workspace(self):
        for leak in ("AI_Projects", "<AI_PROJECTS>", "D:\\AI_Projects"):
            with self.subTest(leak=leak):
                self.assertNotIn(leak, self.text)

    def test_never_tells_an_agent_to_cd_into_the_toolkit(self):
        # Milestone v0.5 acceptance 4: the shell stays in the consuming project,
        # so its config, master, receipt, and casebook land in the right place.
        self.assertRegex(self.text, r"Never `cd` into the toolkit")
        self.assertNotRegex(self.text, re.compile(r"^\s*cd\s+\S", re.MULTILINE))

    def test_reaches_the_reference_documents_through_the_cli(self):
        for doc in ("LEARNINGS", "DESIGN_PLAYBOOK", "CONCEPTING",
                    "SVG_TECHNIQUES", "REVIEW_CHECKLIST", "OUTPUT_TARGETS"):
            with self.subTest(doc=doc):
                self.assertIn(f"iconflow docs {doc}", self.text)
                self.assertEqual(doc, agentkit.resolve_doc(doc))

    def test_keeps_the_gates_that_make_an_icon_worth_shipping(self):
        for gate in ("distinctiveness", "bake.png", "review.png",
                     "iconflow case new", "4/5"):
            with self.subTest(gate=gate):
                self.assertIn(gate, self.text)

    def test_warns_about_pypi_before_any_index_install_command(self):
        """Order matters: an agent runs the first command it reads.

        `ai-iconflow` has no PyPI release, so `install ai-iconflow` would fetch
        whatever else answers to that name. The warning has to come first, not
        as a footnote under the command.
        """
        for path in (SKILL, PLUGIN.parent.parent / "commands" / "setup.md"):
            with self.subTest(document=path.name):
                raw = path.read_text(encoding="utf-8")
                # Both markers wrap across lines, sometimes inside a blockquote.
                text = " ".join(raw.replace("\n>", " ").split())
                install = text.find("install ai-iconflow")
                self.assertNotEqual(-1, install, "expected an index install command")
                self.assertIn("no release on PyPI", text)
                stop = text.find("STOP")
                self.assertNotEqual(-1, stop, "expected a hard stop before installing")
                self.assertLess(stop, install, "the hard stop must come first")


class PluginManifestTest(unittest.TestCase):
    """`/plugin marketplace add` + `/plugin install` is the one-command path."""

    def setUp(self):
        self.plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
        self.marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))

    def test_marketplace_name_is_kebab_case_and_not_reserved(self):
        name = self.marketplace["name"]
        self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertNotIn(name, RESERVED_MARKETPLACES)
        self.assertIn("name", self.marketplace["owner"])

    def test_the_listed_source_is_the_skill_directory(self):
        entries = self.marketplace["plugins"]
        self.assertEqual(1, len(entries))
        entry = entries[0]
        self.assertEqual("iconflow", entry["name"])
        source = entry["source"]
        self.assertTrue(source.startswith("./"), source)
        self.assertNotIn("..", source)
        resolved = ROOT / source[2:]
        self.assertTrue((resolved / ".claude-plugin" / "plugin.json").is_file())

    def test_the_declared_skills_path_reaches_the_canonical_skill(self):
        """The plugin must point at one skill folder, not scan its siblings.

        `commands/` and `.claude-plugin/` sit beside it; naming the folder
        directly means discovery cannot depend on those being ignored. Verified
        against `claude plugin details iconflow`, which reports the skill under
        the name in this file's frontmatter.
        """
        plugin_root = PLUGIN.parent.parent
        declared = (plugin_root / self.plugin["skills"]).resolve()
        self.assertEqual(SKILL.parent.resolve(), declared)
        self.assertTrue((declared / "SKILL.md").is_file())
        self.assertIn("name: iconflow", (declared / "SKILL.md").read_text(encoding="utf-8"))

    def test_command_paths_resolve_inside_the_plugin(self):
        plugin_root = PLUGIN.parent.parent
        commands = plugin_root / self.plugin["commands"]
        found = sorted(path.name for path in commands.glob("*.md"))
        self.assertEqual(["icon.md", "setup.md"], found)

    def test_every_command_declares_a_description(self):
        commands = PLUGIN.parent.parent / self.plugin["commands"]
        for path in sorted(commands.glob("*.md")):
            with self.subTest(command=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"), path.name)
                frontmatter = text.split("---", 2)[1]
                self.assertRegex(frontmatter, re.compile(r"^description: \S", re.MULTILINE))

    def test_the_plugin_never_carries_the_whole_repository(self):
        """A plugin source is copied verbatim into every user's plugin cache.

        Pointing it at the repository root would ship `website/`, `examples/`,
        `tests/`, and — from a local directory install — `.venv`.
        """
        plugin_root = PLUGIN.parent.parent
        self.assertNotEqual(ROOT.resolve(), plugin_root.resolve())
        carried = {path.name for path in plugin_root.rglob("*") if path.is_file()}
        self.assertNotIn("pyproject.toml", carried)

    def test_plugin_version_tracks_the_package(self):
        self.assertEqual(__version__, self.plugin["version"])
        self.assertEqual("CC-BY-SA-4.0", self.plugin["license"])


if __name__ == "__main__":
    unittest.main()
