# IconFlow launch site

Static, dependency-free promotional site for IconFlow. The product name is
`IconFlow`; the canonical host is `ai-iconflow.com`, served by the `iconflow`
Cloudflare Pages project.

Exactly one host serves content. Every other host the site answers on issues a
permanent, path- and query-preserving redirect to the apex:

| Host | Project | Behavior |
|---|---|---|
| `ai-iconflow.com` | `iconflow` | serves the site |
| `iconflow.pages.dev` | `iconflow` | 301 via `functions/_middleware.js` |
| `www.ai-iconflow.com` | `ai-iconflow` | 301 via `_redirects` |
| `ai-iconflow.pages.dev` | `ai-iconflow` | 301 via `_redirects` |
| `<hash>.iconflow.pages.dev` | `iconflow` | serves, so previews stay testable |

`iconflow.pages.dev` cannot be redirected by `_redirects`: Cloudflare Pages does
not support domain-level redirects there, and a project cannot host-match its
own default host. Hence the middleware. `rel=canonical` alone was not enough —
it advises crawlers, but every internal link is root-relative, so a visitor who
landed on the old host stayed on it for the whole session.

The site deliberately uses repository-authored, reviewed assets only. The
technique SVGs are labeled as scaffolds rather than finished identities.

The dedicated `/getting-started/` route is the canonical public onboarding
surface. It separates agent-assisted and direct CLI use, provides copyable
Windows and POSIX setup paths, and keeps current product limits beside the
commands they qualify.

## Preview

Serve `website/` with any static server. Do not open `index.html` directly if
you want root-relative assets to resolve.

## Deploy

Use the script. It pins each directory to its own project and verifies the host
contract afterwards:

```powershell
pwsh scripts/deploy-site.ps1
```

If you deploy by hand, the `--cwd website` is **not optional**:

```powershell
wrangler pages deploy . --cwd website --project-name iconflow --branch main
wrangler pages deploy website-redirect --project-name ai-iconflow --branch main
```

Pages resolves `functions/` relative to Wrangler's working directory, not to the
asset directory. Deploying `website` from the repository root looks like a
success — it prints no error — but silently ships **no** Functions bundle, and
`iconflow.pages.dev` starts serving content again instead of redirecting. A
correct deploy prints `Compiled Worker successfully` and `Uploading Functions
bundle`; if those two lines are absent, the deploy is wrong.

Never deploy `website-redirect/` to the `iconflow` project. Its catch-all would
then be served from the apex, which would redirect `ai-iconflow.com` to itself
and take the site down with `ERR_TOO_MANY_REDIRECTS`.
