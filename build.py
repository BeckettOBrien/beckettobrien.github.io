#!/usr/bin/env python3
"""
Builds the site from ./content into ./dist.

    python3 build.py

No dependencies. Python 3.8+.

Layout it expects:

    content/profile.md              name, links, intro
    content/tools.md                "## Group" headings, one list per group
    content/education.md            front matter + prose
    content/projects/NN-slug/
        index.md                    front matter + description
        anything-else.png           copied to dist/assets/slug/ and linked

Projects are ordered by folder name, so the NN- prefixes control the page
order. Leave gaps (10, 20, 30) so you can insert without renaming.
"""

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
TEMPLATES = ROOT / "templates"
DIST = ROOT / "dist"

TEXT_SUFFIXES = {".md", ".markdown"}
SKIP_NAMES = {".DS_Store", "Thumbs.db"}


# ----------------------------------------------------------------------
# front matter
# ----------------------------------------------------------------------

def parse_front_matter(text):
    """Return (dict, body). Supports `key: value`, block lists, and [a, b]."""
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text

    end = re.search(r"^---\s*$", text[3:], re.M)
    if not end:
        return {}, text
    raw = text[3 : 3 + end.start()]
    body = text[3 + end.end() :].lstrip("\n")

    data = {}
    key = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s+-\s+", line) and key:
            data[key].append(_scalar(line.split("-", 1)[1].strip()))
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            data[key] = []
        elif val.startswith("[") and val.endswith("]"):
            data[key] = [_scalar(p.strip()) for p in val[1:-1].split(",") if p.strip()]
            key = None
        else:
            data[key] = _scalar(val)
            key = None
    return data, body


def _scalar(v):
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d*\.\d+", v):
        return float(v)
    return v


def as_list(v):
    if v is None or v == "":
        return []
    return v if isinstance(v, list) else [v]


def split_pipe(s, n):
    parts = [_scalar(p.strip()) if p.strip() else "" for p in str(s).split("|")]
    parts = [str(p) for p in parts]
    parts += [""] * (n - len(parts))
    return parts[:n]


# ----------------------------------------------------------------------
# markdown -> html  (the subset a project description actually needs)
# ----------------------------------------------------------------------

def inline(text, assets=""):
    out = []
    i = 0
    # protect code spans first
    parts = re.split(r"(`[^`]+`)", text)
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append("<code>" + html.escape(part[1:-1]) + "</code>")
            continue
        s = html.escape(part, quote=False)
        s = re.sub(
            r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)",
            lambda m: '<img src="%s" alt="%s"%s loading="lazy">'
            % (
                html.escape(resolve(m.group(2), assets), quote=True),
                html.escape(m.group(1), quote=True),
                ' title="%s"' % html.escape(m.group(3), quote=True) if m.group(3) else "",
            ),
            s,
        )
        s = re.sub(
            r"\[([^\]]+)\]\(([^)\s]+)\)",
            lambda m: '<a href="%s"%s>%s</a>'
            % (
                html.escape(resolve(m.group(2), assets), quote=True),
                ' target="_blank" rel="noopener"' if m.group(2).startswith("http") else "",
                m.group(1),
            ),
            s,
        )
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", s)
        s = s.replace(" -- ", " &ndash; ")
        out.append(s)
    return "".join(out)


def resolve(src, assets):
    if re.match(r"^(https?:|mailto:|#|/)", src):
        return src
    return assets + src.lstrip("./")


def markdown(text, assets=""):
    """Returns a list of block strings, so callers can peel off the first paragraph."""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks, i = [], 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.startswith("```"):
            lang = line[3:].strip()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            cls = ' class="language-%s"' % html.escape(lang, quote=True) if lang else ""
            blocks.append("<pre><code%s>%s</code></pre>" % (cls, html.escape("\n".join(buf))))
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = min(len(m.group(1)) + 2, 6)  # h1 in a file becomes h3 on the page
            blocks.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2).strip(), assets), lvl))
            i += 1
            continue

        if re.match(r"^\s*([-*_])\s*\1\s*\1[\s\-*_]*$", line):
            blocks.append("<hr>")
            i += 1
            continue

        if line.lstrip().startswith(">"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip())
                i += 1
            blocks.append("<blockquote>%s</blockquote>" % inline(" ".join(buf), assets))
            continue

        m = re.match(r"^\s*([-*+]|\d+[.)])\s+", line)
        if m:
            ordered = not m.group(1) in "-*+"
            items, cur = [], None
            while i < len(lines):
                mm = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$", lines[i])
                if mm:
                    if cur is not None:
                        items.append(cur)
                    cur = mm.group(1).strip()
                    i += 1
                elif lines[i].strip() and lines[i].startswith((" ", "\t")) and cur is not None:
                    cur += " " + lines[i].strip()
                    i += 1
                else:
                    break
            if cur is not None:
                items.append(cur)
            tag = "ol" if ordered else "ul"
            blocks.append(
                "<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(x, assets) for x in items), tag)
            )
            continue

        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^\s*(#{1,6}\s|```|>|[-*+]\s|\d+[.)]\s)", lines[i]
        ):
            buf.append(lines[i].strip())
            i += 1
        para = " ".join(buf)
        if re.fullmatch(r"<img [^>]+>", inline(para, assets).strip()):
            blocks.append('<figure>%s</figure>' % inline(para, assets))
        else:
            blocks.append("<p>%s</p>" % inline(para, assets))

    return blocks


# ----------------------------------------------------------------------
# floorplan: squarified treemap over a 100 x 100 core
# ----------------------------------------------------------------------

def treemap(weights, W=100.0, H=100.0):
    total = sum(max(0.01, w) for w in weights) or 1.0
    nodes = [{"i": i, "area": max(0.01, w) / total * W * H} for i, w in enumerate(weights)]
    rect = {"x": 0.0, "y": 0.0, "w": W, "h": H}
    out = []

    def worst(row, length):
        L = max(length, 1e-6)
        s = sum(n["area"] for n in row) or 1e-6
        mx = max(n["area"] for n in row)
        mn = max(min(n["area"] for n in row), 1e-6)
        return max((L * L * mx) / (s * s), (s * s) / (L * L * mn))

    def place(row):
        s = sum(n["area"] for n in row)
        if rect["w"] >= rect["h"]:
            rw = min(s / max(rect["h"], 1e-6), rect["w"])
            cy = rect["y"]
            for n in row:
                nh = n["area"] / max(rw, 1e-6)
                out.append((n["i"], rect["x"], cy, rw, nh))
                cy += nh
            rect["x"] += rw
            rect["w"] -= rw
        else:
            rh = min(s / max(rect["w"], 1e-6), rect["h"])
            cx = rect["x"]
            for n in row:
                nw = n["area"] / max(rh, 1e-6)
                out.append((n["i"], cx, rect["y"], nw, rh))
                cx += nw
            rect["y"] += rh
            rect["h"] -= rh

    queue, row, guard = list(nodes), [], 0
    while queue and guard < 5000:
        guard += 1
        length = rect["h"] if rect["w"] >= rect["h"] else rect["w"]
        nxt = queue[0]
        if not row or worst(row + [nxt], length) <= worst(row, length):
            row.append(queue.pop(0))
        else:
            place(row)
            row = []
        if rect["w"] <= 1e-4 or rect["h"] <= 1e-4:
            break
    if row:
        place(row)
    for n in queue:
        out.append((n["i"], rect["x"], rect["y"], rect["w"], rect["h"]))
    return {i: (x, y, w, h) for i, x, y, w, h in out}


# ----------------------------------------------------------------------
# loading
# ----------------------------------------------------------------------

def read(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_profile():
    fm, body = parse_front_matter(read(CONTENT / "profile.md"))
    fm["_bio"] = markdown(body)
    fm["_links"] = [
        {"key": k, "label": l, "url": u}
        for k, l, u in (split_pipe(x, 3) for x in as_list(fm.get("links")))
        if u
    ]
    return fm


def load_tools():
    groups, cur = [], None
    for line in read(CONTENT / "tools.md").splitlines():
        m = re.match(r"^#{1,6}\s+(.*)$", line)
        if m:
            cur = {"group": m.group(1).strip(), "items": []}
            groups.append(cur)
            continue
        m = re.match(r"^\s*[-*+]\s+(.*)$", line)
        if m and cur:
            cur["items"].append(m.group(1).strip())
    return [g for g in groups if g["items"]]


def load_education():
    fm, body = parse_front_matter(read(CONTENT / "education.md"))
    fm["_body"] = markdown(body)
    return fm


def load_projects():
    base = CONTENT / "projects"
    if not base.is_dir():
        return []
    out = []
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        index = d / "index.md"
        if not index.exists():
            print("  ! %s has no index.md, skipping" % d.name, file=sys.stderr)
            continue
        fm, body = parse_front_matter(read(index))
        if fm.get("draft"):
            print("  - %s (draft, skipped)" % d.name)
            continue

        slug = re.sub(r"^\d+[-_]", "", d.name)
        assets = "assets/%s/" % slug
        blocks = markdown(body, assets)

        fm.update(
            {
                "_dir": d,
                "_slug": slug,
                "_assets": assets,
                "_summary": blocks[0] if blocks and blocks[0].startswith("<p>") else "",
                "_body": blocks[1:] if blocks and blocks[0].startswith("<p>") else blocks,
                "_tags": as_list(fm.get("tags")),
                "_links": [
                    {"label": l, "url": resolve(u, assets)}
                    for l, u in (split_pipe(x, 2) for x in as_list(fm.get("links")))
                    if u
                ],
                "_order": fm.get("order", d.name),
            }
        )
        out.append(fm)
    out.sort(key=lambda p: (str(p["_order"]).zfill(8), p["_slug"]))
    return out


def copy_assets(projects):
    dest_root = DIST / "assets"
    n = 0
    for p in projects:
        files = [
            f
            for f in p["_dir"].iterdir()
            if f.is_file() and f.suffix.lower() not in TEXT_SUFFIXES and f.name not in SKIP_NAMES
        ]
        if not files:
            continue
        dest = dest_root / p["_slug"]
        dest.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, dest / f.name)
            n += 1
    return n


# ----------------------------------------------------------------------
# rendering
# ----------------------------------------------------------------------

E = lambda s: html.escape(str(s if s is not None else ""), quote=True)

STATUS_WORD = {"active": "active", "shipped": "finished", "planned": "in progress"}


def render_floorplan(projects):
    if not projects:
        return '<p class="die-empty">Add a folder under <code>content/projects/</code>.</p>'
    order = sorted(range(len(projects)), key=lambda i: -float(projects[i].get("weight", 2)))
    cells = treemap([float(projects[i].get("weight", 2)) for i in order])
    gut = 0.9
    parts = []
    for n, (pos, idx) in enumerate(zip(range(len(order)), order)):
        x, y, w, h = cells[pos]
        p = projects[idx]
        cls = ["blk"]
        if w < 22 or h < 16:
            cls.append("sm")
        if w < 14 and h > w * 1.4:
            cls.append("narrow")
        parts.append(
            '<a class="%s" href="#p-%s" data-status="%s" style="left:%.3f%%;top:%.3f%%;'
            'width:%.3f%%;height:%.3f%%;--d:%dms" title="%s">'
            '<span class="tag">%s</span><span class="nm">%s</span></a>'
            % (
                " ".join(cls),
                E(p["_slug"]),
                E(p.get("status", "active")),
                x + gut / 2,
                y + gut / 2,
                max(0.0, w - gut),
                max(0.0, h - gut),
                n * 45,
                E(p.get("name", "")),
                E(p.get("short") or p.get("name", "")[:7]),
                E(p.get("name", "")),
            )
        )
    return "".join(parts)


def render_projects(projects):
    out = []
    for p in projects:
        meta = []
        if p.get("org"):
            meta.append('<p class="who">%s</p>' % E(p["org"]))
        if p.get("role"):
            meta.append('<p class="who muted">%s</p>' % E(p["role"]))
        if p.get("period"):
            meta.append('<p class="when">%s</p>' % E(p["period"]))
        st = p.get("status", "")
        if STATUS_WORD.get(st):
            meta.append(
                '<span class="status" data-s="%s"><b></b>%s</span>' % (E(st), STATUS_WORD[st])
            )

        cover = ""
        if p.get("cover"):
            cover = '<figure class="cover"><img src="%s%s" alt="%s" loading="lazy"></figure>' % (
                E(p["_assets"]),
                E(p["cover"]),
                E(p.get("cover_alt") or p.get("name", "")),
            )

        tags = (
            '<div class="tags">%s</div>' % "".join("<span>%s</span>" % E(t) for t in p["_tags"])
            if p["_tags"]
            else ""
        )
        links = (
            '<div class="plinks">%s</div>'
            % "".join(
                '<a href="%s"%s>%s</a>'
                % (E(l["url"]), ' target="_blank" rel="noopener"' if l["url"].startswith("http") else "", E(l["label"]))
                for l in p["_links"]
            )
            if p["_links"]
            else ""
        )
        note = '<p class="note">%s</p>' % E(p["note"]) if p.get("note") else ""
        summary = p["_summary"].replace("<p>", '<p class="sum">', 1) if p["_summary"] else ""

        out.append(
            '<article class="proj">'
            '<div class="proj-meta">%s</div>'
            '<div class="proj-body"><h3 id="p-%s">%s</h3>%s%s%s%s%s%s</div>'
            "</article>"
            % (
                "".join(meta),
                E(p["_slug"]),
                E(p.get("name", "Untitled")),
                summary,
                cover,
                "".join(p["_body"]),
                note,
                tags,
                links,
            )
        )
    return "".join(out)


def render_tools(groups):
    if not groups:
        return ""
    inner = "".join(
        '<div class="tgroup"><h4>%s</h4><ul>%s</ul></div>'
        % (E(g["group"]), "".join("<li>%s</li>" % E(i) for i in g["items"]))
        for g in groups
    )
    return (
        '<section class="sec" id="tools"><div class="wrap">'
        '<div class="sec-head"><h2>Tools</h2></div>'
        '<div class="tools">%s</div></div></section>' % inner
    )


def render_education(e):
    if not e.get("school"):
        return ""
    left = E(e.get("period", ""))
    if e.get("where"):
        left += ("<br>" if left else "") + E(e["where"])
    return (
        '<section class="sec" id="education"><div class="wrap">'
        '<div class="sec-head"><h2>Education</h2></div>'
        '<div class="edu"><div class="when">%s</div>'
        "<div><h3>%s</h3>%s</div></div></div></section>"
        % (left, E(e["school"]), "".join(e["_body"]))
    )


def render_links(links, cls="contact"):
    return '<div class="%s">%s</div>' % (
        cls,
        "".join(
            '<a href="%s"%s><i>%s</i>%s</a>'
            % (
                E(l["url"]),
                ' target="_blank" rel="noopener"' if l["url"].startswith("http") else "",
                E(l["key"] or "\u2192"),
                E(l["label"]),
            )
            for l in links
        ),
    )


def build():
    profile = load_profile()
    projects = load_projects()
    tools = load_tools()
    education = load_education()

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    n_assets = copy_assets(projects)
    for f in STATIC.glob("*"):
        if f.is_file():
            shutil.copy2(f, DIST / f.name)

    count = len(projects)
    ctx = {
        "{{TITLE}}": E(profile.get("name", "Portfolio")),
        "{{DESCRIPTION}}": E(profile.get("tagline", "")),
        "{{SIG}}": E(profile.get("sig", profile.get("name", ""))),
        "{{NAME}}": E(profile.get("name", "")),
        "{{TAGLINE}}": E(profile.get("tagline", "")),
        "{{BIO}}": "".join(profile["_bio"]),
        "{{CONTACT}}": render_links(profile["_links"]),
        "{{DIE_LABEL}}": E(profile.get("die_label", "floorplan")),
        "{{DIE_HINT}}": E(profile.get("die_hint", "click a block")) if projects else "",
        "{{FLOORPLAN}}": render_floorplan(projects),
        "{{COUNT}}": "%d %s" % (count, "entry" if count == 1 else "entries") if count else "",
        "{{PROJECTS}}": render_projects(projects),
        "{{TOOLS}}": render_tools(tools),
        "{{EDUCATION}}": render_education(education),
        "{{CONTACT_BLURB}}": E(profile.get("contact_blurb", "")),
        "{{CONTACT_2}}": render_links(profile["_links"]),
        "{{FOOTER}}": E(profile.get("footer", "")),
    }

    page = read(TEMPLATES / "base.html")
    for k, v in ctx.items():
        page = page.replace(k, v)

    leftover = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if leftover:
        print("  ! unreplaced placeholders: %s" % ", ".join(sorted(set(leftover))), file=sys.stderr)

    (DIST / "index.html").write_text(page, encoding="utf-8")

    print("built dist/")
    print("  %d project%s" % (count, "" if count == 1 else "s"))
    for p in projects:
        print("    %-12s w=%-4s %s" % (p["_slug"], p.get("weight", 2), p.get("name", "")))
    print("  %d asset file%s" % (n_assets, "" if n_assets == 1 else "s"))
    print("  %d KB" % ((DIST / "index.html").stat().st_size // 1024))


if __name__ == "__main__":
    build()
