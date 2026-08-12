# IconFlow launch site

Static, dependency-free promotional site for IconFlow. The product name is
`IconFlow`; the canonical Cloudflare Pages project and default host are
`iconflow` and `iconflow.pages.dev`. The older `ai-iconflow.pages.dev` project
is a compatibility redirect.

The site deliberately uses repository-authored, reviewed assets only. The
technique SVGs are labeled as scaffolds rather than finished identities.

## Preview

Serve `website/` with any static server. Do not open `index.html` directly if
you want root-relative assets to resolve.

## Deploy

```powershell
wrangler pages deploy website --project-name iconflow --branch main
```

Cloudflare Pages reads `_headers` and `_redirects` from the uploaded directory.
Deploy `website-redirect/` to the `ai-iconflow` project after the canonical
site, so legacy links receive a permanent redirect.

```powershell
wrangler pages deploy website-redirect --project-name ai-iconflow --branch main
```
