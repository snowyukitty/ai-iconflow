# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Build the language-prefixed copies of the public IconFlow site.

English under ``website/`` stays the source of truth. This script

* extracts every translatable string from the English pages into
  ``website/i18n/en.json``, keyed by a slug plus a hash of the English text so
  a key survives regeneration of a page but dies the moment the copy changes;
* renders ``website/<prefix>/...`` for every other language from
  ``website/i18n/<code>.json``, **failing closed**: a language with a missing
  key is not written at all and the run exits non-zero with the list;
* keeps the hreflang blocks, the language switchers, ``sitemap.xml`` and the
  ``_headers`` revalidation stanzas in sync with the route table.

Evidence is never translated: SVGs, PNG proofs, receipts, catalog JSON, code
blocks, command lines, file names, and the archive's 137 entry readings stay
exactly as they ship. Only prose, labels, and metadata move.

Run it from the repository root::

    .venv\\Scripts\\python.exe scripts/build_i18n.py             # sync + extract + render
    .venv\\Scripts\\python.exe scripts/build_i18n.py --status
    .venv\\Scripts\\python.exe scripts/build_i18n.py --verify-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "website"
I18N = SITE / "i18n"
ORIGIN = "https://ai-iconflow.com"


@dataclass(frozen=True)
class Language:
    code: str          # BCP-47 with canonical casing, used in lang/hreflang
    prefix: str        # URL prefix, "" for the English source
    endonym: str       # the language's own name
    short: str         # switcher label

    @property
    def directory(self) -> str:
        return self.prefix.strip("/")


LANGUAGES = (
    Language("en", "", "English", "EN"),
    Language("es", "/es", "Español", "ES"),
    Language("ja", "/ja", "日本語", "日本語"),
    Language("zh-Hant", "/zh-hant", "繁體中文", "繁體"),
    Language("zh-Hans", "/zh-hans", "简体中文", "简体"),
)
SOURCE_LANGUAGE = LANGUAGES[0]
TARGETS = LANGUAGES[1:]
BY_CODE = {language.code: language for language in LANGUAGES}


@dataclass(frozen=True)
class Page:
    route: str            # canonical English route
    source: str           # path under website/
    changefreq: str = ""  # empty keeps the page out of the sitemap
    priority: str = ""
    linked: bool = True   # root-relative links to this route get prefixed


PAGES = (
    Page("/", "index.html", "weekly", "1.0"),
    Page("/getting-started/", "getting-started/index.html", "monthly", "0.9"),
    Page("/how-icons-are-made/", "how-icons-are-made/index.html", "monthly", "0.8"),
    Page("/archive/", "archive/index.html", "monthly", "0.9"),
    Page("/404.html", "404.html", linked=False),
)
# English-only routes (Phase B/C). They stay in the sitemap without alternates
# and keep their English URL when a translated page links to them.
ENGLISH_ONLY = (
    ("/reference/icon-sizes/", "monthly", "0.9"),
    ("/gallery/", "weekly", "0.9"),
    ("/gallery/social-signals/", "monthly", "0.8"),
    ("/gallery/emoji-matrix/", "monthly", "0.8"),
    ("/gallery/emoji-matrix/all/", "monthly", "0.8"),
)
INDEXED_PAGES = tuple(page for page in PAGES if page.changefreq)
LINKED_ROUTES = {page.route: page for page in PAGES if page.linked}

# ---------------------------------------------------------------------------
# What counts as translatable

# Generated evidence blocks: the marks, their names, and their readings are the
# artefact itself and stay English until a later phase.
SKIP_CLASSES = frozenset({
    "archive-track",        # homepage marquee tiles (137 aria-labels)
    "archive-hero-visual",  # archive mosaic tiles
    "finalist-strip",       # finalist cards, names and scores
    "archive-card",         # the 137 entry readings
})
SKIP_TAGS = frozenset({"script", "style", "pre", "textarea", "svg", "template"})
INLINE_WRAPPER = frozenset({
    "a", "abbr", "b", "bdi", "bdo", "cite", "data", "del", "dfn", "em", "i",
    "ins", "mark", "q", "s", "small", "span", "strong", "sub", "sup", "time", "u",
})
# Elements kept whole inside one placeholder: their text is a command or an
# identifier, never a sentence.
INLINE_ATOMIC = frozenset({"code", "kbd", "samp", "var"})
INLINE_VOID = frozenset({"br", "wbr", "img"})
# Inside these an <a> belongs to the sentence; anywhere else it becomes its own
# unit so navigation and button labels stay separate strings.
PROSE_TAGS = frozenset({"p", "li", "dd", "blockquote", "figcaption", "summary"})
VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
})

TRANSLATABLE_ATTRS = ("alt", "title", "aria-label", "aria-valuetext", "placeholder")
TRANSLATABLE_META = frozenset({
    "description", "og:title", "og:description", "og:image:alt",
    "twitter:title", "twitter:description", "twitter:image:alt",
})
TRANSLATABLE_JSONLD = ("description", "headline")
# Metadata that names the page itself and has to follow it into each language.
URL_META = frozenset({"og:url", "twitter:url"})
DATA_LABEL = re.compile(r"^data-label-[a-z0-9-]+$")
# Runtime substitutions the page scripts fill in; a translation must keep them.
TOKEN = re.compile(r"\{[a-z]+\}")
# Evidence: names a visitor types, clicks, or checks. If the English says it,
# every translation has to say it too, or the page stops being verifiable.
EVIDENCE = (
    "IconFlow", "Petal Haypile", "Remix Lab", "Review Lab", "Proof Lab",
    "Flow Gate", "PyPI", "GitHub", "Chromium", "Playwright", "Pillow",
    "Python", "SVG", "PNG", "PWA", "CLI", "JSON", "SHA-256", "Apache-2.0",
    "favicon", "Tauri", "Electron", "macOS", "Emoji Matrix", "Social Signals",
    "iconflow", "master.svg", "tray.svg", "16px", "1024",
)
GLOSSARY_ROW = re.compile(r"^\|(.+)\|$")

MARK_ALTERNATES = ("<!-- i18n:alternates -->", "<!-- /i18n:alternates -->")
MARK_SWITCH = ("<!-- i18n:switch -->", "<!-- /i18n:switch -->")
MARK_HEADERS = ("# i18n:start", "# i18n:end")


def slugify(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    return "-".join(words)[:44].strip("-") or "string"


def key_for(text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{slugify(text)}.{digest}"


def has_letters(text: str) -> bool:
    return any(character.isalpha() for character in text)


def escape_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_attr(value: str) -> str:
    return escape_text(value).replace('"', "&quot;")


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def language_url(language: Language, route: str) -> str:
    return f"{ORIGIN}{language.prefix}/" if route == "/" else f"{ORIGIN}{language.prefix}{route}"


def language_path(language: Language, route: str) -> str:
    return f"{language.prefix}/" if route == "/" else f"{language.prefix}{route}"


# ---------------------------------------------------------------------------
# Placeholder units

PLACEHOLDER = re.compile(r"<(/?)(\d+)(/?)>")


def peel_empty(message: str) -> tuple[list[tuple[int, str]], str, list[tuple[str, int]]]:
    """Split empty placeholder pairs, and the space around them, off both ends."""
    lead: list[tuple[int, str]] = []
    trail: list[tuple[str, int]] = []
    while (match := re.match(r"<(\d+)></\1>( ?)", message)):
        lead.append((int(match.group(1)), match.group(2)))
        message = message[match.end() :]
    while (match := re.search(r"( ?)<(\d+)></\2>$", message)):
        trail.insert(0, (match.group(1), int(match.group(2))))
        message = message[: match.start()]
    return lead, message, trail


class Unit:
    """One translatable run of inline content, with markup as placeholders."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.open: list[str] = []    # opening markup per placeholder
        self.close: list[str] = []   # closing markup, "" for atomic slots

    def add_text(self, text: str) -> None:
        self.parts.append(text)

    def open_slot(self, raw: str) -> int:
        index = len(self.open)
        self.open.append(raw)
        self.close.append("")
        self.parts.append(f"<{index}>")
        return index

    def close_slot(self, index: int, raw: str) -> None:
        self.close[index] = raw
        self.parts.append(f"</{index}>")

    def atomic_slot(self, raw: str) -> int:
        index = len(self.open)
        self.open.append(raw)
        self.close.append("")
        self.parts.append(f"<{index}/>")
        return index

    @property
    def message(self) -> str:
        return normalise("".join(self.parts))

    @property
    def atomic(self) -> set[int]:
        return {index for index, closing in enumerate(self.close) if not closing}

    def render(self, message: str) -> str:
        out: list[str] = []
        cursor = 0
        for match in PLACEHOLDER.finditer(message):
            out.append(escape_text(message[cursor : match.start()]))
            cursor = match.end()
            closing, number, selfclose = match.group(1), int(match.group(2)), match.group(3)
            out.append(self.close[number] if closing and not selfclose else self.open[number])
        out.append(escape_text(message[cursor:]))
        return "".join(out)

    def problem(self, message: str) -> str:
        """Describe how a translated message breaks the placeholder contract."""
        atomic = self.atomic
        seen: list[int] = []
        stack: list[int] = []
        for match in PLACEHOLDER.finditer(message):
            closing, number, selfclose = match.group(1), int(match.group(2)), match.group(3)
            if number >= len(self.open):
                return f"unknown placeholder <{number}>"
            if selfclose:
                if closing or number not in atomic:
                    return f"placeholder <{number}> must not be self-closing"
                if number in seen:
                    return f"placeholder <{number}> used twice"
                seen.append(number)
                continue
            if number in atomic:
                return f"placeholder <{number}> must stay self-closing (<{number}/>)"
            if closing:
                if not stack or stack[-1] != number:
                    return f"placeholder </{number}> does not close the open placeholder"
                stack.pop()
            else:
                if number in seen:
                    return f"placeholder <{number}> used twice"
                seen.append(number)
                stack.append(number)
        if stack:
            return f"placeholder <{stack[-1]}> is never closed"
        if sorted(seen) != list(range(len(self.open))):
            missing = sorted(set(range(len(self.open))) - set(seen))
            return f"placeholder(s) {missing} dropped from the translation"
        return ""


# ---------------------------------------------------------------------------
# The rewriter


@dataclass
class Slot:
    """A translatable string found on a page."""

    key: str
    text: str
    kind: str
    where: str


class Rewriter(HTMLParser):
    """Re-emit an English page, translating text, attributes, and routes."""

    def __init__(self, page: Page, language: Language, strings: dict[str, str] | None) -> None:
        super().__init__(convert_charrefs=False)
        self.page = page
        self.language = language
        self.strings = strings
        self.out: list[str] = []
        self.slots: list[Slot] = []
        self.missing: list[Slot] = []
        self.problems: list[str] = []
        self.stack: list[dict] = []
        self.buffer: Unit | None = None
        self.pending: list[str] = []      # raw text between flushes
        self.atomic: dict | None = None   # element captured whole
        self.jsonld: list[str] | None = None

    # -- helpers ----------------------------------------------------------
    @property
    def where(self) -> str:
        trail = [entry["label"] for entry in self.stack[-3:]]
        return " ".join(trail)

    @property
    def in_skip(self) -> bool:
        return bool(self.stack) and self.stack[-1]["skip"]

    @property
    def in_switch(self) -> bool:
        return bool(self.stack) and self.stack[-1]["switch"]

    @property
    def in_prose(self) -> bool:
        return any(entry["tag"] in PROSE_TAGS for entry in self.stack)

    @property
    def in_slot(self) -> bool:
        """True while an inline placeholder is still open."""
        return any(entry["slot"] is not None for entry in self.stack)

    def translate(self, text: str, kind: str) -> str:
        key = key_for(text)
        slot = Slot(key, text, kind, self.where)
        self.slots.append(slot)
        if self.strings is None:
            return text
        if key not in self.strings:
            self.missing.append(slot)
            return text
        translation = self.strings[key]
        wanted = set(TOKEN.findall(text))
        if wanted != set(TOKEN.findall(translation)):
            self.problems.append(
                f"{self.page.source}: {key} must keep the token(s) {sorted(wanted)}")
            return text
        lost = [name for name in EVIDENCE if name in text and name not in translation]
        if lost:
            self.problems.append(
                f"{self.page.source}: {key} dropped the evidence {lost}")
            return text
        return translation

    def rewrite_url(self, value: str) -> str:
        """Point a root-relative or canonical-origin link at this language."""
        if self.language.prefix == "":
            return value
        target = value
        absolute = target.startswith(ORIGIN)
        if absolute:
            target = target[len(ORIGIN) :] or "/"
        elif not target.startswith("/") or target.startswith("//"):
            return value
        head, sep, tail = target.partition("#")
        path, query_sep, query = head.partition("?")
        if path in LINKED_ROUTES:
            path = language_path(self.language, path)
        else:
            return value
        rebuilt = f"{path}{query_sep}{query}{sep}{tail}"
        return f"{ORIGIN}{rebuilt}" if absolute else rebuilt

    def start_tag(self, tag: str, attrs: list[tuple[str, str | None]], raw: str, *,
                  translated: bool, switch: bool) -> str:
        """Rewrite the attributes of one start tag."""
        values = {name: value for name, value in attrs}
        replacements: dict[str, str] = {}
        remove: list[str] = []
        add: list[str] = []

        for name, value in attrs:
            if value is None:
                continue
            if name in ("href", "src") and not (tag == "link" and values.get("rel") == "alternate"):
                if switch and tag == "a":
                    continue
                fresh = self.rewrite_url(value)
                if fresh != value:
                    replacements[name] = fresh

        if switch and tag == "a" and values.get("hreflang"):
            target = BY_CODE.get(values["hreflang"])
            if target is not None:
                replacements["href"] = language_path(target, self.page.route)
                if target.code == self.language.code:
                    if "aria-current" in values:
                        replacements["aria-current"] = "true"
                    else:
                        add.append('aria-current="true"')
                elif "aria-current" in values:
                    remove.append("aria-current")

        if tag == "html" and "lang" in values:
            replacements["lang"] = self.language.code
        if tag == "meta" and (values.get("property") or values.get("name")) in URL_META:
            content = values.get("content") or ""
            fresh = self.rewrite_url(content)
            if fresh != content:
                replacements["content"] = fresh

        if translated:
            for name, value in attrs:
                if value is None or not value.strip() or not has_letters(value):
                    continue
                if name in TRANSLATABLE_ATTRS or DATA_LABEL.match(name):
                    replacements[name] = self.translate(normalise(value), f"attr:{name}")
            if tag == "meta":
                marker = values.get("name") or values.get("property") or ""
                content = values.get("content")
                if marker in TRANSLATABLE_META and content and has_letters(content):
                    replacements["content"] = self.translate(normalise(content), f"meta:{marker}")

        return edit_tag(raw, replacements, remove, add)

    # -- inline buffering -------------------------------------------------
    def start_unit(self) -> Unit:
        """Open an inline run, keeping any buffered text that carries content."""
        pending = "".join(self.pending)
        self.pending = []
        unit = Unit()
        if pending.strip():
            unit.add_text(pending)
        else:
            self.out.append(escape_text(pending))
        self.buffer = unit
        return unit

    def flush(self) -> None:
        """Emit the buffered inline run, translating it when it carries prose."""
        unit = self.buffer
        self.buffer = None
        if unit is None:
            self.out.append(escape_text("".join(self.pending)))
            self.pending = []
            return
        self.emit_unit(unit)

    def emit_unit(self, unit: Unit) -> None:
        message = unit.message
        if not message:
            return
        # Empty decorative elements at either end (the hamburger bars, for
        # instance) are markup, not copy: keep them out of the string.
        lead, core, trail = peel_empty(message)
        if lead or trail:
            for index, space in lead:
                self.out.append(unit.open[index] + unit.close[index] + space)
            if core.strip():
                self.emit_renumbered(core, unit)
            for space, index in trail:
                self.out.append(space + unit.open[index] + unit.close[index])
            return
        # A run that is nothing but one wrapper keeps its markup outside the
        # string: "<0>Get started</0>" is noise for a translator.
        match = re.fullmatch(r"<(\d+)>(.*)</\1>", message, re.S)
        if match and unit.close[int(match.group(1))]:
            index = int(match.group(1))
            self.out.append(unit.open[index])
            self.emit_renumbered(match.group(2), unit)
            self.out.append(unit.close[index])
            return
        if not has_letters(re.sub(PLACEHOLDER, "", message)):
            self.out.append(unit.render(message))
            return
        translated = self.translate(message, "text")
        problem = unit.problem(translated)
        if problem:
            self.problems.append(f"{self.page.source}: {problem} in {message[:60]!r}")
            translated = message
        self.out.append(unit.render(translated))

    def emit_renumbered(self, message: str, unit: Unit) -> None:
        """Emit the inside of an unwrapped single-wrapper run."""
        inner = Unit()
        mapping: dict[int, int] = {}
        parts: list[str] = []
        cursor = 0
        for match in PLACEHOLDER.finditer(message):
            parts.append(message[cursor : match.start()])
            cursor = match.end()
            closing, number, selfclose = match.group(1), int(match.group(2)), match.group(3)
            if number not in mapping:
                mapping[number] = len(inner.open)
                inner.open.append(unit.open[number])
                inner.close.append(unit.close[number])
            new = mapping[number]
            parts.append(f"</{new}>" if closing and not selfclose else (f"<{new}/>" if selfclose else f"<{new}>"))
        parts.append(message[cursor:])
        inner.parts = parts
        self.emit_unit(inner)

    # -- HTMLParser hooks -------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raw = self.get_starttag_text() or ""
        if self.atomic is not None:
            if tag == self.atomic["tag"] and tag not in VOID_TAGS:
                self.atomic["depth"] += 1
            self.atomic["raw"].append(raw)
            return
        values = {name: value for name, value in attrs}
        classes = set((values.get("class") or "").split())
        skip_here = (
            self.in_skip
            or tag in SKIP_TAGS
            or values.get("translate") == "no"
            or values.get("data-i18n") == "skip"
            or bool(classes & SKIP_CLASSES)
        )
        switch_here = self.in_switch or "data-lang-switch" in values
        void = tag in VOID_TAGS

        if tag in INLINE_ATOMIC and not skip_here and self.buffer is not None:
            self.atomic = {"tag": tag, "depth": 1, "raw": [raw]}
            return

        inline = not skip_here and (
            tag in INLINE_VOID
            or (tag in INLINE_WRAPPER and (tag != "a" or self.in_prose or self.in_slot))
        )
        # A void element with no run open has nothing to attach to; treat it as
        # ordinary markup so the whitespace around it keeps its place.
        inline = inline and not (void and self.buffer is None)
        if not inline:
            self.flush()
        rewritten = self.start_tag(tag, attrs, raw, translated=not skip_here, switch=switch_here)

        slot: int | None = None
        if inline:
            unit = self.buffer if self.buffer is not None else self.start_unit()
            if void:
                unit.atomic_slot(rewritten)
                return
            slot = unit.open_slot(rewritten)
        else:
            self.out.append(rewritten)
            if void:
                return
        if tag == "script" and (values.get("type") or "").strip() == "application/ld+json":
            self.jsonld = []
        self.stack.append(self.entry(tag, values, skip_here, switch_here, slot))

    def entry(self, tag: str, values: dict, skip: bool, switch: bool, slot: int | None) -> dict:
        label = tag
        if values.get("id"):
            label += f"#{values['id']}"
        elif values.get("class"):
            label += "." + (values["class"].split() or [""])[0]
        return {"tag": tag, "label": label, "skip": skip, "slot": slot, "switch": switch}

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS and self.atomic is None:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        raw = f"</{tag}>"
        if self.atomic is not None:
            if tag == self.atomic["tag"]:
                self.atomic["depth"] -= 1
                if self.atomic["depth"] == 0:
                    captured = "".join(self.atomic["raw"]) + raw
                    self.atomic = None
                    assert self.buffer is not None
                    self.buffer.atomic_slot(captured)
                    return
            self.atomic["raw"].append(raw)
            return
        if self.jsonld is not None and tag == "script":
            self.out.append(self.render_jsonld("".join(self.jsonld)))
            self.jsonld = None
        index = self.find(tag)
        if index is None:
            self.flush()
            self.out.append(raw)
            return
        entry = self.stack[index]
        del self.stack[index:]
        if entry["slot"] is not None and self.buffer is not None:
            self.buffer.close_slot(entry["slot"], raw)
            return
        self.flush()
        self.out.append(raw)

    def find(self, tag: str) -> int | None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                return index
        return None

    def handle_data(self, data: str) -> None:
        if self.atomic is not None:
            self.atomic["raw"].append(data)
            return
        if self.jsonld is not None:
            self.jsonld.append(data)
            return
        if self.in_skip:
            self.flush()
            # script/style are CDATA and reach us verbatim; everywhere else the
            # parser has already decoded the entities.
            self.out.append(data if self.stack[-1]["tag"] in ("script", "style") else escape_text(data))
            return
        if self.buffer is None and not has_letters(data):
            self.pending.append(data)
            return
        unit = self.buffer if self.buffer is not None else self.start_unit()
        unit.add_text(data)

    def handle_entityref(self, name: str) -> None:
        self.handle_data({"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'",
                          "nbsp": " "}.get(name, f"&{name};"))

    def handle_charref(self, name: str) -> None:
        try:
            character = chr(int(name[1:], 16) if name[:1].lower() == "x" else int(name))
        except ValueError:
            self.handle_data(f"&#{name};")
            return
        self.handle_data(character)

    def handle_comment(self, data: str) -> None:
        if self.atomic is not None:
            self.atomic["raw"].append(f"<!--{data}-->")
            return
        self.flush()
        self.out.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self.flush()
        self.out.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self.flush()
        self.out.append(f"<?{data}>")

    def unknown_decl(self, data: str) -> None:
        self.flush()
        self.out.append(f"<![{data}]>")

    # -- structured data --------------------------------------------------
    def render_jsonld(self, raw: str) -> str:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.problems.append(f"{self.page.source}: structured data is not valid JSON")
            return raw
        first = next((line for line in raw.splitlines() if line.strip()), "")
        indent = len(first) - len(first.lstrip(" "))

        def walk(node):
            if isinstance(node, dict):
                return {
                    key: (self.translate(normalise(value), f"ld:{key}")
                          if key in TRANSLATABLE_JSONLD and isinstance(value, str) and has_letters(value)
                          else (self.rewrite_url(value) if key in ("url", "@id") and isinstance(value, str)
                                else walk(value)))
                    for key, value in node.items()
                }
            if isinstance(node, list):
                return [walk(item) for item in node]
            return node

        pad = " " * indent
        body = "\n".join(pad + line if line else line
                         for line in json.dumps(walk(data), ensure_ascii=False, indent=2).splitlines())
        return f"\n{body}\n{' ' * max(indent - 2, 0)}"

    def result(self) -> str:
        self.flush()
        return "".join(self.out)


TAG_ATTR = r'(?<![-\w]){name}\s*=\s*("([^"]*)"|\'([^\']*)\')'


def edit_tag(raw: str, replacements: dict[str, str], remove: list[str], add: list[str]) -> str:
    """Rewrite attribute values inside one raw start tag, preserving the rest."""
    for name, value in replacements.items():
        pattern = re.compile(TAG_ATTR.format(name=re.escape(name)), re.I | re.S)
        match = pattern.search(raw)
        if match:
            quote = '"'
            raw = raw[: match.start()] + f'{name}={quote}{escape_attr(value)}{quote}' + raw[match.end() :]
        else:
            raw = raw[:-1].rstrip() + f' {name}="{escape_attr(value)}">' if raw.endswith(">") else raw
    for name in remove:
        pattern = re.compile(r"\s*" + TAG_ATTR.format(name=re.escape(name)), re.I | re.S)
        raw = pattern.sub("", raw)
    if add:
        closing = "/>" if raw.endswith("/>") else ">"
        raw = raw[: -len(closing)].rstrip() + " " + " ".join(add) + closing
    return raw


# ---------------------------------------------------------------------------
# Generated blocks in the English source


def alternates_block(route: str, indent: str = "  ") -> str:
    lines = [f'{indent}<link rel="alternate" hreflang="{language.code}" href="{language_url(language, route)}">'
             for language in LANGUAGES]
    lines.append(f'{indent}<link rel="alternate" hreflang="x-default" href="{language_url(SOURCE_LANGUAGE, route)}">')
    return "\n".join(lines)


def switch_block(route: str, current: Language = SOURCE_LANGUAGE) -> str:
    links = []
    for language in LANGUAGES:
        current_mark = ' aria-current="true"' if language.code == current.code else ""
        links.append(
            f'<a lang="{language.code}" hreflang="{language.code}" translate="no" '
            f'href="{language_path(language, route)}"{current_mark}>{language.short}</a>'
        )
    return '<nav class="lang-switch" data-lang-switch aria-label="Language">' + "".join(links) + "</nav>"


def replace_between(text: str, markers: tuple[str, str], body: str) -> str:
    """Replace every marked block, keeping the markers themselves."""
    start, end = markers
    if start not in text or end not in text:
        raise SystemExit(f"marker {start} missing from a page; add it by hand once")
    pattern = re.compile(re.escape(start) + ".*?" + re.escape(end), re.S)
    return pattern.sub(lambda _: start + body + end, text)


def sync_source() -> list[str]:
    """Refresh the generated blocks inside the English pages."""
    changed = []
    for page in PAGES:
        path = SITE / page.source
        original = path.read_text(encoding="utf-8")
        text = original
        if page.changefreq:
            text = replace_between(text, MARK_ALTERNATES, "\n" + alternates_block(page.route) + "\n  ")
        text = replace_between(text, MARK_SWITCH, switch_block(page.route))
        if text != original:
            path.write_text(text, encoding="utf-8", newline="\n")
            changed.append(page.source)
    return changed


def sitemap_text() -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
             ' xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for page in INDEXED_PAGES:
        for language in LANGUAGES:
            lines.append("  <url>")
            lines.append(f"    <loc>{language_url(language, page.route)}</loc>")
            for alternate in LANGUAGES:
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{alternate.code}"'
                             f' href="{language_url(alternate, page.route)}"/>')
            lines.append('    <xhtml:link rel="alternate" hreflang="x-default"'
                         f' href="{language_url(SOURCE_LANGUAGE, page.route)}"/>')
            lines.append(f"    <changefreq>{page.changefreq}</changefreq>")
            lines.append(f"    <priority>{page.priority}</priority>")
            lines.append("  </url>")
    for route, changefreq, priority in ENGLISH_ONLY:
        lines.append("  <url>")
        lines.append(f"    <loc>{ORIGIN}{route}</loc>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def headers_block() -> str:
    lines = []
    for language in TARGETS:
        for page in PAGES:
            path = language_path(language, page.route)
            lines.append(path)
            lines.append("  Cache-Control: public, max-age=0, must-revalidate")
            lines.append("")
            if page.route.endswith("/"):
                lines.append(f"{path}index.html")
                lines.append("  Cache-Control: public, max-age=0, must-revalidate")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def sync_contract() -> list[str]:
    changed = []
    sitemap = SITE / "sitemap.xml"
    text = sitemap_text()
    if not sitemap.is_file() or sitemap.read_text(encoding="utf-8") != text:
        sitemap.write_text(text, encoding="utf-8", newline="\n")
        changed.append("sitemap.xml")
    headers = SITE / "_headers"
    original = headers.read_text(encoding="utf-8")
    start, end = MARK_HEADERS
    if start not in original:
        original = original.rstrip("\n") + f"\n\n{start}\n{end}\n"
    head, _, rest = original.partition(start)
    _, _, tail = rest.partition(end)
    text = f"{head}{start}\n{headers_block()}{end}{tail if tail.strip() else chr(10)}"
    if text != headers.read_text(encoding="utf-8"):
        headers.write_text(text, encoding="utf-8", newline="\n")
        changed.append("_headers")
    return changed


# ---------------------------------------------------------------------------
# Catalogs


def load_glossary() -> dict[str, dict[str, str]]:
    """Read the agreed-terminology tables out of GLOSSARY.md.

    The document stays the single source of truth; this only lets ``--status``
    report how often a required rendering actually reaches the catalog. It is
    a report, never a gate: a good translation can legitimately paraphrase a
    term away, and a build that refused those would push translators toward
    word-for-word rendering, which is the opposite of what the site needs.
    """
    path = I18N / "GLOSSARY.md"
    if not path.is_file():
        return {}
    codes = [language.code for language in TARGETS]
    table: dict[str, dict[str, str]] = {code: {} for code in codes}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = GLOSSARY_ROW.match(line.strip())
        if not match:
            continue
        cells = [cell.strip().strip("`") for cell in match.group(1).split("|")]
        if len(cells) != len(codes) + 1 or set(cells[0]) <= set("- "):
            continue
        # "ship (as prose, not the command)" keys on "ship"
        note = cells[0].lower()
        term = re.sub(r"\s*\(.*\)", "", cells[0]).strip().lower()
        # A row that says "not the command" names something that also appears
        # verbatim as a command; the report cannot tell the two uses apart.
        if not term or term == "english" or "not the command" in note:
            continue
        for code, expected in zip(codes, cells[1:]):
            if expected and expected.lower() != term:
                table[code][term] = expected
    return table


def glossary_report(source: dict[str, Slot], strings: dict[str, str], terms: dict[str, str]):
    """How often a required rendering reaches the catalog, and what misses."""
    hit = total = 0
    misses: dict[str, int] = {}
    for key, slot in source.items():
        value = strings.get(key)
        if value is None:
            continue
        # File names and command phrases carry the word without using it as a
        # word: "master.svg" is not a use of "master", and "iconflow review"
        # is the command, not the noun.
        english = re.sub(r"[a-z_]+\.[a-z]{2,4}\b|iconflow +[a-z]+", " ", slot.text.lower())
        for term, expected in terms.items():
            if not re.search(rf"\b{re.escape(term)}s?\b", english):
                continue
            total += 1
            # Latin renderings get capitalised at the start of a label.
            if expected.lower() in value.lower():
                hit += 1
            else:
                misses[term] = misses.get(term, 0) + 1
    return hit, total, misses


def load_catalog(code: str) -> dict[str, str]:
    path = I18N / f"{code}.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    strings = data.get("strings", {})
    return {key: value for key, value in strings.items() if isinstance(value, str)}


def extract(write: bool = True) -> dict[str, Slot]:
    found: dict[str, Slot] = {}
    pages: dict[str, list[str]] = {}
    for page in PAGES:
        parser = Rewriter(page, SOURCE_LANGUAGE, None)
        parser.feed((SITE / page.source).read_text(encoding="utf-8"))
        parser.close()
        parser.result()
        for problem in parser.problems:
            print(f"i18n extract: {problem}", file=sys.stderr)
        for slot in parser.slots:
            found.setdefault(slot.key, slot)
            pages.setdefault(slot.key, [])
            if page.source not in pages[slot.key]:
                pages[slot.key].append(page.source)
    payload = {
        "language": "en",
        "generated_by": "scripts/build_i18n.py",
        "note": "English source strings. Keys are slug.hash(text); a copy edit "
                "makes a new key, which makes every translation fail closed.",
        "count": len(found),
        "strings": {
            key: {"text": slot.text, "kind": slot.kind, "where": slot.where, "pages": pages[key]}
            for key, slot in found.items()
        },
    }
    if write:
        (I18N / "en.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    return found


def render(language: Language, strings: dict[str, str]) -> tuple[dict[str, str], list[Slot], list[str]]:
    outputs: dict[str, str] = {}
    missing: list[Slot] = []
    problems: list[str] = []
    for page in PAGES:
        parser = Rewriter(page, language, strings)
        parser.feed((SITE / page.source).read_text(encoding="utf-8"))
        parser.close()
        outputs[f"{language.directory}/{page.source}"] = parser.result()
        missing.extend(parser.missing)
        problems.extend(parser.problems)
    return outputs, missing, problems


def build(only: set[str] | None, *, write: bool = True) -> int:
    source = extract()
    failures = 0
    for language in TARGETS:
        if only and language.code not in only:
            continue
        strings = load_catalog(language.code)
        outputs, missing, problems = render(language, strings)
        unknown = sorted(set(strings) - set(source))
        if missing or problems:
            failures += 1
            keys = sorted({slot.key for slot in missing})
            print(f"i18n {language.code}: FAILED CLOSED — {len(keys)} untranslated key(s),"
                  f" {len(problems)} markup problem(s); nothing written", file=sys.stderr)
            for slot in {slot.key: slot for slot in missing}.values():
                print(f"  missing {slot.key}: {slot.text[:80]!r}", file=sys.stderr)
            for problem in problems[:20]:
                print(f"  {problem}", file=sys.stderr)
            continue
        if unknown:
            print(f"i18n {language.code}: {len(unknown)} obsolete key(s) in the catalog", file=sys.stderr)
            for key in unknown[:20]:
                print(f"  obsolete {key}", file=sys.stderr)
        if write:
            target = SITE / language.directory
            if target.is_dir():
                shutil.rmtree(target)
            for name, text in outputs.items():
                path = SITE / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8", newline="\n")
        print(f"i18n {language.code}: {len(outputs)} page(s) -> website/{language.directory}/")
    return failures


def check_catalog(path: Path) -> int:
    """Validate one catalog draft without writing anything."""
    data = json.loads(path.read_text(encoding="utf-8"))
    code = data.get("language", path.stem)
    language = BY_CODE.get(code)
    if language is None or language.code == SOURCE_LANGUAGE.code:
        print(f"i18n check: unknown language {code!r}; expected one of "
              f"{', '.join(item.code for item in TARGETS)}", file=sys.stderr)
        return 1
    strings = {key: value for key, value in data.get("strings", {}).items() if isinstance(value, str)}
    source = extract(write=False)
    problems: list[str] = []
    for key in sorted(set(source) - set(strings)):
        problems.append(f"missing {key}: {source[key].text[:70]!r}")
    for key in sorted(set(strings) - set(source)):
        problems.append(f"obsolete {key}: not a string on the site any more")
    for key, value in strings.items():
        if key in source and not value.strip():
            problems.append(f"empty {key}")
    _, _, markup = render(language, strings)
    problems.extend(markup)
    for problem in problems[:60]:
        print("i18n check:", problem, file=sys.stderr)
    if problems:
        print(f"i18n check: {code} has {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print(f"i18n check: {code} OK - {len(strings)} strings, placeholders and tokens intact")
    return 0


def status() -> int:
    source = extract(write=False)
    glossary = load_glossary()
    print(f"i18n: {len(source)} translatable string(s) on {len(PAGES)} page(s)")
    for language in TARGETS:
        strings = load_catalog(language.code)
        done = len(set(strings) & set(source))
        obsolete = len(set(strings) - set(source))
        hit, total, misses = glossary_report(source, strings, glossary.get(language.code, {}))
        worst = ", ".join(f"{term} x{count}" for term, count
                          in sorted(misses.items(), key=lambda item: -item[1])[:4])
        coverage = f"{hit / total:4.0%}" if total else "   —"
        print(f"  {language.code:8s} {done:4d}/{len(source)} translated"
              f"{f', {obsolete} obsolete' if obsolete else ''}"
              f"  · glossary {coverage}{f'  (missed: {worst})' if worst else ''}")
    return 0


def verify() -> int:
    """Check the tracked output against the sources without writing anything."""
    problems: list[str] = []
    source = extract(write=False)
    for page in PAGES:
        text = (SITE / page.source).read_text(encoding="utf-8")
        if page.changefreq and alternates_block(page.route) not in text:
            problems.append(f"{page.source} has a stale hreflang block")
        if switch_block(page.route) not in text:
            problems.append(f"{page.source} has a stale language switcher")
    if (I18N / "en.json").is_file():
        tracked = json.loads((I18N / "en.json").read_text(encoding="utf-8"))
        if sorted(tracked.get("strings", {})) != sorted(source):
            problems.append("website/i18n/en.json is stale; run scripts/build_i18n.py")
    else:
        problems.append("website/i18n/en.json is missing; run scripts/build_i18n.py")
    for language in TARGETS:
        strings = load_catalog(language.code)
        outputs, missing, markup = render(language, strings)
        for slot in {slot.key: slot for slot in missing}.values():
            problems.append(f"{language.code}: untranslated {slot.key} ({slot.text[:50]!r})")
        problems.extend(f"{language.code}: {item}" for item in markup)
        for name, text in outputs.items():
            path = SITE / name
            if not path.is_file():
                problems.append(f"{name} is missing; run scripts/build_i18n.py")
            elif path.read_text(encoding="utf-8") != text:
                problems.append(f"{name} is stale; run scripts/build_i18n.py")
    if (SITE / "sitemap.xml").read_text(encoding="utf-8") != sitemap_text():
        problems.append("sitemap.xml is stale; run scripts/build_i18n.py")
    headers = (SITE / "_headers").read_text(encoding="utf-8")
    if headers_block() not in headers:
        problems.append("_headers is stale; run scripts/build_i18n.py")
    for problem in problems[:40]:
        print("i18n verify:", problem, file=sys.stderr)
    if problems:
        print(f"i18n verify: {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print(f"i18n verify: OK — {len(source)} strings, {len(TARGETS)} languages, {len(PAGES)} pages each")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--verify-only", action="store_true", help="check the tracked output without writing")
    parser.add_argument("--status", action="store_true", help="print catalog coverage")
    parser.add_argument("--extract-only", action="store_true", help="refresh website/i18n/en.json only")
    parser.add_argument("--only", default="", help="comma-separated language codes to render")
    parser.add_argument("--check-catalog", default="", metavar="PATH",
                        help="validate one <lang>.json draft without writing anything")
    args = parser.parse_args()

    if args.check_catalog:
        return check_catalog(Path(args.check_catalog))
    if args.verify_only:
        return verify()
    if args.status:
        return status()
    changed = sync_source() + sync_contract()
    if changed:
        print("i18n: refreshed " + ", ".join(changed))
    if args.extract_only:
        source = extract()
        print(f"i18n: {len(source)} string(s) -> website/i18n/en.json")
        return 0
    only = {code.strip() for code in args.only.split(",") if code.strip()} or None
    return 1 if build(only) else verify()


if __name__ == "__main__":
    raise SystemExit(main())
