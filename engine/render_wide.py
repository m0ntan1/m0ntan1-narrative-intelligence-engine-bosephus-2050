#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wide 1600x900 card for ARTICLE readouts. Terminal left, the story's own image
rendered as ASCII on the right.

  python3 render_wide.py <card.json> <out.png> --url https://source/article
  python3 render_wide.py <card.json> <out.png> --image local.jpg

This is the 16:9 cut for link unfurls. 48 columns of monospace leaves a 16:9
canvas mostly empty, which is why the earlier version of this file needed a
character plate to fill the right half. An image belonging to the article is a
better answer than a stock portrait: it is about the story rather than about us.

**The source image is converted to ASCII, not tinted.** That is the house look,
it matches the masthead portrait, and it matters for a second reason: a card
that republishes a news outlet's photograph is a reproduction, and one that
rebuilds it out of characters is a transformation. For anything public, prefer
an image you own or one you have generated. The renderer does not check rights
and cannot.
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_card import (F_REG, F_BOLD, MIN_FS, masthead_lines, paste_portrait,
                         strip, seam, wrap, GREEN, MASTC, HEAD, PINK, DIM, CYAN)

S = 2
W_OUT, H_OUT = 1600, 900
W, H = W_OUT * S, H_OUT * S
# 48 columns at the minimum readable size needs ~840px, so the terminal takes
# the larger share and the ASCII panel gets what is left. Narrower than this and
# fit() refuses, which is how the split was arrived at rather than guessed.
TERM_W = 880 * S
ART_W = W - TERM_W
PAD = 30 * S
COLS = 48

# Dark to light. Blocks at the top end keep it in the same family as the
# masthead art rather than looking like a different toy.
RAMP = " .:-=+*#%▒▓█"

UA = "Mozilla/5.0 (compatible; montan1-nie/1.0; +rick@montanibitcoin.com)"


def fetch_lead_image(url):
    """Pull og:image, then twitter:image, from a source article."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    for prop in ("og:image", "twitter:image"):
        for pat in (r'<meta[^>]+(?:property|name)=["\']' + prop + r'["\'][^>]+content=["\']([^"\']+)',
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']' + prop):
            m = re.search(pat, html, re.I)
            if m:
                src = m.group(1)
                data = urllib.request.urlopen(
                    urllib.request.Request(src, headers={"User-Agent": UA}), timeout=30).read()
                return Image.open(io.BytesIO(data)).convert("RGB"), src
    raise SystemExit("No og:image or twitter:image on {}. Pass --image instead.".format(url))


def tonal_report(img):
    """Warn when a source is a poor ASCII subject before wasting a render.

    ASCII needs a clear silhouette and midtones spread across the ramp. A dark
    interior photograph, which is most news photography of infrastructure, is
    mostly black with a couple of blown highlights, and it converts into two
    bright shapes on an empty field. That is the renderer being faithful, not
    broken, but the result is unusable and it is better to say so up front.
    """
    h = img.convert("L").histogram()
    tot = sum(h) or 1
    dark = sum(h[:64]) / tot
    mid = sum(h[64:192]) / tot
    if dark > 0.65 or mid < 0.25:
        print("  ! Poor ASCII subject: {:.0f}% of this image is near-black and "
              "only {:.0f}% is midtone. Expect bright shapes on an empty field. "
              "A high-contrast subject with a clear silhouette converts far "
              "better. Pass --image to use a different one."
              .format(dark * 100, mid * 100), file=sys.stderr)
    return dark, mid


def asciify(img, cols, rows, font):
    """Rebuild the image as a grid of characters chosen by cell luminance.

    Fits the whole frame inside the panel rather than cropping to fill it. The
    panel is portrait and news photographs are landscape, so cropping to fill
    takes a narrow vertical slice and magnifies it until the subject is
    unreadable. Letterboxing against black costs nothing here because the ground
    is already black.
    """
    cw = font.getlength("0")
    lh = font.size * 1.16

    cell_aspect = lh / cw
    want = (cols * cw) / (rows * lh)
    have = img.width / img.height
    if have > want:                     # source wider: full width, fewer rows
        used_cols = cols
        used_rows = max(1, int(cols * cw / (img.width / img.height) / lh))
    else:                               # source taller: full height, fewer cols
        used_rows = rows
        used_cols = max(1, int(rows * lh * (img.width / img.height) / cw))
    c_off = (cols - used_cols) // 2
    r_off = (rows - used_rows) // 2

    small = img.convert("L").resize((used_cols, used_rows), Image.LANCZOS)

    # Normalise before mapping to the ramp. News photographs are frequently
    # dark and tonally compressed, and an unnormalised map sends most of the
    # frame to blank, leaving only the highlights: the subject disappears and
    # what is left reads as an abstract shape. Autocontrast spreads the range,
    # equalize then flattens the histogram so the ramp is used evenly, and the
    # two are blended so the result keeps some of the original modelling.
    small = Image.blend(ImageOps.autocontrast(small, cutoff=1),
                        ImageOps.equalize(small), 0.55)
    px = small.load()

    layer = Image.new("RGBA", (int(cols * cw), int(rows * lh)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for r in range(used_rows):
        for c in range(used_cols):
            v = px[c, r]
            ch = RAMP[min(len(RAMP) - 1, v * len(RAMP) // 256)]
            if ch == " ":
                continue
            # brighter glyphs at the dense end, so the panel has tonal range
            shade = MASTC if v > 170 else (GREEN if v > 90 else DIM)
            d.text(((c + c_off) * cw, (r + r_off) * lh), ch, font=font,
                   fill=shade + (255,))
    return layer


def build(spec):
    lines = [(m, MASTC, True) for m in masthead_lines(portrait=True)]
    lines.append(("╠══════════════════════════════════════════════╣", MASTC, True))
    lines.append((strip(spec), MASTC, True))
    lines.append(("╚══════════════════════════════════════════════╝", MASTC, True))
    lines.append(("", GREEN, False))
    for ln in wrap(spec["title"]):
        lines.append((ln.upper(), HEAD, True))
    lines.append(("", GREEN, False))
    lines.append((seam(spec["present_line"]), PINK, True))
    lines.append(("", GREEN, False))
    for ln in wrap(spec["quote"]):
        lines.append((ln, GREEN, False))
    lines.append(("", GREEN, False))
    for ln in wrap(spec["cta"]):
        lines.append((ln, HEAD, True))
    return lines


def fit(n, avail_w, avail_h):
    for size in range(120, MIN_FS - 1, -1):
        f = ImageFont.truetype(F_BOLD, size)
        if f.getlength("0" * COLS) > avail_w:
            continue
        if n * round(size * 1.20) > avail_h:
            continue
        return size, round(size * 1.20)
    raise SystemExit(
        "Wide card copy will not fit ({} lines). The 16:9 cut holds less than "
        "the tall one: shorten the quote.".format(n))


def render(spec, source_img, out_path):
    lines = build(spec)
    fs, lh = fit(len(lines), TERM_W - 2 * PAD, H - 2 * PAD - 30 * S)
    reg = ImageFont.truetype(F_REG, fs)
    bold = ImageFont.truetype(F_BOLD, fs)

    base = Image.new("RGB", (W, H), (4, 5, 10))
    bloom = Image.new("L", (140, 90), 0)
    ImageDraw.Draw(bloom).ellipse([-30, -40, 150, 100], fill=85)
    bloom = bloom.resize((TERM_W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(45))
    base.paste(Image.new("RGB", (TERM_W, H), (10, 34, 20)), (0, 0), bloom)

    # ---- ASCII panel -----------------------------------------------------
    afont = ImageFont.truetype(F_REG, 13 * S // 2)   # finer grid, more detail
    cw, alh = afont.getlength("0"), afont.size * 1.16
    cols, rows = int(ART_W / cw), int(H / alh)
    tonal_report(source_img)
    art = asciify(source_img, cols, rows, afont)
    glow = art.filter(ImageFilter.GaussianBlur(5 * S))
    panel = Image.new("RGBA", art.size, (0, 0, 0, 0))
    for g in (glow, art):
        panel = Image.alpha_composite(panel, g)
    base.paste(panel, (TERM_W, 0), panel)

    fade = Image.new("L", (ART_W, 1))
    fp = fade.load()
    for x in range(ART_W):
        t = x / (ART_W * 0.22)
        fp[x, 0] = 0 if t >= 1 else int(255 * (1 - t) ** 1.5)
    base.paste(Image.new("RGB", (ART_W, H), (4, 5, 10)), (TERM_W, 0),
               fade.resize((ART_W, H)))

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
    wide = layer.filter(ImageFilter.GaussianBlur(12 * S))
    tight = layer.filter(ImageFilter.GaussianBlur(3 * S))
    term = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for g in (wide, wide, tight, layer):
        term = Image.alpha_composite(term, g)
    base.paste(term, (0, 0), term)

    scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(scan)
    for yline in range(0, H, 3 * S):
        ds.rectangle([0, yline, W, yline + S - 1], fill=(0, 0, 0, 70))
    base.paste(scan, (0, 0), scan)

    d2 = ImageDraw.Draw(base)
    d2.rectangle([PAD // 3, PAD // 3, W - PAD // 3, H - PAD // 3],
                 outline=(120, 40, 150), width=S)
    d2.text((PAD, H - 26 * S), "MØNTAN1 // NARRATIVE INTELLIGENCE",
            font=ImageFont.truetype(F_BOLD, 14 * S), fill=CYAN, anchor="la")

    base.resize((W_OUT, H_OUT), Image.LANCZOS).save(out_path, optimize=True)
    return fs, len(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card")
    ap.add_argument("out")
    ap.add_argument("--url", help="source article; its og:image is used")
    ap.add_argument("--image", help="local image instead")
    a = ap.parse_args()

    if a.image:
        img, src = Image.open(a.image).convert("RGB"), a.image
    elif a.url:
        img, src = fetch_lead_image(a.url)
    else:
        raise SystemExit("give --url or --image")

    spec = json.load(open(a.card, encoding="utf-8"))
    size, n = render(spec, img, a.out)
    print("wrote {}  ({} lines at {}px)".format(a.out, n, size))
    print("image source: {}".format(src), file=sys.stderr)
