# Tells ledger, sports

Every call SPORTS LOGIC has made. Append on issue, resolve automatically once
the game finishes.

This ledger is the reason the mode exists. Bosephus's policy Tells resolve in
months or years. A ballgame resolves in three hours, so this is the only place
the engine generates honest forward calibration at any speed.

## Rules fixed before the first call, so the standard cannot be moved later

**Auto-graded and publishable**

| Axis | Standard |
|---|---|
| Winner | Binary. Correct or not |
| MLB margin | Final score within 2 runs of the call |
| NFL margin | Final score within 7 points of the call |
| MMA method | KO/TKO, submission, or decision. Correct or not |
| MMA round | Exact round. Scored separately from method, never merged |

**Judged and internal only**

| Axis | Standard |
|---|---|
| Pivot quality | Did the named factor actually decide it |
| Conditions | Did the weather read do any work, or was it decoration |

**The baseline, without which the hit rate means nothing.** Every call is scored
against the naive pick for that game: the home team in MLB and NFL, the betting
favourite where one is recorded. Beating a coin is not an achievement. Beating
the naive pick is. Publish the delta, never the raw number alone.

**Fan games are split out.** Any game involving Boston, Washington's MLB or NFL
club, or WVU carries `fan = yes` and is reported as its own line. If fan
accuracy trails neutral accuracy, that gets published too.


## Ledger

Issued 2026-08-16 before first pitch. Every game verified unstarted at the time
of the call: a call on a game already underway is contaminated and worth nothing.
Baseline for all ten is the naive home pick. Five calls agree with it and five
go against it, so the delta will actually measure something.

| # | Game | Matchup | The call | Fan | Baseline | Reasoning | Outcome |
|---|---|---|---|---|---|---|---|
| S-001 | `823590` | Nationals @ Mets | **Mets 5, Nationals 3** | yes | Mets (H) | Irvin at 5.79 against a 7-3 club, Scott 3.45. Called against his own team | open |
| S-002 | `824236` | White Sox @ Tigers | **White Sox 4, Tigers 2** | no | Tigers (H) | Burke 2.99 over 135 IP is the best arm on the field; Comerica suppresses | open |
| S-003 | `824477` | Marlins @ Reds | **Marlins 6, Reds 4** | no | Reds (H) | Perez 3.39 vs Lodolo 4.86, GABP at 86F and carry 1.05 pushes the total up | open |
| S-004 | `823670` | Phillies @ Twins | **Twins 6, Phillies 5** | no | Twins (H) | Painter 6.27 and Kremer 5.25, neither holds. Home side in a slugfest | open |
| S-005 | `824642` | Cardinals @ Cubs | **Cubs 7, Cardinals 5** | no | Cubs (H) | Cubs 5.17 RS/G, west wind out at Wrigley, carry 1.05. Cabrera survives on run support | open |
| S-006 | `823182` | Rockies @ Giants | **Giants 4, Rockies 2** | no | Giants (H) | Oracle at 63F, carry 1.014, the lowest on the slate. Tidwell 2.78 in a park that eats fly balls | open |
| S-007 | `824965` | Rangers @ Athletics | **Rangers 6, Athletics 4** | no | Athletics (H) | A's 5.79 RA/G is the worst mark in the game, in a hot minor league park | open |
| S-008 | `823991` | Royals @ Angels | **Royals 5, Angels 4** | no | Angels (H) | Cameron 4.45 against Johnson 6.71. Angels are hot but the arm gap is two runs | open |
| S-009 | `823912` | Brewers @ Dodgers | **Brewers 3, Dodgers 2** | no | Dodgers (H) | Henderson 0.91 WHIP against Skubal 0.93. Two aces, low total, best record takes it | open |
| S-010 | `824156` | Mariners @ Astros | **Astros 5, Mariners 3** | no | Astros (H) | Seattle 3.92 RS/G is the weakest offence on the slate, 95F so the roof is likely shut | open |

## Resolution

    python3 grade.py mlb --game <id> --call "<the call>"

Winner and margin auto-grade. Pivot quality and whether the conditions read did
any work stay judged and internal. Publish the delta against the baseline, never
the raw hit rate on its own.