# Tells ledger, sports

Every call SPORTS LOGIC has made. Append on issue, resolve automatically once
the game finishes.

This ledger is the reason the mode exists. Bosephus's policy Tells resolve in
months or years. A ballgame resolves in three hours, so this is the only place
the engine generates honest forward calibration at any speed.

## Rules fixed before the first call, so the standard cannot be moved later

**The pivot is the headline, per spec 6.0.** Outcomes are the noisy surface and
this engine will miss them routinely. What gets published first is whether the
named catalyst fired, on its date. Anyone can post a score.

| Claim | Graded | Published |
|---|---|---|
| Pivot condition fired | Binary, from the box score | **Headline** |
| Branch followed given the condition | Binary | **Headline** |
| Winner and margin | Mechanical | Secondary line |

Pivot verdict is the two by two, per spec 7.1: fired and followed is confirmed,
fired and not followed means the named hinge was not the hinge, not fired but
followed anyway means the hinge was irrelevant, neither is confirmed by
contrapositive.

**Series S and C predate this rule.** Their pivot blocks carry a methodological
assumption rather than a conditional mechanism, so they are graded on outcome
only and their pivots are marked N/A rather than scored. Every slate from
2026-08-17 forward carries a real hinge.

**Outcome axes, auto-graded**

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

| # | Game | Matchup | The call | Pivot condition | Fired | Followed | Verdict | Fan | Baseline | Outcome |
|---|---|---|---|---|---|---|---|---|---|---|
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


## Ledger, NCAA football week 1

Issued 2026-08-16, twelve to twenty-one days before kickoff. Two things a reader
should know before reading a hit rate off these.

**No weather.** NWS forecasts reach 6.5 days. These games are 12 to 21 days out,
so the CONDITIONS block is absent from all ten and the weather layer contributed
nothing. It can be layered in nearer kickoff, but the calls are locked now and do
not move.

**No current-season data.** Week 1 means every record is 0-0. These rest on 2025
final records and home field, nothing more. ESPN's pointsFor and pointsAgainst
fields are not season totals (North Carolina shows PF 16 for a 4-8 year), so they
were ignored rather than trusted. Expect these to grade worse than the MLB set,
and if they do not, that is worth knowing too.

Margin threshold is 10 points for CFB, fixed here before any game is played.
Six calls agree with the naive home pick and four go against it.

| # | Game | Date | Matchup | The call | Fan | Baseline | Reasoning | Outcome |
|---|---|---|---|---|---|---|---|---|
| C-001 | `401856780` | 2026-09-05 | Coastal Carolina @ West Virginia | **West Virginia 27, Coastal Carolina 20** | yes | WVU (H) | WVU 4-8 in 2025 and Coastal 6-7. Home opener, but a four-win team does not blow anybody out. Called close on purpose | open |
| C-002 | `401858206` | 2026-09-05 | Miami @ Stanford | **Miami 38, Stanford 13** | no | Stanford (H) | 13-3 against 4-8. The only thing road status buys Stanford here is a nicer bus ride | open |
| C-003 | `401858209` | 2026-09-05 | Tulane @ Duke | **Tulane 28, Duke 24** | no | Duke (H) | 11-3 on the road against 9-5. Records say the visitor is the better team | open |
| C-004 | `401864432` | 2026-09-06 | Western Kentucky @ Nevada | **Western Kentucky 31, Nevada 21** | no | Nevada (H) | 9-4 at 3-9. Road favourite, and Nevada gave up the season last year | open |
| C-005 | `401860878` | 2026-09-05 | Wyoming @ Colorado State | **Wyoming 24, Colorado State 17** | no | Colorado State (H) | 4-8 at 2-10. Border War, and the worse team is at home | open |
| C-006 | `401858425` | 2026-09-05 | North Texas @ Indiana | **Indiana 34, North Texas 20** | no | Indiana (H) | 16-0 hosting 12-2. North Texas is real, which is why this is not a blowout | open |
| C-007 | `401858433` | 2026-09-05 | Boise State @ Oregon | **Oregon 35, Boise State 17** | no | Oregon (H) | 13-2 at home against 9-5. Boise travels well and still loses this by three scores | open |
| C-008 | `401856660` | 2026-09-05 | Clemson @ LSU | **LSU 27, Clemson 24** | no | LSU (H) | Both 7-6. Dead even on the record, so the call is home field and nothing else | open |
| C-009 | `401858438` | 2026-09-06 | Wisconsin @ Notre Dame | **Notre Dame 31, Wisconsin 13** | no | Notre Dame (H) | 10-2 hosting 4-8 | open |
| C-010 | `401858437` | 2026-09-06 | Washington State @ Washington | **Washington 30, Washington State 23** | no | Washington (H) | Apple Cup. 9-4 over 7-6, and rivalry games run closer than the gap suggests | open |

## Resolution

    python3 grade.py mlb --game <id> --call "<the call>"

Winner and margin auto-grade. Pivot quality and whether the conditions read did
any work stay judged and internal. Publish the delta against the baseline, never
the raw hit rate on its own.