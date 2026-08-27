<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com -->
# Project state

> **Generated file. Do not edit.** Regenerate with
> `python scripts/state.py --write`. Every line below was observed, not
> remembered — which is the whole point, because the checklist this
> replaces spent three days insisting the PyPI name was still free.

Observed 2026-08-27 08:26 UTC.

`10 pass · 4 fail · 2 open gates · 0 unknown`

An **open gate** is a decision waiting on a person, not a defect, and
never fails this report. **Unknown** means a probe could not run: it is
deliberately not a pass, because a tick that means "I could not check"
is worse than no tick at all.

## Generated artifacts

| | Check | Detail |
|---|---|---|
| `PASS` | Five-language site is current | five-language build byte-identical to a fresh render |
| `PASS` | Living archive is current | 137 directions, catalog and page agree |
| `PASS` | Icon-size reference is current | icon-size tables match iconflow/build.py |
| `PASS` | Tray-icon reference is current | tray guide and five evidence PNGs match assemble.to_template |

## Deployed site

| | Check | Detail |
|---|---|---|
| `PASS` | Live site serves current /robots.txt | byte-identical to the checkout |
| `FAIL` | Live site serves current /llms.txt | deployed copy differs (repo 05a4356e7057, live 55d977fd6778) — redeploy |
| `FAIL` | Live site serves current /sitemap.xml | deployed copy differs (repo cf9a7fb8a748, live a076c7a22180) — redeploy |
| `FAIL` | Live /reference/icon-sizes/ is served unmodified | the edge injects a Cloudflare Web Analytics beacon. This site's CSP is script-src 'self', so every visitor's browser blocks it and logs a violation: the analytics collect nothing and the console is never clean. Turn off automatic injection in the Cloudflare dashboard (Web Analytics), or accept a third-party script on a site that advertises local-first. |
| `FAIL` | Live site serves current /reference/tray-icons/ | HTTP 404 — the sitemap advertises this route |

## Distribution

| | Check | Detail |
|---|---|---|
| `PASS` | PyPI carries this version | checkout is 0.5.0; PyPI latest is 0.5.0 (published) |
| `PASS` | Release attestations resolve | signed provenance for 2 artifacts |

## Repository

| | Check | Detail |
|---|---|---|
| `PASS` | Repository is public | visibility public; 1 star, 0 forks |
| `PASS` | Discovery topics are set | 20 of GitHub's 20 topic slots used |
| `OPEN` | Repository social preview is uploaded | still GitHub's generated card — Settings → General → Social preview, upload docs/assets/social-preview.png |
| `OPEN` | Discussions decision | not enabled — gh repo edit snowyukitty/ai-iconflow --enable-discussions |
| `PASS` | CI is green on main | latest main run: success (dc4485a) |

## Waiting on a person

No probe can settle these, and inventing one that pretends otherwise
would be the same mistake in a new costume.

- **Owner reads `LICENSES.md` end to end and confirms the tier boundaries.** A person has to agree with the boundaries; no request can observe that.
- **Owner enables a CLA signature check on pull requests.** The app is installed on an account, not recorded in the repository. Until then, check the signature line by hand on every outside PR.
- **Owner decides whether to register the IconFlow word mark.** `TRADEMARKS.md` asserts common-law rights, which are real but weaker and jurisdiction-dependent.
- **Owner verifies the site in Google Search Console and Bing Webmaster Tools.** Verification lives in those consoles. Without it, `docs/SEO.md`'s page queue is guesswork rather than demand.
- **Owner settles whether `/how-icons-are-made/` stays closed to training crawlers.** It is the most citable page on the site and currently blocked. That is a licensing decision, not an SEO one, and it should be decided rather than inherited.
- **Release tags are signed.** Signing is a local key policy; a tag's absence of a signature is observable, but the decision to adopt one is not.

---

Related: [`LAUNCH_READINESS.md`](LAUNCH_READINESS.md) for how the launch
was reached, [`SEO.md`](SEO.md) for what the open gates cost, and
[`RELEASING.md`](RELEASING.md) for the steps that change these answers.
