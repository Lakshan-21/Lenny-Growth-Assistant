"""Sanitized HTML derivation from `content_markdown` (PRD §6.6 acceptance
criteria: "HTML rendering is sanitized to prevent injection of unsafe
markup").
"""

import markdown
import nh3

# fenced_code/tables/sane_lists: standard GitHub-flavored-Markdown-ish
# extensions so generated content (code blocks, tables) renders correctly.
# nl2br: artifact content_markdown is model-generated prose, not
# hand-authored Markdown with deliberate blank-line paragraph breaks -- a
# single newline should still visually break the line.
_MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "nl2br", "sane_lists"]

# Explicit allowlist rather than nh3's bare defaults: still permissive
# enough for normal Markdown output (headings, lists, tables, code,
# emphasis, links), but link targets are restricted to http(s)/mailto so a
# pasted `javascript:`/`data:` URL can never survive sanitization even if a
# future nh3 default ever changed. This is the actual security boundary of
# this module, not the Markdown conversion step.
_ALLOWED_TAGS = {
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "s", "del", "code", "pre", "blockquote",
    "ul", "ol", "li",
    "a",
    "table", "thead", "tbody", "tr", "th", "td",
}
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
}
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def render_html(*, content_markdown: str) -> str:
    """Convert `content_markdown` to HTML, then sanitize.

    Two distinct stages, deliberately in this order:

    1. `markdown.markdown(...)` — Markdown source -> raw HTML. The
       `markdown` library passes inline HTML in the source through
       untouched by default (that's a Markdown *feature*, not a bug) — so
       raw output must never be treated as safe on its own. An
       artifact's `content_markdown` could contain a pasted `<script>`
       tag (from a QA/Research answer echoing something a user typed, or
       a future artifact-editing feature) and this stage would preserve
       it verbatim.
    2. `nh3.clean(...)` — the actual security boundary. Allowlist-based
       (Mozilla's `ammonia`, via Rust bindings): unknown tags/attributes
       are stripped, not merely escaped. This removes `<script>`/`<style>`
       entirely, strips event-handler attributes (`onclick`, `onerror`,
       ...), and strips `javascript:`/`data:` URLs from `href` — the
       concrete script-injection vectors this function must prevent.
    """

    raw_html = markdown.markdown(content_markdown, extensions=_MARKDOWN_EXTENSIONS)
    return nh3.clean(
        raw_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )
