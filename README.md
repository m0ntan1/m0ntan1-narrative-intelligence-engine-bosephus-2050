# MØNTAN1 Narrative Intelligence Engine

![Bosephus 2050](docs/assets/social-card.png)

A **Narrative Intelligence engine** is not an agent, a bot, or a report generator. It is a machine that constructs a plausible narrative over a verified factual record, keeps a visible seam between the two halves, and leaves falsifiable markers behind so it can be graded later.

The distinction is the whole product, and it is also the entire compliance posture. Call the thing an agent and a reader will take its output as a forecast, which is the one thing it must never be.

This repo holds the reference implementation, **Bosephus 2050**, along with the tooling that makes its output travel.

---

## The seven load-bearing parts

A spec missing any of these is not an engine. It is a prompt with good prose.

| # | Part | Why it is load-bearing |
|---|---|---|
| 1 | **A fixed vantage point** used as the reasoning device, not as decoration | The voice is the analytic method. B0SEPHUS G. ALTAMONT writes from 2050, so everything between now and then is settled history he is recounting rather than a future he is guessing at |
| 2 | **A hard dated seam** between what is retrieved and cited and what is constructed | Rendered as a typographic object, not left as a prose obligation. A reviewer checks compliance at a glance instead of reading for it |
| 3 | **Persistent state** across runs | Without it, invocation one gives you a 2050 where the dollar broke in 2031 and invocation two gives you one where it never did. State is the difference between a character and a bit |
| 4 | **Falsifiable near-term markers** written to a ledger | The part everyone skips, because it is the only part that can make the engine look bad later. Skip it and you have no way to know whether the thing is any good |
| 5 | **A fixed output schema** | Stops the voice wandering into fiction with no analytic spine |
| 6 | **Frozen presentation art** and a required card emit | Markdown does not survive a paste into a chat client. The card is the only form that travels |
| 7 | **A refusal posture** | Constructed content is never dressed as forecast, prediction, or advice |

Full treatment in [SPEC.md](SPEC.md).

---

## The seam

This is the piece worth stealing even if you never build anything else here. Between the cited half and the constructed half of every artifact sits a dated rule:

```
▞▚▞▚▞▚▞▚▞ PRESENT LINE 2026-08-16 · CONSTRUCTED BELOW ▞▚▞▚▞▚▞▚▞▚
```

Everything above it was retrieved and carries a source. Everything below it was constructed and carries none, because there is nothing to source. The rule is mandatory, no cited claim may appear beneath it, and its absence is a failed artifact rather than a style lapse.

Recall is implemented as retrieval, never as memory. The engine's past is accurate because it looks things up, not because a model remembers them.

---

## Quickstart

Requires Python 3, Pillow, and a monospace font with half-block glyph coverage. JetBrains Mono Nerd Font is the reference face. Plenty of mono faces lack `▀ ▄ █ ▞ ▚ ▁` and will render tofu.

```bash
pip install pillow
python3 engine/render_card.py engine/cards/2026-08-16_clarity-act.card.json out.png
```

If your fonts live somewhere unusual:

```bash
NIE_FONT_DIR=/path/to/fonts python3 engine/render_card.py <card.json> <out.png>
```

The card JSON carries seven fields and nothing else:

```json
{
  "present_line": "2026-08-16",
  "mode": "ARTICLE",
  "canon": "v01",
  "title":      ["The bill that could not be written while he was in office"],
  "dek":        ["Warren, the CLARITY Act, and a cloture motion filed at 4:52 in the morning."],
  "quote":      ["\"Stop counting votes and go read the manager's amendment...\""],
  "cta":        ["▸ Read the full recollection of the events that follow."]
}
```

Two things are deliberately not adjustable:

- **Do not hand-wrap the copy.** Write each field as one unbroken string. The renderer wraps to 46 columns. Hand-wrapping is exactly where an author breaks the column grid.
- **Type size is not a choice.** The renderer picks the largest size at which 48 columns fit the width and every line fits the height. If it refuses, shorten the copy. Do not shrink the type and do not edit the script to make room.

For chat surfaces, `render_ansi.py` emits a Discord-ready fenced block from the
same JSON and the same line builder, so the text cut and the PNG cut cannot drift:

```bash
python3 engine/render_ansi.py engine/cards/2026-08-16_clarity-act.card.json
```

**The seam is always neon pink,** `#FF4FD8`, on every surface that can carry
colour. It is the one element that breaks the green, and that is the point: in a
field of phosphor green the eye lands on the seam first, which is the reading
order the artifact wants. The ANSI emitter raises on an unmapped colour rather
than falling back to green, because a silent fallback is exactly how a seam goes
green without anyone noticing.

`render_card_with_element.py` is a wide 1600x900 variant with a character plate beside the terminal. It shares the masthead and wrap logic with the canonical renderer so the two cannot drift.

---

## Layout

```
SPEC.md                  The full Bosephus 2050 spec, including the system prompt
engine/
  masthead.txt           Frozen art. Three cuts: 64 col, 48 col chat, 7-bit ASCII
  render_card.py         Canonical card emit, 1200x1500, terminal only
  render_ansi.py         Discord ANSI block, seam forced to neon pink
  render_card_with_element.py  Wide variant with character plate, 1600x900
  cards/                 Card copy, one JSON per artifact
examples/
  2026-08-16_clarity-act.md    A complete artifact
  2026-08-16_clarity-act_card.png
  canon-2050.md          Persistent timeline state
  tells-ledger.md        The calibration record
```

---

## The worked example

[`examples/2026-08-16_clarity-act.md`](examples/2026-08-16_clarity-act.md) is a real run against the CLARITY Act cloture filing of 2026-08-08. It carries six cited hard numbers, a named pivot, three weighted forks, and five Tells, the first two of which resolve on 2026-09-16.

Read it for the seam and for what sits on either side of it. Note that the market data came from a market data API rather than from press reporting, and that where the largest move in the window looked idiosyncratic the artifact says so and declines to attribute it. Note also that a political claim central to the story is quoted as a claim, with its source, rather than laundered into a verified number.

---

## What this is honest about

- **The engine is not a forecaster.** Every artifact says so in its own footer. Constructed content is a reasoning device.
- **Backtests validate the harness, not the forecaster.** A constructor writing a 2015 branch already knows about the pandemic and the 2022 inflation shock, and no amount of good faith unknows it inside one session. Run 01 scored the machinery at 78.8%. Its 73.5% reality-match measures how well something that knew the answer could write a plausible path to it, which is not a hit rate and is not published as one. Only forward Tells validate the forecaster.
- **Weight bands, never percentages.** Forks are load-bearing, live, or tail. A decimal on a narrative artifact makes it look like model output, which is the exact confusion the whole posture exists to prevent.
- **Boring is allowed and periodically required.** Most decades are mostly continuity with two or three real discontinuities. If every beat is a discontinuity, the artifact is fiction.

---

## Rights

No license is granted. All rights reserved by MØNTAN1 LLC, Rick Thomas. The Bosephus persona, the spec prose, and the artwork are not public domain and are not open source. If you want to use any of it, ask.

Built in West Virginia. Educate. Disintermediate. Innovate. Build.
