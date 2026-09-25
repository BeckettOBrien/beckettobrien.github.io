# becketto.dev

A portfolio site built from markdown. Everything on the page comes from files under
`content/`; `build.py` turns them into a static `dist/` you can host anywhere.

No dependencies, no package manager, no lockfile. Python 3.8+ and nothing else.

```
content/
  profile.md                 name, tagline, links, intro
  tools.md                   "## Group" headings, one list each
  education.md               front matter + prose
  projects/
    10-fpu/
      index.md               front matter + description
      diagram.png            copied to dist/assets/fpu/ and linked automatically
    20-rover/
      index.md
static/                      copied verbatim into dist/  (style.css, CNAME)
templates/base.html          the page shell
build.py                     the whole generator, ~450 lines
```

## Adding a project

Make a folder, write an `index.md`, push.

```sh
make new SLUG=ethernet-mac      # or just mkdir the folder yourself
```

```markdown
---
name: Pipelined Ethernet MAC
short: MAC
org: Personal project
period: Oct 2026 – Present
status: active
weight: 3
tags: [SystemVerilog, cocotb, FPGA]
links:
  - Repository | https://github.com/BeckettOBrien/ethernet-mac
  - Writeup | notes.pdf
cover: block-diagram.png
---

The first paragraph becomes the summary line under the heading.

- Everything after it renders as the body.
- Lists, headings, code fences, blockquotes, and images all work.

![Receive path](rx-path.png)
```

Drop `block-diagram.png`, `rx-path.png`, and `notes.pdf` in the same folder. The build
copies them to `dist/assets/ethernet-mac/` and rewrites every relative path to match, so
paths in markdown stay relative to the file you're editing. That applies to front-matter
links too, which is how `notes.pdf` above resolves.

### Front matter

| key | |
|---|---|
| `name` | heading in the Work list |
| `short` | label inside the floorplan block, ~7 characters |
| `weight` | relative block size in the floorplan, roughly 1–6 |
| `status` | `active`, `shipped`, or `planned` — sets colour and label |
| `org`, `role`, `period` | left column; any can be blank or omitted |
| `tags` | `[A, B, C]` or a block list |
| `links` | `Label \| url` per line; relative URLs resolve to the asset folder |
| `cover` | filename in the folder, shown above the body |
| `note` | small caveat line, e.g. why there's no public repo |
| `draft: true` | build skips it entirely |
| `order` | overrides the folder-name sort |

Ordering comes from the folder name, so `10-`, `20-`, `30-` prefixes control the page
order and leave gaps for inserting. The prefix is stripped from the URL fragment, so
`content/projects/20-rover/` anchors at `#p-rover`.

## The floorplan

The hero is a chip floorplan generated from the project list with a squarified treemap.
Block size comes from `weight`, colour from `status`, and each block links to its entry.
Blocks re-pack themselves on every build, so there's no layout to maintain — the only
knob is `weight`.

## Building

```sh
make build      # -> dist/
make serve      # build, then http://localhost:8000
make clean
```

Open `dist/index.html` through a server rather than as a `file://` path; it's a plain
static page either way, but relative asset paths behave better over http.

## Deploying

`.github/workflows/deploy.yml` builds on every push to `main` and publishes `dist/` to
GitHub Pages. Turn it on once under **Settings → Pages → Source → GitHub Actions**.
`static/CNAME` carries the custom domain through.

`dist/` is gitignored because CI builds it. If you'd rather host somewhere that serves a
committed folder, drop `dist/` from `.gitignore` and commit it.

Any other host works the same way: run `python3 build.py` and upload `dist/`.

## Design

Type is IBM Plex Sans and IBM Plex Mono, loaded from Google Fonts — the only external
request the page makes. To drop that too, self-host the woff2 files and swap the `<link>`
in `templates/base.html`.

Colours are custom properties at the top of `static/style.css`. Light and dark follow the
OS, with a header toggle that overrides and remembers. The only JavaScript on the page is
that toggle; the content is all server-rendered HTML, so it works with JS off and reads
fine to anything crawling it.
