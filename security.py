import re

import bleach
from markupsafe import Markup


ALLOWED_HTML_TAGS = (
    "a",
    "b",
    "blockquote",
    "br",
    "em",
    "h2",
    "h3",
    "h4",
    "i",
    "li",
    "ol",
    "p",
    "strong",
    "ul",
)

ALLOWED_HTML_ATTRIBUTES = {
    "a": ["href", "rel", "title"],
}

ALLOWED_HTML_PROTOCOLS = ("http", "https", "mailto")

TAG_LIKE_PATTERN = re.compile(r"<[A-Za-z!/][^>]*>")
DANGEROUS_BLOCK_PATTERN = re.compile(
    r"<(script|style|iframe|object|embed)[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)


def nl2br(value):
    raw = str(value or "")
    if not raw:
        return ""
    scrubbed = DANGEROUS_BLOCK_PATTERN.sub("", raw)
    cleaned = bleach.clean(
        scrubbed,
        tags=[],
        attributes={},
        strip=True,
        strip_comments=True,
    )
    return Markup("<br>\n".join(cleaned.splitlines()))


def sanitize_html(value):
    raw = str(value or "")
    if not raw:
        return ""

    scrubbed = DANGEROUS_BLOCK_PATTERN.sub("", raw)
    if not TAG_LIKE_PATTERN.search(scrubbed):
        return nl2br(scrubbed)

    cleaned = bleach.clean(
        scrubbed,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRIBUTES,
        protocols=ALLOWED_HTML_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
    return Markup(cleaned)


def register_template_security(app):
    app.add_template_filter(nl2br, "nl2br")
    app.add_template_filter(sanitize_html, "sanitize_html")


def build_content_security_policy():
    directives = {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        "style-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        "img-src": ["'self'", "data:", "https:"],
        "font-src": ["'self'", "data:", "https://cdnjs.cloudflare.com"],
        "connect-src": ["'self'"],
        "frame-src": ["'self'", "https://www.google.com", "https://maps.google.com"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'self'"],
        "upgrade-insecure-requests": [],
    }
    return "; ".join(
        f"{directive} {' '.join(values)}".strip()
        for directive, values in directives.items()
    )


def apply_security_headers(response):
    response.headers.setdefault("Content-Security-Policy", build_content_security_policy())
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return response
