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
  Unavailable  outdoor but no forecast. Block renders and SAYS SO

Weather comes from three NOAA surfaces, not one:

  /gridpoints/{office}/{x},{y}   59 raw variables. skyCover, probabilityOfThunder,
                                 windGust, dewpoint, pressure, QPF. The plain
                                 hourly product exposes about eight of these and
                                 flattens cloud cover into a text blurb.
  /alerts/active?point=          watches and warnings. Discrete delay risk that
                                 no forecast text ever states.
  /stations/{id}/observations    actual observed conditions near the venue, for
                                 grounding the read and grading it afterwards.

Plus one derived value, clearly labelled as derived: air density and a carry
index computed from the cited temperature, dewpoint and pressure. It is the one
weather fact in baseball with real physics behind it rather than folklore.
"""
import argparse
import json
import math
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

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

def parse_duration(d):
    """ISO 8601 duration, the subset NWS actually emits: P1DT6H, PT3H, PT1H."""
    m = re.match(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$", d)
    if not m:
        return timedelta(hours=1)
    days, hours, mins = (int(x) if x else 0 for x in m.groups())
    return timedelta(days=days, hours=hours, minutes=mins)


def grid_value(props, var, target):
    """Value of a raw gridpoint variable for the interval containing target.

    Gridpoint entries are validTime "<start>/<duration>" and the intervals are
    irregular, three and six hour blocks further out. Taking the last entry that
    started before target would silently read a stale block, so the duration is
    respected.
    """
    v = props.get(var) or {}
    for e in v.get("values", []):
        start_s, dur_s = e["validTime"].split("/")
        start = datetime.fromisoformat(start_s)
        if start <= target < start + parse_duration(dur_s):
            return e.get("value")
    return None


def c_to_f(c):
    return None if c is None else round(c * 9 / 5 + 32, 1)


def kmh_to_mph(k):
    return None if k is None else round(k * 0.621371, 1)


def air_density(temp_c, dew_c, press_inhg, elev_m=None, obs=None):
    """Air density and a carry index. DERIVED, never presented as retrieved.

    Ball carry rises as air thins. Hot, humid, low pressure air is thinner than
    cold, dry, high pressure air, which is why the same swing is a home run in
    August and a fly out in April. Index is relative to standard sea level
    density, so above 1.00 means the ball carries further than standard.
    """
    if temp_c is None:
        return None
    t_k = temp_c + 273.15

    # Pressure is NOT published by every NWS forecast office. PBZ carries it,
    # LOT and MTR return an empty series. So there is a fallback chain, and the
    # source is always reported, because a carry index that silently switches
    # inputs is worse than one that admits what it used.
    p_pa, p_src = None, None
    if press_inhg is not None:
        # Empty unit string on this field. Values near 30 are inches of mercury,
        # values near 101000 are pascals. Sniff rather than assume.
        cand = press_inhg if press_inhg > 10000 else press_inhg * 3386.39
        if 80000 < cand < 110000:
            p_pa, p_src = cand, "NWS gridpoint"
    if p_pa is None and obs:
        for k in ("barometric_pressure_pa", "sea_level_pressure_pa"):
            if obs.get(k) and 80000 < obs[k] < 110000:
                p_pa, p_src = obs[k], "nearest station observation"
                break
    if p_pa is None and elev_m is not None:
        # Barometric formula off the standard atmosphere. Elevation is what
        # actually moves density at altitude, which is the whole Coors Field
        # effect, so an elevation-derived estimate is far better than nothing.
        p_pa = 101325.0 * (1 - 2.25577e-5 * float(elev_m)) ** 5.25588
        p_src = "estimated from venue elevation {:.0f} m, standard atmosphere".format(
            float(elev_m))
    if p_pa is None:
        warn("no usable pressure from any source, carry index omitted")
        return None
    if dew_c is not None:
        # Magnus, saturation vapour pressure at the dewpoint
        e_pa = 610.94 * math.exp((17.625 * dew_c) / (dew_c + 243.04))
    else:
        e_pa = 0.0
    rho = ((p_pa - e_pa) / (287.058 * t_k)) + (e_pa / (461.495 * t_k))
    return {
        "air_density_kg_m3": round(rho, 4),
        "carry_index": round(1.225 / rho, 3),
        "pressure_pa": round(p_pa, 1),
        "pressure_source": p_src,
        "note": "Derived from the cited temperature and dewpoint plus the "
                "pressure source named above. Not a retrieved forecast value. "
                "Above 1.00 means the ball carries further than standard sea "
                "level.",
    }


def alerts(lat, lon):
    """Active watches and warnings. Discrete delay risk the forecast never states."""
    try:
        d = get("{}/alerts/active?point={},{}".format(NWS, round(float(lat), 4),
                                                      round(float(lon), 4)))
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None
    out = []
    for f in d.get("features", []):
        p = f["properties"]
        out.append({"event": p.get("event"), "severity": p.get("severity"),
                    "urgency": p.get("urgency"),
                    "ends": p.get("ends") or p.get("expires")})
    return out


def latest_observation(stations_url):
    """Nearest station's latest actual observation. Ground truth, not forecast."""
    try:
        st = get(stations_url)
        sid = st["features"][0]["properties"]["stationIdentifier"]
        o = get("{}/stations/{}/observations/latest".format(NWS, sid))["properties"]
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError):
        return None
    val = lambda k: (o.get(k) or {}).get("value")
    return {
        "station": sid,
        "observed_at": o.get("timestamp"),
        "temp_f": c_to_f(val("temperature")),
        "dewpoint_f": c_to_f(val("dewpoint")),
        "wind_mph": kmh_to_mph(val("windSpeed")),
        "gust_mph": kmh_to_mph(val("windGust")),
        "wind_from_deg": val("windDirection"),
        "text": o.get("textDescription"),
        "barometric_pressure_pa": val("barometricPressure"),
        "sea_level_pressure_pa": val("seaLevelPressure"),
        "note": "Observed, not forecast. Use to ground the read and to grade it "
                "afterwards.",
    }


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
        grid_url = pts["properties"]["forecastGridData"]
        hourly_url = pts["properties"]["forecastHourly"]
        stations_url = pts["properties"]["observationStations"]
        fc = get(hourly_url)
        grid = get(grid_url)
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

    g = grid["properties"]
    at = lambda var: grid_value(g, var, target)

    temp_c = at("temperature")
    dew_c = at("dewpoint")
    press = at("pressure")

    out = {
        "roof": roof,
        "roof_decision_unknown": roof == "Retractable",
        "valid_for": chosen["startTime"],
        # from the plain-language hourly product
        "temp_f": chosen.get("temperature"),
        "wind": chosen.get("windSpeed"),
        "wind_from": chosen.get("windDirection"),
        "sky_text": chosen.get("shortForecast"),
        "precip_pct": (chosen.get("probabilityOfPrecipitation") or {}).get("value"),
        # from the raw gridpoint, 59 variables instead of the hourly product's few
        "sky_cover_pct": at("skyCover"),
        "thunder_pct": at("probabilityOfThunder"),
        "gust_mph": kmh_to_mph(at("windGust")),
        "humidity_pct": at("relativeHumidity"),
        "dewpoint_f": c_to_f(dew_c),
        "precip_amount_mm": at("quantitativePrecipitation"),
        "visibility_m": at("visibility"),
        "ceiling_m": at("ceilingHeight"),
        "sources": [hourly_url, grid_url],
        "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "MECHANISM_REQUIRED": "State how this changes play at this venue, or cut "
                              "the block. Temperature that does not move the game "
                              "is trivia.",
    }

    # Derived, not retrieved. Labelled so, because it is computed from the cited
    # inputs above rather than read off a forecast. Air density drives how far a
    # ball carries, which is the one weather fact in baseball with real physics
    # behind it rather than vibes.
    obs_now = latest_observation(stations_url)
    out["derived"] = air_density(temp_c, dew_c, press,
                                 elev_m=(g.get("elevation") or {}).get("value"),
                                 obs=obs_now)

    # Watches and warnings are a discrete delay risk that no forecast text states.
    out["alerts"] = alerts(lat, lon)

    # Actual observed conditions, but only when the game is close enough for them
    # to mean anything. For a game four days out this is noise.
    hours_out = (target - datetime.now(timezone.utc)).total_seconds() / 3600
    out["observed"] = obs_now if hours_out <= 6 else None

    return out


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
