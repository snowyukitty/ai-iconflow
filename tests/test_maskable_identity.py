# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""A linked maskable source must be the master's mark — read on its plate too.

A card master's figure is its card. The same mark composed full-bleed for a
launcher's crop has no card left, so 0.7 compared a card with a mark and
refused a correct maskable source. The check now also reads the mark drawn on
the plate; a different mark still fails.
"""
import io
import unittest

from PIL import Image, ImageDraw

from iconflow import qa

PAPER, GRAPHITE = (255, 244, 232, 255), (25, 26, 32, 255)
SIZE = qa._IDENTITY_SIZE


def _png(image):
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _mark(draw, box, shape):
    left, top, right, bottom = box
    if shape == "blob":
        # A wide body with two ears: not a box, not symmetric.
        width, height = right - left, bottom - top
        draw.ellipse([left, top + height * 0.3, right, bottom], fill=PAPER)
        draw.ellipse([left + width * 0.15, top, left + width * 0.35, top + height * 0.5], fill=PAPER)
        draw.ellipse([left + width * 0.4, top, left + width * 0.6, top + height * 0.5], fill=PAPER)
    else:
        draw.rectangle([left, top + (bottom - top) * 0.4, right, top + (bottom - top) * 0.6], fill=PAPER)


def card_master(shape="blob"):
    """A graphite card with a large paper mark, flattened on a paper surround."""
    image = Image.new("RGBA", (SIZE, SIZE), PAPER)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([10, 10, SIZE - 11, SIZE - 11], radius=52, fill=GRAPHITE)
    _mark(draw, (40, 50, SIZE - 30, SIZE - 50), shape)
    return _png(image)


def full_bleed(shape="blob", scale=0.8):
    image = Image.new("RGBA", (SIZE, SIZE), GRAPHITE)
    draw = ImageDraw.Draw(image)
    inset = (1 - scale) / 2 * SIZE
    _mark(draw, (40 * scale + inset, 50 * scale + inset,
                 (SIZE - 30) * scale + inset, (SIZE - 50) * scale + inset), shape)
    return _png(image)


class PlateIdentityTests(unittest.TestCase):
    def test_the_same_mark_full_bleed_is_the_same_mark(self):
        self.assertEqual(qa.maskable_identity_findings(
            card_master(), full_bleed(), source_label="maskable.svg"), [])

    def test_another_mark_full_bleed_is_still_refused(self):
        found = qa.maskable_identity_findings(
            card_master(), full_bleed("bar"), source_label="maskable.svg")
        self.assertEqual([f.code for f in found], ["maskable-drift"])

    def test_another_mark_on_the_same_card_is_still_refused(self):
        found = qa.maskable_identity_findings(
            card_master(), card_master("bar"), source_label="maskable.svg")
        self.assertEqual([f.code for f in found], ["maskable-drift"])

    def test_a_silhouette_without_a_plate_reads_one_way(self):
        image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        _mark(ImageDraw.Draw(image), (40, 50, SIZE - 30, SIZE - 50), "blob")
        self.assertEqual(len(qa._figure_candidates(_png(image))), 1)


if __name__ == "__main__":
    unittest.main()
