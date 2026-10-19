<!-- SPDX-License-Identifier: CC-BY-SA-4.0
     SPDX-FileCopyrightText: 2026 snowyukitty · https://ai-iconflow.com
     Reusing this prose requires attribution and the same license. -->
# Owner actions — the gates no commit can close

`python scripts/state.py` reports two FAILs and two OPEN gates that live
outside this repository: in the Cloudflare dashboard and in GitHub's
settings. Each is written here as one step, with the check that proves it is
done. Like `docs/STATE.md`, this file is about this repository and is not
packaged.

## 1. Stop the Cloudflare Web Analytics beacon (two FAILs)

**What is wrong.** Cloudflare injects
`static.cloudflareinsights.com/beacon.min.js` into every HTML page at the
edge. The site's CSP is `script-src 'self'`, so every visitor's browser blocks
it and logs a violation: the analytics collect nothing, and the two reference
pages `state.py` compares byte for byte are served modified.

**Done 2026-10-19.** The beacon was not the Pages project's setting (the
content project is `iconflow`, and its Web Analytics was already off): it
came from the account-level site **ai-iconflow.com** under **Analytics → Web
analytics → Manage site → Real User Measurements**, set to *Enable, excluding
visitor data in the EU*. It is now **Disable** (saved with **Update**, then
re-read after a reload). Redeploy afterwards (`scripts/deploy-site.ps1`) so
every page is served fresh. The API token this repository's deploys use has
no Web Analytics scope; the change was made in the signed-in dashboard.

**Proof.** `python scripts/state.py` shows `Live /reference/icon-sizes/ is
served unmodified` and `Live /reference/tray-icons/ ...` as PASS.

**Fallback, not taken by default.** Cloudflare documents that a response
carrying `Cache-Control: no-transform` is never injected — and also never
compressed by the edge. Adding it to the HTML routes in `website/_headers`
(and in the stanzas `scripts/build_i18n.py` generates) would close the FAILs
from the repository, at the price of uncompressed HTML. Choose it only if the
dashboard switch is unavailable.

**Or keep analytics.** If the analytics are wanted, the honest fix is the
opposite: add `https://static.cloudflareinsights.com` to `script-src` and
`https://cloudflareinsights.com` to `connect-src` in `website/_headers`, and
accept a third-party script on a site that advertises local-first. That is a
product decision; nothing in the repository makes it.

## 2. Upload the repository social preview (OPEN)

**Done 2026-10-19:** `docs/assets/github-social-preview.png`, the brand kit's
deterministic card (mark, outlined Inter wordmark and tagline), uploaded under
**Settings → General → Social preview → Edit → Upload an image**. GitHub has
no API for this. The image GitHub serves was downloaded back and compared:
identical pixels. To change it, rebuild the kit (`docs/BRAND_SYSTEM.md`) and
upload again.

**Proof.** `state.py`: `Repository social preview is uploaded` → PASS.

## 3. Decide on Discussions (OPEN)

**Done 2026-10-19: enabled** (`gh repo edit ... --enable-discussions`). The
default categories already carry the contribution lanes: *Show and tell* (an
icon made with IconFlow, with its sheet), *Q&A*, *Ideas*. A welcome post in
*Announcements* (discussion #1) routes each kind of post, sends bugs to
Issues and security reports to private reporting, and asks people to check a
review sheet for private names before posting it. The owner moderates.

**Proof.** `state.py`: `Discussions decision` → PASS.
