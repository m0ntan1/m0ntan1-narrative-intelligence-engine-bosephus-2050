#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render the seam rule as a PNG strip.

  python3 render_seam.py <date> <out.png> [width_cols]

Exists because GitHub markdown cannot colour text. ANSI escapes print raw,
style attributes get sanitised out of README HTML, and the diff-highlight
trick only reaches red and green. Per spec 5.3 the seam is neon pink on every
surface that can carry colour, so on GitHub it has to be an image or it is not
pink at all.

Same palette, same font, same glow and scanlines as render_card.py, so the
strip in the README is the seam and not an illustration of it.
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from render_card import F_BOLD, PINK

S = 2
PAD_X = 26 * S
PAD_Y = 20 * S
BG = (4, 5, 10)


def seam_text(date, cols=64):
    """The two documented cuts. 64 for artifacts, 48 for chat surfaces.

    The 64-column cut carries PRESENT LINE because an artifact reader needs
    naming. The 48-column cut drops it because at that width the label would
    eat the hazard tape, and by then the reader has the masthead above it.
    """
    label = " PRESENT LINE {} · CONSTRUCTED BELOW ".format(date) if cols >= 64 \
        else " {} · CONSTRUCTED BELOW ".format(date)
    pad = cols - len(label)
    if pad < 4:
        raise SystemExit("seam label does not fit {} columns".format(cols))
    l, r = pad // 2, pad - pad // 2
    tape = lambda n: ("▞▚" * (n // 2 + 1))[:n]
    return tape(l) + label + tape(r)


def render(date, out_path, cols=64):
    text = seam_text(date, cols)
    assert len(text) == cols, "seam is {} chars, expected {}".format(len(text), cols)
    fs = 30 * S
    font = ImageFont.truetype(F_BOLD, fs)

    w = int(font.getlength(text)) + PAD_X * 2
    h = fs + PAD_Y * 2

    base = Image.new("RGB", (w, h), BG)

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((PAD_X, PAD_Y), text, font=font, fill=PINK + (255,))

    wide = layer.filter(ImageFilter.GaussianBlur(12 * S))
    tight = layer.filter(ImageFilter.GaussianBlur(3 * S))
    stack = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for g in (wide, wide, tight, layer):
        stack = Image.alpha_composite(stack, g)
    base.paste(stack, (0, 0), stack)

    scan = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ds = ImageDraw.Draw(scan)
    for yy in range(0, h, 3 * S):
        ds.rectangle([0, yy, w, yy + S - 1], fill=(0, 0, 0, 70))
    base.paste(scan, (0, 0), scan)

    base.resize((w // S, h // S), Image.LANCZOS).save(out_path, optimize=True)
    return w // S, h // S


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    size = render(sys.argv[1], sys.argv[2],
                  int(sys.argv[3]) if len(sys.argv) == 4 else 64)
    print("wrote {}  {}x{}".format(sys.argv[2], *size))
