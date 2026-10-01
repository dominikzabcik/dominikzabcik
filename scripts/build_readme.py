#!/usr/bin/env python3
"""Builds the profile README and its SVG blocks.

Shared facts (roles, projects, skills, profile text, links) come from
data/profile.json, which the website exports from its own content:

    cd ~/website && bun run profile:export ~/orca/dominikzabcik/data/profile.json

README-only content (NFCtron products, hiring, focus, interests, icon slugs)
lives in data/readme.json. Then:

    python3 scripts/build_readme.py                       # writes README.md
    python3 scripts/build_readme.py --out .preview/draft.md   # a draft, git-ignored

Needs Python 3 with fonttools and brotli (`pip3 install fonttools brotli`) and
the Tanker font from the website repo (override with TANKER_FONT).

Every block is drawn twice, dark and light, into assets/site/. Images use the
#gh-dark-mode-only / #gh-light-mode-only fragments because GitHub breaks a
<picture> that sits inside a link. Motion is CSS only and switches off under
prefers-reduced-motion.
"""

import argparse
import glob
import json
import os
import random
import re
import textwrap

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
KIT = os.path.join(ROOT, "scripts", "readme")
ASSETS = os.path.join(ROOT, "assets", "site")
FONT = os.environ.get(
    "TANKER_FONT", os.path.join(ROOT, "..", "..", "website", "src", "fonts", "tanker.woff2")
)

THEMES = {
    "dark": dict(panel="#0b0b0a", top="#10100f", edge="#1c1c1a", ink="#f2f1ec", muted="#9d9c93",
                 dim="#83827a", tint="#8fc4ea", hi="#cfe8f8", lit="#f4fbff", grain=0.03, ghost=0.07),
    "light": dict(panel="#fbfbf8", top="#fefefc", edge="#e4e4dd", ink="#121210", muted="#5c5b55",
                  dim="#6e6d66", tint="#2b7bb4", hi="#17567f", lit="#0b3a5e", grain=0.06, ghost=0.09),
}
SANS = "system-ui, -apple-system, 'Segoe UI', sans-serif"
W = 830  # width of every block below the hero, about GitHub's README column
COL2 = 470  # second column of two-column blocks
DESC = 180  # where descriptions start in name / description rows


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def svg(h, body, label, w=W):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">\n{body}\n</svg>')


def text(x, y, s, c, size=14.5, color="ink", weight=None):
    wt = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}"{wt} fill="{c[color]}">{esc(s)}</text>'


def para(x, y, lines, pitch, c, size=14.5, color="ink", weight=None):
    spans = "".join(f'<tspan x="{x}" y="{y + i * pitch}">{esc(l)}</tspan>' for i, l in enumerate(lines))
    wt = f' font-weight="{weight}"' if weight else ""
    return f'<text font-family="{SANS}" font-size="{size}"{wt} fill="{c[color]}">{spans}</text>'


def label(x, y, s, c):
    return text(x, y, s, c, size=14, color="dim")


def bullet(x, y, c):
    return f'<rect x="{x}" y="{y - 9}" width="7" height="7" rx="1.5" fill="{c["dim"]}"/>'


def arrow(x, y, c):
    return (f'<path d="M{x} {y + 10} L{x + 10} {y} M{x + 2} {y} H{x + 10} V{y + 8}" fill="none" '
            f'stroke="{c["muted"]}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>')


# Text is measured with the macOS system font, the one GitHub's viewers on a Mac
# see. Elsewhere system-ui is a similar width; without the font, guess.
try:
    _sys = TTFont("/System/Library/Fonts/SFNS.ttf")
    _sys_cmap, _sys_hmtx, _sys_em = _sys.getBestCmap(), _sys["hmtx"], _sys["head"].unitsPerEm
except Exception:
    _sys = None


def measure(s, size, weight=None):
    if _sys is None:
        return len(s) * size * 0.55
    units = sum(_sys_hmtx[_sys_cmap.get(ord(ch), _sys_cmap[ord("n")])][0] for ch in s)
    bold = {None: 1.0, 500: 1.05, 600: 1.09}.get(weight, 1.0)
    # The font's default instance is the display cut; text sizes render about 10% wider.
    optical = 1.10 if size < 20 else 1.0
    return units / _sys_em * size * bold * optical


def wrap_px(s, width, size, weight=None):
    lines, line = [], ""
    for word in s.split():
        candidate = f"{line} {word}".strip()
        if line and measure(candidate, size, weight) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + [line]


def fit(s, width, size, weight=None):
    """Wraps s to a pixel width, picking the break that leaves no stray last word."""
    best = None
    for w in range(int(width * 0.8), int(width) + 1, 4):
        lines = wrap_px(s, w, size, weight)
        key = (len(lines), -measure(lines[-1], size, weight))
        if best is None or key < best[0]:
            best = (key, lines)
    return best[1]


# ------------------------------------------------------------------ Tanker

_font = TTFont(FONT)
_font.flavor = None
_glyphs = _font.getGlyphSet()
_cmap = _font.getBestCmap()


def tanker(s, cap, x, baseline, tracking=0.8):
    """Outlines s in Tanker, so the README needs no web font."""
    scale = cap / 750.0
    pen = SVGPathPen(_glyphs, ntos=lambda v: f"{v:.1f}")
    for ch in s:
        g = _cmap[ord(ch)]
        _glyphs[g].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
        x += _glyphs[g].width * scale + tracking
    return pen.getCommands()


# -------------------------------------------------------------------- hero

def hero(c, profile):
    """DOMINIK as a particle field, like the website. Points were sampled from Tanker."""
    pts = json.load(open(os.path.join(KIT, "words.json")))["DOMINIK"]["pts"]
    r = random.Random(11)
    inside = set(map(tuple, pts))
    sizes = [[], [], []]
    for x, y in pts:
        edge = any((x + dx, y + dy) not in inside for dx, dy in ((3, 0), (-3, 0), (0, 3), (0, -3)))
        if r.random() < (0.40 if edge else 0.13):
            q = r.random()
            k = 0 if q < 0.55 else (1 if q < 0.88 else 2)
            sizes[k].append(f"M{x + r.uniform(-1.6, 1.6):.0f} {y + r.uniform(-1.6, 1.6):.0f}h0")
    ghost = "".join(f"M{x} {y}h0" for x, y in pts if r.random() < 0.08)
    haze, deep = [], []
    for _ in range(650):
        x, y = r.choice(pts)
        x, y = x + r.gauss(0, 34), y + r.gauss(0, 28)
        if 24 < x < 1176 and 84 < y < 362:
            haze.append(f"M{x:.0f} {y:.0f}h0")
    for _ in range(520):
        deep.append(f"M{r.uniform(24, 1176):.0f} {r.uniform(84, 362):.0f}h0")
    caption = profile["tagline"][:1].upper() + profile["tagline"][1:]
    host = profile["links"]["site"].split("//")[1]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="400" viewBox="0 10 1200 400" role="img" aria-label="Dominik. {esc(caption)}, spelled in a field of particles.">
<style>
#p0,#p1,#p2{{fill:none;stroke-linecap:round}}
.hz{{fill:none;stroke:{c['tint']};stroke-width:2.6;stroke-linecap:round;stroke-opacity:.5}}
.dp{{fill:none;stroke:{c['tint']};stroke-width:2;stroke-linecap:round;stroke-opacity:.28}}
@media (prefers-reduced-motion: no-preference){{
.a0{{animation:tw 5s ease-in-out infinite alternate}}.a1{{animation:tw 7s ease-in-out -2s infinite alternate}}
.a2{{animation:tw 9s ease-in-out -4s infinite alternate}}.hz{{animation:dr 14s ease-in-out infinite alternate}}
.dp{{animation:dr2 22s ease-in-out infinite alternate}}.sw{{animation:sw 14s linear infinite}}}}
@keyframes sw{{0%,8%{{transform:translateX(0)}}34%,100%{{transform:translateX(1920px)}}}}
@keyframes tw{{from{{opacity:.6}}to{{opacity:1}}}}
@keyframes dr{{from{{transform:translate(-6px,2px)}}to{{transform:translate(7px,-3px)}}}}
@keyframes dr2{{from{{transform:translate(5px,-2px)}}to{{transform:translate(-6px,3px)}}}}
</style>
<defs>
<linearGradient id="pn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c['top']}"/><stop offset="1" stop-color="{c['panel']}"/></linearGradient>
<filter id="gr" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter>
<path id="p0" d="{"".join(sizes[0])}" stroke-width="3.2"/><path id="p1" d="{"".join(sizes[1])}" stroke-width="4.6"/><path id="p2" d="{"".join(sizes[2])}" stroke-width="6.2" stroke="{c['hi']}"/>
<linearGradient id="band" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>
<mask id="swm" maskUnits="userSpaceOnUse" x="0" y="0" width="1200" height="440"><g transform="skewX(-18)"><rect class="sw" x="-420" y="-20" width="260" height="500" fill="url(#band)"/></g></mask>
</defs>
<rect y="10" width="1200" height="400" rx="16" fill="url(#pn)"/>
<rect y="10" width="1200" height="400" rx="16" filter="url(#gr)" opacity="{c['grain']}"/>
<rect x=".5" y="10.5" width="1199" height="399" rx="15.5" fill="none" stroke="{c['edge']}"/>
<path class="dp" d="{"".join(deep)}"/>
<path d="{ghost}" fill="none" stroke="{c['ink']}" stroke-opacity="{c['ghost']}" stroke-width="3.4" stroke-linecap="round"/>
<g stroke="{c['tint']}"><use href="#p0" class="a0"/><use href="#p1" class="a1"/><use href="#p2" class="a2"/></g>
<g stroke="{c['lit']}" mask="url(#swm)"><use href="#p0"/><use href="#p1"/></g>
<path class="hz" d="{"".join(haze)}"/>
<text x="40" y="54" font-family="{SANS}" font-size="22" font-weight="600" fill="{c['ink']}" letter-spacing="-0.2">{esc(profile['name'])}</text>
<text x="1148" y="54" font-family="{SANS}" font-size="21" text-anchor="end" fill="{c['muted']}">{esc(host)}</text>
<path d="M1156 49 L1166 39 M1158 39 H1166 V47" fill="none" stroke="{c['muted']}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
<text x="40" y="386" font-family="{SANS}" font-size="18" fill="{c['muted']}">{esc(caption)}</text>
<text x="1160" y="386" font-family="{SANS}" font-size="16" text-anchor="end" fill="{c['dim']}">50.08° N  14.44° E</text>
</svg>'''


# ------------------------------------------------------------------ blocks

def about(c, profile):
    """About line on the left, roles on the right, the CV profile underneath."""
    statement = fit(profile["about"], 410, 24, 500)
    b = label(0, 14, "About", c) + para(0, 54, statement, 33, c, size=24, weight=500)
    b += label(COL2, 14, "Experience", c)
    y = 44
    for role in profile["experience"]:
        b += text(COL2, y, role["title"], c, size=15, weight=500)
        b += text(COL2, y + 20, f'{role["company"]}, {role["period"]}', c, size=13.5, color="muted")
        y += 46
    top = max(54 + (len(statement) - 1) * 33, y - 26) + 40
    body = fit(profile["profile"], W - 20, 15)
    b += para(0, top, body, 23, c, size=15, color="muted")
    h = top + (len(body) - 1) * 23 + 14
    roles = "; ".join(f'{r["title"]}, {r["period"]}' for r in profile["experience"])
    return svg(h, b, f'About. {profile["about"]} Experience: {roles}. {profile["profile"]}')


def drawn(c, readme):
    b = label(0, 14, "What pulls me in", c)
    rows = 0
    for i, item in enumerate(readme["drawn"]):
        x = i * COL2
        lines = fit(item["text"], COL2 - 50, 14)
        rows = max(rows, len(lines))
        b += text(x, 44, item["name"], c, size=15, weight=600)
        b += para(x, 66, lines, 20, c, size=14, color="muted")
    alt = " ".join(f'{d["name"]}: {d["text"]}' for d in readme["drawn"])
    return svg(66 + (rows - 1) * 20 + 12, b, f"What pulls me in. {alt}")


def nfctron(c, profile, readme):
    """What I do at NFCtron (from the CV) and what NFCtron makes (README only)."""
    n = readme["nfctron"]
    current = profile["experience"][0]
    b = label(0, 14, "NFCtron", c)
    intro = fit(f'{current["title"]}. {n["intro"]}', W - 20, 17)
    b += para(0, 46, intro, 25, c, size=17)
    y = 46 + len(intro) * 25 + 14
    for h in current["highlights"]:
        lines = fit(h, W - 40, 14.5)
        b += bullet(0, y, c) + para(20, y, lines, 21, c, size=14.5)
        y += len(lines) * 21 + 7
    y += 20
    for name, desc in n["products"]:
        lines = fit(desc, W - DESC - 20, 14)
        b += text(0, y, name, c, size=15, weight=600) + para(DESC, y, lines, 20, c, size=14, color="muted")
        y += (len(lines) - 1) * 20 + 30
    alt = " ".join([*intro, *current["highlights"], *(f"{p}: {d}" for p, d in n["products"])])
    return svg(y - 12, b, f"NFCtron. {alt}")


def careers(c, readme):
    k = readme["nfctron"]["careers"]
    b = (f'<text x="0" y="24" font-family="{SANS}" font-size="15"><tspan fill="{c["ink"]}" font-weight="600">'
         f'{esc(k["title"])}</tspan><tspan dx="14" fill="{c["muted"]}">{esc(k["text"])}</tspan></text>'
         + arrow(W - 18, 12, c))
    return svg(40, b, f'{k["title"]}. {k["text"]}.')


def project(c, p, readme):
    """Name in Tanker with kind and year under it; the summary to the right."""
    more = readme["projectMore"].get(p["id"])
    desc = f'{p["summary"]} {more}' if more else p["summary"]
    lines = fit(desc, W - DESC - 50, 14.5)
    b = (f'<path d="{tanker(p["name"].upper(), 17, 0, 18)}" fill="{c["ink"]}"/>'
         + text(0, 40, f'{p["kind"]}, {p["year"]}', c, size=12.5, color="muted")
         + para(DESC, 16, lines, 21, c, size=14.5)
         + arrow(W - 18, 5, c))
    return svg(max(40, 16 + (len(lines) - 1) * 21) + 22, b, f'{p["name"]}. {p["kind"]}, {p["year"]}. {desc}')


def icon_path(slug):
    return re.search(r' d="([^"]+)"', open(os.path.join(KIT, "icons", f"{slug}.svg")).read()).group(1)


def skills(c, profile, readme):
    """The CV's skill groups, one row each, with the real brand marks where they exist."""
    b = ""
    y = 22
    for group in profile["skills"]:
        b += label(0, y, group["name"], c)
        x = DESC
        for item in group["items"]:
            wide = 26 + measure(item["name"], 14.5) + 26
            if x + wide > W and x > DESC:
                x, y = DESC, y + 30
            slug = readme["icons"].get(item["id"])
            if slug:
                b += f'<g transform="translate({x} {y - 15}) scale(0.75)"><path d="{icon_path(slug)}" fill="{c["muted"]}"/></g>'
            else:
                b += bullet(x + 5, y - 2, c)
            b += text(x + 26, y, item["name"], c, size=14.5)
            x += wide
        y += 44
    alt = " ".join(f'{g["name"]}: {", ".join(i["name"] for i in g["items"])}.' for g in profile["skills"])
    return svg(y - 30, b, f"Skills. {alt}")


def focus(c, readme):
    items = readme["focus"]
    per = (len(items) + 1) // 2
    b = label(0, 14, "Current focus", c)
    for i, t in enumerate(items):
        x, y = (i // per) * COL2, 42 + (i % per) * 28
        b += bullet(x, y, c) + text(x + 20, y, t, c)
    return svg(42 + (per - 1) * 28 + 14, b, "Current focus. " + ", ".join(items) + ".")


def link(c, name):
    b = arrow(0, 13, c) + text(18, 24, name, c, size=15, weight=500)
    return svg(36, b, name, w=round(18 + measure(name, 15, 500)) + 26)


# ------------------------------------------------------------------- build

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="README.md", help="markdown file to write, relative to the repo root")
    args = ap.parse_args()

    profile = json.load(open(os.path.join(DATA, "profile.json")))
    readme = json.load(open(os.path.join(DATA, "readme.json")))
    links = profile["links"]

    blocks = {
        "hero": lambda c: hero(c, profile),
        "about": lambda c: about(c, profile),
        "drawn": lambda c: drawn(c, readme),
        "nfctron": lambda c: nfctron(c, profile, readme),
        "careers": lambda c: careers(c, readme),
        "label-projects": lambda c: svg(30, label(0, 20, "Projects", c), "Projects"),
        "skills": lambda c: skills(c, profile, readme),
        "focus": lambda c: focus(c, readme),
    }
    for p in profile["projects"]:
        blocks[f'project-{p["id"]}'] = (lambda p: lambda c: project(c, p, readme))(p)
    elsewhere = [("CV", links["cv"]), ("LinkedIn", links["linkedin"]), ("zabcik.me", links["site"])]
    for name, _ in elsewhere:
        blocks[f"link-{name.lower().replace('.', '')}"] = (lambda n: lambda c: link(c, n))(name)

    os.makedirs(ASSETS, exist_ok=True)
    for stale in glob.glob(os.path.join(ASSETS, "*.svg")):
        os.remove(stale)
    for name, draw in blocks.items():
        for theme, c in THEMES.items():
            with open(os.path.join(ASSETS, f"{name}-{theme}.svg"), "w") as f:
                f.write(draw(c))

    out = os.path.join(ROOT, args.out)
    prefix = os.path.relpath(ASSETS, os.path.dirname(out))

    def img(name, alt, href=None, width=None):
        w = f' width="{width}"' if width else ""
        html = ""
        for theme in ("dark", "light"):
            tag = f'<img alt="{esc(alt)}" src="{prefix}/{name}-{theme}.svg#gh-{theme}-mode-only"{w}>'
            html += f'<a href="{href}">{tag}</a>' if href else tag
        return html

    def live(w):
        """An image served by another site, in its dark and light versions."""
        sep = "&" if "?" in w["image"] else "?"
        return "".join(
            f'<a href="{w["href"]}"><img alt="{esc(w["alt"])}" src="{src}#gh-{theme}-mode-only" width="{W}"></a>'
            for theme, src in (("dark", w["image"]), ("light", f'{w["image"]}{sep}theme=light'))
        )

    def block(items, sep="<br>\n"):
        return "<p>\n" + sep.join(items) + "\n</p>\n"

    careers_link = readme["nfctron"]["careers"]["href"]
    md = [
        "<!-- Generated by scripts/build_readme.py from data/profile.json and data/readme.json. Do not edit by hand. -->\n",
        block([img("hero", f'{profile["name"]}, {profile["tagline"]}.', links["site"], "100%")]),
        block([img("about", f'About. {profile["about"]}')]),
        block([img("drawn", "What pulls me in: " + ", ".join(d["name"] for d in readme["drawn"]))]),
        block([img("nfctron", "NFCtron"), img("careers", "NFCtron is hiring", careers_link)]),
        block([img("label-projects", "Projects")]
              + [img(f'project-{p["id"]}', f'{p["name"]}. {p["summary"]}', p["href"]) for p in profile["projects"]]),
        block([img("skills", "Skills")]),
        block([img("focus", "Current focus")]),
        *([block([live(readme["keyhopWidget"])])] if readme.get("keyhopWidget") else []),
        block([img(f"link-{n.lower().replace('.', '')}", n, h) for n, h in elsewhere], sep="&nbsp;&nbsp;&nbsp;&nbsp;\n"),
    ]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write("\n".join(md))
    print(f"Wrote {os.path.relpath(out, ROOT)} and {len(blocks) * 2} SVGs in {os.path.relpath(ASSETS, ROOT)}")


if __name__ == "__main__":
    main()
