# %%
import pandas as pd
import numpy as np
import requests
from io import StringIO
from pathlib import Path
import time
import json

# ============================================================
# SETTINGS
# ============================================================

MONEYPUCK_URL = "https://moneypuck.com/moneypuck/playerData/careers/gameByGame/all_teams.csv"
NHL_BASE_URL = "https://api-web.nhle.com/v1"

HEADERS = {"User-Agent": "Mozilla/5.0"}

OFFICIAL_RESULTS_CACHE = Path("official_nhl_game_results.csv")

# Player stats are downloaded only for selected team-season-game_type combinations.
# This avoids a 20-minute full-history scrape.
PLAYER_STATS_CACHE_DIR = Path("player_stats_cache")

# Player-stats download modes.
# Full prefetch downloads player stats for every team / season / season type
# found in final_game_data. This is much heavier, but it is resumable because
# every request is cached into player_stats_cache/.
PREFETCH_ALL_PLAYER_STATS = True

# Optional selective mode. Leave False if full prefetch is enabled.
PREFETCH_SELECTED_PLAYER_STATS = False

# Examples:
# ("CAR", 2024, 2) = Carolina 2024/25 regular season
# ("CAR", 2024, 3) = Carolina 2024/25 playoffs
SELECTED_PLAYER_STATS_REQUESTS = [
    # ("CAR", 2024, 2),
    # ("CAR", 2024, 3),
]

# MoneyPuck season 2024 = 2024/2025
MAX_SEASON_EXCLUSIVE = 2025

# First corrected run: True
# Later, once cache is good: False
FORCE_REDOWNLOAD_OFFICIAL_RESULTS = False


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def moneypuck_season_to_nhl_season(season: int) -> int:
    """
    MoneyPuck season 2024 -> NHL API season 20242025.
    """
    return int(f"{season}{season + 1}")


def safe_get_json(url, max_retries=3, sleep_seconds=0.4):
    """
    Robust GET request for NHL API.
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except Exception as e:
            last_error = e
            time.sleep(sleep_seconds * attempt)

    print(f"WARNING: failed URL after {max_retries} attempts: {url}")
    print(f"Last error: {last_error}")
    return None


def extract_team_abbrev(team_obj):
    """
    Extract team abbreviation from NHL API team object.
    """
    if not isinstance(team_obj, dict):
        return None

    if "abbrev" in team_obj:
        return team_obj["abbrev"]

    if "abbreviation" in team_obj:
        return team_obj["abbreviation"]

    return None


def extract_score(team_obj):
    """
    Extract score from NHL API team object.
    """
    if not isinstance(team_obj, dict):
        return np.nan

    return team_obj.get("score", np.nan)


def extract_last_period_type(game):
    """
    Extract whether game ended in REG / OT / SO.
    """
    outcome = game.get("gameOutcome", {})

    if isinstance(outcome, dict):
        val = outcome.get("lastPeriodType")
        if val is not None:
            return val

    period_desc = game.get("periodDescriptor", {})

    if isinstance(period_desc, dict):
        val = period_desc.get("periodType")
        if val is not None:
            return val

    return None


def normalize_last_period_type(x):
    """
    Normalize last period type to REG / OT / SO / UNKNOWN.
    """
    if pd.isna(x):
        return "UNKNOWN"

    x = str(x).upper().strip()

    if x in ["REG", "REGULATION"]:
        return "REG"

    if x in ["OT", "OVERTIME"]:
        return "OT"

    if x in ["SO", "SHOOTOUT"]:
        return "SO"

    return "UNKNOWN"


def clean_moneypuck_team_code(team, season):
    """
    Team code used for matching MoneyPuck to official NHL API data.

    Important:
    MoneyPuck uses ARI even for older Phoenix Coyotes seasons.
    NHL API uses PHX for those older seasons.

    Therefore:
    - 2008/09 to 2013/14: ARI -> PHX
    - 2014/15 onward: ARI stays ARI
    """

    basic_map = {
        "L.A": "LAK",
        "N.J": "NJD",
        "S.J": "SJS",
        "T.B": "TBL"
    }

    team = basic_map.get(team, team)

    if team == "ARI" and int(season) <= 2013:
        return "PHX"

    return team


def display_team_code(team, season):
    """
    Team code for app display.

    I recommend keeping PHX historically as PHX.
    If later you want modern franchise grouping, do it separately in the app.
    """
    return clean_moneypuck_team_code(team, season)


def fetch_official_results_from_nhl(seasons, team_codes):
    """
    Download official game results from lightweight NHL schedule endpoint.

    Output:
    one row per team per game.
    """

    all_game_rows = []

    seasons = sorted(set(int(s) for s in seasons))
    team_codes = sorted(set(str(t).upper() for t in team_codes if pd.notna(t)))

    print("Downloading official NHL results...")
    print(f"Seasons: {seasons[0]} - {seasons[-1]}")
    print(f"Number of team codes queried: {len(team_codes)}")

    for mp_season in seasons:
        nhl_season = moneypuck_season_to_nhl_season(mp_season)

        season_game_objects = {}

        for team in team_codes:
            url = f"{NHL_BASE_URL}/club-schedule-season/{team}/{nhl_season}"
            data = safe_get_json(url)

            if not data or "games" not in data:
                continue

            for game in data["games"]:
                game_id = game.get("id")

                if game_id is None:
                    continue

                season_game_objects[int(game_id)] = game

            time.sleep(0.03)

        print(
            f"Season {mp_season}/{mp_season + 1}: "
            f"unique games found = {len(season_game_objects)}"
        )

        for game_id, game in season_game_objects.items():

            game_state = game.get("gameState")
            game_type = game.get("gameType")

            # NHL API gameType:
            # 2 = Regular season
            # 3 = Playoffs
            if game_type == 2:
                season_type = "Regular season"
            elif game_type == 3:
                season_type = "Playoffs"
            else:
                continue

            # Completed games only
            if game_state not in ["OFF", "FINAL"]:
                continue

            away = game.get("awayTeam", {})
            home = game.get("homeTeam", {})

            away_team = extract_team_abbrev(away)
            home_team = extract_team_abbrev(home)

            away_score = extract_score(away)
            home_score = extract_score(home)

            if away_team is None or home_team is None:
                continue

            if pd.isna(away_score) or pd.isna(home_score):
                continue

            away_score = int(away_score)
            home_score = int(home_score)

            if away_score == home_score:
                # Completed NHL game cannot end tied.
                continue

            last_period_type = normalize_last_period_type(
                extract_last_period_type(game)
            )

            away_won = away_score > home_score
            home_won = home_score > away_score

            ended_in_extra_time = last_period_type in ["OT", "SO"]

            rows = [
                {
                    "season": mp_season,
                    "season_type": season_type,
                    "gameId": int(game_id),
                    "team_match_code": away_team,
                    "opponent_match_code_official": home_team,
                    "home_or_away_official": "AWAY",
                    "official_goals_for": away_score,
                    "official_goals_against": home_score,
                    "official_goal_diff": away_score - home_score,
                    "official_last_period_type": last_period_type,
                    "official_game_state": game_state,
                    "official_game_type": game_type,
                    "official_win": int(away_won),
                    "official_loss": int(not away_won),
                    "official_regulation_win": int(away_won and not ended_in_extra_time),
                    "official_ot_win": int(away_won and last_period_type == "OT"),
                    "official_so_win": int(away_won and last_period_type == "SO"),
                    "official_regulation_loss": int((not away_won) and not ended_in_extra_time),
                    "official_ot_loss": int((not away_won) and last_period_type == "OT"),
                    "official_so_loss": int((not away_won) and last_period_type == "SO")
                },
                {
                    "season": mp_season,
                    "season_type": season_type,
                    "gameId": int(game_id),
                    "team_match_code": home_team,
                    "opponent_match_code_official": away_team,
                    "home_or_away_official": "HOME",
                    "official_goals_for": home_score,
                    "official_goals_against": away_score,
                    "official_goal_diff": home_score - away_score,
                    "official_last_period_type": last_period_type,
                    "official_game_state": game_state,
                    "official_game_type": game_type,
                    "official_win": int(home_won),
                    "official_loss": int(not home_won),
                    "official_regulation_win": int(home_won and not ended_in_extra_time),
                    "official_ot_win": int(home_won and last_period_type == "OT"),
                    "official_so_win": int(home_won and last_period_type == "SO"),
                    "official_regulation_loss": int((not home_won) and not ended_in_extra_time),
                    "official_ot_loss": int((not home_won) and last_period_type == "OT"),
                    "official_so_loss": int((not home_won) and last_period_type == "SO")
                }
            ]

            all_game_rows.extend(rows)

    official = pd.DataFrame(all_game_rows)

    if official.empty:
        raise ValueError("Official NHL results download returned empty dataframe.")

    official = official.drop_duplicates(
        subset=["season", "season_type", "gameId", "team_match_code"]
    ).copy()

    # NHL record:
    # W = all wins
    # L = regulation losses
    # OT = overtime/shootout losses
    official["record_w"] = official["official_win"]
    official["record_l"] = official["official_regulation_loss"]
    official["record_ot"] = official["official_ot_loss"] + official["official_so_loss"]

    official["extra_time_win"] = official["official_ot_win"] + official["official_so_win"]
    official["extra_time_loss"] = official["official_ot_loss"] + official["official_so_loss"]

    # NHL points:
    # win = 2
    # OT/SO loss = 1
    # regulation loss = 0
    official["points"] = np.select(
        [
            official["official_win"] == 1,
            official["record_ot"] == 1,
            official["official_regulation_loss"] == 1
        ],
        [
            2,
            1,
            0
        ],
        default=np.nan
    )

    official["game_result"] = np.select(
        [
            official["official_regulation_win"] == 1,
            official["official_ot_win"] == 1,
            official["official_so_win"] == 1,
            official["official_ot_loss"] == 1,
            official["official_so_loss"] == 1,
            official["official_regulation_loss"] == 1
        ],
        [
            "W",
            "OTW",
            "SOW",
            "OTL",
            "SOL",
            "L"
        ],
        default="UNKNOWN"
    )

    official["game_result_order"] = official["game_result"].map({
        "W": 3,
        "OTW": 2,
        "SOW": 2,
        "OTL": -1,
        "SOL": -1,
        "L": -3,
        "UNKNOWN": 0
    })

    return official




# ============================================================
# OPTIONAL PLAYER STATS HELPERS
# ============================================================

def extract_localized_name(value):
    """
    NHL API names are often dictionaries such as {"default": "Sebastian"}.
    This helper also supports plain strings.
    """
    if isinstance(value, dict):
        return (
            value.get("default")
            or value.get("en")
            or value.get("fr")
            or next(iter(value.values()), "")
        )

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    return str(value)


def build_player_name(player):
    """
    Robust player-name extraction for NHL API club-stats responses.
    """
    first = extract_localized_name(player.get("firstName"))
    last = extract_localized_name(player.get("lastName"))

    full = f"{first} {last}".strip()

    if full:
        return full

    for key in ["skaterFullName", "goalieFullName", "name", "playerName"]:
        if key in player:
            val = extract_localized_name(player.get(key))
            if val:
                return val

    return str(player.get("playerId", "Unknown player"))


def get_player_stat(player, possible_keys, default=np.nan):
    """
    NHL API field names can vary slightly. This helper reads the first available key.
    """
    for key in possible_keys:
        if key in player:
            return player.get(key)
    return default


def normalize_player_stats_response(data, team_code, mp_season, game_type):
    """
    Convert NHL API club-stats JSON into one flat dataframe.

    game_type:
    2 = regular season
    3 = playoffs
    """
    if not data:
        return pd.DataFrame()

    rows = []

    skaters = data.get("skaters", [])
    goalies = data.get("goalies", [])

    # Some API variants may group skaters differently.
    if not skaters:
        skaters = (
            data.get("forwards", [])
            + data.get("defensemen", [])
            + data.get("defencemen", [])
        )

    for player in skaters:
        rows.append({
            "team": team_code,
            "season": int(mp_season),
            "season_label": f"{int(mp_season)}/{int(mp_season) + 1}",
            "nhl_season": moneypuck_season_to_nhl_season(int(mp_season)),
            "game_type": int(game_type),
            "season_type": "Regular season" if int(game_type) == 2 else "Playoffs",
            "player_type": "skater",
            "player_id": get_player_stat(player, ["playerId", "id"]),
            "player": build_player_name(player),
            "position": get_player_stat(player, ["positionCode", "position"], ""),
            "games_played": get_player_stat(player, ["gamesPlayed", "games"]),
            "goals": get_player_stat(player, ["goals"]),
            "assists": get_player_stat(player, ["assists"]),
            "points": get_player_stat(player, ["points"]),
            "plus_minus": get_player_stat(player, ["plusMinus"]),
            "pim": get_player_stat(player, ["pim", "penaltyMinutes"]),
            "shots": get_player_stat(player, ["shots"]),
            "shooting_pct": get_player_stat(player, ["shootingPctg", "shootingPct", "shootingPercentage"]),
            "power_play_goals": get_player_stat(player, ["powerPlayGoals", "ppGoals"]),
            "power_play_points": get_player_stat(player, ["powerPlayPoints", "ppPoints"]),
            "short_handed_goals": get_player_stat(player, ["shorthandedGoals", "shortHandedGoals"]),
            "short_handed_points": get_player_stat(player, ["shorthandedPoints", "shortHandedPoints"]),
            "game_winning_goals": get_player_stat(player, ["gameWinningGoals"]),
            "ot_goals": get_player_stat(player, ["otGoals", "overtimeGoals"]),
            "time_on_ice_per_game": get_player_stat(player, ["avgTimeOnIcePerGame", "timeOnIcePerGame"]),
            "headshot": get_player_stat(player, ["headshot"])
        })

    for player in goalies:
        rows.append({
            "team": team_code,
            "season": int(mp_season),
            "season_label": f"{int(mp_season)}/{int(mp_season) + 1}",
            "nhl_season": moneypuck_season_to_nhl_season(int(mp_season)),
            "game_type": int(game_type),
            "season_type": "Regular season" if int(game_type) == 2 else "Playoffs",
            "player_type": "goalie",
            "player_id": get_player_stat(player, ["playerId", "id"]),
            "player": build_player_name(player),
            "position": "G",
            "games_played": get_player_stat(player, ["gamesPlayed", "games"]),
            "wins": get_player_stat(player, ["wins"]),
            "losses": get_player_stat(player, ["losses"]),
            "ot_losses": get_player_stat(player, ["otLosses", "ties"]),
            "goals_against_average": get_player_stat(player, ["goalsAgainstAverage", "gaa"]),
            "save_pct": get_player_stat(player, ["savePctg", "savePct", "savePercentage"]),
            "shutouts": get_player_stat(player, ["shutouts"]),
            "shots_against": get_player_stat(player, ["shotsAgainst"]),
            "saves": get_player_stat(player, ["saves"]),
            "headshot": get_player_stat(player, ["headshot"])
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Make common numeric columns numeric if they exist.
    numeric_cols = [
        "games_played", "goals", "assists", "points", "plus_minus", "pim",
        "shots", "shooting_pct", "power_play_goals", "power_play_points",
        "short_handed_goals", "short_handed_points", "game_winning_goals",
        "ot_goals", "wins", "losses", "ot_losses", "goals_against_average",
        "save_pct", "shutouts", "shots_against", "saves"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def player_stats_cache_path(team_code, mp_season, game_type):
    nhl_season = moneypuck_season_to_nhl_season(int(mp_season))
    return PLAYER_STATS_CACHE_DIR / f"{team_code}_{nhl_season}_{int(game_type)}.csv"


def fetch_team_player_stats(team_code, mp_season, game_type):
    """
    Fetch one team-season-game_type only.

    This is intentionally selective and fast:
    - one team
    - one season
    - one game type

    NHL API:
    /club-stats/{TEAM}/{SEASON}/{GAME_TYPE}
    """
    team_code = str(team_code).upper()
    nhl_season = moneypuck_season_to_nhl_season(int(mp_season))
    game_type = int(game_type)

    url = f"{NHL_BASE_URL}/club-stats/{team_code}/{nhl_season}/{game_type}"

    data = safe_get_json(url, max_retries=3, sleep_seconds=0.5)

    if data is None:
        print(f"WARNING: no player stats returned for {team_code}, {nhl_season}, game_type={game_type}")
        return pd.DataFrame()

    return normalize_player_stats_response(
        data=data,
        team_code=team_code,
        mp_season=int(mp_season),
        game_type=game_type
    )


def load_or_fetch_team_player_stats(team_code, mp_season, game_type, force_redownload=False):
    """
    Load selected player stats from local cache if available.
    Otherwise fetch from NHL API and save cache.

    This is the function the Streamlit app can reuse later.
    """
    PLAYER_STATS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_path = player_stats_cache_path(team_code, mp_season, game_type)

    if cache_path.exists() and not force_redownload:
        return pd.read_csv(cache_path)

    df = fetch_team_player_stats(team_code, mp_season, game_type)

    if not df.empty:
        df.to_csv(cache_path, index=False)
        print(f"Saved player stats cache: {cache_path} {df.shape}")
    else:
        print(f"WARNING: player stats dataframe is empty, not saving: {cache_path}")

    return df


def top_skaters_by_points(player_stats_df, n=3):
    """
    Return top N skaters by points, then goals, assists, games played.
    """
    if player_stats_df.empty:
        return pd.DataFrame()

    skaters = player_stats_df[player_stats_df["player_type"] == "skater"].copy()

    if skaters.empty:
        return pd.DataFrame()

    for col in ["points", "goals", "assists", "games_played"]:
        if col not in skaters.columns:
            skaters[col] = 0

    skaters = skaters.sort_values(
        ["points", "goals", "assists", "games_played", "player"],
        ascending=[False, False, False, True, True]
    ).head(n)

    cols = [
        "team", "season_label", "season_type", "player",
        "position", "games_played", "goals", "assists", "points",
        "headshot"
    ]

    return skaters[[c for c in cols if c in skaters.columns]].copy()


def build_all_player_stats_requests(final_game_data):
    """
    Build all unique (team, season, game_type) requests from final_game_data.

    We intentionally derive requests from the already prepared team-game dataset
    so we only fetch combinations that actually exist in the app data.
    """
    if final_game_data.empty:
        return []

    temp = final_game_data[["team_match_code", "season", "season_type"]].drop_duplicates().copy()

    temp["game_type"] = temp["season_type"].map({
        "Regular season": 2,
        "Playoffs": 3
    })

    temp = temp.dropna(subset=["game_type"]).copy()
    temp["game_type"] = temp["game_type"].astype(int)

    requests = [
        (str(row["team_match_code"]), int(row["season"]), int(row["game_type"]))
        for _, row in temp.sort_values(["team_match_code", "season", "game_type"]).iterrows()
    ]

    return requests


def prefetch_many_player_stats(requests, force_redownload=False):
    """
    Fetch many team-season-game_type combinations and save each one to cache.
    Also returns two combined tables:
    - all player rows
    - top 3 scorers per team-season-type
    """
    all_frames = []
    all_top3_frames = []

    total = len(requests)

    for i, (team_code, mp_season, game_type) in enumerate(requests, start=1):
        print(f"[{i}/{total}] Player stats: {team_code} | {mp_season}/{mp_season + 1} | game_type={game_type}")

        df = load_or_fetch_team_player_stats(
            team_code=team_code,
            mp_season=mp_season,
            game_type=game_type,
            force_redownload=force_redownload
        )

        if not df.empty:
            all_frames.append(df)

            top3 = top_skaters_by_points(df, n=3)
            if not top3.empty:
                all_top3_frames.append(top3)

    combined = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()
    combined_top3 = pd.concat(all_top3_frames, ignore_index=True) if all_top3_frames else pd.DataFrame()

    return combined, combined_top3


# ============================================================
# 0) LOAD MONEYPUCK RAW DATA
# ============================================================

print("Downloading MoneyPuck data...")

response = requests.get(MONEYPUCK_URL, headers=HEADERS, timeout=120)
response.raise_for_status()

raw_df = pd.read_csv(StringIO(response.text))

# Keep completed seasons only
raw_df = raw_df[raw_df["season"] < MAX_SEASON_EXCLUSIVE].copy()

# Correct date parsing
raw_df["gameDate"] = pd.to_datetime(
    raw_df["gameDate"].astype(str),
    format="%Y%m%d",
    errors="coerce"
)

raw_df["season_type"] = raw_df["playoffGame"].map({
    0: "Regular season",
    1: "Playoffs"
})

raw_df["team_match_code"] = raw_df.apply(
    lambda row: clean_moneypuck_team_code(row["team"], row["season"]),
    axis=1
)

raw_df["opponent_match_code"] = raw_df.apply(
    lambda row: clean_moneypuck_team_code(row["opposingTeam"], row["season"]),
    axis=1
)

raw_df["team_display_code"] = raw_df.apply(
    lambda row: display_team_code(row["team"], row["season"]),
    axis=1
)

raw_df["opponent_display_code"] = raw_df.apply(
    lambda row: display_team_code(row["opposingTeam"], row["season"]),
    axis=1
)

raw_df["season_label"] = (
    raw_df["season"].astype(str) + "/" + (raw_df["season"] + 1).astype(str)
)


# ============================================================
# 1) GET OFFICIAL NHL RESULTS
# ============================================================

seasons_needed = raw_df["season"].dropna().astype(int).unique().tolist()

team_codes_needed = sorted(set(
    raw_df["team_match_code"].dropna().astype(str).str.upper().unique().tolist()
    + raw_df["opponent_match_code"].dropna().astype(str).str.upper().unique().tolist()
    + [
        "ANA", "ARI", "PHX", "UTA", "ATL",
        "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL",
        "DAL", "DET", "EDM", "FLA", "LAK", "MIN", "MTL",
        "NJD", "NSH", "NYI", "NYR", "OTT", "PHI", "PIT",
        "SEA", "SJS", "STL", "TBL", "TOR", "VAN", "VGK",
        "WPG", "WSH"
    ]
))

if OFFICIAL_RESULTS_CACHE.exists() and not FORCE_REDOWNLOAD_OFFICIAL_RESULTS:
    print(f"Loading cached official NHL results from {OFFICIAL_RESULTS_CACHE}...")
    official_results = pd.read_csv(OFFICIAL_RESULTS_CACHE)
else:
    official_results = fetch_official_results_from_nhl(
        seasons=seasons_needed,
        team_codes=team_codes_needed
    )

    official_results.to_csv(OFFICIAL_RESULTS_CACHE, index=False)
    print(f"Saved official NHL results cache: {OFFICIAL_RESULTS_CACHE}")

official_results["gameId"] = official_results["gameId"].astype(int)
official_results["season"] = official_results["season"].astype(int)


# ============================================================
# 2) FULL GAME DATASET
# ============================================================

final_game_data = raw_df[raw_df["situation"] == "all"].copy()

final_game_data = final_game_data[[
    "season",
    "season_label",
    "season_type",
    "gameId",
    "gameDate",
    "team",
    "team_match_code",
    "team_display_code",
    "opposingTeam",
    "opponent_match_code",
    "opponent_display_code",
    "home_or_away",
    "goalsFor",
    "goalsAgainst",
    "faceOffsWonFor",
    "faceOffsWonAgainst",
    "shotsOnGoalFor",
    "shotsOnGoalAgainst",
    "shotAttemptsFor",
    "shotAttemptsAgainst",
    "giveawaysFor",
    "giveawaysAgainst"
]].copy()

final_game_data["gameId"] = final_game_data["gameId"].astype(int)
final_game_data["season"] = final_game_data["season"].astype(int)


# ============================================================
# 3) MERGE OFFICIAL RESULTS
# ============================================================

merge_cols = [
    "season",
    "season_type",
    "gameId",
    "team_match_code",
    "opponent_match_code_official",
    "home_or_away_official",
    "official_goals_for",
    "official_goals_against",
    "official_goal_diff",
    "official_last_period_type",
    "official_game_state",
    "official_game_type",
    "official_win",
    "official_loss",
    "official_regulation_win",
    "official_ot_win",
    "official_so_win",
    "official_regulation_loss",
    "official_ot_loss",
    "official_so_loss",
    "record_w",
    "record_l",
    "record_ot",
    "extra_time_win",
    "extra_time_loss",
    "points",
    "game_result",
    "game_result_order"
]

final_game_data = final_game_data.merge(
    official_results[merge_cols],
    on=["season", "season_type", "gameId", "team_match_code"],
    how="left"
)


# ============================================================
# 4) FINAL GAME RESULT COLUMNS
# ============================================================

# Use official goals for game result.
# Fallback to MoneyPuck only if official merge is missing.
final_game_data["game_goals_for"] = final_game_data["official_goals_for"].fillna(
    final_game_data["goalsFor"]
)

final_game_data["game_goals_against"] = final_game_data["official_goals_against"].fillna(
    final_game_data["goalsAgainst"]
)

final_game_data["game_goal_diff"] = (
    final_game_data["game_goals_for"] - final_game_data["game_goals_against"]
)

final_game_data["win"] = final_game_data["official_win"]
final_game_data["lose"] = final_game_data["official_loss"]

final_game_data["regulation_win"] = final_game_data["official_regulation_win"]
final_game_data["ot_win"] = final_game_data["official_ot_win"]
final_game_data["so_win"] = final_game_data["official_so_win"]

final_game_data["regulation_loss"] = final_game_data["official_regulation_loss"]
final_game_data["ot_loss"] = final_game_data["official_ot_loss"]
final_game_data["so_loss"] = final_game_data["official_so_loss"]

# Draw should be 0 for real completed NHL games.
final_game_data["draw"] = (
    final_game_data["game_goals_for"] == final_game_data["game_goals_against"]
).astype(int)


# ============================================================
# 5) FACEOFFS
# ============================================================

final_game_data["total_faceoffs"] = (
    final_game_data["faceOffsWonFor"] +
    final_game_data["faceOffsWonAgainst"]
)

final_game_data["faceoff_pct"] = np.where(
    final_game_data["total_faceoffs"] > 0,
    final_game_data["faceOffsWonFor"] / final_game_data["total_faceoffs"],
    np.nan
)

final_game_data["faceoff_pct_100"] = final_game_data["faceoff_pct"] * 100


# ============================================================
# 6) GAME NUMBER + CUMULATIVE RECORD
# ============================================================

final_game_data = final_game_data.sort_values(
    ["season", "season_type", "team_match_code", "gameDate", "gameId"]
).copy()

final_game_data["game_number_in_season"] = (
    final_game_data
    .groupby(["season", "season_type", "team_match_code"])
    .cumcount() + 1
)

final_game_data["cumulative_points"] = (
    final_game_data
    .groupby(["season", "season_type", "team_match_code"])["points"]
    .cumsum()
)

final_game_data["cumulative_wins"] = (
    final_game_data
    .groupby(["season", "season_type", "team_match_code"])["record_w"]
    .cumsum()
)

final_game_data["cumulative_losses"] = (
    final_game_data
    .groupby(["season", "season_type", "team_match_code"])["record_l"]
    .cumsum()
)

final_game_data["cumulative_ot_losses"] = (
    final_game_data
    .groupby(["season", "season_type", "team_match_code"])["record_ot"]
    .cumsum()
)

final_game_data["record_string_after_game"] = (
    final_game_data["cumulative_wins"].fillna(0).astype(int).astype(str)
    + "-"
    + final_game_data["cumulative_losses"].fillna(0).astype(int).astype(str)
    + "-"
    + final_game_data["cumulative_ot_losses"].fillna(0).astype(int).astype(str)
)


# ============================================================
# 7) SITUATION DATASET
# ============================================================

final_game_situation_data = raw_df[
    raw_df["situation"].isin(["5on5", "5on4", "4on5"])
].copy()

final_game_situation_data = final_game_situation_data[[
    "season",
    "season_label",
    "season_type",
    "gameId",
    "gameDate",
    "team",
    "team_match_code",
    "team_display_code",
    "opposingTeam",
    "opponent_match_code",
    "opponent_display_code",
    "home_or_away",
    "situation",
    "goalsFor",
    "goalsAgainst",
    "faceOffsWonFor",
    "faceOffsWonAgainst",
    "shotsOnGoalFor",
    "shotsOnGoalAgainst",
    "shotAttemptsFor",
    "shotAttemptsAgainst",
    "giveawaysFor",
    "giveawaysAgainst"
]].copy()

final_game_situation_data["gameId"] = final_game_situation_data["gameId"].astype(int)
final_game_situation_data["season"] = final_game_situation_data["season"].astype(int)

final_game_situation_data["goal_diff"] = (
    final_game_situation_data["goalsFor"] -
    final_game_situation_data["goalsAgainst"]
)

final_game_situation_data["total_faceoffs"] = (
    final_game_situation_data["faceOffsWonFor"] +
    final_game_situation_data["faceOffsWonAgainst"]
)

final_game_situation_data["faceoff_pct"] = np.where(
    final_game_situation_data["total_faceoffs"] > 0,
    final_game_situation_data["faceOffsWonFor"] / final_game_situation_data["total_faceoffs"],
    np.nan
)

final_game_situation_data["faceoff_pct_100"] = (
    final_game_situation_data["faceoff_pct"] * 100
)

game_results = final_game_data[[
    "season",
    "season_type",
    "gameId",
    "team_match_code",
    "game_goals_for",
    "game_goals_against",
    "game_goal_diff",
    "win",
    "lose",
    "draw",
    "points",
    "regulation_win",
    "ot_win",
    "so_win",
    "regulation_loss",
    "ot_loss",
    "so_loss",
    "extra_time_win",
    "extra_time_loss",
    "record_w",
    "record_l",
    "record_ot",
    "game_result",
    "game_result_order",
    "game_number_in_season",
    "cumulative_points",
    "cumulative_wins",
    "cumulative_losses",
    "cumulative_ot_losses",
    "record_string_after_game",
    "official_last_period_type"
]].copy()

final_game_situation_data = final_game_situation_data.merge(
    game_results,
    on=["season", "season_type", "gameId", "team_match_code"],
    how="left"
)


# ============================================================
# 8) SAVE DATA
# ============================================================

final_game_data.to_csv("final_game_data.csv", index=False)
final_game_situation_data.to_csv("final_game_situation_data.csv", index=False)


# ============================================================
# 8B) PLAYER STATS DOWNLOAD / CACHE
# ============================================================

all_player_stats = pd.DataFrame()
all_top_skaters_by_points = pd.DataFrame()

if PREFETCH_ALL_PLAYER_STATS:
    print("\n" + "=" * 70)
    print("PREFETCHING PLAYER STATS FOR ALL TEAM-SEASON COMBINATIONS")
    print("=" * 70)

    all_requests = build_all_player_stats_requests(final_game_data)
    print(f"Total player-stat requests to process: {len(all_requests)}")

    all_player_stats, all_top_skaters_by_points = prefetch_many_player_stats(
        all_requests,
        force_redownload=False
    )

elif PREFETCH_SELECTED_PLAYER_STATS:
    print("\n" + "=" * 70)
    print("PREFETCHING SELECTED PLAYER STATS")
    print("=" * 70)

    if not SELECTED_PLAYER_STATS_REQUESTS:
        print("PREFETCH_SELECTED_PLAYER_STATS is True, but SELECTED_PLAYER_STATS_REQUESTS is empty.")
        print("Add requests such as ('CAR', 2024, 2) to SELECTED_PLAYER_STATS_REQUESTS.")
    else:
        all_player_stats, all_top_skaters_by_points = prefetch_many_player_stats(
            SELECTED_PLAYER_STATS_REQUESTS,
            force_redownload=False
        )

if not all_player_stats.empty:
    all_player_stats.to_csv("all_team_player_stats.csv", index=False)
    print("Saved all_team_player_stats.csv:", all_player_stats.shape)
else:
    print("No combined player stats dataframe was created.")

if not all_top_skaters_by_points.empty:
    all_top_skaters_by_points.to_csv("all_top_skaters_by_points.csv", index=False)
    print("Saved all_top_skaters_by_points.csv:", all_top_skaters_by_points.shape)
else:
    print("No combined top-skaters dataframe was created.")


# ============================================================
# 9) CHECKS
# ============================================================

print("\n" + "=" * 70)
print("DATA SAVED")
print("=" * 70)

print("Saved final_game_data.csv:", final_game_data.shape)
print("Saved final_game_situation_data.csv:", final_game_situation_data.shape)

print("\nSeason range:")
print(final_game_data["season_label"].min(), "-", final_game_data["season_label"].max())

print("\nSeason types:")
print(final_game_data["season_type"].value_counts(dropna=False))

print("\nDate check:")
print(final_game_data["gameDate"].min(), "-", final_game_data["gameDate"].max())

print("\nOfficial merge missing rows:")
missing_official = final_game_data["official_win"].isna().sum()
print(missing_official)

if missing_official > 0:
    print("\nMissing official rows by team:")
    print(
        final_game_data[final_game_data["official_win"].isna()]
        .groupby(["season_label", "team_match_code"])
        .size()
        .sort_values(ascending=False)
        .head(40)
    )

print("\nRows with draw after official merge:")
print(final_game_data["draw"].sum())

print("\nGame result counts:")
print(final_game_data["game_result"].value_counts(dropna=False))

print("\nLast period type counts:")
print(final_game_data["official_last_period_type"].value_counts(dropna=False))

print("\nPoints distribution:")
print(final_game_data["points"].value_counts(dropna=False).sort_index())

print("\nRegular season final records:")
regular_records = (
    final_game_data[final_game_data["season_type"] == "Regular season"]
    .groupby(["season_label", "team_match_code"], as_index=False)
    .agg(
        games=("gameId", "count"),
        W=("record_w", "sum"),
        L=("record_l", "sum"),
        OT=("record_ot", "sum"),
        PTS=("points", "sum")
    )
)

print(regular_records.head(60))

print("\nSuspicious regular-season records:")
suspicious_regular_records = regular_records[
    (regular_records["games"] != 82)
    & ~regular_records["season_label"].isin(["2012/2013", "2019/2020", "2020/2021"])
]

print(suspicious_regular_records.head(60))

print("\nExample rows:")
print(final_game_data[[
    "season_label",
    "season_type",
    "gameDate",
    "team_match_code",
    "opponent_match_code",
    "game_goals_for",
    "game_goals_against",
    "official_last_period_type",
    "game_result",
    "points",
    "record_w",
    "record_l",
    "record_ot",
    "cumulative_points",
    "record_string_after_game"
]].head(20))