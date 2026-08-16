#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wide 1600x900 card for link unfurls. Terminal left, a data panel drawn in ASCII
on the right, built from the readout's own cited numbers.

  python3 render_wide.py <card.json> <out.png>
  python3 render_wide.py <card.json> <out.png> --image plate.jpg   (fallback)

The right panel used to hold the source article's photograph converted to
characters. That is gone and it should be. Lifting a news outlet's image raises
a rights question we cannot answer, the conversion quality is a lottery decided
by a histogram we do not control, and it needs a network fetch that can fail.
It was also wrong for the conceit: a terminal in 2050 does not show you a wire
photo, it draws what it knows.

So the panel draws the numbers instead. Every readout already carries cited hard
numbers in THE RECORD, and usually one comparison is the thesis. On the ERCOT
piece it is 474 GW of interconnection requests against a record peak under a
hundred, which is the entire argument of that readout in one shape.

Card JSON gains an optional `figures`:

    "figures": {
      "title": "Large-load queue vs record peak",
      "unit": "GW",
      "bars": [
        {"label": "Requested",   "value": 474},
        {"label": "Record peak", "value": 95, "approx": true}
      ],
      "subtitle": "Texas, August 2026",
      "note": "~90% of requests are data centres",
      "source": "ERCOT via Utility Dive, retrieved 2026-08-16"
    }

`source` is required. A chart with no attribution is the one place the cited
numbers rule would quietly break.
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_card import (F_REG, F_BOLD, MIN_FS, masthead_lines, paste_portrait,
                         strip, seam, wrap, GREEN, MASTC, HEAD, PINK, DIM, CYAN)

S = 2
W_OUT, H_OUT = 1600, 900
W, H = W_OUT * S, H_OUT * S
# 48 columns at the minimum readable size needs ~840px, so the terminal takes
# the larger share. Narrower and fit() refuses, which is how this split was
# arrived at rather than guessed.
TERM_W = 880 * S
ART_W = W - TERM_W
PAD = 30 * S
COLS = 48

PANEL_COLS = 32      # character width of the data panel
BAR_COLS = 28        # longest bar


def bar_lines(fig):
    """The data panel as coloured lines of characters.

    Bars are scaled to the largest value, so the shape carries the ratio. That
    ratio is the point: a comparison a reader can take in before reading a
    single digit is worth more than the digits.
    """
    unit = fig.get("unit", "")
    bars = fig["bars"]
    top = max(b["value"] for b in bars) or 1

    out = []
    # Eyebrow. Does two jobs: tells a cold viewer what kind of thing this panel
    # is, and marks it as coming from the cited half of the readout. In an
    # engine built on a seam, which side a number sits on is not decoration.
    out.append((fig.get("eyebrow", "VERIFIED · ABOVE THE SEAM")[:PANEL_COLS],
                PINK, True))
    for ln in wrap(fig["title"].upper(), PANEL_COLS)[:3]:
        out.append((ln, HEAD, True))
    if fig.get("subtitle"):
        for ln in wrap(fig["subtitle"], PANEL_COLS)[:2]:
            out.append((ln, GREEN, False))
    out.append(("", GREEN, False))
    for b in bars:
        val = b["value"]
        filled = max(1, round(BAR_COLS * val / top))
        shown = "{}{}{}".format("~" if b.get("approx") else "",
                                "{:,}".format(val) if float(val).is_integer() else val,
                                (" " + unit) if unit else "")
        label = b["label"].upper()
        if len(label) > PANEL_COLS:
            raise SystemExit("Bar label too long for the panel ({} > {}): {!r}"
                             .format(len(label), PANEL_COLS, label))
        out.append((label, GREEN, False))
        out.append(("█" * filled, MASTC, True))
        out.append((shown, HEAD, True))
        out.append(("", GREEN, False))
    for ln in wrap(fig.get("note", ""), PANEL_COLS)[:3]:
        out.append((ln, GREEN, False))
    if not fig.get("source"):
        raise SystemExit(
            "The data panel has no `source`. Every number this engine shows is "
            "cited; a chart without an attribution is the one place that rule "
            "would quietly break.")
    out.append(("", GREEN, False))
    for ln in wrap("Source: " + fig["source"], PANEL_COLS)[:3]:
        out.append((ln, DIM, False))
    return out


def build(spec):
    lines = [(m, MASTC, True) for m in masthead_lines(portrait=True)]
    lines.append(("╠══════════════════════════════════════════════╣", MASTC, True))
    lines.append((strip(spec), MASTC, True))
    lines.append(("╚══════════════════════════════════════════════╝", MASTC, True))
    lines.append(("", GREEN, False))
    for ln in wrap(spec["title"]):
        lines.append((ln.upper(), HEAD, True))
    lines.append(("", GREEN, False))
    lines.append((seam(spec["present_line"], override=spec.get("seam_override")), PINK, True))
    lines.append(("", GREEN, False))
    for ln in wrap(spec["quote"]):
        lines.append((ln, GREEN, False))
    lines.append(("", GREEN, False))
    for ln in wrap(spec["cta"]):
        lines.append((ln, HEAD, True))
    return lines


def fit(n, avail_w, avail_h, cols=COLS):
    for size in range(120, MIN_FS - 1, -1):
        f = ImageFont.truetype(F_BOLD, size)
        if f.getlength("0" * cols) > avail_w:
            continue
        if n * round(size * 1.20) > avail_h:
            continue
        return size, round(size * 1.20)
    raise SystemExit(
        "Wide card will not fit at a readable size ({} lines, {} cols). The "
        "16:9 cut holds less than the tall one: shorten the quote, or use "
        "fewer bars.".format(n, cols))


def glow_stack(layer, wide_r, tight_r):
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    for g in (layer.filter(ImageFilter.GaussianBlur(wide_r)),
              layer.filter(ImageFilter.GaussianBlur(wide_r)),
              layer.filter(ImageFilter.GaussianBlur(tight_r)),
              layer):
        out = Image.alpha_composite(out, g)
    return out


def render(spec, out_path, fallback_image=None):
    lines = build(spec)
    fs, lh = fit(len(lines), TERM_W - 2 * PAD, H - 2 * PAD - 30 * S)
    reg = ImageFont.truetype(F_REG, fs)
    bold = ImageFont.truetype(F_BOLD, fs)

    base = Image.new("RGB", (W, H), (4, 5, 10))
    bloom = Image.new("L", (140, 90), 0)
    ImageDraw.Draw(bloom).ellipse([-30, -40, 150, 100], fill=85)
    bloom = bloom.resize((TERM_W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(45))
    base.paste(Image.new("RGB", (TERM_W, H), (10, 34, 20)), (0, 0), bloom)

    # ---- right panel: the numbers ---------------------------------------
    if spec.get("figures"):
        pl = bar_lines(spec["figures"])
        pfs, plh = fit(len(pl), ART_W - 2 * PAD, H - 2 * PAD - 30 * S, cols=PANEL_COLS)
        preg = ImageFont.truetype(F_REG, pfs)
        pbold = ImageFont.truetype(F_BOLD, pfs)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        py = (H - len(pl) * plh) // 2
        px = TERM_W + (ART_W - pbold.getlength("0" * PANEL_COLS)) / 2
        for text, colour, is_bold in pl:
            if text:
                d.text((px, py), text, font=(pbold if is_bold else preg),
                       fill=colour + (255,))
            py += plh
        panel = glow_stack(layer, 10 * S, 3 * S)
        base.paste(panel, (0, 0), panel)
    elif fallback_image:
        img = Image.open(fallback_image).convert("RGB")
        side = max(ART_W, H)
        img = img.resize((side, side), Image.LANCZOS)
        img = img.crop(((img.width - ART_W) // 2, (img.height - H) // 2,
                        (img.width - ART_W) // 2 + ART_W, (img.height - H) // 2 + H))
        base.paste(img, (TERM_W, 0))
    else:
        raise SystemExit(
            "No `figures` in the card and no --image. The wide cut needs "
            "something in the right half. Give it the comparison that carries "
            "the readout.")

    # ---- terminal --------------------------------------------------------
    y = (H - 30 * S - len(lines) * lh) // 2
    x = (TERM_W - bold.getlength("0" * COLS)) / 2
    base = paste_portrait(base, x, y, bold.getlength("0"), lh)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    yy = y
    for text, colour, is_bold in lines:
        if text:
            d.text((x, yy), text, font=(bold if is_bold else reg), fill=colour + (255,))
        yy += lh
    term = glow_stack(layer, 12 * S, 3 * S)
    base.paste(term, (0, 0), term)

    scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(scan)
    for yline in range(0, H, 3 * S):
        ds.rectangle([0, yline, W, yline + S - 1], fill=(0, 0, 0, 70))
    base.paste(scan, (0, 0), scan)

    d2 = ImageDraw.Draw(base)
    d2.rectangle([PAD // 3, PAD // 3, W - PAD // 3, H - PAD // 3],
                 outline=(120, 40, 150), width=S)
    d2.line([(TERM_W, PAD * 2), (TERM_W, H - PAD * 2)], fill=(40, 90, 65), width=S)
    d2.text((PAD, H - 26 * S), "MØNTAN1 // NARRATIVE INTELLIGENCE",
            font=ImageFont.truetype(F_BOLD, 14 * S), fill=CYAN, anchor="la")

    base.resize((W_OUT, H_OUT), Image.LANCZOS).save(out_path, optimize=True)
    return fs, len(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card")
    ap.add_argument("out")
    ap.add_argument("--image", help="fallback plate when the card has no figures")
    a = ap.parse_args()
    spec = json.load(open(a.card, encoding="utf-8"))
    size, n = render(spec, a.out, a.image)
    print("wrote {}  ({} lines at {}px)".format(a.out, n, size))
