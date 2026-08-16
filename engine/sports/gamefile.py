#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the verified pre-game dossier for SPORTS LOGIC mode. Everything this
returns is retrieved and carries a source, so all of it belongs ABOVE the seam.

  python3 gamefile.py mlb --date 2026-08-16              list games
  python3 gamefile.py mlb --game 776543                  dossier as JSON
  python3 gamefile.py nfl --date 2026-08-16
  python3 gamefile.py mma --date 2026-08-16

The conditions block is the point of this tool. It is populated ONLY when the
venue is actually open to the sky. Roof type comes from the venue record, not
from anybody's memory of the ballpark, because an engine that reports cloud
cover for a dome game does it hundreds of times a season and looks like a fool
every time.

  Open         weather fetched, block renders
  Dome         weather NOT fetched, block does not render at all
  Retractable  weather fetched, flagged roof_decision_unknown
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = "montan1-narrative-intelligence-engine (rick@montanibitcoin.com)"
MLB = "https://statsapi.mlb.com/api/v1"
ESPN = "https://site.api.espn.com/apis/site/v2/sports"
NWS = "https://api.weather.gov"

ESPN_PATH = {"nfl": "football/nfl", "mma": "mma/ufc",
             "cfb": "football/college-football"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def warn(msg):
    print("  ! " + msg, file=sys.stderr)


# ---------------------------------------------------------------- weather

def unavailable(reason):
    """Outdoor venue, no forecast. NOT the same as a dome.

    A dome returns None and the CONDITIONS block is absent. This returns an
    object, and the block MUST render and say plainly that it could not get a
    forecast. Degrade openly, house style. Collapsing the two states into None
    would let a missing forecast masquerade as a roof.
    """
    warn(reason)
    return {"unavailable": reason,
            "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def conditions(lat, lon, when_iso, roof):
    """NWS hourly forecast for the hour containing first pitch.

    Returns None ONLY for a dome, which is the whole point of the tool.
    """
    if roof == "Dome":
        return None
    if roof == "Unknown":
        return unavailable("Roof type could not be resolved. Resolve it by hand "
                           "before deciding whether this block renders.")
    if lat is None or lon is None:
        return unavailable("Venue has no coordinates on record, so no forecast "
                           "could be retrieved.")

    try:
        pts = get("{}/points/{},{}".format(NWS, round(float(lat), 4),
                                           round(float(lon), 4)))
        hourly_url = pts["properties"]["forecastHourly"]
        fc = get(hourly_url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # NWS covers the United States and its territories only. Toronto,
            # London, Mexico City and Munich all fall outside it.
            return unavailable(
                "Venue is outside National Weather Service coverage, which is "
                "the US and its territories only. No forecast retrieved. Do not "
                "substitute another source without citing it.")
        return unavailable("NWS returned HTTP {}. No forecast retrieved.".format(e.code))
    except (urllib.error.URLError, KeyError) as e:
        return unavailable("NWS unreachable ({}). No forecast retrieved.".format(e))

    target = datetime.fromisoformat(when_iso.replace("Z", "+00:00"))
    chosen = None
    for p in fc["properties"]["periods"]:
        start = datetime.fromisoformat(p["startTime"])
        end = datetime.fromisoformat(p["endTime"])
        if start <= target < end:
            chosen = p
            break
    if chosen is None:
        return unavailable("First pitch falls outside the NWS hourly window, "
                           "which runs about 156 hours out. Too far ahead for a "
                           "forecast.")

    return {
        "roof": roof,
        "roof_decision_unknown": roof == "Retractable",
        "valid_for": chosen["startTime"],
        "temp_f": chosen.get("temperature"),
        "wind": chosen.get("windSpeed"),
        "wind_from": chosen.get("windDirection"),
        "sky": chosen.get("shortForecast"),
        "precip_pct": (chosen.get("probabilityOfPrecipitation") or {}).get("value"),
        "humidity_pct": (chosen.get("relativeHumidity") or {}).get("value"),
        "source": hourly_url,
        "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "MECHANISM_REQUIRED": "State how this changes play at this venue, or cut "
                              "the block. Temperature that does not move the game "
                              "is trivia.",
    }


# -------------------------------------------------------------------- mlb

def mlb_games(date):
    d = get("{}/schedule?sportId=1&date={}&hydrate=team,venue".format(MLB, date))
    out = []
    for day in d.get("dates", []):
        for g in day.get("games", []):
            out.append({
                "game_id": g["gamePk"],
                "when": g["gameDate"],
                "away": g["teams"]["away"]["team"]["name"],
                "home": g["teams"]["home"]["team"]["name"],
                "venue": g["venue"]["name"],
            })
    return out


def mlb_dossier(game_pk):
    live = get("{}.1/game/{}/feed/live".format(MLB, game_pk))
    gd = live["gameData"]
    venue_id = gd["venue"]["id"]
    v = get("{}/venues/{}?hydrate=fieldInfo,location".format(MLB, venue_id))["venues"][0]
    fi = v.get("fieldInfo", {}) or {}
    coords = (v.get("location", {}) or {}).get("defaultCoordinates", {}) or {}
    roof = fi.get("roofType", "Unknown")
    when = gd["datetime"]["dateTime"]

    teams = {}
    for side in ("away", "home"):
        t = gd["teams"][side]
        rec = t.get("record", {}) or {}
        teams[side] = {
            "name": t.get("name"),
            "wins": rec.get("wins"),
            "losses": rec.get("losses"),
            "pct": rec.get("winningPercentage"),
            "division": (t.get("division") or {}).get("name"),
        }

    probables = {}
    for side in ("away", "home"):
        p = (gd.get("probablePitchers") or {}).get(side)
        probables[side] = p.get("fullName") if p else None

    return {
        "sport": "mlb",
        "game_id": game_pk,
        "when_utc": when,
        "status": gd["status"]["detailedState"],
        "teams": teams,
        "probable_pitchers": probables,
        "venue": {"name": v["name"], "roof": roof,
                  "lat": coords.get("latitude"), "lon": coords.get("longitude"),
                  "capacity": fi.get("capacity")},
        "conditions": conditions(coords.get("latitude"), coords.get("longitude"),
                                 when, roof),
        "sources": [
            "{}.1/game/{}/feed/live".format(MLB, game_pk),
            "{}/venues/{}?hydrate=fieldInfo,location".format(MLB, venue_id),
        ],
    }


# ------------------------------------------------------------------- espn

def espn_games(sport, date):
    path = ESPN_PATH[sport]
    url = "{}/{}/scoreboard".format(ESPN, path)
    if date:
        url += "?dates=" + date.replace("-", "")
    d = get(url)
    out = []
    for e in d.get("events", []):
        c = (e.get("competitions") or [{}])[0]
        out.append({
            "game_id": e.get("id"),
            "when": e.get("date"),
            "name": e.get("name") or e.get("shortName"),
            "venue": ((c.get("venue") or {}).get("fullName")),
            "indoor": (c.get("venue") or {}).get("indoor"),
        })
    return out


def espn_dossier(sport, event_id):
    path = ESPN_PATH[sport]
    d = get("{}/{}/summary?event={}".format(ESPN, path, event_id))
    comp = ((d.get("header") or {}).get("competitions") or [{}])[0]
    gi = d.get("gameInfo") or {}
    venue = gi.get("venue") or comp.get("venue") or {}
    addr = venue.get("address") or {}

    indoor = venue.get("indoor")
    if sport == "mma":
        roof = "Dome"          # every card is indoors. No weather block, ever.
    elif indoor is True:
        roof = "Dome"
    elif indoor is False:
        roof = "Open"
    else:
        roof = "Unknown"
        warn("ESPN did not report indoor/outdoor for this venue. Resolve the "
             "roof by hand before rendering CONDITIONS.")

    when = (d.get("header") or {}).get("competitions", [{}])[0].get("date")
    lat, lon = venue.get("latitude"), venue.get("longitude")

    return {
        "sport": sport,
        "game_id": event_id,
        "when_utc": when,
        "teams": [{"name": (c.get("team") or {}).get("displayName"),
                   "record": [r.get("displayValue") for r in (c.get("record") or [])]}
                  for c in (comp.get("competitors") or [])],
        "venue": {"name": venue.get("fullName"), "roof": roof,
                  "city": addr.get("city"), "state": addr.get("state"),
                  "lat": lat, "lon": lon},
        "conditions": conditions(lat, lon, when, roof) if when else None,
        "sources": ["{}/{}/summary?event={}".format(ESPN, path, event_id)],
        "caveat": "ESPN endpoints are undocumented and unofficial. Verify "
                  "anything load-bearing against a second source.",
    }


# ------------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sport", choices=["mlb", "nfl", "mma", "cfb"])
    ap.add_argument("--date", help="YYYY-MM-DD")
    ap.add_argument("--game", help="game or event id")
    a = ap.parse_args()

    if a.game:
        doc = mlb_dossier(a.game) if a.sport == "mlb" else espn_dossier(a.sport, a.game)
        json.dump(doc, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    date = a.date or datetime.now().strftime("%Y-%m-%d")
    games = mlb_games(date) if a.sport == "mlb" else espn_games(a.sport, a.date)
    if not games:
        print("no games found for {}".format(date))
        return
    for g in games:
        print("{:<12} {:<58} {}".format(str(g["game_id"]),
                                        g.get("name") or "{} @ {}".format(g["away"], g["home"]),
                                        g.get("venue") or ""))


if __name__ == "__main__":
    main()
