# Security policy

IconFlow treats SVG files and project configuration as untrusted input. The
renderer disables page JavaScript and service workers, blocks every external
request, freezes animation, validates SVG/XML structure and complexity, and
checks generated PNG dimensions before packaging. These controls are security
boundaries; changes to them require regression coverage.

## Supported versions

IconFlow has not published its first release. Security fixes currently target
the latest commit on `main`. After releases begin, only the latest released
minor version will receive security fixes unless a release note says otherwise.

## Report a vulnerability

Do not post exploit details, credentials, private paths, or sensitive SVGs in a
public issue.

**Use GitHub private vulnerability reporting**, enabled on this repository since
2026-08-22: open
<https://github.com/snowyukitty/ai-iconflow/security/advisories/new>. The report
is visible only to you and the maintainer, and it stays private until a fix is
published.

If that form is unavailable to you for any reason, open a minimal public issue
saying only that you need a private security contact — include no technical
details — and the maintainer will open a private advisory for you.

Useful private reports include the affected version or commit, a minimal
redacted reproduction, impact, and whether the issue involves network access,
file writes, review-receipt bypass, resource exhaustion, or secret exposure.

If a report contains a real credential, do not send the credential itself.
Send only a redacted fingerprint and where it was observed.

## Scope

Security-relevant areas include:

- SVG/XML parsing, browser isolation, external resources, scripts, and animation;
- source- and transform-bound review receipts;
- output path traversal, symlinks, junctions, and unsafe overwrite behavior;
- generated Windows shortcut scripts and Unicode path handling;
- package contents and release workflows.

Please distinguish a security boundary failure from an ordinary rendering bug.
Both are welcome, but a visual mismatch without data access, code execution, or
gate bypass can use the normal bug template.
