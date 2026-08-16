# Data sources, and why

Written after a fair criticism: ESPN was the default across every sport for one
bad reason. A single endpoint covered several of them, so nobody checked whether
it was best at any of them. It is not. This is the survey that should have
happened first.

| Sport | Using | Why | Status |
|---|---|---|---|
| **MLB** | `statsapi.mlb.com` | The league's own API. Keyless, no rate limit hit yet, full box scores with per-pitcher innings, earned runs and pitch counts. Nothing beats it | Verified, in use |
| **MMA** | `ufcstats.com` | **UFC's own statistics site.** Per-bout knockdowns, strikes, takedowns, submission attempts, method, round, finish time. Reddit's r/MMA consensus pick and the search agreed | Verified, in use |
| **NCAA FB** | ESPN, moving to CFBD | `collegefootballdata.com` is the comprehensive free source: SP+, returning production, drives, plays, lines. Needs a free bearer key | **Recommended switch**, needs a key |
| **NFL** | ESPN | `nflverse` publishes play-by-play and box scores as CSVs on GitHub, keyless and far richer | Worth switching, not urgent |
| **Weather** | `api.weather.gov` | NOAA's own. Three surfaces: raw gridpoint (59 variables), active alerts, station observations | Verified, in use |

## What ESPN was actually failing at

The MMA summary endpoint returned 404 on live event IDs. Competitor statistics
came back empty. The core API exposed bouts but the shape could not be confirmed.
Meanwhile ufcstats.com had the whole card with grappling numbers on it.

ESPN stays for NFL and CFB scoreboards until those are moved. It is fine for
schedules and scores and thin for anything a pivot is written against.

## The ufcstats fetch caveat

ufcstats.com serves plain curl a three kilobyte shell. Firecrawl gets the real
page. There is no Firecrawl key reachable from a script here, so the split is:

1. Fetch with Firecrawl: `http://www.ufcstats.com/event-details/<id>`, markdown
2. Parse and grade with `sports/ufcstats.py`, which is deterministic and tested

```
python3 sports/ufcstats.py card.md
python3 sports/ufcstats.py card.md --bout Makhachev --fighter Makhachev --condition "td>=1"
```

## Worked example: UFC 330, 2026-08-15

Makhachev def. Machado Garry, unanimous decision, five rounds.

| | Kd | Str | Td | Sub |
|---|---|---|---|---|
| Makhachev | 1 | 22 | **7** | 0 |
| Machado Garry | 0 | **29** | 0 | 0 |

The grappling pivot, *Makhachev wins if he gets it to the mat*, resolves
**MET** on seven takedowns to zero, and the branch followed. **CONFIRMED.**

A striking pivot on the same fight resolves the other way. Garry out-landed him
29 to 22 and lost anyway, so a hinge written on strike volume would be
**REFUTED** even though the winner was called correctly.

That is the two by two doing exactly what it is for: one fight, one correct
outcome, and two hinges that grade oppositely.
