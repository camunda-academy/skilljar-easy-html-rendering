#!/usr/bin/env python3
"""Convert Hugo-style exercise Markdown into standalone HTML pages.

content/<slug>[.<lang>].md  ->  site/<slug>.html   (+ site/index.html)

Handles:
  * YAML-ish front matter (only `title` is used)
  * {{< snippet Name >}} ... {{< /snippet >}} shortcodes -> collapsed <details>
  * plain Markdown (lists, fenced code, tables, inline code)
"""
import html
import re
import shutil
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
SITE = ROOT / "site"
TEMPLATE = (ROOT / "template.html").read_text(encoding="utf-8")

FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SNIPPET = re.compile(
    r"\{\{<\s*snippet\s+(?P<name>[^\s>]+)\s*>\}\}(?P<body>.*?)\{\{<\s*/snippet\s*>\}\}",
    re.DOTALL,
)
ANSWER = re.compile(r"\{\{<\s*answer\s*>\}\}(?P<body>.*?)\{\{<\s*/answer\s*>\}\}", re.DOTALL)
FENCE = re.compile(r"\A\s*```[\w-]*\n(.*?)\n```\s*\Z", re.DOTALL)


def parse_front_matter(text):
    m = FRONT_MATTER.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and not line.startswith((" ", "\t")) and v.strip():
            meta[k.strip()] = v.strip().strip("'\"")
    return meta, text[m.end():]


def reindent(code):
    """Re-indent brace-based code whose indentation was lost in the source."""
    lines = [l.rstrip() for l in code.strip("\n").splitlines()]
    if any(l[:1] in (" ", "\t") for l in lines):
        return "\n".join(lines)  # already indented, leave as is
    out, depth = [], 0
    for line in lines:
        s = line.strip()
        if not s:
            out.append("")
            continue
        net = s.count("{") - s.count("}")
        lead_close = len(s) - len(s.lstrip("}"))
        level = max(depth - lead_close, 0)
        # annotations / javadoc continuation stay at the current level
        out.append("    " * level + s)
        depth = max(depth + net, 0)
    return "\n".join(out)


def snippet_html(name, body, lang):
    m = FENCE.match(body)
    code = m.group(1) if m else body
    code = reindent(code)
    label = html.escape(re.sub(r"[-_]", " ", name))
    return (
        f'<details class="snippet"><summary>{label}</summary>'
        f'<pre><code class="language-{lang}">{html.escape(code)}</code></pre>'
        f"</details>"
    )


def convert(path):
    stem_parts = path.name[: -len(".md")].split(".")
    slug = stem_parts[0]
    lang = stem_parts[1] if len(stem_parts) > 1 else "text"

    meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
    title = meta.get("title", slug)

    # Swap snippets for placeholders so Markdown cannot mangle them.
    blocks = []

    def stash(m):
        blocks.append(snippet_html(m.group("name"), m.group("body"), lang))
        return f"\n\nSNIPPETPLACEHOLDER{len(blocks) - 1}END\n\n"

    def stash_answer(m):
        inner = markdown.markdown(m.group("body").strip(), extensions=["sane_lists"])
        blocks.append(f'<details class="answer"><summary>Show answer</summary>{inner}</details>')
        return f"\n\nSNIPPETPLACEHOLDER{len(blocks) - 1}END\n\n"

    body = SNIPPET.sub(stash, body)
    body = ANSWER.sub(stash_answer, body)

    rendered = markdown.markdown(
        body, extensions=["fenced_code", "tables", "sane_lists"]
    )
    for i, block in enumerate(blocks):
        rendered = rendered.replace(f"<p>SNIPPETPLACEHOLDER{i}END</p>", block)

    banner = ""  # a leading image becomes a full-width banner above the title
    m = re.match(r"\s*(<p>\s*<img [^>]*>\s*</p>)", rendered)
    if m:
        banner = f'<div class="banner">{m.group(1)}</div>\n'
        rendered = rendered[m.end():]

    page = (
        TEMPLATE.replace("{{title}}", html.escape(title))
        .replace("{{body}}", f"{banner}<h1>{html.escape(title)}</h1>\n{rendered}")
    )
    if path.parent == CONTENT:  # flat: content/<slug>.md -> site/<slug>.html
        href, target = f"{slug}.html", SITE / f"{slug}.html"
    else:  # folder: content/<slug>/<slug>.md -> site/<slug>/index.html (+ assets)
        shutil.copytree(path.parent, SITE / slug, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.md"))
        href, target = f"{slug}/", SITE / slug / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    return href, title


def main():
    files = sorted(CONTENT.glob("*.md")) + sorted(CONTENT.glob("*/*.md"))
    if not files:
        sys.exit("no markdown files found in content/")
    pages = [convert(f) for f in files]
    links = "\n".join(f'<li><a href="{s}">{html.escape(t)}</a></li>' for s, t in pages)
    index = (
        TEMPLATE.replace("{{title}}", "Exercises")
        .replace("{{body}}", f"<h1>Exercises</h1><ul>{links}</ul>")
    )
    (SITE / "index.html").write_text(index, encoding="utf-8")
    print(f"built {len(pages)} page(s) into {SITE}")


if __name__ == "__main__":
    main()
