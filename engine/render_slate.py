#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slate card: one PNG carrying a whole group of calls.

  python3 render_slate.py <slate.json> <out.png>

Used when a run issues a group rather than a single artifact. The PNG carries
the load: every matchup and every call is legible on the card itself, so the
image is the deliverable and the write-up is the footnote rather than the other
way round.

Same canvas, palette, font and glow as render_card.py, so a slate and a single
card are the same object with different contents. The character plate that used
to sit on the right was dropped once the portrait moved into the masthead: one
face per card is enough, and the freed width goes to the calls, which are what
the card is for.
"""
import json
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from render_card import (F_REG, F_BOLD, masthead_lines, paste_portrait, strip,
                         seam, wrap, MIN_FS, GREEN, MASTC, HEAD, PINK, DIM, CYAN)

S = 2
W_OUT, H_OUT = 1200, 1500      # same canvas as the article card
W, H = W_OUT * S, H_OUT * S
TERM_W = W
PAD = 40 * S
COLS = 48


def rows_to_lines(spec):
    """Matchup left, call right, inside 46 columns. Markers explained on card."""
    out = []
    for r in spec["rows"]:
        mark = "*" if r.get("fan") else ("^" if r.get("against_baseline") else " ")
        if len(r["matchup"]) > 28 or len(r["call"]) > 17:
            raise SystemExit(
                "Row will not fit: matchup max 28 chars, call max 17. Got "
                "{!r} / {!r}. Shorten it; do not let the card cut it silently."
                .format(r["matchup"], r["call"]))
        line = "{:<28}{:>17} {}".format(r["matchup"], r["call"], mark)
        out.append((line, HEAD if r.get("fan") else GREEN, bool(r.get("fan"))))
    return out


def build(spec):
    lines = [(m, MASTC, True) for m in masthead_lines(portrait=True)]
    lines.append(("╠══════════════════════════════════════════════╣", MASTC, True))
    lines.append((strip(spec), MASTC, True))
    lines.append(("╚══════════════════════════════════════════════╝", MASTC, True))
    lines.append(("", GREEN, False))
    for ln in wrap(spec["title"].upper()):
        lines.append((ln, HEAD, True))
    lines.append(("", GREEN, False))
    lines.append((seam(spec["present_line"], override=spec.get("seam_override")), PINK, True))
    lines.append(("", GREEN, False))
    lines.extend(rows_to_lines(spec))
    lines.append(("", GREEN, False))
    for n in wrap(spec.get("notes", [])):
        lines.append((n, GREEN, False))
    lines.append(("", GREEN, False))
    for ln in wrap(spec["cta"]):
        lines.append((ln, HEAD, True))
    lines.append(("", GREEN, False))
    for ln in wrap(spec.get("disclaimer", "Constructed. Not a forecast, not advice.")):
        lines.append((ln, DIM, False))
    return lines


def fit(n, avail_w, avail_h):
    """Same floor as the canonical card. Duplicating this logic is how the two
    renderers drifted in the first place, so MIN_FS is imported, not restated."""
    for size in range(120, MIN_FS - 1, -1):
        f = ImageFont.truetype(F_BOLD, size)
        if f.getlength("0" * COLS) > avail_w:
            continue
        if n * round(size * 1.20) > avail_h:
            continue
        return size, round(size * 1.20)
    raise SystemExit(
        "Slate will not fit at a readable size ({} lines). Trim rows or notes. "
        "Do not lower MIN_FS.".format(n))


def render(spec, out_path):
    lines = build(spec)
    # reserve the footer strip so the text block cannot crowd the stamp
    fs, lh = fit(len(lines), TERM_W - 2 * PAD, H - 2 * PAD - 34 * S)
    reg = ImageFont.truetype(F_REG, fs)
    bold = ImageFont.truetype(F_BOLD, fs)

    base = Image.new("RGB", (W, H), (4, 5, 10))

    bloom = Image.new("L", (120, 105), 0)
    ImageDraw.Draw(bloom).ellipse([-30, -40, 140, 105], fill=85)
    bloom = bloom.resize((TERM_W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(50))
    base.paste(Image.new("RGB", (TERM_W, H), (10, 34, 20)), (0, 0), bloom)

    y = (H - 34 * S - len(lines) * lh) // 2
    x = (TERM_W - bold.getlength("0" * COLS)) / 2
    base = paste_portrait(base, x, y, bold.getlength("0"), lh)

    layer = Image.new("RGBA", (TERM_W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
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

    ImageDraw.Draw(base).rectangle(
        [PAD // 3, PAD // 3, W - PAD // 3, H - PAD // 3],
        outline=(120, 40, 150), width=S)
    ImageDraw.Draw(base).text(
        (W // 2, H - PAD // 2), "MØNTAN1 // NARRATIVE INTELLIGENCE",
        font=ImageFont.truetype(F_BOLD, 15 * S), fill=CYAN, anchor="ms")

    base.resize((W_OUT, H_OUT), Image.LANCZOS).save(out_path, optimize=True)
    return fs, len(lines)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    size, n = render(spec, sys.argv[2])
    print("wrote {}  ({} lines at {}px)".format(sys.argv[2], n, size))
