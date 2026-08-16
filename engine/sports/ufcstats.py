#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parse a ufcstats.com card and resolve MMA pivot conditions against it.

  # 1. fetch with Firecrawl (the site blocks plain curl: 3KB shell vs the real page)
  #    firecrawl_scrape http://www.ufcstats.com/event-details/<id> --formats markdown
  # 2. parse and grade
  python3 ufcstats.py card.md
  python3 ufcstats.py card.md --bout Makhachev --condition "td>=1"

**Why ufcstats.com and not ESPN.** ESPN was the default here for one bad
reason: a single endpoint covered several sports, so nobody checked whether it
was the best at any of them. It is not. ufcstats.com is UFC's own statistics
site and carries knockdowns, strikes, takedowns and submission attempts per
bout, plus method, round and finish time. ESPN's MMA summary endpoint returned
404s on live event IDs and its competitor statistics came back empty.

**Why the scrape is not in this file.** ufcstats.com serves plain curl a three
kilobyte shell. Firecrawl gets the real page. There is no API key reachable
from a script here, so fetching belongs to whatever has Firecrawl and parsing
belongs to deterministic code that can be tested. This is the second half.

Conditions are written as `<stat><op><value>`, for example `td>=1`, `str>50`,
`kd>=1`. Stats are kd, str, td, sub. That is what a fight hinge is usually
written against: whether the wrestler got it to the mat, whether the striker
kept it standing, whether anybody got hurt.
"""
import argparse
import re
import sys

STATS = ("kd", "str", "td", "sub")
OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
       ">": lambda a, b: a > b, "<": lambda a, b: a < b,
       "==": lambda a, b: a == b, "=": lambda a, b: a == b}


def parse_card(md):
    """Rows off the event table. Two fighters per row, stats stacked in cells."""
    bouts = []
    for line in md.split("\n"):
        if not line.startswith("|") or "fight-details" not in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 10:
            continue

        def pair(cell):
            nums = re.findall(r"\d+", re.sub(r"<[^>]+>", " ", cell))
            return (int(nums[0]), int(nums[1])) if len(nums) >= 2 else (None, None)

        names = re.findall(r"\[([^\]]+)\]\(http://ufcstats\.com/fighter-details", cells[1])
        if len(names) < 2:
            continue
        kd, st, td, sub = (pair(cells[i]) for i in (2, 3, 4, 5))
        method = re.sub(r"<[^>]+>", " ", cells[7]).strip()
        method = re.sub(r"\s+", " ", method)
        bouts.append({
            "winner": names[0], "loser": names[1],
            "fighters": {
                names[0]: {"kd": kd[0], "str": st[0], "td": td[0], "sub": sub[0]},
                names[1]: {"kd": kd[1], "str": st[1], "td": td[1], "sub": sub[1]},
            },
            "method": method,
            "round": re.sub(r"<[^>]+>", "", cells[8]).strip(),
            "time": re.sub(r"<[^>]+>", "", cells[9]).strip(),
            "url": (re.search(r"\(([^)]*fight-details[^)]*)\)", cells[0]) or [None, ""])[1]
            if re.search(r"\(([^)]*fight-details[^)]*)\)", cells[0]) else "",
        })
    return bouts


def find_bout(bouts, needle):
    hits = [b for b in bouts
            if needle.lower() in (b["winner"] + " " + b["loser"]).lower()]
    if not hits:
        raise SystemExit("No bout matching {!r} on this card.".format(needle))
    if len(hits) > 1:
        raise SystemExit("{!r} matches {} bouts. Be more specific."
                         .format(needle, len(hits)))
    return hits[0]


def resolve(bout, fighter, condition):
    """Resolve `td>=1` style conditions against one fighter's line."""
    m = re.match(r"^\s*(%s)\s*(>=|<=|==|=|>|<)\s*(\d+)\s*$" % "|".join(STATS),
                 condition, re.I)
    if not m:
        raise SystemExit(
            "Cannot read condition {!r}. Use <stat><op><value>, stats {}."
            .format(condition, ", ".join(STATS)))
    stat, op, want = m.group(1).lower(), m.group(2), int(m.group(3))
    who = next((f for f in bout["fighters"] if fighter.lower() in f.lower()), None)
    if who is None:
        raise SystemExit("{!r} is not in this bout ({} vs {})."
                         .format(fighter, bout["winner"], bout["loser"]))
    got = bout["fighters"][who][stat]
    if got is None:
        raise SystemExit("No {} recorded for {}.".format(stat, who))
    return {"fighter": who, "stat": stat, "operator": op, "threshold": want,
            "actual": got, "condition_met": OPS[op](got, want)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card", help="markdown of a ufcstats event-details page, or - for stdin")
    ap.add_argument("--bout", help="substring of a fighter name")
    ap.add_argument("--fighter", help="whose stat line the condition applies to")
    ap.add_argument("--condition", help="e.g. td>=1")
    a = ap.parse_args()

    md = sys.stdin.read() if a.card == "-" else open(a.card, encoding="utf-8").read()
    bouts = parse_card(md)
    if not bouts:
        raise SystemExit("No bouts parsed. Is this a ufcstats event-details page?")

    if not a.bout:
        for b in bouts:
            f = b["fighters"]
            print("{:<26} def. {:<26} {:<22} R{} {}".format(
                b["winner"][:26], b["loser"][:26], b["method"][:22], b["round"], b["time"]))
            print("    {:<24} kd {} str {:>3} td {} sub {}".format(
                b["winner"][:24], f[b["winner"]]["kd"], f[b["winner"]]["str"],
                f[b["winner"]]["td"], f[b["winner"]]["sub"]))
            print("    {:<24} kd {} str {:>3} td {} sub {}".format(
                b["loser"][:24], f[b["loser"]]["kd"], f[b["loser"]]["str"],
                f[b["loser"]]["td"], f[b["loser"]]["sub"]))
        return

    bout = find_bout(bouts, a.bout)
    if not a.condition:
        import json
        json.dump(bout, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    r = resolve(bout, a.fighter or a.bout, a.condition)
    print("{} {} {} {}  ->  actual {}  ->  condition {}".format(
        r["fighter"], r["stat"], r["operator"], r["threshold"], r["actual"],
        "MET" if r["condition_met"] else "NOT MET"))
    print("bout result: {} def. {} by {} in R{}".format(
        bout["winner"], bout["loser"], bout["method"], bout["round"]))


if __name__ == "__main__":
    main()
