const CANONICAL_HOST = "ai-iconflow.com";

// Hosts that must never serve content, only move the visitor to the canonical
// origin. rel=canonical is a hint to crawlers; it does not relocate a person,
// and every internal link here is root-relative, so a visitor who lands on the
// legacy host would otherwise stay on it for the whole session.
//
// Deployment and branch aliases (<hash>.iconflow.pages.dev, main.iconflow.pages.dev)
// are deliberately excluded: they exist to be tested before promotion.
const LEGACY_HOSTS = new Set(["iconflow.pages.dev"]);

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (!LEGACY_HOSTS.has(url.hostname)) {
    return context.next();
  }
  url.protocol = "https:";
  url.hostname = CANONICAL_HOST;
  url.port = "";
  return Response.redirect(url.toString(), 301);
}
