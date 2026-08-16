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

| # | Artifact | Sport | Matchup | The call | Fan | Baseline | Resolves | Outcome |
|---|---|---|---|---|---|---|---|---|
| _(none yet)_ | | | | | | | | |
