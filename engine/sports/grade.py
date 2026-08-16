#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolve a SPORTS LOGIC call against the actual result.

  python3 grade.py mlb --game 823344 --call "Red Sox 5, Pirates 3"
  python3 grade.py mlb --game 823344 --call-json '{"away":5,"home":3}'

Grades only what can be graded objectively. Pivot quality and whether the
conditions read did any work are judged by a human and stay internal, because a
model grading its own narrative is not calibration, it is marking its own
homework.

The baseline is not optional. A hit rate with no baseline is a number that
sounds like something and means nothing: picking the home team wins a lot of
games on its own. Every call is scored against the naive pick for that game and
the delta is what gets reported.
"""
import argparse
import json
import re
import sys
import urllib.request

UA = "montan1-narrative-intelligence-engine (rick@montanibitcoin.com)"
ESPN_UA = "curl/8.7.1"   # see get(): ESPN 403s descriptive and browser UAs
MLB = "https://statsapi.mlb.com/api/v1"

MARGIN = {"mlb": 2, "nfl": 7, "cfb": 10}   # fixed in tells-sports.md, before any call
ESPN = "https://site.api.espn.com/apis/site/v2/sports"


def get(url):
    """Per-host User-Agent, and this is not cosmetic.

    NWS policy requires a descriptive UA with contact details. ESPN's edge does
    the opposite: it 403s a descriptive UA and a browser UA, and serves a plain
    curl UA. Sending one UA everywhere breaks one of the two, silently, and the
    ESPN failure looks like a missing game rather than a blocked request.
    """
    ua = ESPN_UA if "espn.com" in url else UA
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def mlb_final(game_pk):
    d = get("{}.1/game/{}/feed/live".format(MLB, game_pk))
    ls = d["liveData"]["linescore"]
    state = d["gameData"]["status"]["detailedState"]
    if state not in ("Final", "Game Over", "Completed Early"):
        raise SystemExit("game is {}, not final. Nothing to grade yet.".format(state))
    return {
        "away": ls["teams"]["away"]["runs"],
        "home": ls["teams"]["home"]["runs"],
        "away_name": d["gameData"]["teams"]["away"]["name"],
        "home_name": d["gameData"]["teams"]["home"]["name"],
    }


def espn_final(sport, event_id):
    path = {"cfb": "football/college-football", "nfl": "football/nfl"}[sport]
    d = get("{}/{}/summary?event={}".format(ESPN, path, event_id))
    comp = ((d.get("header") or {}).get("competitions") or [{}])[0]
    if not comp.get("status", {}).get("type", {}).get("completed"):
        raise SystemExit("game is {}, not final. Nothing to grade yet.".format(
            comp.get("status", {}).get("type", {}).get("description", "unknown")))
    out = {}
    for c in comp.get("competitors", []):
        side = "home" if c.get("homeAway") == "home" else "away"
        out[side] = int(c.get("score"))
        out[side + "_name"] = (c.get("team") or {}).get("displayName")
    return out


def parse_call(text, final):
    """Pull two integers out of a call written the way Bosephus writes it."""
    nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", text)]
    if len(nums) < 2:
        raise SystemExit("could not read two scores out of: {!r}".format(text))
    def locate(full):
        """Find where a club is named, however the writer shortened it.

        Tries the longest form first and works down: the full display name,
        then progressively shorter word-prefixes, then the nickname alone.
        Longest-first is what disambiguates Washington from Washington State,
        and prefix matching is what catches "Duke" inside "Duke Blue Devils"
        and "West Virginia" inside "West Virginia Mountaineers".

        Matching only the full name and the nickname, as this did originally,
        silently reversed every college call: neither form appears in the way
        anybody actually writes a score line.
        """
        low = text.lower()
        parts = full.split()
        cands = [" ".join(parts[:i]) for i in range(len(parts), 0, -1)]
        cands.append(parts[-1])
        for c in cands:
            i = low.find(c.lower())
            if i != -1:
                return i
        return -1

    away_first = locate(final["away_name"])
    home_first = locate(final["home_name"])
    if away_first == -1 or home_first == -1:
        print("  ! team names not both found in the call, assuming away first",
              file=sys.stderr)
        return {"away": nums[0], "home": nums[1]}
    return ({"away": nums[0], "home": nums[1]} if away_first < home_first
            else {"home": nums[0], "away": nums[1]})


# --------------------------------------------------------------- the pivot

PIVOT_VERDICT = {
    (True, True):   ("CONFIRMED", "condition fired and the branch followed"),
    (True, False):  ("REFUTED", "condition fired and the branch did not follow: "
                                "the named hinge was not the hinge"),
    (False, True):  ("REFUTED", "condition did not fire and the branch followed "
                                "anyway: the hinge was irrelevant"),
    (False, False): ("CONFIRMED", "condition did not fire and the branch did not "
                                  "follow, which is the contrapositive"),
}


def grade_pivot(condition_met, branch_followed):
    """Grade a conditional hinge on both halves, not just the outcome.

    A sports pivot is a claim of the form "A wins if B", where B is observable
    in the box score. Checking only whether A won grades the call, not the
    reasoning. Both cells have to be read together:

        fired + followed          confirmed
        fired + did not follow    refuted, the hinge was not the hinge
        did not fire + followed   refuted, the hinge was irrelevant
        did not fire + neither    confirmed, by contrapositive

    Rows two and three are the ones worth having. They are the only way to
    catch a pivot that happened to be attached to a correct outcome, which is
    otherwise indistinguishable from insight.
    """
    verdict, why = PIVOT_VERDICT[(bool(condition_met), bool(branch_followed))]
    return {"condition_met": bool(condition_met),
            "branch_followed": bool(branch_followed),
            "pivot_verdict": verdict, "reason": why}


def mlb_observables(game_pk):
    """Box-score facts a hinge is usually written against, for resolving one."""
    d = get("{}.1/game/{}/feed/live".format(MLB, game_pk))
    box = get("{}/game/{}/boxscore".format(MLB, game_pk))
    out = {}
    for side in ("away", "home"):
        t = box["teams"][side]
        pitchers = t.get("pitchers", [])
        starter = t["players"].get("ID%d" % pitchers[0]) if pitchers else None
        bat = t["teamStats"]["batting"]
        pit = t["teamStats"]["pitching"]
        out[side] = {
            "team": d["gameData"]["teams"][side]["name"],
            "runs": bat.get("runs"), "hits": bat.get("hits"),
            "strikeouts_by_batters": bat.get("strikeOuts"),
            "left_on_base": bat.get("leftOnBase"),
            "starter": starter["person"]["fullName"] if starter else None,
            "starter_ip": starter["stats"]["pitching"].get("inningsPitched") if starter else None,
            "starter_er": starter["stats"]["pitching"].get("earnedRuns") if starter else None,
            "starter_pitches": starter["stats"]["pitching"].get("numberOfPitches") if starter else None,
            "pitchers_used": len(pitchers),
            "team_ip": pit.get("inningsPitched"),
            "home_runs": bat.get("homeRuns"),
        }
    return out


def grade(sport, final, call):
    actual_winner = "home" if final["home"] > final["away"] else "away"
    called_winner = "home" if call["home"] > call["away"] else "away"
    margin = abs((call["away"] - call["home"]) - (final["away"] - final["home"]))
    within = margin <= MARGIN[sport]

    return {
        "final": "{} {}, {} {}".format(final["away_name"], final["away"],
                                       final["home_name"], final["home"]),
        "called": "{} {}, {} {}".format(final["away_name"], call["away"],
                                        final["home_name"], call["home"]),
        "winner_correct": called_winner == actual_winner,
        "margin_error": margin,
        "within_margin": within,
        "exact_score": call["away"] == final["away"] and call["home"] == final["home"],
        # naive pick for this game, per tells-sports.md
        "baseline_pick": "home",
        "baseline_correct": actual_winner == "home",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sport", choices=["mlb", "cfb", "nfl"])
    ap.add_argument("--game", required=True)
    ap.add_argument("--call")
    ap.add_argument("--call-json")
    ap.add_argument("--pivot-fired", choices=["yes", "no"],
                    help="did the named condition occur")
    ap.add_argument("--pivot-followed", choices=["yes", "no"],
                    help="did the predicted branch follow")
    ap.add_argument("--observables", action="store_true",
                    help="print the box-score facts a hinge is written against")
    a = ap.parse_args()

    if a.observables:
        if a.sport != "mlb":
            raise SystemExit("observables are MLB only for now. MMA bout stats "
                             "exist on the ESPN core API but the shape is "
                             "unverified until a card has actually been fought.")
        json.dump(mlb_observables(a.game), sys.stdout, indent=2)
        sys.stdout.write("\n")
        raise SystemExit(0)

    final = mlb_final(a.game) if a.sport == "mlb" else espn_final(a.sport, a.game)
    if a.call_json:
        call = json.loads(a.call_json)
    elif a.call:
        call = parse_call(a.call, final)
    else:
        raise SystemExit("give --call or --call-json")

    r = grade(a.sport, final, call)
    if a.pivot_fired and a.pivot_followed:
        r["pivot"] = grade_pivot(a.pivot_fired == "yes", a.pivot_followed == "yes")
    print(json.dumps(r, indent=2))
    print("\nledger row:", file=sys.stderr)
    print("| {} | {} | {} | winner {} | margin {} | baseline {} |".format(
        a.game, r["called"], r["final"],
        "HIT" if r["winner_correct"] else "MISS",
        "HIT" if r["within_margin"] else "MISS",
        "HIT" if r["baseline_correct"] else "MISS"), file=sys.stderr)


if __name__ == "__main__":
    main()
