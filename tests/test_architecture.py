# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The module layering in docs/ARCHITECTURE.md, checked rather than described.

Every top-level import must point down the layer table. An import that points
up is allowed only inside a function and only if it is one of the edges the
document names, so a new upward dependency is a deliberate, documented choice
and never the first step of an import cycle.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "iconflow"

# Bottom (0) to top, as in the table of docs/ARCHITECTURE.md.
LAYERS = (
    ("rasterize", "session"),
    ("build", "ios", "ladder", "assemble", "htmlhead"),
    ("plan",),
    ("audit", "qa", "budget", "shapefield", "neighbours", "family"),
    ("config", "review", "headless"),
    ("cli", "detect", "brand"),
)
# Import nothing of IconFlow's; any layer may use them.
LEAVES = ("findings", "styles", "agentkit", "casebook", "shortcut")
ENTRY = ("__init__", "__main__")

# The function-level upward imports the document names, (importer, imported).
UPWARD = {
    ("build", "plan"),
    ("plan", "qa"),
    ("audit", "config"),
    ("neighbours", "config"),
    ("budget", "review"),
    ("family", "review"),
}


def _layer_of() -> dict[str, int]:
    return {module: index for index, layer in enumerate(LAYERS) for module in layer}


def _imports(path: Path):
    """(imported module, is_top_level) for every relative import of a sibling."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    top = {id(node) for node in tree.body}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level != 1:
            continue
        names = [node.module] if node.module else [alias.name for alias in node.names]
        for name in names:
            yield name.split(".")[0], id(node) in top


class LayeringTest(unittest.TestCase):
    def test_every_module_has_a_place(self):
        placed = set(_layer_of()) | set(LEAVES) | set(ENTRY)
        on_disk = {path.stem for path in PACKAGE.glob("*.py")}
        self.assertEqual(sorted(on_disk - placed), [], "add the new module to ARCHITECTURE.md")
        self.assertEqual(sorted(placed - on_disk), [], "a module in the table no longer exists")

    def test_leaves_import_nothing_of_iconflow(self):
        for leaf in LEAVES:
            with self.subTest(leaf=leaf):
                self.assertEqual(list(_imports(PACKAGE / f"{leaf}.py")), [])

    def test_imports_point_down_except_the_named_edges(self):
        layer = _layer_of()
        seen = set()
        for module, index in layer.items():
            for imported, top_level in _imports(PACKAGE / f"{module}.py"):
                if imported not in layer or layer[imported] <= index:
                    continue
                edge = (module, imported)
                with self.subTest(edge=edge):
                    self.assertFalse(top_level, f"top-level upward import {module} -> {imported}")
                    self.assertIn(edge, UPWARD, f"undocumented upward import {module} -> {imported}")
                seen.add(edge)
        self.assertEqual(seen, UPWARD, "ARCHITECTURE.md names an upward edge that no longer exists")

    def test_the_document_names_every_module_and_edge(self):
        text = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
        for module in [*_layer_of(), *LEAVES]:
            with self.subTest(module=module):
                self.assertIn(f"`{module}`", text)


if __name__ == "__main__":
    unittest.main()
