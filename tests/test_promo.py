# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Contract tests for the HyperFrames promotional-film handoff."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROMO = ROOT / "docs" / "promo"
STORYBOARDS = tuple(sorted(PROMO.glob("storyboard-*.json")))
MOTIONS = {"rise", "hold", "focus", "reveal"}
ITEM_LIMITS = {
    "metrics": (2, 4),
    "cards": (2, 3),
    "list": (2, 5),
}


class PromoStoryboardTests(unittest.TestCase):
    def test_all_three_cuts_follow_the_hyperframes_storyboard_contract(self) -> None:
        self.assertEqual(3, len(STORYBOARDS))
        for path in STORYBOARDS:
            data = json.loads(path.read_text(encoding="utf-8"))
            slides = data["slides"]
            with self.subTest(storyboard=path.name):
                self.assertEqual(
                    data["targetDurationSeconds"],
                    sum(slide["durationTarget"] for slide in slides),
                )
                self.assertEqual("draft", data["production"]["status"])
                self.assertEqual("pending", data["production"]["humanPreview"])
                self.assertEqual(3840, data["production"]["width"])
                self.assertEqual(2160, data["production"]["height"])
                self.assertEqual(24, data["production"]["fps"])
                self.assertEqual(1216, data["production"]["safeRegion"]["width"])

            ids = {slide["id"] for slide in slides}
            self.assertEqual(len(slides), len(ids), path.name)
            for slide in slides:
                with self.subTest(storyboard=path.name, slide=slide["id"]):
                    for key in (
                        "id",
                        "title",
                        "durationTarget",
                        "image",
                        "subtitle",
                        "narration",
                    ):
                        self.assertIn(key, slide)
                    self.assertGreaterEqual(slide["durationTarget"], 1)
                    self.assertIn(slide["motion"], MOTIONS)
                    self.assertLessEqual(len(slide.get("blocks", [])), 3)
                    for block in slide.get("blocks", []):
                        block_type = block["type"]
                        if block_type in ITEM_LIMITS:
                            minimum, maximum = ITEM_LIMITS[block_type]
                            self.assertGreaterEqual(len(block["items"]), minimum)
                            self.assertLessEqual(len(block["items"]), maximum)

    def test_media_bindings_are_source_bound_and_slide_specific(self) -> None:
        for path in STORYBOARDS:
            data = json.loads(path.read_text(encoding="utf-8"))
            slides = {slide["id"]: slide for slide in data["slides"]}
            targets: set[str] = set()
            for binding in data["mediaBindings"]:
                with self.subTest(storyboard=path.name, slide=binding["slide"]):
                    self.assertIn(binding["slide"], slides)
                    self.assertNotIn(binding["target"], targets)
                    targets.add(binding["target"])
                    self.assertEqual(binding["target"], slides[binding["slide"]]["image"])
                    source = ROOT / binding["source"]
                    self.assertTrue(source.is_file(), binding["source"])
                    self.assertEqual(
                        binding["sha256"],
                        hashlib.sha256(source.read_bytes()).hexdigest(),
                    )

            for slide in slides.values():
                if slide["image"]:
                    self.assertIn(slide["image"], targets)

    def test_handoff_contains_no_machine_local_paths(self) -> None:
        for path in STORYBOARDS:
            text = path.read_text(encoding="utf-8")
            with self.subTest(storyboard=path.name):
                self.assertNotIn("D:\\", text)
                self.assertNotIn("AI_Projects", text)


if __name__ == "__main__":
    unittest.main()
