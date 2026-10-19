# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""0.10: semantic layers and the ``ios`` target.

Each regression names the design-consult finding it closes (C-F01..C-F21,
recorded in docs/MILESTONE_v0.10.md). Everything runs without Chromium except
the class marked NEEDS_CHROMIUM.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

# Imported before any test patches ``iconflow.rasterize.Rasterizer``: a module
# first imported under that patch would bind the fake renderer for good.
from iconflow import headless, ios, qa, review  # noqa: F401
from iconflow.audit import AuditInputs, run_audit
from iconflow.casebook import AXES
from iconflow.cli import main
from iconflow.config import IconFlowConfig, contract_inputs, review_build_contract
from iconflow.detect import detect_targets
from iconflow.plan import (
    PlanError, RenderPlan, audit_ios, audit_origins, compute_plan, consumed_roles,
    write_plan,
)

NEEDS_CHROMIUM = unittest.skipUnless(
    os.environ.get("ICONFLOW_BROWSER_TESTS") == "1",
    "set ICONFLOW_BROWSER_TESTS=1 after installing Chromium",
)
ROOT = Path(__file__).resolve().parents[1]
RATIONALE = [f"--rationale={axis}=read the {axis} strip on the sheet" for axis in AXES]
PASSING = "legibility=4 distinctiveness=4 balance=4 color=4 scalability=4 craft=4"

CARD = ('<rect id="iconflow-background" x="40" y="40" width="944" height="944" '
        'rx="212" fill="#191A20"/>')
MARK = '<circle cx="512" cy="512" r="300" fill="#FFF4E8"/>'


def svg(body: str, view_box: str = "0 0 1024 1024") -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">{body}</svg>\n'


DECLARED = svg(CARD + MARK)
UNTAGGED = svg(CARD.replace(' id="iconflow-background"', "") + MARK)


def png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def disc(size: int, colour, ground=(0, 0, 0, 0)) -> bytes:
    image = Image.new("RGBA", (size, size), ground)
    margin = size // 4
    ImageDraw.Draw(image).ellipse((margin, margin, size - margin, size - margin), fill=colour)
    return png(image)


class Layered:
    """A renderer that honours the background layer: an opaque card when the
    SVG still declares one, the mark alone on transparency when it does not.
    The mark is light in the light scheme and pale blue in the dark one, so a
    test can see which scheme drew it."""

    renders: list = []
    #: Declares the sibling protocol, so the dark scheme is opened beside it.
    shares_browser = True

    def __init__(self, color_scheme="light", share=None):
        self.color_scheme = color_scheme
        self._share = share

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def render(self, text, size, bg="transparent"):
        Layered.renders.append((self.color_scheme, size, "iconflow-background" in text))
        mark = (255, 244, 232, 255) if self.color_scheme == "light" else (200, 220, 255, 255)
        image = Image.open(io.BytesIO(disc(size, mark)))
        if "iconflow-background" in text:
            # The card: inset like the house card, or the canvas once stretched.
            card = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            inset = 0 if 'width="1024"' in text and 'x="0"' in text else max(1, size // 16)
            ImageDraw.Draw(card).rectangle((inset, inset, size - 1 - inset, size - 1 - inset),
                                           fill=(25, 26, 32, 255))
            card.alpha_composite(image)
            image = card
        return png(image)

    def render_rect(self, text, width, height, bg="transparent"):
        return self.render(text, width, bg)


def write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def files_of(plan: RenderPlan) -> dict[str, bytes]:
    return {record.path: record.data for record in plan.files}


def ios_build(directory: Path, master_text: str = DECLARED, **kwargs) -> RenderPlan:
    master = write(directory, "master.svg", master_text)
    return compute_plan(master, ["ios"], bg_color="#ffffff", rasterizer=Layered(), **kwargs)


# --------------------------------------------------------------- the layers

class LayerTests(unittest.TestCase):
    def test_declared_background_resolves_with_its_fill(self):
        layers = ios.resolve(DECLARED)
        self.assertTrue(layers.declared)
        self.assertEqual(layers.fill, "#191A20")

    def test_C_F04_an_untagged_card_is_never_inferred(self):
        # 944x944 is 84.98% of the canvas: the inference the design proposed
        # would not even have found the house card. Only a declaration counts.
        layers = ios.resolve(UNTAGGED)
        self.assertFalse(layers.declared)
        self.assertIn('id="iconflow-background"', layers.hint)
        self.assertIn("looks like a card", layers.hint)

    def test_C_F05_C_F06_backgrounds_that_cannot_be_honoured_are_refused(self):
        cases = {
            "nested": svg(f"<g>{CARD}</g>{MARK}"),
            "not first": svg(MARK + CARD),
            "group": svg('<g id="iconflow-background"><rect width="1024" height="1024" '
                         'fill="#000"/></g>' + MARK),
            "transform": svg(CARD.replace("/>", ' transform="scale(2)"/>') + MARK),
            "style": svg(CARD.replace("/>", ' style="fill:red"/>') + MARK),
            "class": svg(CARD.replace("/>", ' class="card"/>') + MARK),
            "opacity": svg(CARD.replace("/>", ' opacity="0.5"/>') + MARK),
            "fill-opacity": svg(CARD.replace("/>", ' fill-opacity="0.5"/>') + MARK),
            "ladder": svg(CARD.replace("/>", ' data-lod="plate"/>') + MARK),
            "no fill": svg(CARD.replace(' fill="#191A20"', "") + MARK),
            "fill none": svg(CARD.replace('fill="#191A20"', 'fill="none"') + MARK),
            "translucent": svg(CARD.replace('fill="#191A20"', 'fill="#19192080"') + MARK),
            "pattern": svg('<defs><pattern id="p" width="8" height="8"/></defs>'
                           + CARD.replace('fill="#191A20"', 'fill="url(#p)"') + MARK),
            "missing paint": svg(CARD.replace('fill="#191A20"', 'fill="url(#gone)"') + MARK),
            "duplicate": svg(CARD + CARD.replace('x="40"', 'x="41"') + MARK),
            "use href": svg(CARD + '<use href="#iconflow-background"/>' + MARK),
            "xlink href": svg(CARD + '<use xmlns:xlink="http://www.w3.org/1999/xlink" '
                              'xlink:href="#iconflow-background"/>' + MARK),
            "clip reference": svg('<defs><clipPath id="c"><use href="#iconflow-background"/>'
                                  '</clipPath></defs>' + CARD + MARK),
            "stylesheet": svg('<style>#iconflow-background{fill:red}</style>' + CARD + MARK),
        }
        for label, text in cases.items():
            with self.subTest(label), self.assertRaises(ios.LayerError):
                ios.resolve(text)

    def test_a_gradient_background_is_honoured(self):
        text = svg('<defs><linearGradient id="g"><stop offset="0" stop-color="#123"/>'
                   '</linearGradient></defs>'
                   + CARD.replace('fill="#191A20"', 'fill="url(#g)"') + MARK)
        self.assertEqual(ios.resolve(text).fill, "url(#g)")
        self.assertIn('fill="url(#g)"', ios.full_bleed(text))

    def test_full_bleed_covers_the_view_box_and_mark_only_drops_the_card(self):
        text = svg(CARD + MARK, view_box="-10 20 1024 1024")
        bleed = ios.full_bleed(text)
        self.assertIn('x="-10" y="20" width="1024" height="1024"', bleed)
        self.assertNotIn('rx="212"', bleed)
        self.assertIn("<circle", bleed)
        mark = ios.mark_only(text)
        self.assertNotIn("iconflow-background", mark)
        self.assertIn("<circle", mark)

    def test_C_F02_derivations_are_independent_of_order(self):
        first = (ios.full_bleed(DECLARED), ios.mark_only(DECLARED))
        second = (ios.full_bleed(DECLARED), ios.mark_only(DECLARED))
        reverse = (ios.mark_only(DECLARED), ios.full_bleed(DECLARED))
        self.assertEqual(first, second)
        self.assertEqual(first, reverse[::-1])
        self.assertIn("iconflow-background", DECLARED)  # the master is never mutated

    def test_C_F09_C_F19_composer_layer_is_one_rung_with_lf(self):
        text = svg(CARD + '<g data-lod="plate">' + MARK + '</g>'
                   '<g data-lod="glyph"><rect width="9" height="9"/></g>')
        layer = ios.composer_svg(text.replace("\n", "\r\n"))
        self.assertNotIn("data-lod", layer)
        self.assertNotIn("<rect", layer)  # the glyph rung is not the 1024 rung
        self.assertNotIn("\r", layer)
        self.assertTrue(layer.endswith("\n") and not layer.endswith("\n\n"))

    def test_variants_policy(self):
        self.assertEqual(ios.appearances("auto", declared=True, linked=False), ios.APPEARANCES)
        self.assertEqual(ios.appearances("auto", declared=False, linked=True), ios.APPEARANCES)
        self.assertEqual(ios.appearances("auto", declared=False, linked=False), ("light",))
        self.assertEqual(ios.appearances("system", declared=True, linked=True), ("light",))
        with self.assertRaises(ValueError):
            ios.appearances("dark", declared=True, linked=False)


# ------------------------------------------------------------- the encodings

class EncodingTests(unittest.TestCase):
    def test_C_F10_light_composites_translucency_before_dropping_alpha(self):
        half = Image.new("RGBA", (4, 4), (255, 0, 0, 128))
        light = Image.open(io.BytesIO(ios.light_png(png(half), "#0000ff")))
        self.assertEqual(light.mode, "RGB")
        red, _green, blue = light.getpixel((0, 0))
        self.assertTrue(100 < red < 160 and 100 < blue < 160, light.getpixel((0, 0)))

    def test_C_F08_tinted_ignores_invisible_rgb_and_never_stretches(self):
        hidden = Image.new("RGBA", (4, 4), (255, 255, 255, 0))
        other = Image.new("RGBA", (4, 4), (0, 255, 0, 0))
        self.assertEqual(ios.tinted_png(png(hidden)), ios.tinted_png(png(other)))
        grey = Image.new("RGBA", (4, 4), (128, 128, 128, 255))
        tinted = Image.open(io.BytesIO(ios.tinted_png(png(grey))))
        self.assertEqual(tinted.mode, "L")
        self.assertEqual(tinted.getpixel((0, 0)), 128)  # a fixed mapping: no min-max stretch
        white = Image.new("RGBA", (4, 4), (255, 255, 255, 255))
        self.assertEqual(Image.open(io.BytesIO(ios.tinted_png(png(white)))).getpixel((1, 1)), 255)

    def test_contents_json_is_the_shape_actool_compiled(self):
        document = json.loads(ios.contents_json(ios.APPEARANCES))
        self.assertEqual(document["info"], {"author": "iconflow", "version": 1})
        self.assertEqual([image["filename"] for image in document["images"]],
                         ["icon-1024.png", "icon-1024-dark.png", "icon-1024-tinted.png"])
        self.assertNotIn("appearances", document["images"][0])
        self.assertEqual(document["images"][2]["appearances"],
                         [{"appearance": "luminosity", "value": "tinted"}])
        for image in document["images"]:
            self.assertEqual((image["idiom"], image["platform"], image["size"]),
                             ("universal", "ios", "1024x1024"))
        light_only = json.loads(ios.contents_json(("light",)))
        self.assertEqual(len(light_only["images"]), 1)

    def valid(self) -> dict:
        light = Image.new("RGB", (1024, 1024), (25, 26, 32))
        dark = Image.open(io.BytesIO(disc(1024, (255, 244, 232, 255))))
        tinted = Image.new("L", (1024, 1024), 0)
        return {ios.CONTENTS: ios.contents_json(ios.APPEARANCES), ios.LIGHT: png(light),
                ios.DARK: png(dark), ios.TINTED: png(tinted)}

    def test_C_F10_C_F11_the_validator_refuses_what_actool_accepts(self):
        ios.validate_files(self.valid(), ios.APPEARANCES)
        rgba = png(Image.new("RGBA", (1024, 1024), (25, 26, 32, 255)))
        rgb_tinted = png(Image.new("RGB", (1024, 1024)))
        opaque_dark = png(Image.new("RGBA", (1024, 1024), (9, 9, 9, 255)))
        small = png(Image.new("RGB", (512, 512)))
        trns = io.BytesIO()
        Image.new("L", (1024, 1024)).save(trns, "PNG", transparency=0)
        for label, change in {
            "light with alpha": {ios.LIGHT: rgba},
            "light too small": {ios.LIGHT: small},
            "tinted in colour": {ios.TINTED: rgb_tinted},
            "tinted with tRNS": {ios.TINTED: trns.getvalue()},
            "opaque dark": {ios.DARK: opaque_dark},
            "not a png": {ios.DARK: b"GIF89a"},
            "catalog lies": {ios.CONTENTS: ios.contents_json(("light",))},
            "stray file": {f"{ios.IOS_DIR}/extra.png": rgba},
        }.items():
            files = {**self.valid(), **change}
            with self.subTest(label), self.assertRaises(ValueError):
                ios.validate_files(files, ios.APPEARANCES)
        files = self.valid()
        del files[ios.TINTED]
        with self.assertRaises(ValueError):
            ios.validate_files(files, ios.APPEARANCES)


# ---------------------------------------------------------------- the probes

def shipped_files(dark_png: bytes) -> dict[str, bytes]:
    return {ios.DARK: dark_png, ios.TINTED: ios.tinted_png(dark_png)}


class ProbeTests(unittest.TestCase):
    plan = ios.Plan(ios.APPEARANCES, declared=True, linked=False, fill="#191A20", hint="")

    def test_a_light_mark_passes(self):
        metrics = ios.measure(shipped_files(disc(1024, (255, 244, 232, 255))), ios.APPEARANCES)
        self.assertEqual(ios.findings(metrics, self.plan), ([], []))

    def test_C_F07_a_dark_mark_on_a_light_card_is_refused(self):
        metrics = ios.measure(shipped_files(disc(1024, (20, 20, 22, 255))), ios.APPEARANCES)
        warnings, _ = ios.findings(metrics, self.plan)
        self.assertEqual({w.code for w in warnings}, {"ios-dark-contrast", "ios-tinted-faint"})
        self.assertIn("ios_dark_svg", warnings[0])
        self.assertIn('ios_variants = "system"', warnings[0])

    def test_C_F07_a_bright_dot_cannot_rescue_an_invisible_core(self):
        image = Image.open(io.BytesIO(disc(1024, (20, 20, 22, 255))))
        ImageDraw.Draw(image).ellipse((500, 500, 540, 540), fill=(255, 255, 255, 255))
        metrics = ios.measure(shipped_files(png(image)), ios.APPEARANCES)
        self.assertLess(metrics["dark_legible_share"], ios.DARK_LEGIBLE_SHARE)

    def test_cuts_in_the_card_colour_are_not_counted_against_the_mark(self):
        image = Image.open(io.BytesIO(disc(1024, (255, 244, 232, 255))))
        ImageDraw.Draw(image).rectangle((300, 300, 724, 724), fill=(25, 26, 32, 255))
        files = shipped_files(png(image))
        uncounted = ios.measure(files, ios.APPEARANCES)
        counted = ios.measure(files, ios.APPEARANCES, counter=(25, 26, 32))
        self.assertGreater(counted["dark_counter_share"], 0.3)
        self.assertGreater(counted["dark_legible_share"], uncounted["dark_legible_share"])
        self.assertEqual(counted["dark_legible_share"], 1.0)

    def test_an_empty_dark_layer_is_refused(self):
        empty = png(Image.new("RGBA", (1024, 1024), (0, 0, 0, 0)))
        warnings, _ = ios.findings(ios.measure(shipped_files(empty), ios.APPEARANCES), self.plan)
        self.assertEqual([w.code for w in warnings], ["ios-dark-empty"])

    def test_C_F21_leaving_variants_to_ios_only_advises(self):
        system = ios.Plan(("light",), declared=False, linked=False, fill=None, hint="declare it")
        warnings, advisories = ios.findings({}, system)
        self.assertEqual(warnings, [])
        self.assertEqual([a.code for a in advisories],
                         ["ios-variants-system", "ios-light-flattened"])

    def test_C_F16_a_dark_preview_shows_the_ground_through_its_transparency(self):
        files = {ios.DARK: png(Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))),
                 ios.LIGHT: png(Image.new("RGB", (1024, 1024), (255, 255, 255)))}
        shown = ios.previews(files, ("light", "dark"), 64)
        centre = shown["dark"].getpixel((32, 32))
        self.assertLess(max(centre[:3]), 80)  # the dark ground, never white
        self.assertEqual(centre[3], 255)
        self.assertEqual(shown["dark"].getpixel((0, 0))[3], 0)  # outside the mask
        self.assertNotIn("tinted", ios.previews(files, ("light",), 64))


# ------------------------------------------------------------ build and plan

class BuildTests(unittest.TestCase):
    def setUp(self):
        Layered.renders = []
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_a_declared_master_ships_all_three_appearances(self):
        plan = ios_build(self.dir)
        self.assertEqual(plan.produced, [ios.CONTENTS, ios.LIGHT, ios.DARK, ios.TINTED,
                                         ios.COMPOSER_MARK, ios.README])
        files = files_of(plan)
        light = Image.open(io.BytesIO(files[ios.LIGHT]))
        self.assertEqual(light.getpixel((2, 2)), (25, 26, 32))  # full bleed: no inset border
        self.assertEqual(Image.open(io.BytesIO(files[ios.DARK])).getpixel((2, 2))[3], 0)
        # the dark variant is drawn in the dark scheme, the light one in the build's
        self.assertIn(("dark", 1024, False), Layered.renders)
        self.assertIn(("light", 1024, True), Layered.renders)

    def test_an_untagged_master_ships_the_light_icon_alone(self):
        plan = ios_build(self.dir, UNTAGGED)
        self.assertEqual(plan.produced, [ios.CONTENTS, ios.LIGHT, ios.README])
        self.assertIn(b"iOS draws its own dark and tinted", files_of(plan)[ios.README])

    def test_system_variants_ship_the_light_icon_alone(self):
        plan = ios_build(self.dir, ios_variants="system")
        self.assertEqual(plan.produced, [ios.CONTENTS, ios.LIGHT, ios.README])
        self.assertEqual(plan.parameters["ios_variants"], "system")

    def test_a_linked_dark_source_is_captured_and_rendered(self):
        dark = write(self.dir, "dark.svg", svg('<circle cx="512" cy="512" r="200" fill="#fff"/>'))
        plan = ios_build(self.dir, UNTAGGED, ios_dark_svg=dark)
        self.assertIn("ios_dark", plan.inputs)
        self.assertIn(ios.DARK, plan.produced)
        self.assertNotIn(ios.COMPOSER_MARK, plan.produced)  # no declared foreground

    def test_C_F05_an_invalid_declaration_fails_the_build(self):
        with self.assertRaises(ios.LayerError):
            ios_build(self.dir, svg(f"<g>{CARD}</g>{MARK}"))

    def test_C_F19_text_files_are_lf_only(self):
        files = files_of(ios_build(self.dir))
        for path in (ios.CONTENTS, ios.README, ios.COMPOSER_MARK):
            self.assertNotIn(b"\r", files[path], path)

    def test_C_F01_C_F02_older_targets_and_parameters_are_untouched(self):
        master = write(self.dir, "master.svg", DECLARED)
        without = compute_plan(master, ["web", "tauri"], rasterizer=Layered())
        with_ios = compute_plan(master, ["web", "tauri", "ios"], rasterizer=Layered())
        old = files_of(without)
        new = files_of(with_ios)
        self.assertEqual({path: new[path] for path in old}, old)
        self.assertNotIn("ios_variants", without.parameters)
        self.assertEqual(with_ios.produced[:len(without.produced)], without.produced)

    def test_C_F01_the_contract_binds_ios_only_where_it_changes_bytes(self):
        dark = write(self.dir, "dark.svg", svg(MARK))

        def contract(targets, **kwargs):
            return review_build_contract(**contract_inputs(
                theme_color="#000000", background_color="#ffffff", electron_radius=0,
                tray_template_mode="auto", color_scheme="light", targets=targets, **kwargs))

        base = contract(["web"])
        self.assertEqual(contract(["web"], ios_dark_svg=dark, ios_variants="system"), base)
        self.assertEqual(contract(["web", "ios"]), base)
        self.assertEqual(contract(["web", "ios"], ios_variants="system")["ios_variants"], "system")
        self.assertIn("ios_dark_source_sha256", contract(["ios"], ios_dark_svg=dark))
        self.assertNotIn("ios_dark_source_sha256",
                         contract(["ios"], ios_dark_svg=dark, ios_variants="system"))

    def test_the_dark_source_is_consumed_only_by_ios_derivation(self):
        def roles(targets, variants="auto"):
            return consumed_roles(targets, tray_svg=None, maskable_svg=None, monochrome_svg=None,
                                  ios_dark_svg="dark.svg", ios_variants=variants)

        self.assertEqual(roles(["web"]), {"master"})
        self.assertEqual(roles(["ios"]), {"master", "ios_dark"})
        self.assertEqual(roles(["ios"], "system"), {"master"})

    def test_C_F18_a_build_refuses_to_leave_stale_ios_files_behind(self):
        out = self.dir / "out"
        write_plan(ios_build(self.dir), out)
        light_only = ios_build(self.dir, ios_variants="system")
        before = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
        with self.assertRaises(ValueError) as caught:
            write_plan(light_only, out)
        self.assertIn(ios.DARK, str(caught.exception))
        after = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
        self.assertEqual(before, after)
        fresh = self.dir / "fresh"
        self.assertEqual(write_plan(light_only, fresh), light_only.produced)

    def test_C_F10_C_F11_a_plan_with_a_broken_ios_file_is_refused(self):
        plan = ios_build(self.dir)
        audit_ios(plan)
        tampered = files_of(plan)
        tampered[ios.TINTED] = png(Image.new("RGB", (1024, 1024)))
        broken = RenderPlan.create(tampered, inputs=plan.inputs, parameters=plan.parameters,
                                   toolchain=plan.toolchain)
        with self.assertRaises(PlanError):
            audit_ios(broken)
        missing = files_of(plan)
        del missing[ios.TINTED], missing[ios.DARK]
        light_only = RenderPlan.create(missing, inputs=plan.inputs, parameters=plan.parameters,
                                       toolchain=plan.toolchain)
        with self.assertRaises(PlanError):  # the catalog still names dark and tinted
            audit_ios(light_only)

    def test_C_F12_provenance_names_each_shipped_ios_file(self):
        plan = ios_build(self.dir)
        origins = audit_origins(plan, maskable=False, linked=False, ios_target=True)
        self.assertEqual({key for key in origins if key.startswith("ios-")},
                         {"ios-light", "ios-dark", "ios-tinted"})
        self.assertEqual(origins["ios-tinted"]["file"], ios.TINTED)
        self.assertEqual(origins["ios-tinted"]["from"], "plan")
        self.assertNotIn("ios-light", audit_origins(plan, maskable=False, linked=False))


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        for target in ("iconflow.rasterize.Rasterizer", "iconflow.qa.Rasterizer"):
            patcher = mock.patch(target, new=Layered)
            patcher.start()
            self.addCleanup(patcher.stop)

    def audit(self, text, targets=("ios",), plan=None, **kwargs):
        master = write(self.dir, "master.svg", text)
        inputs = AuditInputs(master=master, targets=tuple(targets), **kwargs)
        return run_audit(inputs, rasterizer=Layered(), plan=plan)

    def test_the_audit_reads_the_plans_ios_files(self):
        plan = ios_build(self.dir)
        result = self.audit(DECLARED, plan=plan)
        self.assertEqual(result.frames["ios-dark"]["from"], "plan")
        self.assertIn("ios", result.metrics)

    def test_without_a_plan_the_audit_measures_the_same_bytes(self):
        result = self.audit(DECLARED)
        self.assertEqual(result.frames["ios-dark"]["from"], "render")
        planned = self.audit(DECLARED, plan=ios_build(self.dir))
        self.assertEqual(result.metrics["ios"], planned.metrics["ios"])

    def test_C_F11_a_plan_whose_appearances_the_policy_contradicts_is_refused(self):
        plan = ios_build(self.dir, ios_variants="system")
        with self.assertRaises(PlanError):
            self.audit(DECLARED, plan=plan)  # auto with a declared layer means three

    def test_C_F14_a_full_bleed_square_is_fine_when_only_ios_crops_it(self):
        square = svg('<rect width="1024" height="1024" fill="#123456"/>')
        with mock.patch("iconflow.qa.Rasterizer", new=Layered):
            only = self.audit(square, targets=("ios",))
            mixed = self.audit(square, targets=("web", "ios"))
        self.assertNotIn("coverage-16", {getattr(w, "code", "") for w in only.warnings})
        self.assertEqual(only.inputs.describe()["ios_variants"], "auto")
        self.assertNotIn("ios_variants", self.audit(square, targets=("web",)).inputs.describe())
        del mixed  # mixed selections keep 0.9's checks (exercised by test_audit)


class DetectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def targets(self):
        return {d.target: d.reason for d in detect_targets(self.root)}

    def test_C_F20_only_real_ios_projects_are_detected(self):
        catalog = self.root / "ios" / "AppIcon.appiconset"
        catalog.mkdir(parents=True)
        self.assertNotIn("ios", self.targets())  # IconFlow's own output is not evidence
        mac = self.root / "Mac.xcodeproj"
        mac.mkdir()
        (mac / "project.pbxproj").write_text("SDKROOT = macosx;", encoding="utf-8")
        self.assertNotIn("ios", self.targets())
        (mac / "project.pbxproj").write_text("SDKROOT = iphoneos;", encoding="utf-8")
        self.assertIn("iphoneos", self.targets()["ios"])

    def test_C_F20_framework_scaffolds(self):
        (self.root / "app.json").write_text(json.dumps({"expo": {"name": "x"}}), encoding="utf-8")
        self.assertNotIn("ios", self.targets())
        (self.root / "app.json").write_text(
            json.dumps({"expo": {"ios": {"bundleIdentifier": "a.b"}}}), encoding="utf-8")
        self.assertIn("Expo", self.targets()["ios"])
        (self.root / "app.json").unlink()
        (self.root / "pubspec.yaml").write_text("name: x", encoding="utf-8")
        (self.root / "ios" / "Runner.xcodeproj").mkdir(parents=True)
        self.assertIn("Flutter", self.targets()["ios"])


# ------------------------------------------------------- review, score, ship

def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main([*argv, "--json"])
    return code, json.loads(out.getvalue()), err.getvalue()


def write_png(path, *_args, **_kwargs):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (40, 40, 40)).save(path)
    return path


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        write(self.dir, "master.svg", DECLARED)
        self.config = write(self.dir, "iconflow.toml", '''schema_version = 1
[project]
name = "Card"
master = "master.svg"
output = "out"
[build]
targets = ["tauri", "ios"]
''')
        from iconflow.budget import Budget

        for target, kwargs in (
            ("iconflow.rasterize.Rasterizer", {"new": Layered}),
            ("iconflow.qa.Rasterizer", {"new": Layered}),
            ("iconflow.budget.budget_svg", {"return_value": Budget(
                source="master.svg", ground="transparent", cuts_256=1, cuts_16=1,
                parts_256=1, parts_16=1)}),
            ("iconflow.review.contact_sheet", {"side_effect": lambda m, out, **kw: write_png(out)}),
        ):
            patcher = mock.patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def review_and_score(self):
        evidence, receipt = self.dir / "evidence", self.dir / "receipt.json"
        code, envelope, err = run(["review", "--config", str(self.config),
                                   "--evidence", str(evidence)])
        self.assertEqual(code, 0, (envelope, err))
        code, envelope, err = run([
            "score", "--config", str(self.config), "--evidence", str(evidence),
            "--scores", PASSING, *RATIONALE, "--notes", "weakest: legibility",
            "--reviewer-name", "agent", "--out", str(receipt)])
        self.assertEqual(code, 0, (envelope, err))
        return evidence, receipt

    def test_C_F12_C_F13_review_score_ship_and_replay_carry_ios(self):
        evidence, receipt = self.review_and_score()
        findings = json.loads((evidence / "findings.json").read_text(encoding="utf-8"))
        self.assertIn("ios-tinted", findings["audit_provenance"]["frames"])
        self.assertEqual(findings["audit"]["ios_variants"], "auto")
        code, envelope, err = run(["ship", "--config", str(self.config), "--review", str(receipt)])
        self.assertEqual(code, 0, (envelope, err))
        self.assertTrue(envelope["outputs"]["plan"]["audited"])
        self.assertTrue((self.dir / "out" / ios.TINTED).is_file())
        code, envelope, err = run(["ship", "--config", str(self.config), "--review", str(receipt),
                                   "--plan", str(evidence / "plan"), "--out", str(self.dir / "r")])
        self.assertEqual(code, 0, (envelope, err))
        self.assertEqual((self.dir / "r" / ios.TINTED).read_bytes(),
                         (self.dir / "out" / ios.TINTED).read_bytes())

    def test_C_F12_an_ios_frame_dropped_from_the_findings_is_refused(self):
        evidence, _ = self.review_and_score()
        path = evidence / "findings.json"
        findings = json.loads(path.read_text(encoding="utf-8"))
        del findings["audit_provenance"]["frames"]["ios-dark"]
        path.write_text(json.dumps(findings), encoding="utf-8")
        code, envelope, err = run([
            "score", "--config", str(self.config), "--evidence", str(evidence),
            "--scores", PASSING, *RATIONALE, "--notes", "n", "--reviewer-name", "a",
            "--out", str(self.dir / "again.json")])
        self.assertEqual(code, 2, (envelope, err))

    def test_C_F11_an_ios_approval_without_its_plan_is_refused(self):
        _, receipt = self.review_and_score()
        data = json.loads(receipt.read_text(encoding="utf-8"))
        del data["plan"]
        receipt.write_text(json.dumps(data), encoding="utf-8")
        code, envelope, err = run(["ship", "--config", str(self.config), "--review", str(receipt)])
        self.assertEqual(code, 1, (envelope, err))
        self.assertIn("render plan it reviewed", err)
        self.assertFalse((self.dir / "out").exists())

    def test_the_config_round_trips_the_ios_keys(self):
        from iconflow.config import config_text, load_config

        config = load_config(self.config)
        self.assertEqual((config.ios_variants, config.ios_dark_svg), ("auto", ""))
        self.assertNotIn("ios_", config_text(config))
        config.ios_variants, config.ios_dark_svg = "system", "dark.svg"
        text = config_text(config)
        self.assertIn('ios_variants = "system"', text)
        self.assertIn('ios_dark_svg = "dark.svg"', text)
        broken = write(self.dir, "bad.toml", self.config.read_text(encoding="utf-8")
                       + 'ios_variants = "never"\n')
        from iconflow.config import ConfigError

        with self.assertRaises(ConfigError):
            load_config(broken)
        self.assertIsInstance(config, IconFlowConfig)


# -------------------------------------------------------------- real pixels

@NEEDS_CHROMIUM
class RealChromiumTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_the_brand_master_derives_three_legible_appearances(self):
        plan = compute_plan(ROOT / "brand" / "master.svg", ["ios"], bg_color="#191A20")
        files = files_of(plan)
        ios.validate_files(files, ios.APPEARANCES)
        layers = ios.resolve((ROOT / "brand" / "master.svg").read_text(encoding="utf-8"))
        metrics = ios.measure(files, ios.APPEARANCES, counter=ios.counter_colour(layers.fill))
        self.assertGreater(metrics["dark_legible_share"], 0.9)
        self.assertGreater(metrics["tinted_mean"], 150)

    def test_C_F07_the_woodcut_scaffold_is_refused_on_the_dark_screen(self):
        master = ROOT / "templates" / "presets" / "woodcut.svg"
        result = run_audit(AuditInputs(master=master, targets=("ios",)))
        self.assertIn("ios-dark-contrast", {w.code for w in result.warnings},
                      (result.metrics.get("ios"), [a.code for a in result.advisories]))

    def test_C_F03_tagged_presets_render_exactly_as_before(self):
        import subprocess

        from iconflow.rasterize import Rasterizer

        tagged = subprocess.run(["git", "cat-file", "-e", "v0.9.0:templates/presets"],
                                cwd=ROOT, capture_output=True)
        if tagged.returncode != 0:
            self.skipTest("needs the v0.9.0 tag (a shallow CI checkout has none)")
        with Rasterizer() as r:
            for path in sorted((ROOT / "templates" / "presets").glob("*.svg")):
                text = path.read_text(encoding="utf-8")
                if 'id="iconflow-background"' not in text:
                    continue
                with self.subTest(path.name):
                    old = subprocess.run(
                        ["git", "show", f"v0.9.0:templates/presets/{path.name}"],
                        cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
                    self.assertTrue(ios.resolve(text).declared)
                    for size in (16, 64, 1024):
                        self.assertEqual(r.render(old, size), r.render(text, size))

    def test_scheme_sibling_shares_the_open_browser(self):
        from iconflow.rasterize import Rasterizer
        from iconflow.session import scheme_sibling

        query = svg('<style>@media (prefers-color-scheme: dark){rect{fill:#fff}}</style>'
                    '<rect width="1024" height="1024" fill="#000"/>')
        with Rasterizer() as light, scheme_sibling(light, "dark") as dark:
            self.assertIsNot(dark, light)
            white = Image.open(io.BytesIO(dark.render(query, 8))).convert("RGB").getpixel((4, 4))
            black = Image.open(io.BytesIO(light.render(query, 8))).convert("RGB").getpixel((4, 4))
        self.assertEqual((white, black), ((255, 255, 255), (0, 0, 0)))


if __name__ == "__main__":
    unittest.main()
