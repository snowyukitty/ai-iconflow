# IconFlow launch site

Static, dependency-free promotional site for IconFlow. The product name is
`IconFlow`; the canonical host is `ai-iconflow.com`, served by the `iconflow`
Cloudflare Pages project. `iconflow.pages.dev` remains that project's Pages
default host. The `ai-iconflow` project is a redirect-only shell that serves
`www.ai-iconflow.com` and `ai-iconflow.pages.dev` as permanent 301s to the apex.

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

```powershell
wrangler pages deploy website --project-name iconflow --branch main
```

Cloudflare Pages reads `_headers` and `_redirects` from the uploaded directory.
Deploy `website-redirect/` to the `ai-iconflow` project after the canonical
site, so legacy links and `www` receive a permanent redirect.

```powershell
wrangler pages deploy website-redirect --project-name ai-iconflow --branch main
```
