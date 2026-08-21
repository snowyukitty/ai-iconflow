# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
"""Build the 20-case Social Signals clean-room design study.

The public catalog contains generic user-job labels only. Direct platform
context and trademark research live in the git-ignored work appendix.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from iconflow.casebook import AXES, new_case
from iconflow.config import (
    load_config,
    load_review_receipt,
    review_build_contract,
    review_contract_digest,
    svg_sha256,
)
from iconflow.qa import check
from iconflow.rasterize import Rasterizer, load_svg
from iconflow.review import compare_sheet, contact_sheet, visual_silhouette


ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / "work" / "social-signals"
SOURCE_ROOT = ROOT / "gallery" / "social-signals" / "cases"
CATALOG_PATH = ROOT / "gallery" / "social-signals" / "catalog.json"
DEPLOY_ROOT = ROOT / "website" / "assets" / "gallery" / "social-signals"
DECISIONS_PATH = ROOT / "gallery" / "social-signals" / "review-decisions.json"
CASEBOOK = ROOT / "casebook"
DATE = "2026-08-12"
SEED = "iconflow-social-signals-2026-08-12-v1"
STYLES = [
    "flat-geometric", "gradient-glow", "line-mark", "mascot", "duotone",
    "stencil-cut", "pixel-grid", "isometric", "cut-paper", "enamel",
    "blueprint", "stained-glass", "risograph", "clay", "woven",
    "glass-stack", "cel-shaded", "ink-brush", "chrome", "woodcut",
]


ITEMS = [
    {
        "id": "friends-and-groups", "title": "Gathering Table",
        "job": "Keep up with friends and gather around shared groups.",
        "essence": "belonging", "noun": "community table", "style": "cel-shaded",
        "cliche": "letter tiles, people-dot clusters, familiar social-network blue",
        "signature": "a single open place interrupts the inked round table",
        "concepts": ["Object: community table", "Verb: pull up a seat", "Negative space: open place", "Material: hard shadow plane"],
    },
    {
        "id": "creator-video-library", "title": "Projection Keeper",
        "job": "Watch, publish, and revisit creator-led video libraries.",
        "essence": "broadcast", "noun": "projection lantern", "style": "mascot",
        "cliche": "play triangles, red media buttons, wordmark fragments",
        "signature": "one asymmetric reel-cheek becomes the keeper's expression",
        "concepts": ["Character: projection keeper", "Object: lantern projector", "Verb: cast a beam", "Silhouette: reel cheek"],
    },
    {
        "id": "visual-journal", "title": "Memory Folio",
        "job": "Share a visual journal of moments, places, and making.",
        "essence": "curation", "noun": "contact-sheet folio", "style": "isometric",
        "cliche": "camera outlines, aperture rings, purple-orange gradients",
        "signature": "one folded corner becomes a deep isometric page well",
        "concepts": ["Object: contact folio", "Place: archive shelf", "Verb: unfold a memory", "Negative space: page well"],
    },
    {
        "id": "private-messaging", "title": "Sealed Relay",
        "job": "Exchange private messages and calls with trusted contacts.",
        "essence": "trust", "noun": "sealed message capsule", "style": "stained-glass",
        "cliche": "speech bubbles, telephone handsets, signature green",
        "signature": "a diagonal lead seam locks into a central wax-like seal",
        "concepts": ["Object: sealed capsule", "Verb: hand over privately", "Negative space: locked seam", "Material: leaded panes"],
    },
    {
        "id": "short-video-discovery", "title": "Pocket Flipbook",
        "job": "Discover and make compact, fast-moving video stories.",
        "essence": "momentum", "noun": "flipbook", "style": "line-mark",
        "cliche": "music notes, play buttons, cyan-magenta edge effects",
        "signature": "one page escapes the uniform contour as a turning beat",
        "concepts": ["Object: flipbook", "Verb: thumb through", "Rhythm: page cadence", "Silhouette: lifted page"],
    },
    {
        "id": "group-services", "title": "Shared Carrier",
        "job": "Coordinate group messages, daily services, and shared routines.",
        "essence": "coordination", "noun": "tiffin carrier", "style": "woven",
        "cliche": "paired chat bubbles, official green, app-grid imitation",
        "signature": "two load-bearing bands alternate over and under the stacked tiers",
        "concepts": ["Object: tiffin carrier", "System: stacked services", "Relationship: interlaced straps", "Verb: carry together"],
    },
    {
        "id": "channel-broadcasting", "title": "Relay Mailbox",
        "job": "Broadcast durable updates to large subscribed channels.",
        "essence": "reach", "noun": "relay mailbox", "style": "risograph",
        "cliche": "paper planes, official blue, circular send buttons",
        "signature": "misregistered spot plates converge at one outbound slot",
        "concepts": ["Object: relay mailbox", "Verb: dispatch outward", "System: channel slot", "Material: two ink plates"],
    },
    {
        "id": "live-chat", "title": "Switchboard Shuttle",
        "job": "Continue fast conversations across devices and contexts.",
        "essence": "continuity", "noun": "switchboard shuttle", "style": "pixel-grid",
        "cliche": "lightning bolts, chat bubbles, familiar blue-purple gradients",
        "signature": "a one-cell staircase reroutes through the square switchboard",
        "concepts": ["Object: switchboard shuttle", "Verb: hand off", "Grid: routed staircase", "Silhouette: keyed connector"],
    },
    {
        "id": "ephemeral-visuals", "title": "Moment Cartridge",
        "job": "Send visual moments that are intentionally temporary.",
        "essence": "ephemeral", "noun": "sand-timer cartridge", "style": "flat-geometric",
        "cliche": "ghost mascots, yellow app fields, speech bubbles",
        "signature": "the cartridge window is cut by a single falling sand bridge",
        "concepts": ["Object: timer cartridge", "Verb: vanish after viewing", "Negative space: falling bridge", "Silhouette: clipped corners"],
    },
    {
        "id": "remix-video", "title": "Glow Zoetrope",
        "job": "Discover, remix, and circulate short-form video performances.",
        "essence": "remix", "noun": "zoetrope drum", "style": "gradient-glow",
        "cliche": "musical notes, play triangles, black neon trade dress",
        "signature": "one luminous slit crosses the opaque drum rim as a timing notch",
        "concepts": ["Object: zoetrope", "Verb: remix a loop", "Light: timing slit", "Silhouette: drum rim"],
    },
    {
        "id": "everyday-live-video", "title": "Story Lantern",
        "job": "Share everyday short videos and live slices of ordinary life.",
        "essence": "presence", "noun": "story lantern", "style": "enamel",
        "cliche": "camera loops, official orange, play-button framing",
        "signature": "a book-fold inlay replaces the expected lantern window",
        "concepts": ["Object: story lantern", "Verb: illuminate daily life", "Narrative: book-fold window", "Material: enamel boundary"],
    },
    {
        "id": "interest-forums", "title": "Topic Drawer",
        "job": "Discuss topics in interest-led forums with durable context.",
        "essence": "discussion", "noun": "card-catalog drawer", "style": "chrome",
        "cliche": "alien mascots, antennae, orange conversation marks",
        "signature": "a broad specular band stops at the inset topic label",
        "concepts": ["Object: catalog drawer", "Place: topic archive", "Verb: pull a thread", "Material: stopped chrome band"],
    },
    {
        "id": "public-current-conversation", "title": "Dispatch Ticker",
        "job": "Follow and join fast public conversation about current events.",
        "essence": "current", "noun": "dispatch ticker", "style": "glass-stack",
        "cliche": "letter X, bird silhouettes, black square trade dress",
        "signature": "two translucent news panes cross an opaque vertical ticker spine",
        "concepts": ["Object: dispatch ticker", "Verb: update in public", "System: crossing panes", "Silhouette: opaque spine"],
    },
    {
        "id": "saved-inspiration", "title": "Idea Swatches",
        "job": "Collect visual references and return to saved inspiration.",
        "essence": "inspiration", "noun": "swatch folio", "style": "woodcut",
        "cliche": "map pins, letter P, signature red circles",
        "signature": "one carved diagonal binds the fanned swatches into a single relief mass",
        "concepts": ["Object: swatch folio", "Verb: save for later", "Collection: fanned samples", "Material: binding gouge"],
    },
    {
        "id": "professional-identity", "title": "Credential Folio",
        "job": "Present professional identity, experience, and working relationships.",
        "essence": "credibility", "noun": "credential folio", "style": "stencil-cut",
        "cliche": "initials, blue business tiles, profile-card UI",
        "signature": "one continuous cut joins portrait window, spine, and credential notch",
        "concepts": ["Object: credential folio", "Verb: present experience", "Negative space: continuous credential cut", "Silhouette: tabbed cover"],
    },
    {
        "id": "voice-communities", "title": "Roundtable Radio",
        "job": "Keep persistent groups together across voice, text, and activity.",
        "essence": "togetherness", "noun": "roundtable radio", "style": "duotone",
        "cliche": "game controllers, face mascots, signature violet",
        "signature": "a secondary plane forms one shared channel across the round table",
        "concepts": ["Object: roundtable radio", "Place: persistent room", "Relationship: shared channel", "Material: split plane"],
    },
    {
        "id": "threaded-text", "title": "Conversation Spool",
        "job": "Write and follow connected public text conversations.",
        "essence": "continuity", "noun": "spool shuttle", "style": "clay",
        "cliche": "at-sign spirals, wordmark letters, black-and-white imitation",
        "signature": "the thread exits through one oversized diagonal shuttle notch",
        "concepts": ["Object: spool shuttle", "Verb: carry a thread", "Negative space: shuttle notch", "Material: chunky clay"],
    },
    {
        "id": "messages-and-stickers", "title": "Stamp Album",
        "job": "Exchange messages, expressive stickers, and everyday services.",
        "essence": "expression", "noun": "stamp album", "style": "blueprint",
        "cliche": "speech-bubble wordmarks, official green, licensed characters",
        "signature": "one measured perforation line folds into the album spine",
        "concepts": ["Object: stamp album", "Verb: collect expressions", "System: measured perforation", "Silhouette: folded spine"],
    },
    {
        "id": "live-creator-community", "title": "Cue Brush",
        "job": "Watch live creators while participating with the community.",
        "essence": "live", "noun": "stage cue brush", "style": "ink-brush",
        "cliche": "glitch bubbles, wordmark blocks, signature purple",
        "signature": "one edge-open dry cut turns the bristle mass into an audience cue",
        "concepts": ["Object: cue brush", "Place: live stage", "Verb: cue the audience", "Material: edge-open dry cut"],
    },
    {
        "id": "decentralized-conversation", "title": "Weather Relay",
        "job": "Join portable public conversation across an open social network.",
        "essence": "openness", "noun": "weather-vane relay", "style": "cut-paper",
        "cliche": "butterfly silhouettes, sky-blue brand fields, mirrored wings",
        "signature": "one offset paper vane passes through the shared relay pivot",
        "concepts": ["Object: weather vane", "Verb: carry across servers", "System: shared pivot", "Material: offset paper layers"],
    },
]


def _font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _write_if_changed(path: Path, content: str) -> None:
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def _glyph(slug: str) -> str:
    glyphs = {
        "friends-and-groups": '''<path d="M426 174H598V330H426ZM174 440H330V608H174ZM672 424H850V590H672ZM432 694H610V850H432Z" fill="#D96A55" stroke="#151923" stroke-width="50" stroke-linejoin="round"/><ellipse cx="512" cy="512" rx="244" ry="214" fill="#F7DDA5" stroke="#151923" stroke-width="58"/><path d="M292 548Q512 674 736 486Q710 682 512 726Q334 700 292 548Z" fill="#D96A55"/><path d="M364 420Q512 328 660 420" fill="none" stroke="#151923" stroke-width="48" stroke-linecap="round"/>''',
        "creator-video-library": '''<path d="M298 414Q298 270 438 238H590Q724 270 724 414V650Q724 774 600 802H424Q298 774 298 650Z" fill="#F2B568" stroke="#35282A" stroke-width="52"/><path d="M724 424L854 350V636L724 562Z" fill="#FFF2D3" stroke="#35282A" stroke-width="48" stroke-linejoin="round"/><path d="M350 276Q430 150 512 252Q594 150 674 276L622 330H402Z" fill="#6A8F7A" stroke="#35282A" stroke-width="48" stroke-linejoin="round"/><circle cx="512" cy="488" r="132" fill="#FFF2D3" stroke="#35282A" stroke-width="44"/><path d="M512 406L590 542H434Z" fill="#D96550" stroke="#35282A" stroke-width="34" stroke-linejoin="round"/><path d="M394 700Q512 644 630 700" fill="none" stroke="#FFF2D3" stroke-width="42" stroke-linecap="round"/>''',
        "visual-journal": '''<path d="M230 410L500 260V624L230 776Z" fill="#D96550" stroke="#171A22" stroke-width="42" stroke-linejoin="round"/><path d="M500 260L790 426V790L500 624Z" fill="#68A49A" stroke="#171A22" stroke-width="42" stroke-linejoin="round"/><path d="M296 438L430 364V490L296 566Z" fill="#F3C66E" stroke="#171A22" stroke-width="34"/><path d="M570 386L718 470V596L570 512Z" fill="#FFF2D6" stroke="#171A22" stroke-width="34"/><path d="M296 650L430 576M570 622L718 706" stroke="#F3C66E" stroke-width="34" stroke-linecap="round"/><path d="M500 260V624" stroke="#171A22" stroke-width="58"/>''',
        "private-messaging": '''<path d="M278 276Q278 182 372 182H650Q744 182 744 276V344L842 512L744 580V748Q744 842 650 842H372Q278 842 278 748Z" fill="#1B2132" stroke="#10131D" stroke-width="54" stroke-linejoin="round"/><path d="M316 340L510 226L704 340L510 520Z" fill="#E6B75C" stroke="#10131D" stroke-width="42"/><path d="M316 664L510 520L704 664V770H316Z" fill="#6FA6A0" stroke="#10131D" stroke-width="42"/><path d="M316 340L510 520L704 340" fill="none" stroke="#10131D" stroke-width="42"/><path d="M466 476H554V564H466Z" fill="#D95F54" stroke="#10131D" stroke-width="28"/>''',
        "short-video-discovery": '''<path d="M260 310H626Q680 310 680 364V712M306 256H668Q722 256 722 310V694Q722 748 668 748H306Q252 748 252 694V310Q252 256 306 256ZM350 350H638M350 476H638M350 602H552" fill="none" stroke="#F7E8CC" stroke-width="104" stroke-linecap="round" stroke-linejoin="round"/><path d="M260 310H626Q680 310 680 364V712M306 256H668Q722 256 722 310V694Q722 748 668 748H306Q252 748 252 694V310Q252 256 306 256ZM350 350H638M350 476H638M350 602H552" fill="none" stroke="#17202A" stroke-width="56" stroke-linecap="round" stroke-linejoin="round"/><path d="M552 602Q650 602 722 530V694Q722 748 668 748H552Z" fill="#D96655" stroke="#17202A" stroke-width="54" stroke-linejoin="round"/>''',
        "group-services": '''<path d="M270 286Q270 214 342 214H728V350H430Q398 350 398 382V738Q398 810 326 810H270Z" fill="#F4D06F"/><path d="M754 286Q754 214 682 214H296V350H594Q626 350 626 382V738Q626 810 698 810H754Z" fill="#63A99F"/><path d="M398 446H626V574H398Z" fill="#17212B"/><path d="M398 446H480V574H398Z" fill="#F4D06F"/><path d="M544 446H626V574H544Z" fill="#63A99F"/><path d="M270 286Q270 214 342 214H728M754 286Q754 214 682 214H296" fill="none" stroke="#17212B" stroke-width="42"/>''',
        "channel-broadcasting": '''<path d="M238 392Q238 268 362 268H670Q794 268 794 392V736H238Z" fill="#F06A5B" opacity=".9"/><path d="M282 430Q282 306 406 306H714Q838 306 838 430V774H282Z" fill="#4AA3A1" opacity=".88"/><path d="M258 410Q258 286 382 286H690Q814 286 814 410V754H258Z" fill="none" stroke="#17202A" stroke-width="56"/><path d="M512 286V570H814M346 642H674" fill="none" stroke="#17202A" stroke-width="56"/><path d="M634 286V168H780V356H634Z" fill="#EBC564" stroke="#17202A" stroke-width="52" stroke-linejoin="round"/><circle cx="766" cy="740" r="38" fill="#17202A"/>''',
        "live-chat": '''<path d="M224 288H352V416H224ZM672 608H800V736H672Z" fill="#D65F52"/><path d="M352 320H608V384H672V512H608V576H480V640H352V576H288V448H352Z" fill="#F4D06F"/><path d="M288 320H416V448H288ZM608 576H736V704H608Z" fill="#1A2630"/><path d="M352 384H480V448H544V512H608V576H480V512H416V448H352Z" fill="#D65F52"/>''',
        "ephemeral-visuals": '''<path d="M314 206H710L752 260L650 472Q634 504 666 548L752 764L710 818H314L272 764L374 550Q390 516 358 474L272 260Z" fill="#E8C25E"/><path d="M360 282H664L566 474Q548 510 582 550L664 742H360L458 550Q474 516 442 474Z" fill="#18202A"/><path d="M412 338H612L512 496Z" fill="#F4E8CE"/><path d="M410 686H614L512 532Z" fill="#D86452"/><path d="M484 478H540V572H484Z" fill="#F4E8CE"/>''',
        "remix-video": '''<defs><radialGradient id="g" cx="50%" cy="42%" r="62%"><stop offset="0" stop-color="#FFE39B"/><stop offset=".54" stop-color="#E86A77"/><stop offset="1" stop-color="#6746A5"/></radialGradient></defs><path d="M276 296Q304 202 512 202Q720 202 748 296L674 346Q620 304 512 304Q404 304 350 346Z" fill="url(#g)"/><path d="M276 296V692Q276 790 512 814Q748 790 748 692V544H650V666Q650 720 512 734Q374 720 374 666V334Z" fill="#151923"/><path d="M276 692Q300 790 512 814Q724 790 748 692L650 650Q618 718 512 730Q406 718 374 650Z" fill="url(#g)"/><path d="M366 356V626M474 390V684M582 390V684" stroke="#F9D77E" stroke-width="52" stroke-linecap="round"/><path d="M650 304H748V544H650Z" fill="#FFF0C8"/>''',
        "everyday-live-video": '''<path d="M410 238Q512 130 614 238" fill="none" stroke="#F4E8CE" stroke-width="92" stroke-linecap="round"/><path d="M410 238Q512 130 614 238" fill="none" stroke="#11151B" stroke-width="52" stroke-linecap="round"/><path d="M356 238H668L754 350V726Q754 786 694 786H330Q270 786 270 726V350Z" fill="#20252C" stroke="#11151B" stroke-width="52"/><path d="M326 384L512 506L698 384V692L512 574L326 692Z" fill="#E8B75E" stroke="#11151B" stroke-width="42" stroke-linejoin="round"/><path d="M512 506V574" stroke="#D85F52" stroke-width="52"/><path d="M336 328H688" stroke="#F4E8CE" stroke-width="28"/>''',
        "interest-forums": '''<defs><linearGradient id="c" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F8F1DD"/><stop offset=".22" stop-color="#6F7886"/><stop offset=".42" stop-color="#E8EDF1"/><stop offset=".64" stop-color="#343B48"/><stop offset=".84" stop-color="#D8B86B"/><stop offset="1" stop-color="#697482"/></linearGradient></defs><path d="M214 238H744Q792 238 792 286V738Q792 786 744 786H214Z" fill="#131820" stroke="#0B0F15" stroke-width="48"/><path d="M260 284H742V740H260Z" fill="url(#c)"/><path d="M304 352H680V542H304Z" fill="#171C25"/><path d="M372 410H738Q822 410 822 494Q822 578 738 578H372Z" fill="#F5E7C8" stroke="#171C25" stroke-width="50"/><path d="M388 664H626" stroke="#171C25" stroke-width="58" stroke-linecap="round"/>''',
        "public-current-conversation": '''<path d="M270 252H662L758 348V646L684 720L632 818L568 720H366L270 624Z" fill="#6DA7A2" opacity=".64"/><path d="M346 318H738V650L648 740H256V408Z" fill="#E1B45C" opacity=".62"/><path d="M430 202H552V730H430Z" fill="#171B23"/><path d="M304 406H698M304 544H698M344 682H630" stroke="#F6E9CF" stroke-width="58" stroke-linecap="round"/><path d="M430 406H552V544H430Z" fill="#D65F52"/>''',
        "saved-inspiration": '''<path fill="#D9A956" fill-rule="evenodd" d="M254 278Q512 190 770 278L714 772Q512 842 310 772ZM344 350L402 688L480 674L422 336ZM502 310L516 678L598 676L584 308Z"/><path d="M282 492Q512 386 742 456" fill="none" stroke="#191B20" stroke-width="58"/><path d="M318 720Q512 788 704 720" fill="none" stroke="#191B20" stroke-width="54"/><circle cx="680" cy="310" r="54" fill="#191B20"/>''',
        "professional-identity": '''<path fill="#D76151" fill-rule="evenodd" d="M282 230H418V170H606V230H742L794 282V774L742 826H282L230 774V282ZM466 220H558V302H466ZM338 370H496V528H338ZM340 600H684V668H340ZM340 712H590V768H340ZM558 370H686V528H558Z"/><path d="M230 330H378V230H282L230 282ZM646 726H794V774L742 826H646Z" fill="#F3E6C9"/>''',
        "voice-communities": '''<path d="M246 530Q246 304 438 244L474 360Q362 398 362 530Q362 660 474 704L430 814Q246 742 246 530Z" fill="#E5BA62"/><path d="M778 506Q778 318 620 254L574 366Q662 410 662 506Q662 610 568 654L616 766Q778 698 778 506Z" fill="#5D8E87"/><path d="M444 372Q444 314 502 314H526Q584 314 584 372V554Q584 612 526 612H502Q444 612 444 554Z" fill="#17202A"/><path d="M392 540Q392 678 512 678Q632 678 632 540" fill="none" stroke="#17202A" stroke-width="64" stroke-linecap="round"/><path d="M512 678V790" stroke="#17202A" stroke-width="64" stroke-linecap="round"/>''',
        "threaded-text": '''<ellipse cx="466" cy="304" rx="210" ry="92" fill="#F2C070" stroke="#33282C" stroke-width="44"/><path d="M256 304V650Q256 750 466 770Q676 750 676 650V304Q616 396 466 396Q316 396 256 304Z" fill="#D96A5A" stroke="#33282C" stroke-width="44"/><path d="M328 450Q466 544 604 450V582Q466 674 328 582Z" fill="#F4E6CB"/><path d="M610 600Q804 620 806 770Q806 844 722 844Q654 844 670 770Q684 714 610 706" fill="none" stroke="#33282C" stroke-width="62" stroke-linecap="round"/><path d="M318 276Q466 224 614 276" fill="none" stroke="#FFF0D3" stroke-width="34" stroke-linecap="round"/>''',
        "messages-and-stickers": '''<path d="M270 238H730Q778 238 778 286V738Q778 786 730 786H270Z" fill="none" stroke="#E8D59B" stroke-width="46"/><path d="M352 238V786M352 342H778" fill="none" stroke="#69A3A1" stroke-width="34"/><path d="M432 424Q432 378 478 378H624Q670 378 670 424V566Q670 612 624 612H544L466 676V612H478Q432 612 432 566Z" fill="none" stroke="#E8D59B" stroke-width="44"/><circle cx="352" cy="342" r="42" fill="#D96052"/><circle cx="670" cy="612" r="36" fill="#D96052"/><path d="M242 214H382M746 314V210" stroke="#E8D59B" stroke-width="28" stroke-linecap="round"/>''',
        "live-creator-community": '''<path d="M382 182Q396 128 450 142L594 178Q648 192 634 246L552 568L318 510Z" fill="#17191F"/><path d="M430 218L570 254L502 520L364 486Z" fill="#F3E2BF"/><path d="M318 510L552 568L618 814L548 786L506 858L448 778L376 824L346 746L270 754Z" fill="#D15E4E"/><path d="M318 510L552 568L530 654L296 596Z" fill="#17191F"/><path d="M296 596L400 622L370 740L270 714Z" fill="#F3E2BF"/><path d="M430 218L472 134L622 172L594 256Z" fill="#D15E4E"/>''',
        "decentralized-conversation": '''<path d="M286 304L486 210L680 306L522 412Z" fill="#E7B85F"/><path d="M252 456L486 330L704 450L520 578Z" fill="#D86654"/><path d="M300 610L492 500L660 598L520 720Z" fill="#6C9B8F"/><path d="M462 226H552V814H462Z" fill="#17202A"/><path d="M508 456L790 276L862 380L568 574Z" fill="#F2E5C8"/><path d="M772 286L880 236L844 352Z" fill="#D86654"/><circle cx="510" cy="510" r="66" fill="#17202A"/>''',
    }
    glyphs.update({
        "friends-and-groups": '''<path d="M450 170H584V324H450ZM142 430H306V574H142ZM430 704H626V856H430Z" fill="#D96A55" stroke="#151923" stroke-width="50" stroke-linejoin="round"/><ellipse cx="512" cy="510" rx="256" ry="216" fill="#F7DDA5" stroke="#151923" stroke-width="58"/><path d="M278 534Q486 716 744 464Q726 678 516 728Q322 692 278 534Z" fill="#D96A55"/><path d="M354 414Q506 316 674 422" fill="none" stroke="#151923" stroke-width="48" stroke-linecap="round"/>''',
        "creator-video-library": '''<path d="M296 398Q296 264 430 236H594Q728 264 728 398V650Q728 774 604 802H420Q296 774 296 650Z" fill="#F2B568" stroke="#35282A" stroke-width="52"/><path d="M728 420L858 350V640L728 566Z" fill="#FFF2D3" stroke="#35282A" stroke-width="48" stroke-linejoin="round"/><path d="M350 278Q430 144 512 250Q594 144 674 278L620 330H404Z" fill="#6A8F7A" stroke="#35282A" stroke-width="48"/><circle cx="512" cy="490" r="132" fill="#FFF2D3" stroke="#35282A" stroke-width="44"/><path d="M450 472Q512 406 574 472Q552 558 512 578Q472 558 450 472Z" fill="#D96550" stroke="#35282A" stroke-width="34"/><path d="M386 688Q512 626 640 688" fill="none" stroke="#FFF2D3" stroke-width="42" stroke-linecap="round"/><path d="M296 632L182 720L332 746Z" fill="#6A8F7A" stroke="#35282A" stroke-width="42" stroke-linejoin="round"/>''',
        "private-messaging": '''<path d="M278 276Q278 182 372 182H650Q744 182 744 276V344L842 512L744 580V748Q744 842 650 842H372Q278 842 278 748Z" fill="#1B2132" stroke="#10131D" stroke-width="54" stroke-linejoin="round"/><path d="M316 340L510 226L704 340L510 520Z" fill="#E6B75C" stroke="#10131D" stroke-width="42"/><path d="M316 664L510 520L704 664V770H316Z" fill="#6FA6A0" stroke="#10131D" stroke-width="42"/><path d="M316 340L510 520L704 340" fill="none" stroke="#10131D" stroke-width="42"/><circle cx="510" cy="520" r="64" fill="#D95F54" stroke="#10131D" stroke-width="30"/><path d="M278 616H212V418H278" fill="none" stroke="#E6B75C" stroke-width="48" stroke-linejoin="round"/>''',
        "short-video-discovery": '''<path d="M224 330H624Q680 330 680 386V748H224Z" fill="#F7E8CC" stroke="#17202A" stroke-width="54"/><path d="M286 274H686Q742 274 742 330V692L660 774H286Z" fill="#17202A" stroke="#F7E8CC" stroke-width="34"/><path d="M350 376H658M350 492H612M350 608H552" stroke="#F7E8CC" stroke-width="54" stroke-linecap="round"/><path d="M552 608H742V692L660 774H552Z" fill="#D96655" stroke="#17202A" stroke-width="46" stroke-linejoin="round"/><path d="M742 430L812 466V612L742 646Z" fill="#F7E8CC" stroke="#17202A" stroke-width="46" stroke-linejoin="round"/>''',
        "group-services": '''<path d="M244 790V388Q244 290 342 290H684Q782 290 782 388V790" fill="none" stroke="#17212B" stroke-width="62"/><path d="M292 770V364H650Q716 364 716 430V770" fill="none" stroke="#F4D06F" stroke-width="112" stroke-linecap="square" stroke-linejoin="round"/><path d="M732 770V272H390Q324 272 324 338V770" fill="none" stroke="#63A99F" stroke-width="112" stroke-linecap="square" stroke-linejoin="round"/><path d="M292 470H394" stroke="#F4D06F" stroke-width="112"/><path d="M650 364H716V472" stroke="#F4D06F" stroke-width="112"/><path d="M324 566H438M620 566H732" stroke="#63A99F" stroke-width="112"/><path d="M438 566H620" stroke="#17212B" stroke-width="124"/><path d="M280 214Q512 100 744 214" fill="none" stroke="#17212B" stroke-width="54" stroke-linecap="round"/>''',
        "live-chat": '''<path d="M196 222H430V456H196Z" fill="#F4D06F"/><path d="M594 568H828V802H594Z" fill="#D65F52"/><path d="M246 272H380V406H246ZM644 618H778V752H644Z" fill="#1A2630"/><path d="M380 314H500V430H562V548H644V682" fill="none" stroke="#1A2630" stroke-width="86" stroke-linejoin="miter"/><path d="M380 314H458V430H520V548H644" fill="none" stroke="#D65F52" stroke-width="42"/><path d="M168 286H232V392H168ZM792 632H856V738H792Z" fill="#1A2630"/>''',
        "ephemeral-visuals": '''<path d="M306 196H688L748 256L646 474Q632 506 664 550L748 770L688 830H306L246 770L350 550Q366 516 334 474L246 256Z" fill="#E8C25E"/><path d="M364 282H632L544 474Q530 508 558 550L632 744H364L454 550Q468 516 440 474Z" fill="#18202A"/><path d="M410 338H586L512 486Z" fill="#F4E8CE"/><path d="M410 690H606L512 538Z" fill="#D86452"/><path d="M748 374H842V566H748Z" fill="#18202A"/><path d="M788 416H842" stroke="#E8C25E" stroke-width="42"/>''',
        "remix-video": '''<defs><radialGradient id="g" cx="50%" cy="42%" r="62%"><stop offset="0" stop-color="#FFE39B"/><stop offset=".54" stop-color="#E86A77"/><stop offset="1" stop-color="#6746A5"/></radialGradient></defs><path d="M276 296Q304 202 512 202Q720 202 748 296L674 346Q620 304 512 304Q404 304 350 346Z" fill="url(#g)"/><path d="M276 296V692Q276 790 512 814Q748 790 748 692V556H638V668Q638 720 512 734Q386 720 386 668V334Z" fill="#151923"/><path d="M276 692Q300 790 512 814Q724 790 748 692L650 650Q618 718 512 730Q406 718 374 650Z" fill="url(#g)"/><path d="M342 344V596M464 402V684M586 344V596" stroke="#F9D77E" stroke-width="54" stroke-linecap="round"/><path d="M638 304H748V556H638Z" fill="#FFF0C8"/><path d="M720 426L846 370V520L720 568Z" fill="#E86A77"/>''',
        "everyday-live-video": '''<path d="M374 250Q512 102 650 250" fill="none" stroke="#11151B" stroke-width="58" stroke-linecap="round"/><path d="M316 268H708L780 362V740Q780 802 718 802H306Q244 802 244 740V362Z" fill="#20252C" stroke="#11151B" stroke-width="52"/><path d="M310 410L506 324V686L310 764Z" fill="#E8B75E" stroke="#11151B" stroke-width="42"/><path d="M506 324L714 414V766L506 686Z" fill="#D85F52" stroke="#11151B" stroke-width="42"/><path d="M370 454L458 416V560L370 596ZM560 418L654 458V602L560 562Z" fill="#F4E8CE"/><path d="M244 536H170M780 536H854" stroke="#E8B75E" stroke-width="44" stroke-linecap="round"/>''',
        "interest-forums": '''<defs><linearGradient id="c" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F8F1DD"/><stop offset=".22" stop-color="#6F7886"/><stop offset=".42" stop-color="#E8EDF1"/><stop offset=".64" stop-color="#343B48"/><stop offset=".84" stop-color="#D8B86B"/><stop offset="1" stop-color="#697482"/></linearGradient></defs><path d="M206 254H700V514H206Z" fill="url(#c)" stroke="#0B0F15" stroke-width="48"/><path d="M264 526H758V786H264Z" fill="url(#c)" stroke="#0B0F15" stroke-width="48"/><path d="M326 332H762Q840 332 840 410Q840 488 762 488H326Z" fill="#F5E7C8" stroke="#171C25" stroke-width="52"/><path d="M384 604H820Q898 604 898 682Q898 760 820 760H384Z" fill="#D8B86B" stroke="#171C25" stroke-width="52"/>''',
        "public-current-conversation": '''<path d="M204 354Q204 272 286 272H738Q820 272 820 354V672Q820 754 738 754H286Q204 754 204 672Z" fill="#6DA7A2" opacity=".58"/><path d="M274 304H750V714H274Z" fill="#E1B45C" opacity=".62"/><path d="M204 422H820M204 584H820" stroke="#F6E9CF" stroke-width="58"/><path d="M322 360H594M430 516H702M322 678H594" stroke="#171B23" stroke-width="54" stroke-linecap="round"/><path d="M204 472L122 530L204 586ZM820 344L902 286V432L820 488Z" fill="#D65F52"/><path d="M486 304H548V714H486Z" fill="#171B23"/>''',
        "voice-communities": '''<path d="M214 520Q214 292 418 226L462 354Q346 396 346 520Q346 646 466 690L412 818Q214 742 214 520Z" fill="#E5BA62"/><path d="M810 492Q810 306 642 236L590 362Q686 406 686 492Q686 604 576 652L632 780Q810 704 810 492Z" fill="#5D8E87"/><path d="M438 358Q438 300 496 300H530Q588 300 588 358V558Q588 616 530 616H496Q438 616 438 558Z" fill="#17202A"/><path d="M380 538Q380 688 512 688Q644 688 644 538M512 688V800" fill="none" stroke="#17202A" stroke-width="64" stroke-linecap="round"/><path d="M216 388L146 346M808 640L886 684M348 742L294 820" stroke="#17202A" stroke-width="50" stroke-linecap="round"/>''',
        "messages-and-stickers": '''<path d="M194 332L470 218V702L194 814Z" fill="none" stroke="#E8D59B" stroke-width="46" stroke-linejoin="round"/><path d="M470 218L830 354V838L470 702Z" fill="none" stroke="#69A3A1" stroke-width="46" stroke-linejoin="round"/><path d="M266 400L398 348V516L266 568Z" fill="none" stroke="#E8D59B" stroke-width="34" stroke-dasharray="48 28"/><path d="M552 400L724 464V632L552 568Z" fill="none" stroke="#E8D59B" stroke-width="34" stroke-dasharray="48 28"/><circle cx="398" cy="348" r="34" fill="#D96052"/><circle cx="724" cy="632" r="34" fill="#D96052"/><path d="M470 218V702M192 856H832M236 834V878M788 834V878" stroke="#E8D59B" stroke-width="28"/>''',
        "decentralized-conversation": '''<path d="M294 262L488 182L682 262L486 372Z" fill="#E7B85F"/><path d="M250 416L488 326L670 414L486 512Z" fill="#D86654"/><path d="M286 574L490 486L630 566L486 654Z" fill="#6C9B8F"/><path d="M442 186H534V824H442Z" fill="#17202A"/><path d="M486 426L788 250L866 362L552 550Z" fill="#F2E5C8"/><path d="M788 250L900 212L846 330Z" fill="#D86654"/><circle cx="488" cy="490" r="62" fill="#17202A"/>''',
    })
    glyphs.update({
        "friends-and-groups": '''<path fill="#F7DDA5" stroke="#151923" stroke-width="58" fill-rule="evenodd" d="M190 506Q190 256 500 216Q812 236 830 500Q810 778 494 806Q190 766 190 506ZM174 390H344V522H174ZM468 188H612V348H468ZM650 588H846V734H650Z"/><path d="M242 564Q506 790 774 486Q728 722 506 744Q300 720 242 564Z" fill="#D96A55"/><path d="M342 398Q504 286 686 408" fill="none" stroke="#151923" stroke-width="48" stroke-linecap="round"/>''',
        "private-messaging": '''<path d="M230 286Q230 206 310 206H642Q706 206 748 260L900 512L748 764Q706 818 642 818H310Q230 818 230 738Z" fill="#1B2132" stroke="#10131D" stroke-width="54" stroke-linejoin="round"/><path d="M278 322L500 220L746 390L500 536Z" fill="#E6B75C" stroke="#10131D" stroke-width="42"/><path d="M278 704L500 536L748 694L680 772H278Z" fill="#6FA6A0" stroke="#10131D" stroke-width="42"/><path d="M278 322L500 536L746 390" fill="none" stroke="#10131D" stroke-width="42"/><circle cx="558" cy="566" r="62" fill="#D95F54" stroke="#10131D" stroke-width="30"/>''',
        "short-video-discovery": '''<path d="M210 304H598V714L520 792H210Z" fill="#17202A" stroke="#F7E8CC" stroke-width="34"/><path d="M280 250H668V660L590 738H280Z" fill="#F7E8CC" stroke="#17202A" stroke-width="50"/><path d="M354 196H742V606L664 684H354Z" fill="#17202A" stroke="#F7E8CC" stroke-width="34"/><path d="M742 438L844 484L742 570Z" fill="#D96655" stroke="#17202A" stroke-width="42" stroke-linejoin="round"/><path d="M664 684L590 738L520 792" fill="none" stroke="#D96655" stroke-width="52"/>''',
        "group-services": '''<path d="M224 714C224 518 328 318 744 254" fill="none" stroke="#F4D06F" stroke-width="126" stroke-linecap="round"/><path d="M276 250C548 280 744 426 800 734" fill="none" stroke="#63A99F" stroke-width="126" stroke-linecap="round"/><path d="M440 392L560 354" stroke="#17212B" stroke-width="142"/><path d="M440 392L560 354" stroke="#F4D06F" stroke-width="126"/><path d="M262 760H762" stroke="#17212B" stroke-width="58" stroke-linecap="round"/><path d="M300 714V810M722 656V810" stroke="#17212B" stroke-width="58"/>''',
        "ephemeral-visuals": '''<path d="M222 258H650V322H714V386H822V812H306L222 728Z" fill="#E8C25E"/><path d="M318 350H602V442H430V528H670V616H500V706H822" fill="none" stroke="#18202A" stroke-width="72" stroke-linejoin="miter"/><path d="M354 386H550V406H394V564H624V580H464V670H746" fill="none" stroke="#F4E8CE" stroke-width="30" stroke-linejoin="miter"/><path d="M680 706H822" stroke="#D86452" stroke-width="72"/><path d="M650 258V322H714V386H822" fill="none" stroke="#18202A" stroke-width="34"/>''',
        "public-current-conversation": '''<path d="M196 326Q278 246 376 294L710 460Q804 508 858 424V650Q772 732 674 684L338 518Q248 474 196 558Z" fill="#6DA7A2" opacity=".68"/><path d="M196 410Q280 330 378 378L710 544Q802 590 858 508V732Q776 814 676 766L340 600Q248 556 196 640Z" fill="#E1B45C" opacity=".68"/><path d="M238 364L756 624" stroke="#171B23" stroke-width="66" stroke-linecap="round"/><path d="M366 430L506 500M576 534L716 604" stroke="#F6E9CF" stroke-width="54" stroke-linecap="round"/><path d="M196 326L108 392L196 470Z" fill="#D65F52"/>''',
        "saved-inspiration": '''<path fill="#191B20" fill-rule="evenodd" d="M178 744L262 264L424 300L402 674L438 202L600 216L574 680L642 286L806 330L738 758L610 812H286ZM256 674L334 324L382 336L334 680ZM454 676L486 270L548 278L520 682ZM624 692L682 354L748 370L688 704Z"/><path d="M242 610L350 574M466 552L548 526M650 618L728 592" stroke="#D9A956" stroke-width="42" stroke-linecap="square"/><path d="M286 744H738L610 812H286Z" fill="#D9A956"/>''',
        "voice-communities": '''<path d="M190 286L372 206L432 350L270 438L178 380Z" fill="#E5BA62"/><path d="M700 214L842 326L776 486L620 394L630 286Z" fill="#5D8E87"/><path d="M214 676L332 548L470 666L354 824L232 792Z" fill="#E5BA62"/><path d="M366 416Q512 334 654 438L612 670Q488 746 350 632Z" fill="#5D8E87" opacity=".52"/><g transform="rotate(12 554 510)"><path d="M508 368Q508 314 562 314H584Q638 314 638 368V534Q638 588 584 588H562Q508 588 508 534Z" fill="#17202A"/><path d="M452 514Q452 648 574 648Q696 648 696 514M574 648V774" fill="none" stroke="#17202A" stroke-width="58" stroke-linecap="round"/></g>''',
        "live-creator-community": '''<path d="M206 734Q262 418 460 198Q530 120 636 196Q728 262 670 354Q612 448 500 520Q380 598 318 822Z" fill="#17191F"/><path d="M280 690Q342 444 500 262Q530 226 568 256Q600 280 572 318Q510 410 416 484Q334 550 280 690Z" fill="#F3E2BF"/><path d="M206 734L318 822L250 898L164 812Z" fill="#D15E4E"/><path d="M452 210L520 126L662 232L618 314Z" fill="#D15E4E"/><path d="M378 530L446 460L496 508L432 574L392 554L350 598Z" fill="#17191F"/>''',
    })
    return glyphs[slug]


def _alternate_glyph(slug: str, variant: int) -> str:
    """Return independently drawn verb and negative-space concepts for bake-offs."""
    concepts = {
        "friends-and-groups": (
            '''<circle cx="512" cy="512" r="174" fill="#D96A55" stroke="#151923" stroke-width="54"/><path d="M512 210L592 340H432ZM252 690L408 640L358 798ZM772 690L616 640L666 798Z" fill="#F7DDA5" stroke="#151923" stroke-width="48" stroke-linejoin="round"/>''',
            '''<path fill="#F7DDA5" fill-rule="evenodd" d="M512 188A324 324 0 1 1 284 742L370 656A202 202 0 1 0 512 310ZM284 742L196 830L380 804Z"/><path d="M512 308A204 204 0 0 1 704 444L618 480A112 112 0 0 0 512 402Z" fill="#D96A55"/>''',
        ),
        "creator-video-library": (
            '''<path d="M248 286H706Q778 286 778 358V738H248Z" fill="#F2B568" stroke="#35282A" stroke-width="52"/><circle cx="430" cy="510" r="126" fill="#FFF2D3" stroke="#35282A" stroke-width="44"/><path d="M430 426L514 566H346Z" fill="#D96550"/><path d="M778 426L866 376V636L778 586Z" fill="#6A8F7A" stroke="#35282A" stroke-width="44"/>''',
            '''<path d="M260 236H744V786H260Z" fill="#35282A"/><path d="M320 296H684V726H320Z" fill="#F2B568"/><path d="M320 296L684 512L320 726Z" fill="#FFF2D3"/><path d="M320 458L488 558L320 658Z" fill="#6A8F7A"/>''',
        ),
        "visual-journal": (
            '''<path d="M220 326L468 220V696L220 802Z" fill="#D96550" stroke="#171A22" stroke-width="44"/><path d="M468 220L806 356V832L468 696Z" fill="#68A49A" stroke="#171A22" stroke-width="44"/><path d="M540 350L718 422V544L540 472ZM540 588L718 660V782L540 710Z" fill="#FFF2D6"/>''',
            '''<path d="M206 622L368 290L512 486L656 290L818 622L656 782L512 586L368 782Z" fill="#D96550" stroke="#171A22" stroke-width="48" stroke-linejoin="round"/><path d="M368 290L512 486L656 290L512 586Z" fill="#F3C66E"/>''',
        ),
        "private-messaging": (
            '''<path d="M220 430L512 236L804 430V716L512 852L220 716Z" fill="#6FA6A0" stroke="#10131D" stroke-width="52"/><path d="M220 430L512 626L804 430" fill="none" stroke="#10131D" stroke-width="52"/><path d="M448 512H576V640H448Z" fill="#E6B75C" stroke="#10131D" stroke-width="36"/>''',
            '''<path fill="#1B2132" fill-rule="evenodd" d="M252 236H772V788H252ZM330 334L512 504L694 334V690H330ZM470 474H554V558H470Z"/><path d="M252 236L512 474L772 236" fill="#E6B75C"/>''',
        ),
        "short-video-discovery": (
            '''<path d="M244 260H622V746H244Z" fill="#F7E8CC" stroke="#17202A" stroke-width="54"/><path d="M402 318H780V804H402Z" fill="#D96655" stroke="#17202A" stroke-width="54"/><path d="M490 424L650 532L490 640Z" fill="#F7E8CC"/>''',
            '''<path d="M220 326H684M286 492H750M352 658H816" stroke="#17202A" stroke-width="74" stroke-linecap="round"/><path d="M684 254L812 326L684 398ZM750 420L878 492L750 564ZM816 586L944 658L816 730Z" fill="#D96655"/>''',
        ),
        "group-services": (
            '''<path d="M312 222H712V802H312Z" fill="#F4D06F"/><path d="M244 344H780V472H244ZM244 598H780V726H244Z" fill="#63A99F"/><path d="M448 344H576V472H448ZM320 598H448V726H320Z" fill="#17212B"/>''',
            '''<path fill="#F4D06F" fill-rule="evenodd" d="M230 236H794V788H230ZM356 354H668V670H356Z"/><path d="M230 512H442V670H582V354H794" fill="none" stroke="#63A99F" stroke-width="92"/>''',
        ),
        "channel-broadcasting": (
            '''<path d="M242 304H664V782H242Z" fill="#F06A5B"/><path d="M300 354H722V832H300Z" fill="#4AA3A1"/><path d="M270 328H692V806H270Z" fill="none" stroke="#17202A" stroke-width="52"/><path d="M592 328V194H776V452H592Z" fill="#EBC564" stroke="#17202A" stroke-width="46"/>''',
            '''<path d="M220 272H804V752H220Z" fill="#17202A"/><path d="M300 360H630V664H300Z" fill="#E8DFC9"/><path d="M630 430L820 512L630 594Z" fill="#F06A5B"/><path d="M366 430H530M366 512H570M366 594H530" stroke="#4AA3A1" stroke-width="42"/>''',
        ),
        "live-chat": (
            '''<path d="M230 304H426V500H230ZM598 524H794V720H598Z" fill="#F4D06F"/><path d="M426 368H598V432H662V524H598V588H426V524H362V432H426Z" fill="#D65F52"/>''',
            '''<path d="M214 294H810V730H594L456 840V730H214Z" fill="#1A2630"/><path d="M302 398H430V526H302ZM594 500H722V628H594Z" fill="#F4D06F"/><path d="M430 462H594V540H430Z" fill="#D65F52"/>''',
        ),
        "ephemeral-visuals": (
            '''<path d="M286 218H738L628 480H396ZM286 806H738L628 544H396Z" fill="#E8C25E"/><path d="M448 480H576V544H448Z" fill="#D86452"/>''',
            '''<path fill="#18202A" fill-rule="evenodd" d="M250 230H774L650 512L774 794H250L374 512ZM414 324L512 474L610 324ZM414 700L512 550L610 700Z"/><path d="M480 472H544V552H480Z" fill="#D86452"/>''',
        ),
        "remix-video": (
            '''<path d="M256 510A256 256 0 0 1 690 326" fill="none" stroke="#E86A77" stroke-width="94" stroke-linecap="round"/><path d="M690 220L826 358L640 398Z" fill="#FFE39B"/><path d="M768 514A256 256 0 0 1 334 698" fill="none" stroke="#6746A5" stroke-width="94" stroke-linecap="round"/><path d="M334 804L198 666L384 626Z" fill="#FFE39B"/>''',
            '''<path d="M230 278H794V746H230Z" fill="#151923"/><path d="M294 350H462V674H294ZM562 350H730V674H562Z" fill="#E86A77"/><path d="M462 456H562V568H462Z" fill="#FFE39B"/>''',
        ),
        "everyday-live-video": (
            '''<path d="M270 360L512 210L754 360V780H270Z" fill="#20252C" stroke="#11151B" stroke-width="52"/><path d="M350 436L512 326L674 436L512 566Z" fill="#E8B75E"/><path d="M512 566V724" stroke="#D85F52" stroke-width="52"/>''',
            '''<path d="M246 286H778V782H246Z" fill="#20252C"/><path d="M246 286L512 544L778 286" fill="#E8B75E"/><circle cx="512" cy="544" r="76" fill="#D85F52"/><path d="M392 210Q512 86 632 210" fill="none" stroke="#11151B" stroke-width="58"/>''',
        ),
        "interest-forums": (
            '''<path d="M238 244H698V794H238Z" fill="#131820" stroke="#0B0F15" stroke-width="48"/><path d="M314 342H786V492H314ZM314 558H846V708H314Z" fill="#D8B86B" stroke="#171C25" stroke-width="44"/>''',
            '''<path d="M244 284H780V730H244Z" fill="#171C25"/><path d="M344 390H680V624H344Z" fill="#F5E7C8"/><path d="M680 444H834V570H680Z" fill="#D8B86B"/><path d="M402 452H604M402 548H564" stroke="#697482" stroke-width="38"/>''',
        ),
        "public-current-conversation": (
            '''<path d="M216 316H808L706 512L808 708H216L318 512Z" fill="#6DA7A2"/><path d="M318 386H706M318 512H706M318 638H706" stroke="#F6E9CF" stroke-width="50"/><path d="M478 244H546V780H478Z" fill="#171B23"/>''',
            '''<path d="M252 252H674L786 364V772H364L252 660Z" fill="#E1B45C" opacity=".7"/><path d="M364 252H772V660L660 772H252V364Z" fill="#6DA7A2" opacity=".7"/><path d="M454 364H570V660H454Z" fill="#171B23"/>''',
        ),
        "saved-inspiration": (
            '''<path d="M286 226H738V806L512 676L286 806Z" fill="#D9A956" stroke="#191B20" stroke-width="52"/><path d="M386 340H638M386 460H596" stroke="#191B20" stroke-width="52" stroke-linecap="round"/>''',
            '''<path fill="#D9A956" fill-rule="evenodd" d="M236 276Q512 170 788 276L706 788Q512 856 318 788ZM346 354L422 704L500 684L424 334ZM548 320L530 690L616 696L634 326Z"/>''',
        ),
        "professional-identity": (
            '''<path d="M388 198H636L686 298H782V806H242V298H338Z" fill="#D76151"/><path d="M430 198H594V314H430Z" fill="#17212A"/><circle cx="416" cy="488" r="92" fill="#F3E6C9"/><path d="M560 424H696M560 526H696M330 668H694" stroke="#F3E6C9" stroke-width="52"/>''',
            '''<path fill="#D76151" fill-rule="evenodd" d="M244 254H780V798H244ZM414 254H610V374H414ZM346 462H678V674H346Z"/><path d="M346 568H678" stroke="#F3E6C9" stroke-width="50"/>''',
        ),
        "voice-communities": (
            '''<path d="M220 512Q220 274 430 224L470 360Q356 398 356 512Q356 628 470 666L430 802Q220 752 220 512ZM804 512Q804 274 594 224L554 360Q668 398 668 512Q668 628 554 666L594 802Q804 752 804 512Z" fill="#E5BA62"/><rect x="452" y="332" width="120" height="260" rx="60" fill="#17202A"/>''',
            '''<path fill="#5D8E87" fill-rule="evenodd" d="M512 198A314 314 0 1 1 290 734L390 634A172 172 0 1 0 512 340ZM290 734L204 820L386 792Z"/><path d="M462 402H562V612H462Z" fill="#17202A"/>''',
        ),
        "threaded-text": (
            '''<path d="M222 392L512 226L802 392L512 558Z" fill="#F2C070" stroke="#33282C" stroke-width="46"/><path d="M222 392V668L512 834V558Z" fill="#D96A5A"/><path d="M802 392V668L512 834V558Z" fill="#B45350"/><path d="M652 620Q844 694 744 824" fill="none" stroke="#33282C" stroke-width="58" stroke-linecap="round"/>''',
            '''<path d="M222 346H802V678H592L480 804V678H222Z" fill="#D96A5A" stroke="#33282C" stroke-width="48"/><path d="M330 458H694M330 562H610" stroke="#F4E6CB" stroke-width="50" stroke-linecap="round"/>''',
        ),
        "messages-and-stickers": (
            '''<path d="M248 242H776V806H248Z" fill="none" stroke="#E8D59B" stroke-width="46"/><path d="M342 242V806M342 344H776" stroke="#69A3A1" stroke-width="34"/><path d="M438 430H650V642H438Z" fill="none" stroke="#E8D59B" stroke-width="42" stroke-dasharray="60 34"/><circle cx="342" cy="344" r="40" fill="#D96052"/>''',
            '''<path fill="#172A3B" fill-rule="evenodd" d="M238 230H786V794H600L470 874V794H238ZM334 334H690V654H334Z"/><path d="M416 438H608M416 550H560" stroke="#E8D59B" stroke-width="42"/><circle cx="690" cy="654" r="46" fill="#D96052"/>''',
        ),
        "live-creator-community": (
            '''<path d="M250 382L670 218L806 566L386 730Z" fill="#17191F"/><path d="M316 414L646 286L716 468L386 596Z" fill="#F3E2BF"/><path d="M386 730L326 850M638 632L730 742" stroke="#D15E4E" stroke-width="62"/><path d="M600 326L756 252L692 442Z" fill="#D15E4E"/>''',
            '''<path d="M220 640Q264 318 532 226Q734 156 812 354Q682 308 590 430Q472 590 220 640Z" fill="#F3E2BF"/><path d="M220 640L468 522L336 784Z" fill="#17191F"/><path d="M590 430L812 354L686 532Z" fill="#D15E4E"/>''',
        ),
        "decentralized-conversation": (
            '''<path d="M512 202L800 380L512 558L224 380Z" fill="#E7B85F"/><path d="M512 466L800 644L512 822L224 644Z" fill="#6C9B8F"/><path d="M466 246H558V778H466Z" fill="#17202A"/>''',
            '''<path d="M206 512L430 258V420H626V258L818 512L626 766V604H430V766Z" fill="#E7DDCA"/><circle cx="512" cy="512" r="92" fill="#17202A"/><path d="M512 512L820 328" stroke="#D86654" stroke-width="74" stroke-linecap="round"/>''',
        ),
    }
    return concepts[slug][variant - 1]


def _svg(item: dict[str, object], variant: int = 0) -> str:
    palettes = {
        "friends-and-groups": ("#16212B", "#F5DCA8"),
        "creator-video-library": ("#EED9B8", "#35282A"),
        "visual-journal": ("#E9E1D2", "#171A22"),
        "private-messaging": ("#C9D3CA", "#171B2C"),
        "short-video-discovery": ("#1B2730", "#F7E8CC"),
        "group-services": ("#18242D", "#F4D06F"),
        "channel-broadcasting": ("#E8DFC9", "#17202A"),
        "live-chat": ("#17212A", "#F4D06F"),
        "ephemeral-visuals": ("#1B2430", "#E8C25E"),
        "remix-video": ("#161621", "#E86A77"),
        "everyday-live-video": ("#E9DDC8", "#20252C"),
        "interest-forums": ("#171C24", "#D8B86B"),
        "public-current-conversation": ("#E8E0D2", "#171B23"),
        "saved-inspiration": ("#E9D9B8", "#191B20"),
        "professional-identity": ("#17212A", "#F3E6C9"),
        "voice-communities": ("#18232C", "#E5BA62"),
        "threaded-text": ("#E8D8BC", "#33282C"),
        "messages-and-stickers": ("#172A3B", "#E8D59B"),
        "live-creator-community": ("#202027", "#F3E2BF"),
        "decentralized-conversation": ("#E7DDCA", "#17202A"),
    }
    background, accent = palettes[str(item["id"])]
    glyph = _glyph(str(item["id"])) if variant == 0 else _alternate_glyph(str(item["id"]), variant)
    title = str(item["title"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img" aria-labelledby="title">
  <title id="title">{title} — original {item['noun']} study</title>
  <g>{glyph}</g>
</svg>
'''


def _validate_assignment() -> None:
    shuffled = STYLES.copy()
    random.Random(SEED).shuffle(shuffled)
    actual = [str(item["style"]) for item in ITEMS]
    if actual != shuffled:
        raise ValueError(f"seeded assignment drift: expected {shuffled}, got {actual}")
    if len(ITEMS) != 20 or len(set(actual)) != 20 or set(actual) != set(STYLES):
        raise ValueError("Social Signals must use all 20 styles exactly once")


def _config_text(item: dict[str, object], theme: str, background: str) -> str:
    return f'''# Generated from scripts/build_social_signals.py.
schema_version = 1

[project]
name = {json.dumps(str(item['title']))}
master = "master.svg"
output = "build"
casebook = "../../../casebook"

[brief]
app_intent = {json.dumps("provide an independent clean-room visual study for " + str(item['job']))}
user_job = {json.dumps(str(item['job']))}
essence = {json.dumps(str(item['essence']))}
personality = ["independent", "specific", "crafted"]

[design]
palette = [{json.dumps(theme)}, {json.dumps(background)}]
cliches = [{json.dumps(str(item['cliche']))}]
signature_device = {json.dumps(str(item['signature']))}
device_family = "object-silhouette"
device_detail = {json.dumps(str(item['signature']))}
concept_lens = "clean-room-user-job"

[build]
targets = ["web"]
theme_color = "{theme}"
background_color = "{background}"
electron_radius = 0
tray_ts = false
tray_svg = ""
tray_template_mode = "auto"
color_scheme = "light"
optimize_png = true

[review]
status = "pending"
source_sha256 = ""
contract_sha256 = ""
scores = {{}}
notes = ""
'''


def _make_contact() -> Path:
    out = WORK_ROOT / "contacts" / "social-signals.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1600, 1280), "#111216")
    draw = ImageDraw.Draw(sheet)
    title_font, label_font, meta_font = _font(30), _font(18), _font(13)
    draw.text((34, 20), "Social Signals — 20 clean-room user-job studies", fill="#FFF4E8", font=title_font)
    for index, item in enumerate(ITEMS):
        row, column = divmod(index, 5)
        x, y = column * 320, 70 + row * 300
        case = SOURCE_ROOT / str(item["id"])
        icon = Image.open(case / "renders" / "128.png").convert("RGBA")
        native = Image.open(case / "renders" / "16.png").convert("RGBA")
        sil = Image.open(case / "renders" / "silhouette-128.png").convert("RGBA")
        draw.rounded_rectangle((x + 18, y + 12, x + 164, y + 158), 16, fill="#FFF4E8")
        sheet.paste(icon, (x + 27, y + 21), icon)
        native_zoom = native.resize((96, 96), Image.Resampling.NEAREST)
        draw.rounded_rectangle((x + 178, y + 12, x + 292, y + 126), 14, fill="#FFFFFF")
        sheet.paste(native_zoom, (x + 187, y + 21), native_zoom)
        sheet.paste(sil.resize((72, 72)), (x + 198, y + 140), sil.resize((72, 72)))
        draw.text((x + 20, y + 180), str(item["title"]), fill="#FFF4E8", font=label_font)
        draw.text((x + 20, y + 208), str(item["noun"]), fill="#A5A6AD", font=meta_font)
        draw.text((x + 20, y + 232), str(item["style"]), fill="#FF766D", font=meta_font)
        draw.text((x + 184, y + 130), "Pixel zoom · native 16px", fill="#A5A6AD", font=meta_font)
    sheet.save(out, optimize=True)
    return out


def _check_source(path: str) -> tuple[str, list[str]]:
    source = Path(path)
    return source.parent.name, check(source)


def _render_review(job: tuple[str, str]) -> str:
    source, output = map(Path, job)
    contact_sheet(source, output, background_color="#FFF4E8")
    return str(output)


def stage() -> None:
    _validate_assignment()
    finalists = WORK_ROOT / "finalists"
    bake_root = WORK_ROOT / "bakeoffs"
    reviews = WORK_ROOT / "reviews"
    check_results: list[dict[str, object]] = []
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    source_paths: list[str] = []
    for item in ITEMS:
        slug = str(item["id"])
        candidate_dir = finalists / slug
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidates = []
        for variant, label in enumerate(("object viewpoint", "verb viewpoint", "negative-space viewpoint")):
            path = candidate_dir / f"{chr(97 + variant)}.svg"
            _write_if_changed(path, _svg(item, variant))
            candidates.append((label, path))
        bake_path = bake_root / f"{slug}.png"
        if not bake_path.is_file() or bake_path.stat().st_mtime < max(path.stat().st_mtime for _, path in candidates):
            compare_sheet(candidates, bake_path)

    for item in ITEMS:
        slug = str(item["id"])
        case_dir = SOURCE_ROOT / slug
        render_dir = case_dir / "renders"
        case_dir.mkdir(parents=True, exist_ok=True)
        render_dir.mkdir(parents=True, exist_ok=True)
        master = case_dir / "master.svg"
        _write_if_changed(master, _svg(item))
        source_paths.append(str(master))
        (case_dir / "iconflow.toml").write_text(
            _config_text(item, "#FF766D", "#FFF4E8"), encoding="utf-8"
        )

    cached: dict[str, dict[str, object]] = {}
    checks_path = WORK_ROOT / "check-results.json"
    if checks_path.is_file():
        payload = json.loads(checks_path.read_text(encoding="utf-8"))
        cached = {str(entry["id"]): entry for entry in payload.get("results", [])}
    pending = []
    for source_path in source_paths:
        source = Path(source_path)
        entry = cached.get(source.parent.name)
        if entry and entry.get("source_sha256") == svg_sha256(source):
            check_results.append(entry)
        else:
            pending.append(source_path)
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        for slug, warnings in executor.map(_check_source, pending):
            entry = {
                "id": slug,
                "source_sha256": svg_sha256(SOURCE_ROOT / slug / "master.svg"),
                "warnings": warnings,
            }
            check_results.append(entry)
    check_results.sort(key=lambda entry: next(
        index for index, item in enumerate(ITEMS) if item["id"] == entry["id"]
    ))
    checks_path.write_text(
        json.dumps({"checked": len(check_results), "results": check_results}, indent=2) + "\n",
        encoding="utf-8",
    )
    failed_checks = [entry for entry in check_results if entry["warnings"]]
    if failed_checks:
        raise ValueError(f"Social Signals IconFlow check warnings: {failed_checks}")

    with Rasterizer() as rasterizer:
        for item in ITEMS:
            slug = str(item["id"])
            case_dir = SOURCE_ROOT / slug
            render_dir = case_dir / "renders"
            master = case_dir / "master.svg"
            svg_text = load_svg(master)
            for size in (16, 128):
                (render_dir / f"{size}.png").write_bytes(rasterizer.render(svg_text, size))
            sil = visual_silhouette((render_dir / "128.png").read_bytes())
            sil.save(render_dir / "silhouette-128.png", optimize=True)
    review_jobs = []
    for item in ITEMS:
        slug = str(item["id"])
        review_path = reviews / f"{slug}.png"
        master = SOURCE_ROOT / slug / "master.svg"
        if not review_path.is_file() or review_path.stat().st_mtime < master.stat().st_mtime:
            review_jobs.append((str(master), str(review_path)))
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        list(executor.map(_render_review, review_jobs))
    contact = _make_contact()
    print(f"social-signals staged: {len(ITEMS)} clean sources")
    print(f"contact: {contact}")


def _receipt(item: dict[str, object], decision: dict[str, object], source: Path) -> dict[str, object]:
    source_hash = svg_sha256(source)
    build = review_build_contract(
        theme_color="#FF766D", background_color="#FFF4E8", electron_radius=0,
        tray_template_mode="auto", color_scheme="light", tray_source_sha256=None,
    )
    contract = review_contract_digest(
        source_sha256=source_hash, project=str(item["title"]), targets=("web",), build=build,
    )
    return {
        "schema": 1, "source": "master.svg", "source_sha256": source_hash,
        "contract_sha256": contract, "project": item["title"], "user_job": item["job"],
        "essence": item["essence"], "personality": "independent, specific, crafted",
        "signature_device": item["signature"], "cliches": [item["cliche"]],
        "targets": ["web"], "build": build, "warnings": [], "scores": decision["scores"],
        "notes": decision["notes"], "status": "ready",
    }


def _record_case(item: dict[str, object], decision: dict[str, object]) -> str:
    slug = "social-signal-" + str(item["id"])
    path = CASEBOOK / f"{DATE}-{slug}.md"
    if not path.exists():
        path = new_case(
            CASEBOOK, slug, project=str(item["title"]), targets="web study",
            essence=str(item["essence"]), style_family=str(item["style"]),
            signature_device=str(item["signature"]), device_family="object-silhouette",
            device_detail=str(item["signature"]), concept_lens="clean-room-user-job",
            cliche_avoided=str(item["cliche"]), status="reviewed",
            scores_first=decision["first_scores"], scores_final=decision["scores"],
            iterations=int(decision["iterations"]),
            summary=(f"{item['title']} translates the generic job '{item['job']}' into an original "
                     f"{item['noun']} without vendor geometry or trade dress."),
            lessons=[f"At 16px, the {item['noun']} needs its structural {item['signature']} before material detail."],
            date=DATE,
        )
        content = path.read_text(encoding="utf-8").replace("- [ ] At 16px,", "- [x] At 16px,")
        path.write_text(content, encoding="utf-8")
    return path.name


def finalize() -> None:
    _validate_assignment()
    if not DECISIONS_PATH.is_file():
        raise ValueError(f"missing visually reviewed decisions: {DECISIONS_PATH}")
    decisions_raw = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    decisions = {entry["id"]: entry for entry in decisions_raw["cases"]}
    if set(decisions) != {str(item["id"]) for item in ITEMS}:
        raise ValueError("review decisions must cover exactly the 20 Social Signals")
    DEPLOY_ROOT.mkdir(parents=True, exist_ok=True)
    catalog: list[dict[str, object]] = []
    for number, item in enumerate(ITEMS, 1):
        slug = str(item["id"])
        decision = decisions[slug]
        scores = decision.get("scores", {})
        if set(scores) != set(AXES) or any(not isinstance(value, int) or value < 4 for value in scores.values()):
            raise ValueError(f"{slug}: every reviewed axis must be an integer >= 4")
        source_dir = SOURCE_ROOT / slug
        source = source_dir / "master.svg"
        warnings = check(source)
        if warnings:
            raise ValueError(f"{slug}: IconFlow check warnings: {warnings}")
        if decision.get("source_sha256") != svg_sha256(source):
            raise ValueError(f"{slug}: review decision source hash drift")
        receipt = _receipt(item, decision, source)
        receipt_path = source_dir / "master-review.json"
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        config = load_config(source_dir / "iconflow.toml")
        validated = load_review_receipt(receipt_path, config)
        case_file = _record_case(item, decision)
        deploy_dir = DEPLOY_ROOT / slug
        deploy_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, deploy_dir / "master.svg")
        shutil.copy2(receipt_path, deploy_dir / "review.json")
        for asset in ("16.png", "128.png", "silhouette-128.png"):
            shutil.copy2(source_dir / "renders" / asset, deploy_dir / asset)
        shutil.copy2(CASEBOOK / case_file, deploy_dir / "case.md")
        catalog.append({
            "number": number, "id": slug, "title": item["title"], "category": slug,
            "user_job": item["job"], "essence": item["essence"], "noun": item["noun"],
            "style": item["style"], "cliche_avoided": item["cliche"],
            "signature_device": item["signature"], "concepts": item["concepts"],
            "source_sha256": validated.source_sha256,
            "contract_sha256": validated.contract_sha256, "scores": scores,
            "assets": {
                "svg": f"/assets/gallery/social-signals/{slug}/master.svg",
                "native": f"/assets/gallery/social-signals/{slug}/16.png",
                "proof": f"/assets/gallery/social-signals/{slug}/128.png",
                "silhouette": f"/assets/gallery/social-signals/{slug}/silhouette-128.png",
                "receipt": f"/assets/gallery/social-signals/{slug}/review.json",
                "case": f"/assets/gallery/social-signals/{slug}/case.md",
            },
        })
    record = {
        "schema_version": 1, "generated_on": DATE, "research_snapshot": DATE,
        "collection": "Social Signals", "status": "reviewed-practice-specimens",
        "affiliation": "Independent clean-room design study; no platform endorsement or affiliation.",
        "risk_note": "Visual distance reduces confusion risk but is not a legal clearance guarantee.",
        "seed": SEED, "generated_count": 20, "admitted_count": 20, "rejected_count": 0,
        "style_count": 20,
        "source_set_sha256": hashlib.sha256(
            ("\n".join(f"{entry['id']}:{entry['source_sha256']}" for entry in catalog) + "\n").encode()
        ).hexdigest(),
        "cases": catalog, "rejected": [],
    }
    text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(text, encoding="utf-8")
    (DEPLOY_ROOT / "catalog.json").write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode()).hexdigest()
    print(f"social-signals finalized: 20 reviewed cases, catalog sha256={digest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", action="store_true", help="Generate finalists, sources, renders, and review sheets")
    parser.add_argument("--finalize", action="store_true", help="Require visual decisions and publish source-bound evidence")
    args = parser.parse_args()
    if args.stage == args.finalize:
        parser.error("choose exactly one of --stage or --finalize")
    stage() if args.stage else finalize()


if __name__ == "__main__":
    main()
