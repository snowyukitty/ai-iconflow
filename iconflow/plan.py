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
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping

from PIL import Image

from . import assemble, htmlhead
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
MAX_PIXELS = 8192 * 8192
#: Gate codes (exit 1): rendered pixels differ from the approved ones, or a
#: saved plan cannot be published as the reviewed output.
GATE_PLAN_DRIFT = "plan-drift"
GATE_PLAN_REPLAY = "plan-replay"


class PlanError(ValueError):
    """A plan that cannot honestly stand for reviewed output."""


def toolchain() -> dict[str, str | None]:
    """What rendered the pixels. Provenance only: it explains drift, never excuses it."""
    import importlib.metadata

    from . import __version__

    try:
        iconflow_version = importlib.metadata.version("iconflow")
    except importlib.metadata.PackageNotFoundError:
        iconflow_version = __version__
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


_TEXT_SUFFIXES = frozenset({".svg", ".html", ".webmanifest", ".xml", ".ts", ".json"})


def content_sha256(path: str, data: bytes) -> str:
    """The content identity of one output (see the module docstring)."""
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".png":
        return _pixels_sha256(data)
    if suffix in {".ico", ".icns"}:
        try:
            frames = assemble.ico_frames(data) if suffix == ".ico" else assemble.icns_frames(data)
        except (ValueError, IndexError) as exc:  # struct errors surface as these
            raise PlanError(f"{path}: unreadable container ({exc})") from exc
        if not frames:
            raise PlanError(f"{path}: container has no frames")
        # Slot order is part of the identity: ICO directory order is observable.
        listing = "".join(f"{slot}:{size}:{_pixels_sha256(frames[size])}\n"
                          for slot, size in enumerate(frames))
        return _sha256(f"iconflow-{suffix[1:]}-v1\n{listing}".encode("ascii"))
    if suffix in _TEXT_SUFFIXES:
        return _sha256(data.replace(b"\r\n", b"\n"))
    return _sha256(data)


def _listing_digest(kind: str, entries: Mapping[str, str]) -> str:
    listing = "".join(f"{path}\t{entries[path]}\n" for path in sorted(entries))
    return _sha256(f"iconflow-plan-{kind}-v1\n{listing}".encode("utf-8"))


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

    @property
    def digest(self) -> str:
        return _listing_digest("content", {r.path: r.content_sha256 for r in self.files})

    @property
    def artifact_digest(self) -> str:
        return _listing_digest("bytes", {r.path: f"{len(r.data)}:{r.sha256}" for r in self.files})

    def binding(self) -> dict:
        """What a review receipt records about the pixels it approved."""
        return {
            "schema": PLAN_SCHEMA,
            "digest": self.digest,
            "artifact_digest": self.artifact_digest,
            "files": {r.path: {"content": r.content_sha256, "sha256": r.sha256} for r in self.files},
            "toolchain": _thaw(self.toolchain),
        }

    def manifest(self) -> dict:
        return {
            "schema": PLAN_SCHEMA,
            "digest": self.digest,
            "artifact_digest": self.artifact_digest,
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
                    maskable_scale, maskable_svg) -> dict:
    """The effective output parameters a plan records (and ``ship --plan`` re-derives)."""
    from .build import ADAPTIVE_TARGETS, resolve_maskable_scale

    options = web_options or htmlhead.WebMetaOptions()
    adaptive = bool(ADAPTIVE_TARGETS & set(targets))
    return {
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
                 rasterizer=None) -> RenderPlan:
    """Render every output of a build into memory. No publication writes.

    Takes exactly :func:`iconflow.build.build`'s arguments (less ``outdir``),
    validates them the same way, and returns a plan whose files are the bytes
    ``build`` writes, in its order. Each source is read once; its snapshot is
    rendered, hashed and (for an unannotated favicon) copied, so an edit made
    mid-build cannot mix two versions of a file. Optional sources a selected
    target does not consume are not read.
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
    master_path = Path(master_svg)
    master = snapshot(master_path, "master")
    adaptive = bool(b.ADAPTIVE_TARGETS & set(targets))
    sources: dict[str, Source] = {"master": master}

    def take(path, role) -> Source | None:
        # A link that names the master is still a link (the default maskable
        # scale depends on it), but it is the same snapshot.
        if path is None:
            return None
        path = Path(path)
        if path.resolve() == master_path.resolve():
            source = Source(role=role, path=str(path), raw=master.raw, text=master.text)
        else:
            source = snapshot(path, role)
        sources[role] = source
        return source

    tray = take(tray_svg, "tray") if "tray" in targets or (
        "android" in targets and monochrome_svg is None) else None
    maskable = take(maskable_svg, "maskable") if adaptive else None
    monochrome = take(monochrome_svg, "monochrome") if "android" in targets else None

    def render(r) -> dict[str, bytes]:
        cache = b.RenderCache(master.text, r, optimize=optimize_png)
        caches: dict[str, object] = {}

        def cache_for(source: Source | None):
            if source is None:
                return None
            if source.raw is master.raw:
                return cache
            if source.path not in caches:
                caches[source.path] = b.RenderCache(source.text, r, optimize=optimize_png)
            return caches[source.path]

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
        return files

    if rasterizer is not None:
        files = render(rasterizer)
    else:
        # Through `iconflow.build` so substituting its renderer (as tests and
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
            maskable_svg=maskable_svg,
        ),
        toolchain=toolchain(),
    )


# --------------------------------------------------------------- publication

# Portable relative paths only: no drive, no ADS, no Windows-reserved names,
# nothing a different filesystem would read as another path.
_SEGMENT = re.compile(r"^[A-Za-z0-9_@+\-][A-Za-z0-9_@+.\-]*$")
_RESERVED = frozenset({"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)),
                       *(f"lpt{i}" for i in range(10))})


def _relative(path: str) -> PurePosixPath:
    """A plan path, refused unless it is a plain, portable relative path."""
    if not isinstance(path, str) or not path or len(path) > 255:
        raise PlanError(f"plan file path must be a plain relative path: {path!r}")
    pure = PurePosixPath(path)
    for part in path.split("/"):
        if (not _SEGMENT.match(part) or part.endswith(".")
                or part.split(".")[0].lower() in _RESERVED):
            raise PlanError(f"plan file path must be a plain relative path: {path!r}")
    return pure


def write_plan(plan: RenderPlan, outdir: str | Path) -> list[str]:
    """Write a complete plan into ``outdir``; returns :attr:`RenderPlan.produced`.

    Guarantees, and their limits (``docs/RENDER_PLAN.md``):

    * nothing in ``outdir`` changes until every file is computed and staged,
      so a failed render or a failed staging write leaves it as it was;
    * files are then moved into place one at a time; if a move fails, the
      files already replaced are restored from the staged backups and the
      error is raised;
    * this is not crash-atomic: a power loss mid-commit can leave a mixture,
      and an interrupted run can leave a ``.iconflow-staging-*`` directory;
    * files ``outdir`` already holds that the plan does not name are left
      alone, exactly as every earlier release did.
    """
    from .build import _validate_output_tree

    outdir = Path(outdir)
    _validate_output_tree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".iconflow-staging-", dir=outdir))
    try:
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
        except BaseException:
            for destination, backup in reversed(committed):
                try:
                    if backup is not None and backup.exists():
                        os.replace(backup, destination)
                    elif backup is None and destination.exists():
                        destination.unlink()
                except OSError:
                    pass
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return plan.produced


def export_plan(plan: RenderPlan, directory: str | Path) -> Path:
    """Save a plan for ``ship --plan``: ``plan.json`` plus every file under ``files/``."""
    from .build import _validate_output_tree

    directory = Path(directory)
    _validate_output_tree(directory)
    if directory.exists() and any(directory.iterdir()):
        shutil.rmtree(directory)
    payload = directory / FILES_DIR
    for record in plan.files:
        target = payload / _relative(record.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(record.data)
    manifest = directory / MANIFEST_NAME
    manifest.write_text(json.dumps(plan.manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise PlanError("plan.json repeats a key")
    return dict(pairs)


def _is_hex64(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def load_plan(directory: str | Path) -> RenderPlan:
    """Import a saved plan as a hostile artifact.

    Every identity is recomputed from the bytes actually read; the manifest's
    own hashes are only compared against, never believed. The directory may
    not contain or traverse a link, may hold no file the manifest does not
    name, and is bounded in size.
    """
    from .build import _is_link_or_reparse_point, link_in_path

    directory = Path(directory)
    link = link_in_path(directory)
    if link is not None or _is_link_or_reparse_point(directory):
        raise PlanError(f"the plan is read through a link or junction ({link or directory})")
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file() or _is_link_or_reparse_point(manifest_path):
        raise PlanError(f"no {MANIFEST_NAME} in {directory}")
    if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise PlanError(f"{MANIFEST_NAME} is too large")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeError, ValueError) as exc:
        raise PlanError(f"unreadable {MANIFEST_NAME}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != PLAN_SCHEMA:
        raise PlanError(f"{MANIFEST_NAME} is not a schema-{PLAN_SCHEMA} plan")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_PLAN_FILES:
        raise PlanError(f"{MANIFEST_NAME} has no valid file list")
    for key in ("inputs", "parameters", "toolchain"):
        if not isinstance(manifest.get(key), dict):
            raise PlanError(f"{MANIFEST_NAME} has no {key} object")

    payload_root = directory / FILES_DIR
    if _is_link_or_reparse_point(payload_root) or not payload_root.is_dir():
        raise PlanError(f"{directory} has no {FILES_DIR}/ directory")
    on_disk: set[str] = set()
    for root, dirs, names in os.walk(payload_root, followlinks=False):
        for name in [*dirs, *names]:
            entry = Path(root) / name
            if _is_link_or_reparse_point(entry):
                raise PlanError(f"the plan contains a link or junction: {entry}")
        for name in names:
            on_disk.add((Path(root) / name).relative_to(payload_root).as_posix())

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
    plan = RenderPlan.create(files, inputs=manifest["inputs"], parameters=manifest["parameters"],
                             toolchain=manifest["toolchain"])
    if plan.digest != manifest.get("digest") or plan.artifact_digest != manifest.get("artifact_digest"):
        raise PlanError(f"{MANIFEST_NAME} digests do not match its files")
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
    for key in ("digest", "artifact_digest"):
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
