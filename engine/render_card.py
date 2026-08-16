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
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

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


# ---------------------------------------------------------------- portrait

_HERE = os.path.dirname(os.path.abspath(__file__))
# vault layout puts Elements beside tools/; repo layout puts it inside engine/
PORTRAIT = next((p for p in (
    os.path.join(_HERE, "Elements", "X"),
    os.path.join(os.path.dirname(_HERE), "Elements", "X"),
) if os.path.isdir(os.path.dirname(p))), os.path.join(_HERE, "Elements", "X"))
PORTRAIT = os.path.join(
    os.path.dirname(PORTRAIT),
    "nano-banana-2_Professional_graphic_design_2D_illustration_Make_this_an_ASCII_Hex_color_8DFFB4_-0.jpg")

# The masthead's left half is a block-character sun. On a PNG we can do better,
# so the portrait is composited into exactly that footprint. Text surfaces keep
# the drawn sun, because Discord and plaintext cannot carry an image and the
# masthead has to stay one object across all of them.
PORTRAIT_COLS = (1, 23)     # inside the frame, left of the 2050 wordmark
PORTRAIT_ROWS = (1, 7)      # the sun rows, stopping above the horizon


def masthead_lines(portrait=False):
    """Masthead art, with the drawn sun blanked when a plate will cover it.

    Off by default, because text surfaces share this function and a blanked sun
    with no image over it is an empty box. Only the PNG renderers that actually
    composite the plate pass portrait=True.

    The sun glyphs and the portrait occupy the same cells, so drawing both puts
    block characters across his face. Blanking is done here rather than by
    editing masthead.txt, because that file is the canonical text cut and still
    needs its sun for Discord and plaintext.
    """
    if not portrait or not os.path.exists(PORTRAIT):
        return MASTHEAD
    c0, c1 = PORTRAIT_COLS
    out = []
    for i, line in enumerate(MASTHEAD):
        if PORTRAIT_ROWS[0] <= i < PORTRAIT_ROWS[1]:
            line = line[:c0] + " " * (c1 - c0) + line[c1:]
        out.append(line)
    return out


def paste_portrait(base, x0, y0, char_w, lh, tint=(141, 255, 180)):
    """Composite the character plate over the sun region of the masthead.

    Uses the plate's own luminance as alpha, so its near-black surround drops
    out and only the drawn figure lights up. Screened rather than pasted, so it
    reads as phosphor on the same ground as the type instead of a photograph
    stuck on top of it.
    """
    if not os.path.exists(PORTRAIT):
        return base

    c0, c1 = PORTRAIT_COLS
    r0, r1 = PORTRAIT_ROWS
    box_w = int((c1 - c0) * char_w)
    box_h = int((r1 - r0) * lh)
    side = min(box_w, box_h)
    px = int(x0 + c0 * char_w + (box_w - side) / 2)
    py = int(y0 + r0 * lh + (box_h - side) / 2)

    plate = Image.open(PORTRAIT).convert("L").resize((side, side), Image.LANCZOS)

    # radial feather so the square edge never shows
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, side - 1, side - 1], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(side * 0.03))

    lum = ImageChops.multiply(plate, mask)
    tinted = Image.new("RGB", (side, side), tint)
    layer = Image.new("RGB", base.size, (0, 0, 0))
    layer.paste(tinted, (px, py), lum)
    layer = ImageChops.add(layer, layer.filter(ImageFilter.GaussianBlur(side * 0.02)))
    return ImageChops.screen(base, layer)


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


def build_lines(spec, portrait=False):
    lines = [(m, MASTC, True) for m in masthead_lines(portrait)]
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
    lines = build_lines(spec, portrait=True)
    fs, lh = fit(len(lines))
    reg = ImageFont.truetype(F_REG, fs)
    bold = ImageFont.truetype(F_BOLD, fs)

    base = Image.new("RGB", (W, H), (4, 5, 10))

    bloom = Image.new("L", (120, 150), 0)
    ImageDraw.Draw(bloom).ellipse([-30, -40, 150, 120], fill=80)
    bloom = bloom.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(60))
    base.paste(Image.new("RGB", (W, H), (10, 34, 20)), (0, 0), bloom)

    y = (H - len(lines) * lh) // 2
    x = (W - bold.getlength("0" * COLS)) / 2
    base = paste_portrait(base, x, y, bold.getlength("0"), lh)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
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
