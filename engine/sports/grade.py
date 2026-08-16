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
    a = ap.parse_args()

    final = mlb_final(a.game) if a.sport == "mlb" else espn_final(a.sport, a.game)
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
