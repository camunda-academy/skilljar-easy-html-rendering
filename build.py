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
import textwrap
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
QUIZ = re.compile(r'\{\{<\s*quiz(?:\s+"(?P<title>[^"]*)")?\s*>\}\}(?P<body>.*?)\{\{<\s*/quiz\s*>\}\}', re.DOTALL)
QUIZ_OPTION = re.compile(r"^- \[( |x|X)\] ?(.*)$")
# Same syntax as the official converter: !!! type "Title" (always open), ??? (collapsed), ???+ (open).
ADMONITION = re.compile(
    r'^(?P<marker>!!!|\?\?\?\+?)[ \t]+(?P<type>\w+)(?:[ \t]+"(?P<title>[^"\n]*)")?[ \t]*\n'
    r"(?P<body>(?:(?:[ ]{4}|\t)[^\n]*(?:\n|\Z)|[ \t]*\n)+)",
    re.MULTILINE,
)
CALLOUT_TYPES = {"info", "note", "tip", "warning", "danger", "success"}
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


def inline_md(text):
    return re.sub(r"\A<p>|</p>\Z", "", markdown.markdown(text.strip()).strip())


def quiz_html(body, qid, title=None):
    """Single-choice quiz: question text, then `- [ ]` / `- [x]` options with indented feedback."""
    question, options = [], []
    for line in body.strip("\n").splitlines():
        m = QUIZ_OPTION.match(line)
        if m:
            options.append([m.group(1).lower() == "x", m.group(2), []])
        elif options:
            options[-1][2].append(line.strip())
        else:
            question.append(line)
    if len(options) < 2 or sum(o[0] for o in options) != 1:
        sys.exit(f"quiz #{qid}: needs 2+ options and exactly one [x]:\n{body.strip()[:80]}")
    items = "".join(
        f'<div class="quiz-opt" data-correct="{int(ok)}"><label>'
        f'<input type="radio" name="quiz{qid}"><span>{inline_md(answer)}</span></label>'
        f'<div class="quiz-fb" role="status" hidden>{markdown.markdown(chr(10).join(fb).strip(), extensions=["sane_lists"])}</div></div>'
        for ok, answer, fb in options
    )
    q = markdown.markdown("\n".join(question).strip(), extensions=["fenced_code", "sane_lists"])
    label = html.escape(title or "Challenge")
    return (
        f'<details class="quiz-box"><summary>{label}</summary>'
        f'<div class="quiz" role="group" aria-labelledby="quiz{qid}q"><div class="quiz-q" id="quiz{qid}q">{q}</div>{items}</div></details>'
    )


def admonition_html(m):
    kind = m.group("type").lower()
    kind = kind if kind in CALLOUT_TYPES else "note"
    title = m.group("title")
    title = kind.capitalize() if title is None else title
    inner = markdown.markdown(
        textwrap.dedent(m.group("body")).strip("\n"),
        extensions=["fenced_code", "tables", "sane_lists"],
    )
    label = html.escape(title)
    if m.group("marker") == "!!!":
        head = f'<div class="callout-title">{label}</div>' if title else ""
        return f'<div class="callout callout-{kind}">{head}<div class="callout-body">{inner}</div></div>'
    opened = " open" if m.group("marker").endswith("+") else ""
    return (
        f'<details class="callout callout-{kind}"{opened}><summary class="callout-title">{label or kind.capitalize()}'
        f'</summary><div class="callout-body">{inner}</div></details>'
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

    def stash_quiz(m):
        blocks.append(quiz_html(m.group("body"), len(blocks), m.group("title")))
        return f"\n\nSNIPPETPLACEHOLDER{len(blocks) - 1}END\n\n"

    def stash_admonition(m):
        blocks.append(admonition_html(m))
        return f"\n\nSNIPPETPLACEHOLDER{len(blocks) - 1}END\n\n"

    body = ADMONITION.sub(stash_admonition, body)
    body = SNIPPET.sub(stash, body)
    body = QUIZ.sub(stash_quiz, body)
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
