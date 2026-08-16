#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bosephus 2050 social card renderer. Canonical emit step.

  python3 render-card.py cards/<artifact-id>.card.json social/<artifact-id>_card.png

Renders the frozen 48-column masthead plus the artifact summary as a green
phosphor CRT panel. No character art, no decoration beyond the terminal.
Type auto-fits: the script picks the largest font size at which 48 columns
fit the width and every line fits the height, so card length can vary
between artifacts without anyone hand-tuning a point size.

Body copy is auto-wrapped to 46 columns. Do not hand-wrap it in the JSON.
"""
import glob
import hashlib
import json
import os
import sys
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W_OUT, H_OUT = 1200, 1500          # 4:5, the tallest aspect X shows uncropped
S = 2                               # supersample
W, H = W_OUT * S, H_OUT * S
PAD = 60 * S
COLS = 48
WRAP = 46

# The masthead needs half-block glyphs (▀ ▄ █ ▞ ▚ ▁) and box drawing. Plenty of
# monospace faces lack them and render tofu. JetBrains Mono Nerd Font has full
# coverage and is the reference face. Override with NIE_FONT_DIR if yours lives
# somewhere else.
FONT_DIRS = [d for d in [
    os.environ.get("NIE_FONT_DIR"),
    os.path.expanduser("~/Library/Fonts"),
    "/Library/Fonts",
    os.path.expanduser("~/.local/share/fonts"),
    "/usr/share/fonts/truetype/jetbrains-mono",
    "/usr/share/fonts",
] if d]


def find_font(*patterns):
    for d in FONT_DIRS:
        for pat in patterns:
            hits = sorted(glob.glob(os.path.join(d, "**", pat), recursive=True))
            if hits:
                return hits[0]
    raise SystemExit(
        "No suitable monospace font found. Install JetBrains Mono Nerd Font, or "
        "point NIE_FONT_DIR at a directory holding a mono face with half-block "
        "glyph coverage. Tried: " + ", ".join(FONT_DIRS))


F_REG = find_font("JetBrainsMonoNerdFontMono-Regular.ttf",
                  "JetBrainsMono*Regular.ttf", "JetBrainsMono-Regular.ttf")
F_BOLD = find_font("JetBrainsMonoNerdFontMono-Bold.ttf",
                   "JetBrainsMono*Bold.ttf", "JetBrainsMono-Bold.ttf")

GREEN = (53, 255, 106)
MASTC = (141, 255, 180)
HEAD = (201, 255, 220)
PINK = (255, 79, 216)
DIM = (31, 157, 76)
CYAN = (191, 247, 255)

MASTHEAD = [
    "╔══════════════════════════════════════════════╗",
    "║        ▄▄▄▄▄▄▄▄        ▄▀▀▄ ▄▀▀▄ █▀▀▀ ▄▀▀▄   ║",
    "║     ▄████████████▄       ▄▀ █  █ ▀▀▀▄ █  █   ║",
    "║    ████████████████    █▄▄▄ ▀▄▄▀ ▀▄▄▀ ▀▄▄▀   ║",
    "║    ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀                          ║",
    "║     ██████████████     B 0 S E P H U S       ║",
    "║      ▀▀▀▀▀▀▀▀▀▀▀▀      G .  A L T A M O N T  ║",
    "║ ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁ ║",
    "║  \\    \\    \\   |   /    /    /               ║",
]


def readout_id(spec):
    """Short identifier for one readout. Never a version number.

    A version implies succession and readouts have none: each is drawn fresh
    from the world as it stood the day it was asked. Derived from the artifact
    so it is reproducible, and stable for a given date and title.
    """
    if spec.get("readout"):
        return spec["readout"]
    title = spec.get("title", "")
    if isinstance(title, list):          # artifact cards wrap copy in lists,
        title = " ".join(title)          # slate cards use plain strings
    seed = (spec.get("present_line", "") + title).encode("utf-8")
    return hashlib.sha1(seed).hexdigest()[:4].upper()


def strip(spec):
    """Bottom masthead row. Never a Tell count, never a Canon version."""
    s = " {} ▸ {} ▸ READOUT {}".format(
        spec["present_line"], spec["mode"].upper(), readout_id(spec))
    return "║" + s.ljust(46)[:46] + "║"


def seam(date):
    txt = " {} · CONSTRUCTED BELOW ".format(date)
    pad = COLS - len(txt)
    l, r = pad // 2, pad - pad // 2
    tape = lambda n: ("▞▚" * (n // 2 + 1))[:n]
    return tape(l) + txt + tape(r)


def wrap(block):
    """Wrap to 46 columns.

    Accepts a string or a list of strings. A bare string used to be iterated
    character by character, so a 40 character disclaimer became 40 lines and
    the card silently rendered as garbage. Normalise instead of trusting the
    author to always reach for a list.
    """
    if isinstance(block, str):
        block = [block]
    out = []
    for para in block:
        out.extend(textwrap.wrap(para, WRAP) or [""])
    return out


def build_lines(spec):
    lines = [(m, MASTC, True) for m in MASTHEAD]
    lines.append(("╠══════════════════════════════════════════════╣", MASTC, True))
    lines.append((strip(spec), MASTC, True))
    lines.append(("╚══════════════════════════════════════════════╝", MASTC, True))
    lines.append(("", GREEN, False))
    for t in wrap(spec["title"]):
        lines.append((t.upper(), HEAD, True))
    lines.append(("", GREEN, False))
    for t in wrap(spec["dek"]):
        lines.append((t, GREEN, False))
    lines.append(("", GREEN, False))
    lines.append((seam(spec["present_line"]), PINK, True))
    lines.append(("", GREEN, False))
    for t in wrap(spec["quote"]):
        lines.append((t, GREEN, False))
    lines.append(("", GREEN, False))
    for t in wrap(spec["cta"]):
        lines.append((t, HEAD, True))
    lines.append(("", GREEN, False))
    for t in wrap(spec.get("disclaimer", [
            "Constructed content. Not a forecast, not advice."])):
        lines.append((t, DIM, False))
    return lines


MIN_FS = 56          # supersampled; 28px in the 1200x1500 output

def fit(n_lines):
    """Largest size where 48 cols fit the width and n lines fit the height.

    Floors at MIN_FS and refuses below it. Without a floor this silently
    produced microtype for over-long copy, which is the failure the spec
    forbids: the fix for copy that will not fit is shorter copy, never
    smaller type.
    """
    for size in range(140, MIN_FS - 1, -1):
        f = ImageFont.truetype(F_BOLD, size)
        if f.getlength("0" * COLS) > W - 2 * PAD:
            continue
        if n_lines * round(size * 1.20) > H - 2 * PAD:
            continue
        return size, round(size * 1.20)
    raise SystemExit(
        "Card copy will not fit at a readable size ({} lines). Shorten the "
        "quote or the dek. Do not lower MIN_FS.".format(n_lines))


def render(spec, out_path):
    lines = build_lines(spec)
    fs, lh = fit(len(lines))
    reg = ImageFont.truetype(F_REG, fs)
    bold = ImageFont.truetype(F_BOLD, fs)

    base = Image.new("RGB", (W, H), (4, 5, 10))

    bloom = Image.new("L", (120, 150), 0)
    ImageDraw.Draw(bloom).ellipse([-30, -40, 150, 120], fill=80)
    bloom = bloom.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(60))
    base.paste(Image.new("RGB", (W, H), (10, 34, 20)), (0, 0), bloom)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = (H - len(lines) * lh) // 2
    x = (W - bold.getlength("0" * COLS)) / 2
    for text, colour, is_bold in lines:
        if text:
            d.text((x, y), text, font=(bold if is_bold else reg), fill=colour + (255,))
        y += lh

    wide = layer.filter(ImageFilter.GaussianBlur(14 * S))
    tight = layer.filter(ImageFilter.GaussianBlur(4 * S))
    term = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for g in (wide, wide, tight, layer):
        term = Image.alpha_composite(term, g)
    base.paste(term, (0, 0), term)

    scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(scan)
    for yy in range(0, H, 3 * S):
        ds.rectangle([0, yy, W, yy + S - 1], fill=(0, 0, 0, 70))
    base.paste(scan, (0, 0), scan)

    d2 = ImageDraw.Draw(base)
    d2.rectangle([PAD // 3, PAD // 3, W - PAD // 3, H - PAD // 3],
                 outline=(120, 40, 150), width=S)
    d2.text((W // 2, H - PAD // 2), "MØNTAN1 // NARRATIVE INTELLIGENCE",
            font=ImageFont.truetype(F_BOLD, 15 * S), fill=CYAN, anchor="ms")

    base.resize((W_OUT, H_OUT), Image.LANCZOS).save(out_path, optimize=True)
    return fs, len(lines)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    size, n = render(spec, sys.argv[2])
    print("wrote {}  ({} lines at {}px)".format(sys.argv[2], n, size))
