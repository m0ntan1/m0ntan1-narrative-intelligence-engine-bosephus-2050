#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slate card: one PNG carrying a whole group of calls, with the character plate.

  python3 render_slate.py <slate.json> <element.png> <out.png>

Used when a run issues a group rather than a single artifact. The PNG carries
the load: every matchup and every call is legible on the card itself, so the
image is the deliverable and the write-up is the footnote rather than the other
way round.

Reuses the masthead, palette, font and glow from render_card.py, so a slate and
a single card are visibly the same object.
"""
import json
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from render_card import (F_REG, F_BOLD, MASTHEAD, strip, seam,
                         GREEN, MASTC, HEAD, PINK, DIM, CYAN)

S = 2
W_OUT, H_OUT = 1600, 1400
W, H = W_OUT * S, H_OUT * S
ART_W = 560 * S
TERM_W = W - ART_W
PAD = 40 * S
COLS = 48


def rows_to_lines(spec):
    """Matchup left, call right, inside 46 columns. Markers explained on card."""
    out = []
    for r in spec["rows"]:
        mark = "*" if r.get("fan") else ("^" if r.get("against_baseline") else " ")
        line = "{:<28}{:>17} {}".format(r["matchup"][:28], r["call"][:17], mark)
        out.append((line, HEAD if r.get("fan") else GREEN, bool(r.get("fan"))))
    return out


def build(spec):
    lines = [(m, MASTC, True) for m in MASTHEAD]
    lines.append(("╠══════════════════════════════════════════════╣", MASTC, True))
    lines.append((strip(spec), MASTC, True))
    lines.append(("╚══════════════════════════════════════════════╝", MASTC, True))
    lines.append(("", GREEN, False))
    lines.append((spec["title"].upper()[:46], HEAD, True))
    lines.append(("", GREEN, False))
    lines.append((seam(spec["present_line"]), PINK, True))
    lines.append(("", GREEN, False))
    lines.extend(rows_to_lines(spec))
    lines.append(("", GREEN, False))
    for n in spec.get("notes", []):
        lines.append((n[:46], GREEN, False))
    lines.append(("", GREEN, False))
    lines.append((spec["cta"][:46], HEAD, True))
    lines.append(("", GREEN, False))
    lines.append((spec.get("disclaimer", "Constructed. Not a forecast, not advice.")[:46],
                  DIM, False))
    return lines


def fit(n, avail_w, avail_h):
    for size in range(120, 10, -1):
        f = ImageFont.truetype(F_BOLD, size)
        if f.getlength("0" * COLS) > avail_w:
            continue
        if n * round(size * 1.20) > avail_h:
            continue
        return size, round(size * 1.20)
    raise SystemExit("slate too long to fit, trim rows or notes")


def render(spec, element_path, out_path):
    lines = build(spec)
    fs, lh = fit(len(lines), TERM_W - 2 * PAD, H - 2 * PAD)
    reg = ImageFont.truetype(F_REG, fs)
    bold = ImageFont.truetype(F_BOLD, fs)

    base = Image.new("RGB", (W, H), (4, 5, 10))

    bloom = Image.new("L", (120, 105), 0)
    ImageDraw.Draw(bloom).ellipse([-30, -40, 140, 105], fill=85)
    bloom = bloom.resize((TERM_W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(50))
    base.paste(Image.new("RGB", (TERM_W, H), (10, 34, 20)), (0, 0), bloom)

    art = Image.open(element_path).convert("RGB")
    side = max(ART_W, H)
    art = art.resize((side, side), Image.LANCZOS)
    # Bias the crop left of centre. The almanac is the storytelling object in
    # this plate and dead-centre cropping slices its title off.
    cx = int((art.width - ART_W) * 0.34)
    art = art.crop((cx, (art.height - H) // 2, cx + ART_W, (art.height - H) // 2 + H))
    fade = Image.new("L", (ART_W, 1))
    px = fade.load()
    for x in range(ART_W):
        t = x / (ART_W * 0.26)
        px[x, 0] = 0 if t >= 1 else int(255 * (1 - t) ** 1.4)
    art.paste(Image.new("RGB", (ART_W, H), (4, 5, 10)), (0, 0), fade.resize((ART_W, H)))
    base.paste(art, (TERM_W, 0))

    layer = Image.new("RGBA", (TERM_W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = (H - len(lines) * lh) // 2
    x = (TERM_W - bold.getlength("0" * COLS)) / 2
    for text, colour, is_bold in lines:
        if text:
            d.text((x, y), text, font=(bold if is_bold else reg), fill=colour + (255,))
        y += lh

    wide = layer.filter(ImageFilter.GaussianBlur(14 * S))
    tight = layer.filter(ImageFilter.GaussianBlur(4 * S))
    term = Image.new("RGBA", (TERM_W, H), (0, 0, 0, 0))
    for g in (wide, wide, tight, layer):
        term = Image.alpha_composite(term, g)
    base.paste(term, (0, 0), term)

    scan = Image.new("RGBA", (TERM_W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(scan)
    for yy in range(0, H, 3 * S):
        ds.rectangle([0, yy, TERM_W, yy + S - 1], fill=(0, 0, 0, 70))
    base.paste(scan, (0, 0), scan)

    div = Image.new("RGB", (4 * S, H))
    dd = ImageDraw.Draw(div)
    for yy in range(H):
        t = abs(yy - H / 2) / (H / 2)
        dd.line([(0, yy), (4 * S, yy)],
                fill=(int(255 - 255 * t), int(47 + 182 * t), int(208 + 47 * t)))
    halo = Image.new("RGB", (W, H), (0, 0, 0))
    halo.paste(div, (TERM_W - 2 * S, 0))
    halo = halo.filter(ImageFilter.GaussianBlur(16 * S))
    base.paste(halo, (0, 0), halo.convert("L").point(lambda v: min(255, int(v * 1.6))))
    base.paste(div, (TERM_W - 2 * S, 0))

    ImageDraw.Draw(base).text(
        (W - 22 * S, H - 30 * S), "MØNTAN1 // NARRATIVE INTELLIGENCE",
        font=ImageFont.truetype(F_BOLD, 15 * S), fill=CYAN, anchor="ra")

    base.resize((W_OUT, H_OUT), Image.LANCZOS).save(out_path, optimize=True)
    return fs, len(lines)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    size, n = render(spec, sys.argv[2], sys.argv[3])
    print("wrote {}  ({} lines at {}px)".format(sys.argv[3], n, size))
