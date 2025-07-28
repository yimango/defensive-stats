#!/usr/bin/env python3

import os
import requests
import logging
import csv
import math
from collections import defaultdict

# --- Configuration ---
SPORTSRADAR_API_KEY   = os.getenv("SPORTSRADAR_API_KEY")
SPORTSRADAR_BASE_URL  = "https://api.sportradar.us/nhl/production/v7/en"
SEASON                = "2024"
PERIOD_LENGTH_SECONDS = 20 * 60  # 20 minute periods

# --- Testing Feature Flag ---
TEST_MODE       = True
TEST_GAME_LIMIT = 10

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

HEADERS = {
    "accept": "application/json",
    "x-api-key": SPORTSRADAR_API_KEY
}


# --- Helpers ---

def clock_to_seconds(clock_str, period):
    """Convert MM:SS-left-in-period to cumulative seconds since puck-drop."""
    m, s = map(int, clock_str.split(":"))
    left = m * 60 + s
    elapsed = PERIOD_LENGTH_SECONDS - left
    return (period - 1) * PERIOD_LENGTH_SECONDS + elapsed


def estimate_xg(event):
    """Get expected goals from API or distance buckets."""
    if "expected_goals" in event:
        return event["expected_goals"]
    dist = event.get("details", {}).get("distance")
    if dist is None:
        return 0.0
    if dist <= 10:   return 0.20
    if dist <= 20:   return 0.12
    if dist <= 30:   return 0.08
    if dist <= 40:   return 0.04
    return 0.02


def fetch_schedule():
    """Fetch the list of games for the season."""
    url = f"{SPORTSRADAR_BASE_URL}/games/{SEASON}/REG/schedule.json"
    logger.info("Fetching schedule for season %s REG...", SEASON)
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    games = resp.json().get("games", [])
    logger.info(" → Retrieved %d games", len(games))
    return games


def fetch_game_pbp(game_id):
    """Fetch and flatten play-by-play events for one game."""
    url = f"{SPORTSRADAR_BASE_URL}/games/{game_id}/pbp.json"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    plays = []
    for period in data.get("periods", []):
        for ev in period.get("events", []):
            ev["period"] = period["number"]
            plays.append(ev)
    return plays


def parse_shifts(plays, home_id, away_id):
    """
    Reconstruct on-ice shift intervals from substitution events.
    Returns dict[player_id] -> list of (start_sec, end_sec).
    """
    subs = [ev for ev in plays if ev.get("event_type") == "substitution"]
    if not subs:
        return defaultdict(list)

    def side(tid):
        return "home" if tid == home_id else "away"

    subs_sorted = sorted(
        subs,
        key=lambda ev: clock_to_seconds(ev["clock_decimal"], ev["period"])
    )

    shifts = defaultdict(list)
    on_ice = {"home": set(), "away": set()}
    shift_start = {}

    for ev in subs_sorted:
        t0      = clock_to_seconds(ev["clock_decimal"], ev["period"])
        team_id = ev["attribution"]["id"]
        sd      = side(team_id)
        group   = {p["id"] for p in ev["players"]}

        # close existing shifts for players who left
        for pid in on_ice[sd] - group:
            start = shift_start.pop(pid, None)
            if start is not None:
                shifts[pid].append((start, t0))

        # open shifts for new players
        for pid in group - on_ice[sd]:
            shift_start[pid] = t0

        on_ice[sd] = group

    # determine end-of-game time from all plays
    all_times = [
        clock_to_seconds(ev["clock_decimal"], ev["period"])
        for ev in plays
    ]
    final_t = max(all_times) if all_times else 0

    # close any still-open shifts at final timestamp
    for pid, start in shift_start.items():
        shifts[pid].append((start, final_t))

    return shifts


def on_off_ice(shifts, t, atk_id, home_roster, away_roster, home_id):
    """
    Given timestamp t and attacking team id, classify each defender
    as on-ice or off-ice.
    """
    defenders = away_roster if atk_id == home_id else home_roster
    on_, off_ = [], []
    for pid in defenders:
        if any(s <= t <= e for s, e in shifts.get(pid, [])):
            on_.append(pid)
        else:
            off_.append(pid)
    return on_, off_


# --- Main Script ---

if __name__ == "__main__":
    games = fetch_schedule()
    if TEST_MODE:
        logger.info("TEST_MODE enabled — limiting to %d games", TEST_GAME_LIMIT)
        games = games[:TEST_GAME_LIMIT]

    csv_path = "nhl_defense_shot_data.csv"
    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["game_id", "period", "clock_seconds", "player_id", "on_off", "xg"])

        total_rows = 0
        for game in games:
            gid     = game["id"]
            home_id = game["home"]["id"]
            away_id = game["away"]["id"]

            logger.info("Processing game %s", gid)
            pbp    = fetch_game_pbp(gid)
            shifts = parse_shifts(pbp, home_id, away_id)

            # build rosters from substitutions
            rosters = {"home": set(), "away": set()}
            for ev in pbp:
                if ev.get("event_type") == "substitution":
                    sd = "home" if ev["attribution"]["id"] == home_id else "away"
                    rosters[sd].update(p["id"] for p in ev["players"])
            home_roster = rosters["home"]
            away_roster = rosters["away"]

            shots, rows = 0, 0
            for ev in pbp:
                for stat in ev.get("statistics", []):
                    if stat.get("type") != "shot":
                        continue
                    shots += 1
                    t_ev   = clock_to_seconds(ev["clock_decimal"], ev["period"])
                    xg     = estimate_xg(ev)
                    atk_id = stat["team"]["id"]

                    on_d, off_d = on_off_ice(shifts, t_ev, atk_id, home_roster, away_roster, home_id)
                    for pid in on_d:
                        writer.writerow([gid, ev["period"], t_ev, pid, "on",  xg])
                        rows += 1
                    for pid in off_d:
                        writer.writerow([gid, ev["period"], t_ev, pid, "off", xg])
                        rows += 1

            total_rows += rows
            logger.info(" → shots=%d, rows_added=%d, cumulative_rows=%d", shots, rows, total_rows)

    logger.info("Done. Wrote %d rows to %s", total_rows, csv_path)
