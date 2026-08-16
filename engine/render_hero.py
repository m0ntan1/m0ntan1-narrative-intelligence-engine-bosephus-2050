#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hero card: terminal left, character plate right, 1600x900.

  python3 render_hero.py <card.json> <element.png> <out.png>

This is the brand image, not a per-readout emit. It is what a link to the
project itself should unfurl with, and it is deliberately about the character
rather than about any one story. Per-readout wide cards are render_wide.py,
whose right half carries the readout's own cited numbers.

Un-retired 2026-08-16: it was archived when the portrait moved into the
masthead, on the reasoning that two faces on one card is one too many. That
holds for a data card and does not hold for a hero.

Shares the masthead, the wrap rule and the palette with render_card.py, so the
two can never drift apart.
"""
import json
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from render_card import (
    F_REG, F_BOLD, build_lines, paste_portrait, GREEN, CYAN,
)

S = 2
W_OUT, H_OUT = 1600, 900
W, H = W_OUT * S, H_OUT * S
TERM_W = 720 * S
ART_W = W - TERM_W
PAD_X = 34 * S
FS = 22 * S
LH = 26 * S


MAX_LINES = (H - 2 * 30 * S) // LH      # what the 720px terminal panel holds


def render(spec, element_path, out_path):
    # portrait=True: the hero carries the face in the masthead like every other
    # card. It was defaulting to the old block sun, which made the one image
    # most people see the only one with the wrong logo on it.
    lines = build_lines(spec, portrait=True)
    if len(lines) > MAX_LINES:
        raise SystemExit(
            "Copy overflows the terminal panel: {} lines into room for {}. "
            "This variant uses a fixed type size because the panel is only 720 "
            "of 1600 columns, so the fix is shorter copy. Shorten the quote or "
            "the dek.".format(len(lines), MAX_LINES))
    reg = ImageFont.truetype(F_REG, FS)
    bold = ImageFont.truetype(F_BOLD, FS)

    base = Image.new("RGB", (W, H), (4, 5, 10))

    bloom = Image.new("L", (160, 90), 0)
    ImageDraw.Draw(bloom).ellipse([-20, -30, 120, 90], fill=90)
    bloom = bloom.resize((TERM_W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
    base.paste(Image.new("RGB", (TERM_W, H), (10, 34, 20)), (0, 0), bloom)

    # element, cropped square and faded into the terminal on its left edge
    art = Image.open(element_path).convert("RGB")
    side = max(ART_W, H)
    art = art.resize((side, side), Image.LANCZOS)
    art = art.crop(((art.width - ART_W) // 2, (art.height - H) // 2,
                    (art.width - ART_W) // 2 + ART_W, (art.height - H) // 2 + H))
    fade = Image.new("L", (ART_W, 1))
    px = fade.load()
    for x in range(ART_W):
        t = x / (ART_W * 0.30)
        px[x, 0] = 0 if t >= 1 else int(255 * (1 - t) ** 1.4)
    art.paste(Image.new("RGB", (ART_W, H), (4, 5, 10)), (0, 0), fade.resize((ART_W, H)))
    base.paste(art, (TERM_W, 0))

    y = (H - len(lines) * LH) // 2
    base = paste_portrait(base, PAD_X, y, bold.getlength("0"), LH)

    layer = Image.new("RGBA", (TERM_W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for text, colour, is_bold in lines:
        if text:
            d.text((PAD_X, y), text, font=(bold if is_bold else reg), fill=colour + (255,))
        y += LH

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


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2], sys.argv[3])
    print("wrote", sys.argv[3])
