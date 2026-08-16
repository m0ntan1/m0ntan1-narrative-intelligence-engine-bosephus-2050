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
MLB = "https://statsapi.mlb.com/api/v1"

MARGIN = {"mlb": 2, "nfl": 7}          # fixed in tells-sports.md, before any call


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
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


def parse_call(text, final):
    """Pull two integers out of a call written the way Bosephus writes it."""
    nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", text)]
    if len(nums) < 2:
        raise SystemExit("could not read two scores out of: {!r}".format(text))
    def locate(full):
        """Full club name first, then the last word. Last word alone is
        ambiguous: Red Sox and White Sox both reduce to 'sox', as do the two
        Chicago clubs' nicknames in other sports."""
        low = text.lower()
        i = low.find(full.lower())
        if i != -1:
            return i
        nick = full.split()[-1].lower()
        # only trust the nickname if it appears exactly once
        return i if low.count(nick) != 1 else low.find(nick)

    away_first = locate(final["away_name"])
    home_first = locate(final["home_name"])
    if away_first == -1 or home_first == -1:
        print("  ! team names not both found in the call, assuming away first",
              file=sys.stderr)
        return {"away": nums[0], "home": nums[1]}
    return ({"away": nums[0], "home": nums[1]} if away_first < home_first
            else {"home": nums[0], "away": nums[1]})


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
    ap.add_argument("sport", choices=["mlb"])
    ap.add_argument("--game", required=True)
    ap.add_argument("--call")
    ap.add_argument("--call-json")
    a = ap.parse_args()

    final = mlb_final(a.game)
    if a.call_json:
        call = json.loads(a.call_json)
    elif a.call:
        call = parse_call(a.call, final)
    else:
        raise SystemExit("give --call or --call-json")

    r = grade(a.sport, final, call)
    print(json.dumps(r, indent=2))
    print("\nledger row:", file=sys.stderr)
    print("| {} | {} | {} | winner {} | margin {} | baseline {} |".format(
        a.game, r["called"], r["final"],
        "HIT" if r["winner_correct"] else "MISS",
        "HIT" if r["within_margin"] else "MISS",
        "HIT" if r["baseline_correct"] else "MISS"), file=sys.stderr)


if __name__ == "__main__":
    main()
