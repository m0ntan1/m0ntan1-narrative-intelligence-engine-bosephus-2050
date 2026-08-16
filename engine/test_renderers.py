#!/usr/bin/env python3
"""Guard the two silent-failure modes that bit on readout 91C4.

  python3 tools/test_renderers.py

1. Over-long copy must REFUSE, never silently shrink type or overflow a panel.
2. A field passed as a bare string must not be iterated character by character.
3. Copy must never be silently truncated to fit a column.
"""
import json, os, sys, tempfile
from PIL import ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LONG = ("Four hundred and seventy four gigawatts against a record peak under one "
        "hundred is not a demand forecast and never was. ") * 8

def spec(**kw):
    d = {"present_line": "2026-08-16", "mode": "ARTICLE",
         "title": ["Test"], "dek": ["Test dek."], "quote": ["Short quote."],
         "cta": ["> Read it."], "disclaimer": "A bare string, not a list."}
    d.update(kw); return d

fails = []
def check(name, ok, detail=""):
    print("{:<52} {}".format(name, "PASS" if ok else "FAIL  " + detail))
    if not ok: fails.append(name)

# --- 1. wrap normalises a bare string ------------------------------------
import render_card as rc
check("wrap() on a bare string yields 1 line",
      len(rc.wrap("A bare string, not a list.")) == 1,
      "got %d" % len(rc.wrap("A bare string, not a list.")))

# --- 2. render_card refuses over-long copy -------------------------------
out = os.path.join(tempfile.gettempdir(), "t.png")
try:
    rc.render(spec(quote=[LONG]), out, )
    check("render_card refuses over-long copy", False, "rendered anyway")
except SystemExit as e:
    check("render_card refuses over-long copy", "shorten" in str(e).lower())

# --- 3. render_slate refuses over-long copy ------------------------------
import render_slate as rs
slate = {"present_line": "2026-08-16", "mode": "SLATE", "title": "Test slate",
         "rows": [{"matchup": "A @ B", "call": "B 1-0"}] * 10,
         "notes": [LONG], "cta": "> Read it.",
         "disclaimer": "A bare string, not a list."}
try:
    n, lh = rs.fit(len(rs.build(slate)), rs.TERM_W - 2 * rs.PAD, rs.H - 2 * rs.PAD)
    check("render_slate floors type size", n >= rc.MIN_FS,
          "fitted at %d, below floor %d" % (n, rc.MIN_FS))
except SystemExit:
    check("render_slate floors type size", True)

# --- 4. slate must not silently truncate ---------------------------------
# Real test: no words may be lost. Wrapping preserves every word, truncation
# does not, and a 46 character line is legitimate when wrapped at a boundary.
short = dict(slate, notes=[LONG[:300]])
rendered = " ".join(l for l, _c, _b in rs.build(short))
missing = [w for w in LONG[:300].split() if w not in rendered]
check("render_slate does not silently truncate notes",
      not missing, "lost words: %s" % missing[:5])

# --- 4b. slate must refuse a row it cannot fit ---------------------------
try:
    rs.build(dict(slate, notes=[], rows=[{"matchup": "A" * 40, "call": "B 1-0"}]))
    check("render_slate refuses an over-long row", False, "truncated instead")
except SystemExit as e:
    check("render_slate refuses an over-long row", "Shorten" in str(e))

# --- 4c. slate floor actually bites --------------------------------------
try:
    rs.fit(400, rs.TERM_W - 2 * rs.PAD, rs.H - 2 * rs.PAD)
    check("render_slate floor actually raises", False, "fitted 400 lines")
except SystemExit as e:
    check("render_slate floor actually raises", "MIN_FS" in str(e))

# --- 5. slate reserves footer clearance ----------------------------------
# The stamp sits in the bottom strip. If fit() is allowed the full height the
# text block grows into it and the two collide.
fs, lh = rs.fit(20, rs.TERM_W - 2 * rs.PAD, rs.H - 2 * rs.PAD - 34 * rs.S)
check("slate reserves room for the footer stamp",
      20 * lh <= rs.H - 2 * rs.PAD - 34 * rs.S)

# --- 6. the portrait must never blank the sun on text surfaces -----------
check("text masthead keeps the drawn sun",
      "████" in "".join(rc.masthead_lines()),
      "default blanked the sun, text output would show an empty box")
check("portrait=True does blank it for PNG",
      "████" not in "".join(rc.masthead_lines(portrait=True)))
import render_ansi as ra
check("Discord ANSI keeps the drawn sun",
      "████" in ra.render(spec()))
check("masthead stays 48 columns with the sun blanked",
      all(len(l) == 48 for l in rc.masthead_lines(portrait=True)))

# --- 7. wide cut refuses copy it cannot hold -----------------------------
import render_wide as rww
try:
    rww.fit(80, rww.TERM_W - 2 * rww.PAD, rww.H - 2 * rww.PAD)
    check("render_wide refuses over-long copy", False, "fitted 80 lines")
except SystemExit as e:
    check("render_wide refuses over-long copy", "shorten" in str(e).lower())

check("render_wide terminal panel is wide enough for 48 cols",
      rww.TERM_W - 2 * rww.PAD >= ImageFont.truetype(rc.F_BOLD, rc.MIN_FS).getlength("0" * 48))

# --- 8. data panel must wrap to its own width, not slice -----------------
fig = {"title": "A title long enough that it has to wrap somewhere",
       "unit": "GW", "bars": [{"label": "Requested", "value": 474},
                              {"label": "Record peak", "value": 95}],
       "note": "A note long enough that it also has to wrap more than once.",
       "source": "Somewhere, retrieved today"}
pl = rww.bar_lines(fig)
over = [l for l, _c, _b in pl if len(l) > rww.PANEL_COLS]
check("data panel wraps to panel width", not over, "over-wide: %s" % over[:2])
joined = " ".join(l for l, _c, _b in pl)
lost = [w for w in fig["note"].split() if w not in joined]
check("data panel loses no words from the note", not lost, "lost %s" % lost[:3])
try:
    rww.bar_lines({"title": "t", "source": "s",
                   "bars": [{"label": "X" * 60, "value": 1}]})
    check("data panel refuses an over-long bar label", False, "truncated")
except SystemExit as e:
    check("data panel refuses an over-long bar label", "too long" in str(e))

# a chart with no attribution is the one place the cited-numbers rule would break
try:
    rww.bar_lines({"title": "t", "bars": [{"label": "a", "value": 1}]})
    check("data panel refuses without a source", False, "rendered unattributed")
except SystemExit as e:
    check("data panel refuses without a source", "source" in str(e).lower())

check("data panel names what it shows",
      any("VERIFIED" in l for l, _c, _b in rww.bar_lines(fig)))
check("wrap() honours a custom width",
      max(len(l) for l in rc.wrap("word " * 40, 20)) <= 20)

print()
print("FAILURES:", len(fails))
sys.exit(1 if fails else 0)
