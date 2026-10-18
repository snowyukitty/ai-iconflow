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

**The one step (preferred).** Cloudflare dashboard → **Workers & Pages** →
the `ai-iconflow` Pages project → **Metrics** → **Web Analytics** → disable.
If the site was instead added under **Analytics & Logs → Web Analytics**,
open it there and turn off automatic setup. Cloudflare adds or removes the
snippet at deployment, so redeploy afterwards (`scripts/deploy-site.ps1`).

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

GitHub has no API for the social preview image. **The one step:** GitHub →
`snowyukitty/ai-iconflow` → **Settings** → **General** → **Social preview** →
**Edit** → **Upload an image** → `docs/assets/social-preview.png`
(1280x640, already rendered by `scripts/render_social_preview.py`).

Once a wordmark is chosen, `iconflow brand build` writes a deterministic
`social/github-social-1280x640.png` from the approved mark and the outlined
wordmark (`docs/BRAND_KIT.md`); the current preview renders its text with
system fonts, so it differs slightly between machines.

**Proof.** `state.py`: `Repository social preview is uploaded` → PASS.

## 3. Decide on Discussions (OPEN)

**The one step, if yes:**

```powershell
gh repo edit snowyukitty/ai-iconflow --enable-discussions
```

Suggested categories, matching the contribution lanes in `CONTRIBUTING.md`:
*Show a case* (an icon made with IconFlow, with its sheet), *Q&A*, *Ideas*.
If no, record the decision in `docs/LAUNCH_READINESS.md` so `state.py` stops
asking; the gate is a question, not a defect.

**Proof.** `state.py`: `Discussions decision` → PASS.
