<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license.
     Applying the methods it describes requires nothing: icons you design
     with IconFlow are entirely yours. See LICENSES.md section 1. -->
# Milestone — Discovery Loop: Problem → Proof → Install

Decided 2026-08-27 from the post-v0.5 adoption evidence. The package, demo,
review gate, multilingual site, gallery, and release path already exist. The
weak link is discovery: someone who does not know the IconFlow name needs to
meet the project while solving a concrete icon problem.

## Product decision

Build narrow reference verticals only when all four conditions hold:

1. the query describes a real failure, not a category page invented for SEO;
2. IconFlow has a distinctive mechanism that resolves it;
3. the answer and visual proof can be generated from the mechanism itself; and
4. the page leads to a reproducible local success, not a hosted upload funnel.

This changes the growth loop from **brand page → explanation → hope** to
**problem → exact answer → visible proof → install**. It also extends
IconFlow's product principle to its own publishing system: a claim that can
drift must have a source binding and a failing check.

## First complete vertical: macOS tray icons

`/reference/tray-icons/` owns the black-square failure because that intent is
different from a general icon-size lookup. It ships as one coherent vertical:

- the failed full-card `alpha` conversion, the `auto` recovery, and the
  dedicated `tray.svg` result, generated from real IconFlow outputs;
- the exact 16px / 32px retina filenames read from the real target builder;
- the `auto`, `alpha`, and `contrast` behaviours plus the linked-source audit;
- Apple and Electron primary-source links, accessibility guidance, and FAQ;
- `TechArticle`, `FAQPage`, and `BreadcrumbList` structured data;
- a dedicated 1200×630 social card rendered from the same evidence;
- sitemap, cache, `llms.txt`, README, gallery, and icon-size-reference links;
  and
- offline project-state verification for the page and all five evidence PNGs.

## Acceptance contract

- `scripts/build_tray_reference.py --check` is byte-identical for the page and
  all evidence assets.
- The preferred evidence PNG equals the tray template the brand build ships.
- No literal retina `@` survives in raw page HTML outside JSON-LD, preventing
  CDN email obfuscation from corrupting a filename.
- Desktop and mobile browser renders make the failure and fix legible without
  JavaScript.
- Website, state, and full repository tests pass before publication.
- The deployed route is compared with the checkout by `scripts/state.py`.

## Deliberate non-goals

No thin route per platform, competitor-comparison pages, invented testimonials,
AI-generated product UI, hosted icon upload, telemetry added against the
local-first promise, or package-version bump merely to announce a web page.

## Next decision

`/reference/16px/` is the next hypothesis, not an automatic task. Promote it
only when Search Console impressions, external issues, or repeated user
language confirm the need. The reference generator, social renderer, site
contract tests, and self-audit now form the reusable system for that next
vertical.

Owner-controlled visibility gates remain separate: GitHub social-preview
upload, Discussions, Search Console/Bing verification, and the Cloudflare Web
Analytics/CSP decision. None is silently changed by this milestone.
