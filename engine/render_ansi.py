#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emit the Discord-ready ANSI block for a Bosephus 2050 card.

  python3 render_ansi.py <card.json> [out.txt]

Prints a fenced ```ansi block sized for Discord's 2000 character message cap,
built from the same card.json and the same build_lines() the PNG renderer uses.
The two therefore cannot drift, and the seam cannot come out green.

Colour is not a per-surface judgment call, per spec 5.3. The seam is neon pink
everywhere that can carry colour. Discord's ANSI palette is fixed and magenta
is the closest it gets, so the seam is ESC[1;35m and nothing else.
"""
import json
import sys

from render_card import build_lines, MASTC, HEAD, GREEN, PINK, DIM

ESC = "\x1b"

# RGB from render_card.py -> Discord ANSI. Keep this table exhaustive: an
# unmapped colour raises rather than silently falling back to green, because a
# silent fallback is exactly how the seam turned green the first time.
ANSI = {
    MASTC: "[1;32m",   # masthead, bright green
    HEAD:  "[1;32m",   # headline and CTA, bright green
    GREEN: "[2;32m",   # body, dim green
    DIM:   "[2;32m",   # disclaimer, dim green
    PINK:  "[1;35m",   # THE SEAM. Always. Never green.
}

LIMIT = 2000


def render(spec):
    out = []
    for text, colour, _bold in build_lines(spec):
        if colour not in ANSI:
            raise SystemExit("unmapped colour {}, refusing to guess".format(colour))
        out.append(ESC + ANSI[colour] + text)
    block = "```ansi\n" + "\n".join(out) + "\n```"
    if len(block) > LIMIT:
        raise SystemExit(
            "block is {} chars, Discord's cap is {}. Shorten the card copy, "
            "do not split the masthead across messages.".format(len(block), LIMIT))
    return block


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    block = render(json.load(open(sys.argv[1], encoding="utf-8")))
    if len(sys.argv) == 3:
        open(sys.argv[2], "w", encoding="utf-8").write(block)
        print("wrote {}  ({} of {} chars)".format(sys.argv[2], len(block), LIMIT),
              file=sys.stderr)
    else:
        sys.stdout.write(block)
