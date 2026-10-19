# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""The render plan: every byte a build will ship, computed once.

Before 0.8, ``ship`` audited in one Chromium session and ``build`` rendered
everything again in another, writing each file as it went. Nothing checked
that the pixels a person reviewed were the pixels that shipped, and a target
that failed late (an emote over its upload limit, an Android themed layer that
could not be derived) left a half-written output tree behind.

A :class:`RenderPlan` is the whole output — every PNG, container, manifest and
snippet — held in memory, immutable, with the source snapshots and parameters
that produced it. ``build`` computes one and writes it only once it is
complete. Review records the plan's identity in its receipt, and ``ship``
compares the plan it is about to write against that identity, so "the
reviewed pixels are the shipped pixels" is checked, not assumed. The design,
and what it does not promise, is ``docs/RENDER_PLAN.md``.

Two identities, deliberately different:

* :attr:`RenderPlan.digest` (content) — a PNG contributes the SHA-256 of its
  decoded RGBA pixels and size; an ICO or ICNS the pixels of every frame, in
  order, with its slot; any other file its bytes (text with CRLF read as LF).
  A lossless re-encode of a PNG or a platform's newlines are not drift; a
  changed pixel always is. It is a *hybrid* fingerprint: ``trayIcon.ts``
  embeds PNG bytes, so it is byte-sensitive.
* :attr:`RenderPlan.artifact_digest` (exact bytes) — every file's SHA-256.
  This is what ``ship --plan`` replays: the reviewed bytes, byte for byte.
"""
from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import os
import platform
import re
import shutil
import struct
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping

from PIL import Image

from . import assemble, htmlhead, ios
from .rasterize import svg_text_from_bytes

#: Version of the manifest and of a receipt's ``plan`` binding.
PLAN_SCHEMA = 1
#: The manifest's file name inside a plan directory; payloads live under FILES_DIR.
MANIFEST_NAME = "plan.json"
FILES_DIR = "files"
#: Import bounds: a plan is a handful of icons, never a disk image.
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_PLAN_BYTES = 256 * 1024 * 1024
MAX_PLAN_FILES = 512
MAX_PLAN_DEPTH = 8
MAX_PIXELS = 8192 * 8192
#: Gate codes (exit 1): rendered pixels differ from the approved ones, or a
#: saved plan cannot be published as the reviewed output.
GATE_PLAN_DRIFT = "plan-drift"
GATE_PLAN_REPLAY = "plan-replay"


class PlanError(ValueError):
    """A plan that cannot honestly stand for reviewed output."""


def toolchain() -> dict[str, str | None]:
    """What rendered the pixels. Provenance only: it explains drift, never excuses it."""
    # The version of the code that ran, not of whatever distribution metadata
    # the interpreter finds: a stale editable install reported 0.7.0 for 0.8.
    from . import __version__ as iconflow_version
    try:
        import PIL
        pillow_version = getattr(PIL, "__version__", None)
    except ImportError:
        pillow_version = None
    chromium_version = None
    try:
        import playwright
        catalog = Path(playwright.__file__).resolve().parent / "driver" / "package" / "browsers.json"
        for browser in json.loads(catalog.read_text(encoding="utf-8")).get("browsers", []):
            if browser.get("name") == "chromium":
                chromium_version = browser.get("browserVersion") or None
                break
    except (ImportError, OSError, ValueError, AttributeError):
        chromium_version = None
    return {
        "iconflow": iconflow_version,
        "chromium": chromium_version,
        "pillow": pillow_version,
        "platform": platform.system() or None,
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ----------------------------------------------------------------- identities

def _pixels_sha256(png: bytes) -> str:
    """Domain-separated digest of a PNG's decoded RGBA8 samples, row-major."""
    try:
        with Image.open(io.BytesIO(png)) as image:
            if image.format != "PNG":
                raise PlanError("a .png output is not a PNG")
            if getattr(image, "is_animated", False):
                raise PlanError("an animated PNG cannot stand for one icon")
            if image.width * image.height > MAX_PIXELS:
                raise PlanError("a PNG output is too large to be an icon")
            image.load()
            rgba = image.convert("RGBA")
    except PlanError:
        raise
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise PlanError(f"an image output cannot be decoded: {exc}") from exc
    header = b"iconflow-pixels-v1\0" + rgba.width.to_bytes(4, "big") + rgba.height.to_bytes(4, "big")
    return _sha256(header + rgba.tobytes())


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_TEXT_SUFFIXES = frozenset({".svg", ".html", ".webmanifest", ".xml", ".ts", ".json"})


def content_sha256(path: str, data: bytes) -> str:
    """The content identity of one output (see the module docstring).

    A container contributes every entry in slot order — its directory fields
    or chunk type, and the decoded pixels of its payload — so a repeated, an
    extra, a reordered or a re-described frame is a different container.
    """
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".png":
        return _pixels_sha256(data)
    if suffix in {".ico", ".icns"}:
        try:
            if suffix == ".ico":
                entries = [(",".join(map(str, fields[:6])), payload)
                           for fields, payload in assemble.ico_entries(data)]
            else:
                entries = [(ostype.hex(), payload) for ostype, payload in assemble.icns_entries(data)]
        except (ValueError, IndexError, struct.error) as exc:
            raise PlanError(f"{path}: unreadable container ({exc})") from exc
        # A PNG payload by its pixels; anything else (a BMP frame, a TOC or
        # unknown chunk) by its bytes, so it still counts.
        listing = "".join(
            f"{slot}:{described}:"
            f"{_pixels_sha256(payload) if payload[:8] == _PNG_SIGNATURE else _sha256(payload)}\n"
            for slot, (described, payload) in enumerate(entries))
        return _sha256(f"iconflow-{suffix[1:]}-v1\n{listing}".encode("ascii"))
    if suffix in _TEXT_SUFFIXES:
        return _sha256(data.replace(b"\r\n", b"\n"))
    return _sha256(data)


def _listing_digest(kind: str, entries: Mapping[str, str]) -> str:
    listing = "".join(f"{path}\t{entries[path]}\n" for path in sorted(entries))
    return _sha256(f"iconflow-plan-{kind}-v1\n{listing}".encode("utf-8"))


def provenance_digest(inputs: Mapping, parameters: Mapping) -> str:
    """What produced the plan: each source role's hash and every effective setting.

    Source *paths* are left out — they are machine-local — so the same
    sources and settings give the same provenance on every machine.
    """
    canonical = {
        "inputs": {role: _thaw(record).get("sha256") for role, record in inputs.items()},
        "parameters": _thaw(parameters),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256(b"iconflow-plan-provenance-v1\n" + encoded.encode("utf-8"))


# ------------------------------------------------------------------- records

@dataclass(frozen=True)
class Source:
    """One source file, read once. Rendering, hashing and copying all use these bytes."""

    role: str
    path: str
    raw: bytes = field(repr=False)
    text: str = field(repr=False)

    @property
    def sha256(self) -> str:
        """The normalised-text hash receipts bind (``config.svg_sha256``)."""
        normalised = self.text.replace("\r\n", "\n").replace("\r", "\n")
        return _sha256(normalised.encode("utf-8"))


def snapshot(path: str | Path, role: str) -> Source:
    raw = Path(path).read_bytes()
    return Source(role=role, path=str(path), raw=raw, text=svg_text_from_bytes(raw, path))


@dataclass(frozen=True)
class PlanFile:
    path: str
    data: bytes = field(repr=False)
    sha256: str
    content_sha256: str

    @classmethod
    def of(cls, path: str, data: bytes) -> "PlanFile":
        _relative(path)
        data = bytes(data)
        return cls(path=path, data=data, sha256=_sha256(data), content_sha256=content_sha256(path, data))


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


#: Plan files that hold the master's own renders, untransformed, and how to
#: read sizes out of them (R01: approval surfaces show these, not new renders).
_MASTER_FRAME_FILES = ("favicon.ico", "icons/icon.ico", "icons/icon.icns")
_MASTER_PNG = re.compile(r"^(?:icon-(\d+)\.png|icons/(\d+)x\2\.png|emote/(\d+)\.png)$")


@dataclass(frozen=True)
class RenderPlan:
    """Every output of one build, immutable, with what produced it."""

    files: tuple[PlanFile, ...]
    inputs: Mapping[str, Mapping[str, str]]
    parameters: Mapping[str, object]
    toolchain: Mapping[str, object]

    @classmethod
    def create(cls, files: Mapping[str, bytes], *, inputs, parameters, toolchain) -> "RenderPlan":
        records = tuple(PlanFile.of(path, data) for path, data in files.items())
        folded = [record.path.casefold() for record in records]
        if len(set(folded)) != len(folded):
            raise PlanError("a plan names the same output path twice")
        return cls(files=records, inputs=_freeze(inputs), parameters=_freeze(parameters),
                   toolchain=_freeze(toolchain))

    @property
    def produced(self) -> list[str]:
        """Relative paths in the order the build produces them (``build()``'s return)."""
        return [record.path for record in self.files]

    def file(self, path: str) -> bytes:
        for record in self.files:
            if record.path == path:
                return record.data
        raise KeyError(path)

    def get(self, path: str) -> bytes | None:
        try:
            return self.file(path)
        except KeyError:
            return None

    def master_frames(self) -> dict[int, bytes]:
        """The master's own renders this plan ships, by pixel size.

        Taken from the untransformed outputs (favicon and Tauri containers,
        ``icon-N.png``, Tauri and emote PNGs), so a review surface that shows
        "the icon at 32px" can show the exact frame that ships.
        """
        frames: dict[int, bytes] = {}
        for record in self.files:
            match = _MASTER_PNG.match(record.path)
            if match:
                size = int(next(group for group in match.groups() if group))
                frames.setdefault(size, record.data)
            elif record.path in _MASTER_FRAME_FILES:
                read = assemble.ico_frames if record.path.endswith(".ico") else assemble.icns_frames
                for size, payload in read(record.data).items():
                    frames.setdefault(size, payload)
        return frames

    @property
    def digest(self) -> str:
        return _listing_digest("content", {r.path: r.content_sha256 for r in self.files})

    @property
    def artifact_digest(self) -> str:
        return _listing_digest("bytes", {r.path: f"{len(r.data)}:{r.sha256}" for r in self.files})

    @property
    def provenance_digest(self) -> str:
        return provenance_digest(self.inputs, self.parameters)

    def binding(self) -> dict:
        """What a review receipt records about the pixels it approved."""
        return {
            "schema": PLAN_SCHEMA,
            "digest": self.digest,
            "artifact_digest": self.artifact_digest,
            "provenance_digest": self.provenance_digest,
            "files": {r.path: {"content": r.content_sha256, "sha256": r.sha256} for r in self.files},
            "toolchain": _thaw(self.toolchain),
        }

    def manifest(self) -> dict:
        return {
            "schema": PLAN_SCHEMA,
            "digest": self.digest,
            "artifact_digest": self.artifact_digest,
            "provenance_digest": self.provenance_digest,
            "inputs": _thaw(self.inputs),
            "parameters": _thaw(self.parameters),
            "toolchain": _thaw(self.toolchain),
            "files": [
                {"path": r.path, "bytes": len(r.data), "sha256": r.sha256,
                 "content_sha256": r.content_sha256}
                for r in self.files
            ],
        }


# ------------------------------------------------------------------ planning

def plan_parameters(targets, *, name, theme_color, bg_color, electron_radius, tray_ts,
                    color_scheme, web_options, optimize_png, tray_template_mode,
                    maskable_scale, maskable_svg, ios_variants: str = "auto") -> dict:
    """The effective output parameters a plan records (and ``ship --plan`` re-derives).

    ``ios_variants`` is recorded only for a plan that builds ``ios``, so every
    other plan keeps exactly the parameters it had in 0.9 (C-F01).
    """
    from .build import ADAPTIVE_TARGETS, resolve_maskable_scale

    options = web_options or htmlhead.WebMetaOptions()
    adaptive = bool(ADAPTIVE_TARGETS & set(targets))
    parameters = {
        "targets": list(targets),
        "name": name,
        "theme_color": theme_color,
        "background_color": bg_color,
        "electron_radius": electron_radius,
        "tray_ts": bool(tray_ts),
        "color_scheme": color_scheme,
        "optimize_png": bool(optimize_png),
        "tray_template_mode": tray_template_mode,
        "maskable_scale": (
            resolve_maskable_scale(maskable_scale, linked=maskable_svg is not None)
            if adaptive else None
        ),
        "web_options": dataclasses.asdict(options),
    }
    if "ios" in targets:
        parameters["ios_variants"] = ios_variants
    return parameters


#: Every source role a plan can record, in capture order.
ROLES = ("master", "tray", "maskable", "monochrome", "ios_dark")


def consumed_roles(targets, *, tray_svg, maskable_svg, monochrome_svg,
                   ios_dark_svg=None, ios_variants: str = "auto") -> set[str]:
    """The source roles a build with these targets reads (the master always)."""
    from .build import ADAPTIVE_TARGETS

    targets = set(targets)
    roles = {"master"}
    if tray_svg is not None and ("tray" in targets or ("android" in targets and monochrome_svg is None)):
        roles.add("tray")
    if maskable_svg is not None and ADAPTIVE_TARGETS & targets:
        roles.add("maskable")
    if monochrome_svg is not None and "android" in targets:
        roles.add("monochrome")
    if ios_dark_svg is not None and "ios" in targets and ios_variants != "system":
        roles.add("ios_dark")
    return roles


def _file_identity(path) -> object:
    """The same key for every path to one file (device and inode where the OS has them)."""
    try:
        status = os.stat(path)
    except OSError:
        return os.path.normcase(os.path.realpath(path))
    if status.st_ino:
        return (status.st_dev, status.st_ino)
    return os.path.normcase(os.path.realpath(path))


def capture_sources(master_svg: str | Path, targets, *, tray_svg=None, maskable_svg=None,
                    monochrome_svg=None, ios_dark_svg=None, ios_variants: str = "auto",
                    consumed_only: bool = True) -> dict[str, Source]:
    """Read every source a build with these targets consumes, once, by role.

    One read per *file*, shared by every role that names it — by file
    identity, so a symlink or a hard link to the same file is read once (a
    link that names the master is still a link: the default maskable scale
    depends on it, but the bytes are the master's). Each role keeps its own
    path, so a role whose file is later replaced is still seen to change
    (R01). A command captures once and hands the result to the plan, the
    audit and the approval check, so all of them measure the same bytes (D01).

    With ``consumed_only=False`` every configured source is captured, also
    one the selected targets do not build from but a review still shows or
    hashes (a linked maskable source under ``--targets emote``): what a
    command freezes and checks must cover everything it reads (V-R01).
    """
    import importlib

    b = importlib.import_module(".build", __package__)
    targets = b.normalize_targets(targets)
    roles = consumed_roles(targets, tray_svg=tray_svg, maskable_svg=maskable_svg,
                           monochrome_svg=monochrome_svg, ios_dark_svg=ios_dark_svg,
                           ios_variants=ios_variants)
    linked = (("tray", tray_svg), ("maskable", maskable_svg), ("monochrome", monochrome_svg),
              ("ios_dark", ios_dark_svg))
    if not consumed_only:
        # An unconsumed link to a missing file was harmless in 0.8 and stays so.
        roles |= {role for role, path in linked if path is not None and Path(path).is_file()}
    by_file: dict[object, Source] = {}
    sources: dict[str, Source] = {}
    for role, path in (("master", master_svg), *linked):
        if role not in roles:
            continue
        key = _file_identity(path)
        if key not in by_file:
            by_file[key] = snapshot(path, role)
        read = by_file[key]
        # The same bytes objects: the plan renders a shared file once.
        sources[role] = Source(role=role, path=str(path), raw=read.raw, text=read.text)
    return sources


def consumed(sources: Mapping[str, Source], targets, *, tray_svg=None, maskable_svg=None,
             monochrome_svg=None, ios_dark_svg=None,
             ios_variants: str = "auto") -> dict[str, Source]:
    """The captured roles a build with these targets reads (what ``compute_plan`` takes)."""
    roles = consumed_roles(targets, tray_svg=tray_svg, maskable_svg=maskable_svg,
                           monochrome_svg=monochrome_svg, ios_dark_svg=ios_dark_svg,
                           ios_variants=ios_variants)
    return {role: source for role, source in sources.items() if role in roles}


def frozen_view(sources: Mapping[str, Source]):
    """While it is entered, every :func:`~iconflow.rasterize.load_svg` of a
    captured path returns the captured text (R01)."""
    from .rasterize import frozen_sources

    return frozen_sources({source.path: source.text for source in sources.values()})


def changed_sources(sources: Mapping[str, Source]) -> list[str]:
    """The roles whose file no longer holds the bytes captured (a mid-run edit)."""
    changed = []
    for role, source in sources.items():
        try:
            raw = Path(source.path).read_bytes()
        except OSError:
            changed.append(role)
            continue
        if raw != source.raw:
            changed.append(role)
    return changed


def compute_plan(master_svg: str | Path, targets=("web",), *,
                 name: str = "App", theme_color: str = "#0b0d12",
                 bg_color: str = "#ffffff", electron_radius: float = 0.0,
                 tray_ts: bool = False, color_scheme: str = "light",
                 web_options: htmlhead.WebMetaOptions | None = None,
                 optimize_png: bool = True, tray_svg: str | Path | None = None,
                 tray_template_mode: str = "auto",
                 maskable_scale: float | None = None,
                 maskable_svg: str | Path | None = None,
                 monochrome_svg: str | Path | None = None,
                 ios_dark_svg: str | Path | None = None, ios_variants: str = "auto",
                 rasterizer=None, sources: Mapping[str, Source] | None = None) -> RenderPlan:
    """Render every output of a build into memory. No publication writes.

    Takes exactly :func:`iconflow.build.build`'s arguments (less ``outdir``),
    validates them the same way, and returns a plan whose files are the bytes
    ``build`` writes, in its order. Each source *file* is read once, whatever
    roles it plays; its snapshot is rendered, hashed and (for an unannotated
    favicon) copied, so an edit made mid-build cannot mix two versions.
    Optional sources a selected target does not consume are not read.
    """
    import importlib

    # ``iconflow.build`` the module: the package re-exports a function by that name.
    b = importlib.import_module(".build", __package__)

    targets = b.normalize_targets(targets)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    assemble.opaque_color(theme_color, "theme color")
    assemble.opaque_color(bg_color, "background color")
    electron_radius = assemble.validate_radius(electron_radius)
    if tray_template_mode not in {"auto", "alpha", "contrast"}:
        raise ValueError("tray_template_mode must be 'auto', 'alpha', or 'contrast'")
    if web_options and web_options.tile_color:
        assemble.opaque_color(web_options.tile_color, "tile color")
    if maskable_scale is not None:
        maskable_scale = b.validate_maskable_scale(maskable_scale)
    if ios_variants not in ios.VARIANTS:
        raise ValueError("ios_variants must be 'auto' or 'system'")
    roles = consumed_roles(targets, tray_svg=tray_svg, maskable_svg=maskable_svg,
                           monochrome_svg=monochrome_svg, ios_dark_svg=ios_dark_svg,
                           ios_variants=ios_variants)
    if sources is None:
        sources = capture_sources(master_svg, targets, tray_svg=tray_svg,
                                  maskable_svg=maskable_svg, monochrome_svg=monochrome_svg,
                                  ios_dark_svg=ios_dark_svg, ios_variants=ios_variants)
    elif set(sources) != roles:
        raise PlanError("captured sources do not match the roles these targets consume: "
                         f"captured {sorted(sources)}, consumed {sorted(roles)}")
    sources = dict(sources)
    master = sources["master"]
    tray = sources.get("tray")
    maskable = sources.get("maskable")
    monochrome = sources.get("monochrome")
    ios_dark = sources.get("ios_dark")
    # Resolved before any render, so a declared layer IconFlow cannot honour
    # fails the build up front (C-F05).
    ios_plan = (ios.plan_for(master.text, variants=ios_variants, linked=ios_dark is not None)
                if "ios" in targets else None)

    def render(r) -> dict[str, bytes]:
        caches: dict[int, object] = {}

        def cache_for(source: Source | None):
            if source is None:
                return None
            # Keyed by the bytes read, so roles that share one file share a cache.
            if id(source.raw) not in caches:
                caches[id(source.raw)] = b.RenderCache(source.text, r, optimize=optimize_png)
            return caches[id(source.raw)]

        cache = cache_for(master)
        files: dict[str, bytes] = {}
        maskable_cache = cache_for(maskable)
        if "web" in targets or "pwa" in targets:
            files.update(b.web_files(
                cache, master.raw, name, theme_color, bg_color, web_options,
                maskable_scale=maskable_scale, maskable_cache=maskable_cache,
            ))
        if "tauri" in targets:
            files.update(b.tauri_files(cache))
        if "electron" in targets:
            files.update(b.electron_files(cache, electron_radius))
        if "tray" in targets:
            files.update(b.tray_files(
                cache, tray_ts, tray_cache=cache_for(tray), template_mode=tray_template_mode,
            ))
        if "android" in targets:
            files.update(b.android_assets(
                cache, bg_color, maskable_scale=maskable_scale, maskable_cache=maskable_cache,
                monochrome_cache=cache_for(monochrome if monochrome is not None else tray),
                template_mode=tray_template_mode,
            ))
        if "emote" in targets:
            files.update(b.emote_files(cache))
        if ios_plan is not None:
            files.update(ios_files(r, ios_plan, master.text,
                                   ios_dark.text if ios_dark is not None else None, bg_color))
        return files

    if rasterizer is not None:
        files = render(rasterizer)
    else:
        # Through ``iconflow.build`` so substituting its renderer (as tests and
        # callers have since 0.5) substitutes the plan's.
        with b.Rasterizer(color_scheme=color_scheme) as owned:
            files = render(owned)
    return RenderPlan.create(
        files,
        inputs={role: {"path": s.path, "sha256": s.sha256, "bytes_sha256": _sha256(s.raw)}
                for role, s in sources.items()},
        parameters=plan_parameters(
            targets, name=name, theme_color=theme_color, bg_color=bg_color,
            electron_radius=electron_radius, tray_ts=tray_ts, color_scheme=color_scheme,
            web_options=web_options, optimize_png=optimize_png,
            tray_template_mode=tray_template_mode, maskable_scale=maskable_scale,
            maskable_svg=maskable_svg, ios_variants=ios_variants,
        ),
        toolchain=toolchain(),
    )


def ios_files(r, ios_plan, master_text: str, dark_text: str | None,
              bg_color: str) -> dict[str, bytes]:
    """The iOS files, from caches of their own (C-F02).

    Each derived text gets an independent :class:`~iconflow.build.RenderCache`
    — a cache keyed by size must never answer for a different text — while
    renders still go through the command's one session. The iOS encoders
    write their own PNG modes, so the RGBA re-pack ``optimize_png`` does is
    never applied to them.
    """
    import importlib

    b = importlib.import_module(".build", __package__)
    light_text = ios.full_bleed(master_text) if ios_plan.declared else master_text
    light = b.RenderCache(light_text, r, optimize=False)
    if "dark" not in ios_plan.shipped:
        return ios.files(light, None, ios_plan, master_text=master_text, bg_color=bg_color)
    if dark_text is None:
        dark_text = ios.mark_only(master_text)
    with ios.dark_renderer(r) as dark_r:
        dark = b.RenderCache(dark_text, dark_r, optimize=False)
        return ios.files(light, dark, ios_plan, master_text=master_text, bg_color=bg_color)


# ------------------------------------------------------------ audit frames

#: Plan files that are the master rendered at one size and nothing else —
#: what the audit may measure instead of rendering (0.9, F09). Apple-touch is
#: flattened, Electron rounded, tray and Android composed, and emote sizes are
#: none the audit probes, so none of them can stand for "the master at N px".
AUDIT_PNGS = {
    "icon-192.png": 192, "icon-512.png": 512,
    "icons/32x32.png": 32, "icons/64x64.png": 64, "icons/128x128.png": 128,
    "icons/128x128@2x.png": 256, "icons/icon.png": 512,
}
AUDIT_CONTAINERS = ("favicon.ico", "icons/icon.ico", "icons/icon.icns")
#: The one maskable composition web and PWA ship.
MASKABLE_FILE = "icon-512-maskable.png"


@dataclass(frozen=True)
class AuditFrame:
    """One shipped image the audit measured, and exactly where it came from."""

    png: bytes
    origin: Mapping[str, object]


def _audit_frame(path: str, slot: int | None, size: int, payload: bytes) -> AuditFrame:
    if payload[:8] != _PNG_SIGNATURE:
        raise PlanError(f"{path}: the {size}px frame is not a PNG")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            dimensions = image.size
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise PlanError(f"{path}: the {size}px frame cannot be decoded: {exc}") from exc
    if dimensions != (size, size):
        raise PlanError(f"{path}: the frame named {size}px decodes to "
                        f"{dimensions[0]}x{dimensions[1]}")
    origin = {"from": "plan", "file": path, "slot": slot, "size": size,
              "sha256": _sha256(payload), "content_sha256": _pixels_sha256(payload)}
    return AuditFrame(payload, MappingProxyType(origin))


def audit_frames(plan: RenderPlan) -> dict[int, AuditFrame]:
    """The master's shipped renders by pixel size, each with its origin.

    Every representation of a size is decoded and checked: a frame whose
    pixels are not the size its name or slot claims, or two representations
    of one size that disagree, make the plan unusable as audit evidence
    (``PlanError``) — never a reason to measure a fresh render instead. The
    first representation in build order is the one recorded.
    """
    found: dict[int, list[AuditFrame]] = {}
    for record in plan.files:
        if record.path in AUDIT_PNGS:
            entries = [(None, AUDIT_PNGS[record.path], record.data)]
        elif record.path in AUDIT_CONTAINERS:
            try:
                read = (assemble.ico_frames if record.path.endswith(".ico")
                        else assemble.icns_frames)
                entries = [(size, size, payload) for size, payload in read(record.data).items()]
            except (ValueError, IndexError, struct.error) as exc:
                raise PlanError(f"{record.path}: unreadable container ({exc})") from exc
        else:
            continue
        for slot, size, payload in entries:
            found.setdefault(size, []).append(_audit_frame(record.path, slot, size, payload))
    frames: dict[int, AuditFrame] = {}
    for size, candidates in found.items():
        if len({frame.origin["content_sha256"] for frame in candidates}) > 1:
            files = ", ".join(sorted({str(frame.origin["file"]) for frame in candidates}))
            raise PlanError(f"the plan carries two different {size}px renders of the master ({files})")
        frames[size] = candidates[0]
    return frames


def audit_maskable(plan: RenderPlan) -> AuditFrame | None:
    """The shipped maskable composition, or None when no selected target writes it."""
    data = plan.get(MASKABLE_FILE)
    return None if data is None else _audit_frame(MASKABLE_FILE, None, 512, data)


#: Files a target's plan must carry before it can stand as audit evidence: a
#: plan that claims web but lacks its favicon is not "a plan without a 16 px
#: frame", it is an incomplete plan (R03).
REQUIRED_AUDIT_FILES = {
    "web": ("favicon.ico", "icon-192.png", "icon-512.png", MASKABLE_FILE),
    "pwa": ("favicon.ico", "icon-192.png", "icon-512.png", MASKABLE_FILE),
    "tauri": (*AUDIT_PNGS.keys() - {"icon-192.png", "icon-512.png"},
              "icons/icon.ico", "icons/icon.icns"),
    "ios": (ios.CONTENTS, ios.LIGHT),
}
FAVICON_SLOTS = (16, 32, 48)


def _required_slots() -> dict[str, set[int]]:
    """Every audit container's exact slot set: a container missing a frame its
    build always writes is an incomplete plan, not a smaller one (V-R03)."""
    from .build import ICNS_FRAME_SIZES, ICO_FRAME_ORDER

    return {"favicon.ico": set(FAVICON_SLOTS), "icons/icon.ico": set(ICO_FRAME_ORDER),
            "icons/icon.icns": set(ICNS_FRAME_SIZES)}


def audit_evidence(plan: RenderPlan) -> tuple[dict[int, AuditFrame], AuditFrame | None]:
    """The plan's audit frames and maskable file, after proving the plan complete.

    Refuses (``PlanError``) a plan missing a file its targets must ship, or a
    favicon without its 16, 32 and 48 px slots, before any frame is used.
    """
    targets = (plan.parameters or {}).get("targets")
    if (not isinstance(targets, (list, tuple)) or not targets
            or any(not isinstance(target, str) for target in targets)):
        raise PlanError("the plan does not say which targets it was rendered for")
    missing = sorted({path for target in targets
                      for path in REQUIRED_AUDIT_FILES.get(target, ()) if plan.get(path) is None})
    if missing:
        raise PlanError("the plan lacks files its targets must ship: " + ", ".join(missing))
    for path, required in _required_slots().items():
        data = plan.get(path)
        if data is None:
            continue
        try:
            read = assemble.ico_frames if path.endswith(".ico") else assemble.icns_frames
            slots = set(read(data))
        except (ValueError, IndexError, struct.error) as exc:
            raise PlanError(f"{path}: unreadable container ({exc})") from exc
        if slots != required:
            raise PlanError(f"{path} must carry exactly the "
                            + ", ".join(map(str, sorted(required))) + " px frames, not "
                            + ", ".join(map(str, sorted(slots))))
    if "ios" in targets:
        audit_ios(plan)
    return audit_frames(plan), audit_maskable(plan)


def audit_ios(plan: RenderPlan) -> dict[str, AuditFrame]:
    """The plan's iOS appearance files by appearance, after validating the set.

    The catalog, the files and Apple's encodings are checked on the plan's
    bytes (:func:`iconflow.ios.validate_files`), because the plan's content
    identity cannot tell an ``L`` image from an RGB one (C-F10).
    """
    files = {path: plan.get(path) for path in plan.produced
             if path.startswith(ios.IOS_DIR + "/")}
    shipped = ios.APPEARANCES if (ios.DARK in files or ios.TINTED in files) else ("light",)
    try:
        ios.validate_files(files, shipped)
    except ValueError as exc:
        raise PlanError(f"the plan's iOS app icon is not valid: {exc}") from exc
    return {appearance: _audit_frame(ios.APPEARANCE_FILES[appearance], None, ios.SIZE,
                                     files[ios.APPEARANCE_FILES[appearance]])
            for appearance in shipped}


def audit_origins(plan: RenderPlan, *, maskable: bool, linked: bool,
                  ios_target: bool = False) -> dict[str, dict]:
    """Where every plan-aware probe must take its pixels from, for this plan.

    The single definition :func:`iconflow.qa.check` follows and evidence
    validation compares against, so a record cannot omit a probe, claim a
    render where the plan ships the frame, or name a frame the plan does not
    hold (R04).
    """
    frames, shipped_maskable = audit_evidence(plan)

    def master(size: int) -> dict:
        frame = frames.get(size)
        if frame is not None:
            return dict(frame.origin)
        return {"from": "render", "size": size, "reason": "no shipped frame at this size"}

    origins = {"master-16": master(16), "master-32": master(32)}
    if maskable:
        if shipped_maskable is not None:
            origins["maskable-512"] = dict(shipped_maskable.origin)
        else:
            origins["maskable-512"] = {"from": "render", "size": 512,
                                       "reason": "no selected target ships the maskable composition"}
        if linked or shipped_maskable is None:
            origins["master-512"] = master(512)
    if ios_target:
        for appearance, frame in audit_ios(plan).items():
            origins[f"ios-{appearance}"] = dict(frame.origin)
    return origins


# --------------------------------------------------------------- publication

# Portable relative paths only: no drive, no ADS, no control characters, no
# Windows-reserved names, nothing another filesystem would read as another path.
_SEGMENT = re.compile(r"[A-Za-z0-9_@+\-][A-Za-z0-9_@+.\-]*")
_RESERVED = frozenset({"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)),
                       *(f"lpt{i}" for i in range(10))})


def _relative(path: str) -> PurePosixPath:
    """A plan path, refused unless it is a plain, portable relative path."""
    if not isinstance(path, str) or not path or len(path) > 255:
        raise PlanError(f"plan file path must be a plain relative path: {path!r}")
    for part in path.split("/"):
        if (not _SEGMENT.fullmatch(part) or part.endswith(".")
                or part.split(".")[0].lower() in _RESERVED):
            raise PlanError(f"plan file path must be a plain relative path: {path!r}")
    return PurePosixPath(path)


def _preflight(plan: RenderPlan, outdir: Path) -> None:
    """Refuse, before touching anything, a destination a plan file cannot replace.

    A planned *file* must land on a file or on nothing — never on a directory
    (replacing one would delete what is in it) — and every directory above it
    must be a directory or nothing.
    """
    from .build import _is_link_or_reparse_point

    planned = set(plan.produced)
    if planned & set(ios.ALL_FILES):
        stale = [path for path in ios.ALL_FILES
                 if path not in planned and (outdir / _relative(path)).exists()]
        if stale:
            raise ValueError(
                "the output already holds iOS files this build does not write ("
                + ", ".join(stale) + "): an installer copying the folder would ship them "
                "unreviewed. Remove them, or build into a fresh directory")
    for record in plan.files:
        relative = _relative(record.path)
        current = outdir
        for part in relative.parts[:-1]:
            current = current / part
            if _is_link_or_reparse_point(current) or (current.exists() and not current.is_dir()):
                raise ValueError(f"cannot write {record.path}: {current} is not a directory")
        destination = outdir / relative
        if _is_link_or_reparse_point(destination) or (destination.exists() and not destination.is_file()):
            raise ValueError(f"cannot write {record.path}: {destination} exists and is not a file")


def write_plan(plan: RenderPlan, outdir: str | Path) -> list[str]:
    """Write a complete plan into ``outdir``; returns :attr:`RenderPlan.produced`.

    Guarantees, and their limits (``docs/RENDER_PLAN.md``):

    * every destination is checked first; a planned file never replaces a
      directory, a link, or a file standing where a directory must be;
    * nothing in ``outdir`` changes until every file is staged, so a failure
      before the commit leaves it exactly as it was, and an output directory
      that did not exist is removed again;
    * files are then moved into place one at a time; if a move fails, the
      files already replaced are restored. If a restore itself fails, the
      backups are *kept* and the error names where they are;
    * this is not crash-atomic: a power loss mid-commit can leave a mixture,
      and an interrupted run can leave a ``.iconflow-staging-*`` directory;
    * files ``outdir`` already holds that the plan does not name are left
      alone, exactly as every earlier release did.
    """
    from .build import _validate_output_tree

    outdir = Path(outdir)
    _validate_output_tree(outdir)
    _preflight(plan, outdir)
    created: list[Path] = []
    probe = outdir
    while not probe.exists():
        created.append(probe)
        probe = probe.parent
    staging: Path | None = None
    keep_staging = False
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".iconflow-staging-", dir=outdir))
        backups = staging / "backup"
        staged = staging / "new"
        for record in plan.files:
            target = staged / _relative(record.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(record.data)
        committed: list[tuple[Path, Path | None]] = []
        try:
            for record in plan.files:
                relative = _relative(record.path)
                destination = outdir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                backup = None
                if destination.exists():
                    backup = backups / relative
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(destination, backup)
                committed.append((destination, backup))
                os.replace(staged / relative, destination)
        except BaseException as exc:
            unrecovered = []
            for destination, backup in reversed(committed):
                try:
                    if backup is not None:
                        os.replace(backup, destination)
                    elif destination.exists():
                        destination.unlink()
                except OSError:
                    unrecovered.append(str(backup or destination))
            if unrecovered:
                keep_staging = True
                raise OSError(
                    f"writing the icon set failed ({exc}) and {len(unrecovered)} file(s) could "
                    f"not be restored; the originals are kept in {backups}: "
                    + ", ".join(unrecovered[:5])
                ) from exc
            raise
    except BaseException:
        if staging is not None and not keep_staging:
            shutil.rmtree(staging, ignore_errors=True)
            staging = None
        if not keep_staging:
            for directory in created:  # innermost first; only those this run made
                if not directory.exists():
                    continue
                try:
                    directory.rmdir()
                except OSError:
                    break
        raise
    if staging is not None:
        shutil.rmtree(staging, ignore_errors=True)
    return plan.produced


def _is_export(directory: Path) -> bool:
    """Whether ``directory`` is exactly a previous, intact plan export.

    Ownership is proven the way an import proves a plan: every entry is one
    the manifest names, with the bytes it records. Anything else — a note
    beside the files, a stray file inside ``files/`` — and it is not ours.
    """
    try:
        load_plan(directory)
    except PlanError:
        return False
    return True


def export_plan(plan: RenderPlan, directory: str | Path) -> Path:
    """Save a plan for ``ship --plan``: ``plan.json`` plus every file under ``files/``.

    The new export is written beside the destination and swapped in only once
    complete, so a failure keeps the previous export. A destination that holds
    anything other than a previous export is refused, never cleared.
    """
    from .build import _is_link_or_reparse_point, _validate_output_tree, link_in_path

    directory = Path(directory)
    link = link_in_path(directory)
    if link is not None:
        raise PlanError(f"the plan directory goes through a link or junction: {link}")
    _validate_output_tree(directory)
    if directory.exists() and any(directory.iterdir()) and not _is_export(directory):
        raise PlanError(f"{directory} holds files that are not a saved plan; choose an empty directory")
    directory.parent.mkdir(parents=True, exist_ok=True)
    fresh = Path(tempfile.mkdtemp(prefix=".iconflow-plan-", dir=directory.parent))
    try:
        for record in plan.files:
            target = fresh / FILES_DIR / _relative(record.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(record.data)
        (fresh / MANIFEST_NAME).write_text(
            json.dumps(plan.manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        retired = None
        if directory.exists():
            retired = directory.with_name(f".{directory.name}.retired-{os.getpid()}")
            if _is_link_or_reparse_point(directory):
                raise PlanError(f"{directory} became a link")
            os.replace(directory, retired)
        try:
            os.replace(fresh, directory)
        except OSError:
            if retired is not None:
                os.replace(retired, directory)
            raise
        if retired is not None:
            shutil.rmtree(retired, ignore_errors=True)
    finally:
        if fresh.exists():
            shutil.rmtree(fresh, ignore_errors=True)
    return directory / MANIFEST_NAME


_MANIFEST_KEYS = frozenset({"schema", "digest", "artifact_digest", "provenance_digest",
                            "inputs", "parameters", "toolchain", "files"})
MAX_MANIFEST_DEPTH = 16


def _depth(value) -> int:
    """How deeply a decoded JSON value nests, without recursion."""
    deepest, pending = 0, [(value, 1)]
    while pending:
        item, level = pending.pop()
        deepest = max(deepest, level)
        if level > MAX_MANIFEST_DEPTH:
            break
        if isinstance(item, dict):
            pending.extend((child, level + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, level + 1) for child in item)
    return deepest


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise PlanError("plan.json repeats a key")
    return dict(pairs)


def _is_hex64(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def load_plan(directory: str | Path) -> RenderPlan:
    """Import a saved plan as a hostile artifact.

    The directory holds exactly ``plan.json`` and ``files/``; nothing in it is
    a link; ``files/`` holds exactly the files the manifest names, within
    bounds checked while walking. Every identity is recomputed from the bytes
    actually read — the manifest's own hashes are only compared against.
    """
    from .build import _is_link_or_reparse_point, link_in_path

    directory = Path(directory)
    link = link_in_path(directory)
    if link is not None or _is_link_or_reparse_point(directory):
        raise PlanError(f"the plan is read through a link or junction ({link or directory})")
    if not directory.is_dir():
        raise PlanError(f"no saved plan at {directory}")
    root_names = set()
    with os.scandir(directory) as listing:
        for entry in listing:  # incremental: a huge directory stops at the third name
            root_names.add(entry.name)
            if len(root_names) > 2:
                break
    if root_names != {MANIFEST_NAME, FILES_DIR}:
        raise PlanError(f"{directory} must hold exactly {MANIFEST_NAME} and {FILES_DIR}/; "
                        f"found: {', '.join(sorted(root_names)) or 'nothing'}")
    manifest_path = directory / MANIFEST_NAME
    payload_root = directory / FILES_DIR
    for entry in (manifest_path, payload_root):
        if _is_link_or_reparse_point(entry):
            raise PlanError(f"the plan contains a link or junction: {entry}")
    if not manifest_path.is_file() or not payload_root.is_dir():
        raise PlanError(f"{directory} has no {MANIFEST_NAME} file and {FILES_DIR}/ directory")
    if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise PlanError(f"{MANIFEST_NAME} is too large")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)
    except PlanError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise PlanError(f"unreadable {MANIFEST_NAME}: {type(exc).__name__}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != PLAN_SCHEMA:
        raise PlanError(f"{MANIFEST_NAME} is not a schema-{PLAN_SCHEMA} plan")
    unknown = sorted(set(manifest) - _MANIFEST_KEYS)
    if unknown:
        raise PlanError(f"{MANIFEST_NAME} has keys a plan does not: {', '.join(unknown[:5])}")
    if _depth(manifest) > MAX_MANIFEST_DEPTH:
        raise PlanError(f"{MANIFEST_NAME} is nested deeper than a plan is")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_PLAN_FILES:
        raise PlanError(f"{MANIFEST_NAME} has no valid file list")
    for key in ("inputs", "parameters", "toolchain"):
        if not isinstance(manifest.get(key), dict):
            raise PlanError(f"{MANIFEST_NAME} has no {key} object")
    inputs = manifest["inputs"]
    if "master" not in inputs:
        raise PlanError(f"{MANIFEST_NAME} names no master source")
    for role, record in inputs.items():
        if (role not in ROLES or not isinstance(record, dict)
                or not isinstance(record.get("path"), str) or not _is_hex64(record.get("sha256"))
                or not _is_hex64(record.get("bytes_sha256"))):
            raise PlanError(f"{MANIFEST_NAME} has a malformed {role!r} source record")

    on_disk: set[str] = set()
    directories: set[str] = set()
    seen = 0
    pending = [(payload_root, 0)]
    while pending:
        current, depth = pending.pop()
        if depth > MAX_PLAN_DEPTH:
            raise PlanError("the plan is nested deeper than any icon set")
        try:
            with os.scandir(current) as listing:
                for entry in listing:  # incremental, so the bound holds while reading
                    seen += 1
                    if seen > 4 * MAX_PLAN_FILES:
                        raise PlanError("the plan holds far more entries than any icon set")
                    path = Path(entry.path)
                    if _is_link_or_reparse_point(path):
                        raise PlanError(f"the plan contains a link or junction: {path}")
                    if entry.is_dir(follow_symlinks=False):
                        directories.add(path.relative_to(payload_root).as_posix())
                        pending.append((path, depth + 1))
                    elif entry.is_file(follow_symlinks=False):
                        on_disk.add(path.relative_to(payload_root).as_posix())
                    else:
                        raise PlanError(f"the plan contains something that is not a file: {path}")
        except OSError as exc:
            raise PlanError(f"the plan cannot be read: {exc}") from exc

    files: dict[str, bytes] = {}
    total = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise PlanError(f"{MANIFEST_NAME} has a malformed file entry")
        path = entry.get("path")
        _relative(path)
        if path in files:
            raise PlanError(f"{MANIFEST_NAME} names {path} twice")
        if not _is_hex64(entry.get("sha256")) or not _is_hex64(entry.get("content_sha256")):
            raise PlanError(f"{MANIFEST_NAME} entry {path} has no valid hashes")
        target = payload_root / _relative(path)
        if path not in on_disk or not target.is_file():
            raise PlanError(f"the plan is missing {path}")
        size = target.stat().st_size
        total += size
        if total > MAX_PLAN_BYTES:
            raise PlanError("the plan is larger than any icon set could be")
        data = target.read_bytes()
        if len(data) != size or entry.get("bytes") != len(data) or _sha256(data) != entry["sha256"]:
            raise PlanError(f"{path} changed after the plan was saved")
        if content_sha256(path, data) != entry["content_sha256"]:
            raise PlanError(f"{path}: its recorded content identity does not match its bytes")
        files[path] = data
    extra = sorted(on_disk - set(files))
    if extra:
        raise PlanError("the plan holds files its manifest does not name: " + ", ".join(extra[:5]))
    # Directories too: only the ones the named files live in. An empty folder
    # someone added is not part of the plan, and export must not delete it.
    owned = {str(PurePosixPath(path).parents[index]) for path in files
             for index in range(len(PurePosixPath(path).parents) - 1)}
    stray = sorted(directories - owned)
    if stray:
        raise PlanError("the plan holds directories its manifest does not need: " + ", ".join(stray[:5]))
    plan = RenderPlan.create(files, inputs=inputs, parameters=manifest["parameters"],
                             toolchain=manifest["toolchain"])
    if (plan.digest != manifest.get("digest") or plan.artifact_digest != manifest.get("artifact_digest")
            or plan.provenance_digest != manifest.get("provenance_digest")):
        raise PlanError(f"{MANIFEST_NAME} digests do not match its files and settings")
    return plan


# ---------------------------------------------------------------- comparison

@dataclass(frozen=True)
class PlanCheck:
    """How a plan compares with the plan a receipt approved."""

    #: True: same content. False: drift. None: nothing to compare against.
    verified: bool | None
    #: True only when every file is byte-identical to the approved one.
    bytes_verified: bool | None
    changed: tuple[str, ...] = ()
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    approved_toolchain: Mapping | None = None

    @property
    def drift(self) -> list[str]:
        return [*self.changed, *self.added, *self.removed]

    def describe(self, plan: RenderPlan) -> dict:
        """The ``outputs.plan`` object of the ``--json`` envelopes."""
        return {
            "digest": plan.digest,
            "artifact_digest": plan.artifact_digest,
            "verified": self.verified,
            "bytes_verified": self.bytes_verified,
            "drift": self.drift,
        }


def validate_binding(value) -> dict:
    """A receipt's ``plan`` object, checked for shape. Raises PlanError."""
    if not isinstance(value, dict):
        raise PlanError("review receipt plan must be an object")
    if value.get("schema") != PLAN_SCHEMA:
        raise PlanError(f"review receipt plan schema must be {PLAN_SCHEMA}")
    for key in ("digest", "artifact_digest", "provenance_digest"):
        if not _is_hex64(value.get(key)):
            raise PlanError(f"review receipt plan.{key} must be a SHA-256 hex digest")
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise PlanError("review receipt plan.files must name every approved output")
    for path, entry in files.items():
        _relative(path)
        if (not isinstance(entry, dict) or not _is_hex64(entry.get("content"))
                or not _is_hex64(entry.get("sha256"))):
            raise PlanError(f"review receipt plan.files[{path!r}] is malformed")
    if _listing_digest("content", {p: e["content"] for p, e in files.items()}) != value["digest"]:
        raise PlanError("review receipt plan.digest does not match its file list")
    if value.get("toolchain") is not None and not isinstance(value.get("toolchain"), dict):
        raise PlanError("review receipt plan.toolchain must be an object")
    return value


def compare(binding: Mapping | None, plan: RenderPlan) -> PlanCheck:
    """Compare a plan with an approved binding (None: legacy, unbound)."""
    if binding is None:
        return PlanCheck(verified=None, bytes_verified=None)
    approved = binding["files"]
    current = {r.path: r for r in plan.files}
    changed = tuple(sorted(p for p in set(approved) & set(current)
                           if approved[p]["content"] != current[p].content_sha256))
    added = tuple(sorted(set(current) - set(approved)))
    removed = tuple(sorted(set(approved) - set(current)))
    verified = not (changed or added or removed) and binding["digest"] == plan.digest
    return PlanCheck(
        verified=verified,
        bytes_verified=verified and binding["artifact_digest"] == plan.artifact_digest,
        changed=changed, added=added, removed=removed,
        approved_toolchain=binding.get("toolchain"),
    )
