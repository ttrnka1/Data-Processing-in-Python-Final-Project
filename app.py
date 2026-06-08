import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.express as px
import os
import base64
import html
import urllib.request
import subprocess
import sys
from pathlib import Path

# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="NHL Team Dashboard",
    layout="wide"
)

st.title("🏒 NHL Team Statistics Dashboard")


# ============================================================
# CONSTANTS
# ============================================================

TEAM_COL = "team_match_code"
OPP_COL = "opponent_match_code"

DISPLAY_TEAM_COL = "team_display_code"
DISPLAY_OPP_COL = "opponent_display_code"



def render_regular_season_logo_table(ranking_table, selected_team):
    """
    HTML league table with logos and highlighted selected team.
    Used mainly for Regular season, where standings are more meaningful.
    """
    rows_html = []

    for _, row in ranking_table.iterrows():
        team_code = str(row["Team"])
        selected_class = " selected-row" if team_code == selected_team else ""
        logo = team_logo_html(team_code, size=32)

        rows_html.append(f"""
            <tr class="{selected_class}">
                <td class="rank-cell">{int(row["Rank"])}</td>
                <td class="logo-cell">{logo}</td>
                <td class="team-cell">
                    <div class="team-name-main">{html.escape(team_full_name(team_code))}</div>
                    <div class="team-code-sub">{html.escape(team_code)}</div>
                </td>
                <td class="pts-cell">{int(row["PTS"])}</td>
                <td>{int(row["W"])}</td>
                <td>{int(row["L"])}</td>
                <td>{int(row["OT"])}</td>
                <td>{int(row["GP"])}</td>
                <td>{int(row["GD"])}</td>
            </tr>
        """)

    return f"""
    <style>
        .standings-wrap {{
            width: 100%;
            overflow-x: auto;
            margin-top: 8px;
            border-radius: 16px;
            border: 1px solid rgba(148, 163, 184, 0.35);
        }}
        table.logo-standings {{
            width: 100%;
            border-collapse: collapse;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
        }}
        .logo-standings thead tr {{
            background: #0f172a;
            color: white;
        }}
        .logo-standings th {{
            text-align: left;
            padding: 10px 12px;
            font-weight: 800;
            letter-spacing: 0.4px;
            white-space: nowrap;
        }}
        .logo-standings td {{
            padding: 9px 12px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.25);
            vertical-align: middle;
            white-space: nowrap;
        }}
        .logo-standings tbody tr:nth-child(even) {{
            background: rgba(248, 250, 252, 0.75);
        }}
        .logo-standings tbody tr:nth-child(odd) {{
            background: rgba(255, 255, 255, 0.95);
        }}
        .logo-standings tr.selected-row {{
            background: rgba(250, 204, 21, 0.28) !important;
            outline: 2px solid #facc15;
            outline-offset: -2px;
            font-weight: 800;
        }}
        .rank-cell {{
            font-weight: 800;
            color: #0f172a;
            width: 48px;
        }}
        .logo-cell {{
            width: 46px;
        }}
        .team-cell {{
            min-width: 220px;
        }}
        .team-name-main {{
            font-weight: 800;
            color: #0f172a;
            line-height: 1.1;
        }}
        .team-code-sub {{
            font-size: 11px;
            color: #64748b;
            margin-top: 2px;
        }}
        .pts-cell {{
            font-weight: 900;
            color: #0f172a;
        }}
    </style>

    <div class="standings-wrap">
        <table class="logo-standings">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Logo</th>
                    <th>Team</th>
                    <th>PTS</th>
                    <th>W</th>
                    <th>L</th>
                    <th>OT</th>
                    <th>GP</th>
                    <th>GD</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """



def build_sortable_league_table(ranking, selected_team, playoff_teams=None):
    """
    Build a sortable Streamlit dataframe for league standings/stat comparison.
    Includes logo, conference/division, and all major stats that users may want to sort by.
    """
    table = ranking.copy()
    playoff_teams = set(playoff_teams or [])

    table["Conference"] = table[TEAM_COL].apply(team_conference)
    table["Division"] = table[TEAM_COL].apply(team_division)
    table["Logo"] = table[TEAM_COL].apply(lambda x: logo_data_uri(str(x)) or "")
    table["Team"] = table[TEAM_COL].astype(str)
    table["Team name"] = table[TEAM_COL].apply(team_full_name)

    show = pd.DataFrame({
        "Rank": table["rank"].astype(int),
        "Logo": table["Logo"],
        "Team": table["Team"],
        "Team name": table["Team name"],
        "Conference": table["Conference"],
        "Division": table["Division"],
        "Data range": table[TEAM_COL].apply(team_available_range_text),
        "Playoffs": table[TEAM_COL].astype(str).apply(lambda x: "Yes" if x in playoff_teams else "No"),
        "PTS": table["total_points"].round(0).astype(int),
        "W": table["W"].round(0).astype(int),
        "L": table["L"].round(0).astype(int),
        "OT": table["OT"].round(0).astype(int),
        "RW": table["RW"].round(0).astype(int),
        "ROW": table["ROW"].round(0).astype(int),
        "GP": table["games"].round(0).astype(int),
        "GD": table["goal_diff_total"].round(0).astype(int),
        "PTS/GP": table["points_per_game"].round(2),
        "GD/GP": table["goal_diff_per_game"].round(2),
        "GF/GP": table["goals_for_per_game"].round(2),
        "GA/GP": table["goals_against_per_game"].round(2),
        "SF/GP": table["shots_for_per_game"].round(2),
        "SA/GP": table["shots_against_per_game"].round(2),
        "Shot attempts/GP": table["shot_attempts_for_per_game"].round(2),
        "FO%": table["faceoff_pct"].round(2),
        "Giveaways/GP": table["giveaways_per_game"].round(2),
    })

    return show


def highlight_selected_team(row, selected_team):
    if str(row.get("Team", "")) == str(selected_team):
        return ["background-color: rgba(250, 204, 21, 0.42); font-weight: 900;"] * len(row)

    if str(row.get("Playoffs", "")) == "Yes":
        return ["background-color: rgba(34, 197, 94, 0.13);"] * len(row)

    return [""] * len(row)


def show_sortable_league_table(ranking, selected_team, season_type, view_mode, playoff_teams=None):
    table = build_sortable_league_table(ranking, selected_team, playoff_teams=playoff_teams)

    st.caption(
        "Click any column header to sort the table. "
        "Use the filters below to show only one conference or one division. "
        "NHL record format is W-L-OT, not draws."
        + (" Current table reflects the selected game situation." if view_mode != "Full game" else "")
    )

    f1, f2 = st.columns(2)

    conference_options = ["All"] + [
        c for c in sorted(table["Conference"].dropna().unique().tolist())
        if c != "Unknown"
    ]

    selected_conference = f1.selectbox(
        "Conference",
        options=conference_options,
        index=0,
        key=f"league_conference_filter_{season}_{season_type}_{view_mode}"
    )

    if selected_conference == "All":
        division_base = table.copy()
    else:
        division_base = table[table["Conference"] == selected_conference].copy()

    division_options = ["All"] + [
        d for d in sorted(division_base["Division"].dropna().unique().tolist())
        if d != "Unknown"
    ]

    selected_division = f2.selectbox(
        "Division",
        options=division_options,
        index=0,
        key=f"league_division_filter_{season}_{season_type}_{view_mode}_{selected_conference}"
    )

    filtered = table.copy()

    if selected_conference != "All":
        filtered = filtered[filtered["Conference"] == selected_conference]

    if selected_division != "All":
        filtered = filtered[filtered["Division"] == selected_division]

    # Re-number visible rows after filtering so the filtered table is readable.
    filtered = filtered.copy()
    filtered["Rank"] = range(1, len(filtered) + 1)

    styled_table = filtered.style.apply(
        lambda row: highlight_selected_team(row, selected_team),
        axis=1
    )

    st.dataframe(
        styled_table,
        use_container_width=True,
        hide_index=True,
        row_height=46,
        column_config={
            "Logo": st.column_config.ImageColumn("Logo", help="Team logo", width="small"),
            "Team name": st.column_config.TextColumn("Team name", width="medium"),
            "Conference": st.column_config.TextColumn("Conference", width="small"),
            "Division": st.column_config.TextColumn("Division", width="small"),
            "Data range": st.column_config.TextColumn("Data range", help="Seasons available for this team code in the dataset."),
            "Playoffs": st.column_config.TextColumn("Playoffs", help="Yes if the team qualified for the playoffs in the selected season."),
            "PTS": st.column_config.NumberColumn("PTS", help="Total NHL points."),
            "W": st.column_config.NumberColumn("W", help="Wins."),
            "L": st.column_config.NumberColumn("L", help="Regulation losses."),
            "OT": st.column_config.NumberColumn("OT", help="Overtime/shootout losses."),
            "RW": st.column_config.NumberColumn("RW", help="Regulation wins."),
            "ROW": st.column_config.NumberColumn("ROW", help="Regulation plus overtime wins, excluding shootout wins."),
            "FO%": st.column_config.NumberColumn("FO%", help="Faceoff win percentage."),
        }
    )



def add_official_like_standings_order(ranking):
    """
    Sort standings with unique positions using NHL-style available tiebreakers.

    Implemented from available columns:
    1) Points
    2) Fewer games played / better points percentage proxy
    3) Regulation wins (RW)
    4) Regulation + overtime wins, excluding shootout wins (ROW)
    5) Total wins (W)
    6) Goal differential (GD)
    7) Goals for (GF)

    Official NHL head-to-head points are not implemented here because they require
    pairwise schedule-level calculations for each tied group.
    """
    out = ranking.copy()

    # These columns are available in game-level data, so aggregate them before calling this
    # or default to safe fallback if an older table does not include them.
    for col in ["RW", "ROW", "GF", "GD"]:
        if col not in out.columns:
            out[col] = 0

    out = out.sort_values(
        by=["total_points", "games", "RW", "ROW", "W", "GD", "GF", TEAM_COL],
        ascending=[False, True, False, False, False, False, False, True],
        kind="mergesort"
    ).reset_index(drop=True)

    out["rank"] = np.arange(1, len(out) + 1)
    return out




# ============================================================
# ANALYTICAL SECTIONS HELPERS
# ============================================================

def selected_team_playoff_path_table(playoff_team_games, selected_team):
    """
    Create a readable playoff path summary:
    Round/Series, opponent, W/L, score, games, goals.
    """
    if playoff_team_games.empty:
        return pd.DataFrame()

    games = add_playoff_series_info(playoff_team_games.copy())

    if "series_number" not in games.columns:
        return pd.DataFrame()

    rows = []

    for series_number, group in games.groupby("series_number", sort=True):
        group = group.sort_values(["gameDate", "gameId"]).copy()

        opponents = group[OPP_COL].dropna().astype(str).unique().tolist()
        opponent = opponents[0] if opponents else "Unknown"

        wins = int((group["points"] == 2).sum())
        losses = int((group["points"] < 2).sum())

        gf = int(group["game_goals_for"].sum())
        ga = int(group["game_goals_against"].sum())

        result = "Won" if wins > losses else "Lost"
        score = f"{wins}-{losses}"

        # If the series summary is built correctly, series_number is chronological.
        rows.append({
            "Round / series": f"Series {int(series_number)}",
            "Opponent": opponent,
            "Result": result,
            "Series score": score,
            "Games": int(group["gameId"].nunique()),
            "Goals for": gf,
            "Goals against": ga
        })

    return pd.DataFrame(rows)


def render_playoff_path_cards(path_df, selected_team):
    if path_df.empty:
        st.info("No playoff path summary available for this team.")
        return

    cols = st.columns(min(len(path_df), 4))

    for i, (_, row) in enumerate(path_df.iterrows()):
        with cols[i % len(cols)]:
            won = str(row["Result"]) == "Won"
            icon = "✅" if won else "❌"
            st.markdown(
                f"""
                <div style="
                    border: 1px solid rgba(148,163,184,0.35);
                    border-radius: 16px;
                    padding: 14px 16px;
                    background: {'rgba(34,197,94,0.10)' if won else 'rgba(239,68,68,0.10)'};
                    min-height: 132px;
                ">
                    <div style="font-size: 13px; font-weight: 800; color: #64748b;">
                        {html.escape(str(row['Round / series']))}
                    </div>
                    <div style="font-size: 22px; font-weight: 950; margin-top: 4px;">
                        {icon} {html.escape(str(row['Result']))} {html.escape(str(row['Series score']))}
                    </div>
                    <div style="font-size: 15px; margin-top: 6px;">
                        vs <b>{html.escape(team_full_name(row['Opponent']))} ({html.escape(str(row['Opponent']))})</b>
                    </div>
                    <div style="font-size: 12px; margin-top: 8px; color: #64748b;">
                        Goals: {int(row['Goals for'])}–{int(row['Goals against'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


def build_head_to_head_summary(game_df, team_a, team_b, season, season_type):
    h2h = (
        game_df[
            (game_df["season"] == season) &
            (game_df["season_type"] == season_type) &
            (game_df[TEAM_COL] == team_a) &
            (game_df[OPP_COL] == team_b)
        ]
        .drop_duplicates(["gameId", TEAM_COL])
        .sort_values(["gameDate", "gameId"])
        .copy()
    )

    if h2h.empty:
        return h2h, {}

    summary = {
        "games": int(h2h["gameId"].nunique()),
        "wins": int(h2h["record_w"].sum()),
        "losses": int(h2h["record_l"].sum()),
        "ot_losses": int(h2h["record_ot"].sum()),
        "points": int(h2h["points"].sum()),
        "goals_for": int(h2h["game_goals_for"].sum()),
        "goals_against": int(h2h["game_goals_against"].sum())
    }

    summary["record"] = f"{summary['wins']}-{summary['losses']}-{summary['ot_losses']}"
    summary["goals"] = f"{summary['goals_for']}-{summary['goals_against']}"

    return h2h, summary


def add_conference_division_ranks(ranking):
    out = ranking.copy()
    out["Conference"] = out[TEAM_COL].apply(team_conference)
    out["Division"] = out[TEAM_COL].apply(team_division)

    out["Conference rank"] = (
        out.groupby("Conference")["rank"]
        .rank(method="first", ascending=True)
        .astype(int)
    )

    out["Division rank"] = (
        out.groupby("Division")["rank"]
        .rank(method="first", ascending=True)
        .astype(int)
    )

    return out


def playoff_race_summary_table(ranking, selected_team, playoff_teams_for_season):
    """
    Practical playoff race summary based on known playoff qualifiers in the dataset.
    The cutoff is inferred from the lowest-points playoff team in the selected team's conference.
    """
    if ranking.empty or selected_team not in ranking[TEAM_COL].values:
        return pd.DataFrame(), {}

    table = add_conference_division_ranks(ranking)

    selected_row = table.loc[table[TEAM_COL] == selected_team].iloc[0]
    selected_conf = selected_row["Conference"]

    conf_table = table[table["Conference"] == selected_conf].copy()

    conf_playoff = conf_table[conf_table[TEAM_COL].astype(str).isin(playoff_teams_for_season)].copy()

    if conf_playoff.empty:
        cutoff_points = np.nan
        points_above_cutoff = np.nan
    else:
        cutoff_points = float(conf_playoff["total_points"].min())
        points_above_cutoff = float(selected_row["total_points"] - cutoff_points)

    summary = {
        "conference": selected_conf,
        "division": selected_row["Division"],
        "conference_rank": int(selected_row["Conference rank"]),
        "division_rank": int(selected_row["Division rank"]),
        "qualified": str(selected_team) in playoff_teams_for_season,
        "points": int(selected_row["total_points"]),
        "cutoff_points": cutoff_points,
        "points_above_cutoff": points_above_cutoff
    }

    display = conf_table[[
        "rank", TEAM_COL, "Conference rank", "Division rank",
        "total_points", "W", "L", "OT", "goal_diff_total"
    ]].copy()

    display = display.rename(columns={
        "rank": "League rank",
        TEAM_COL: "Team",
        "total_points": "PTS",
        "goal_diff_total": "GD"
    })

    display["Team name"] = display["Team"].apply(team_full_name)
    display["Playoffs"] = display["Team"].astype(str).apply(
        lambda x: "Yes" if x in playoff_teams_for_season else "No"
    )

    display = display[[
        "Conference rank", "Division rank", "Team", "Team name",
        "PTS", "W", "L", "OT", "GD", "Playoffs"
    ]].sort_values("Conference rank")

    return display, summary



# ============================================================
# LOAD DATA
# ============================================================


REQUIRED_DATA_FILES = [
    "final_game_data.csv",
    "final_game_situation_data.csv",
    "all_team_player_stats.csv",
]

DATA_PREP_SCRIPT = "data_preparation.py"


def missing_required_data_files():
    return [file for file in REQUIRED_DATA_FILES if not Path(file).exists()]


def run_data_preparation_script():
    """
    Run data_preparation.py from inside the Streamlit app when data files are missing.
    This keeps large CSV outputs out of GitHub while still making the app reproducible.
    """
    if not Path(DATA_PREP_SCRIPT).exists():
        raise FileNotFoundError(
            f"{DATA_PREP_SCRIPT} was not found. Put the app file and data_preparation.py in the same GitHub folder."
        )

    result = subprocess.run(
        [sys.executable, DATA_PREP_SCRIPT],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        st.error("Data preparation failed.")
        with st.expander("STDOUT tail"):
            st.text(result.stdout[-4000:])
        with st.expander("STDERR tail"):
            st.text(result.stderr[-4000:])
        raise RuntimeError("Data preparation failed. See Streamlit output above.")

    return result.stdout


def ensure_data_available():
    missing = missing_required_data_files()

    if not missing:
        return

    st.error(
        "Large NHL data files are missing. They are intentionally not stored in GitHub."
    )

    st.write("Missing files:")
    st.write(missing)

    st.info(
        "Click the button below to run data_preparation.py. "
        "The first run can take a while because it downloads team and player data. "
        "After that, the generated CSV/cache files stay available locally."
    )

    if st.button("Generate / download NHL data now"):
        with st.spinner("Running data_preparation.py. This may take several minutes on the first run..."):
            output = run_data_preparation_script()

        st.success("Data preparation finished. Please refresh / rerun the app.")
        with st.expander("Show data-prep output"):
            st.text(output[-8000:])

        st.stop()

    st.stop()


@st.cache_data
def load_data():
    ensure_data_available()

    game_df = pd.read_csv("final_game_data.csv")
    situation_df = pd.read_csv("final_game_situation_data.csv")

    game_df["gameDate"] = pd.to_datetime(game_df["gameDate"])
    situation_df["gameDate"] = pd.to_datetime(situation_df["gameDate"])

    return game_df, situation_df


def season_label(season):
    return f"{int(season)}/{int(season) + 1}"


def season_note(season):
    season = int(season)

    notes = {
        2012: "Lockout-shortened season: teams played 48 regular-season games.",
        2019: "Covid-interrupted season: regular season was shortened and playoffs were played under a special format.",
        2020: "Covid-shortened season: teams played 56 regular-season games with realigned divisions."
    }

    return notes.get(season, "")


def safe_divide(numerator, denominator):
    return numerator / denominator if denominator != 0 else np.nan


def format_number(x, decimals=2):
    if pd.isna(x):
        return "N/A"
    return round(float(x), decimals)


METRIC_HELP = {
    "Games": "Number of games in the selected season and season type.",
    "Record": "NHL record format: wins - regulation losses - overtime/shootout losses.",
    "Points": "NHL points: 2 for any win, 1 for OT/SO loss, 0 for regulation loss.",
    "Points per game": "Total points divided by games played.",
    "Goal differential/game": "Average goals for minus goals against per game.",
    "Goals for/game": "Average number of goals scored by the team per game.",
    "Goals against/game": "Average number of goals conceded by the team per game.",
    "Shots for/game": "Average shots on goal created by the team per game.",
    "Shots against/game": "Average shots on goal allowed per game.",
    "Shot attempts/game": "Average shot attempts created per game, including shots on goal, missed shots, and blocked attempts if available.",
    "Faceoff %": "Faceoffs won divided by total faceoffs, multiplied by 100.",
    "Giveaways/game": "Average giveaways by the team per game.",
    "Team value": "Selected ranking statistic value for the chosen team.",
    "Vs league average": "Team value minus the league average for the selected statistic.",
}


def metric_help(label):
    return METRIC_HELP.get(label, None)


def get_logo_path(team_code):
    return f"logos/{team_code}.svg"


def find_logo_path(team_code):
    """Finds a local logo file for the selected team."""
    for ext in ["svg", "png", "jpg", "jpeg", "webp"]:
        path = f"logos/{team_code}.{ext}"
        if os.path.exists(path):
            return path
    return None


def result_to_numeric(result):
    mapping = {
        "W": 3,
        "OTW": 2,
        "SOW": 2,
        "OTL": -1,
        "SOL": -1,
        "L": -3
    }
    return mapping.get(result, 0)


# ============================================================
# PLAYOFF BRACKET HELPERS
# ============================================================

NHL_TEAM_NAMES = {
    "ANA": "Anaheim Ducks", "ARI": "Arizona Coyotes", "PHX": "Phoenix Coyotes",
    "UTA": "Utah Hockey Club", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
    "CAR": "Carolina Hurricanes", "CBJ": "Columbus Blue Jackets", "CGY": "Calgary Flames",
    "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche", "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers", "FLA": "Florida Panthers",
    "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild", "MTL": "Montreal Canadiens",
    "NJD": "New Jersey Devils", "NSH": "Nashville Predators", "NYI": "New York Islanders",
    "NYR": "New York Rangers", "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins", "SEA": "Seattle Kraken", "SJS": "San Jose Sharks",
    "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs",
    "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights", "WPG": "Winnipeg Jets",
    "WSH": "Washington Capitals", "ATL": "Atlanta Thrashers"
}


def team_full_name(team_code):
    return NHL_TEAM_NAMES.get(str(team_code), str(team_code))

TEAM_TO_CONFERENCE = {
    "ANA": "Western", "ARI": "Western", "PHX": "Western", "UTA": "Western",
    "CGY": "Western", "CHI": "Western", "COL": "Western", "DAL": "Western",
    "EDM": "Western", "LAK": "Western", "MIN": "Western", "NSH": "Western",
    "SJS": "Western", "SEA": "Western", "STL": "Western", "VAN": "Western",
    "VGK": "Western", "WPG": "Western",
    "ATL": "Eastern", "BOS": "Eastern", "BUF": "Eastern", "CAR": "Eastern",
    "CBJ": "Eastern", "DET": "Eastern", "FLA": "Eastern", "MTL": "Eastern",
    "NJD": "Eastern", "NYI": "Eastern", "NYR": "Eastern", "OTT": "Eastern",
    "PHI": "Eastern", "PIT": "Eastern", "TBL": "Eastern", "TOR": "Eastern",
    "WSH": "Eastern"
}


def team_conference(team_code):
    return TEAM_TO_CONFERENCE.get(str(team_code), "Unknown")


TEAM_TO_DIVISION = {
    # Pacific
    "ANA": "Pacific", "CGY": "Pacific", "EDM": "Pacific", "LAK": "Pacific",
    "SEA": "Pacific", "SJS": "Pacific", "VAN": "Pacific", "VGK": "Pacific",

    # Central
    "ARI": "Central", "PHX": "Central", "UTA": "Central", "CHI": "Central",
    "COL": "Central", "DAL": "Central", "MIN": "Central", "NSH": "Central",
    "STL": "Central", "WPG": "Central",

    # Atlantic
    "BOS": "Atlantic", "BUF": "Atlantic", "DET": "Atlantic", "FLA": "Atlantic",
    "MTL": "Atlantic", "OTT": "Atlantic", "TBL": "Atlantic", "TOR": "Atlantic",

    # Metropolitan
    "CAR": "Metropolitan", "CBJ": "Metropolitan", "NJD": "Metropolitan",
    "NYI": "Metropolitan", "NYR": "Metropolitan", "PHI": "Metropolitan",
    "PIT": "Metropolitan", "WSH": "Metropolitan",

    # Defunct / historical fallback
    "ATL": "Southeast / Historical"
}


def team_division(team_code):
    return TEAM_TO_DIVISION.get(str(team_code), "Unknown")


def infer_series_conference(row, final_round_order):
    if int(row["round_order"]) == int(final_round_order):
        return "Final"

    team_a_conf = team_conference(row["Team A"])
    team_b_conf = team_conference(row["Team B"])

    if team_a_conf == team_b_conf:
        return team_a_conf

    winner_conf = team_conference(row["Winner"])
    if winner_conf != "Unknown":
        return winner_conf

    if team_a_conf != "Unknown":
        return team_a_conf
    if team_b_conf != "Unknown":
        return team_b_conf
    return "Unknown"


def attach_bracket_conferences(series_summary):
    if series_summary.empty:
        return series_summary

    df = series_summary.copy()
    final_round_order = int(df["round_order"].max())
    df["Conference"] = df.apply(lambda row: infer_series_conference(row, final_round_order), axis=1)
    return df


def short_series_banner_name(team_code):
    full = team_full_name(team_code)
    replacements = {
        "Columbus Blue Jackets": "Columbus",
        "Vegas Golden Knights": "Vegas",
        "Tampa Bay Lightning": "Tampa Bay",
        "New Jersey Devils": "New Jersey",
        "New York Islanders": "NY Islanders",
        "New York Rangers": "NY Rangers",
        "St. Louis Blues": "St. Louis",
        "Los Angeles Kings": "Los Angeles",
    }
    return replacements.get(full, full)



@st.cache_data(show_spinner=False)
def logo_data_uri(team_code):
    """
    Returns a base64 data URI for a local team logo.
    Supports svg/png/jpg/webp. Falls back to None.
    """
    candidates = [
        f"logos/{team_code}.svg",
        f"logos/{team_code}.png",
        f"logos/{team_code}.jpg",
        f"logos/{team_code}.jpeg",
        f"logos/{team_code}.webp"
    ]

    for path in candidates:
        if os.path.exists(path):
            ext = path.split(".")[-1].lower()
            mime = {
                "svg": "image/svg+xml",
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "webp": "image/webp"
            }.get(ext, "image/png")

            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")

            return f"data:{mime};base64,{encoded}"

    return None


STANLEY_CUP_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/3/3f/Stanley_Cup_no_background.png"
STANLEY_CUP_LOCAL_PATH = os.path.join("assets", "stanley_cup_no_background.png")


@st.cache_data(show_spinner=False)
def stanley_cup_data_uri():
    """
    Download and cache a real transparent Stanley Cup image from Wikimedia Commons.
    The local cache avoids re-downloading it every app run.
    """
    os.makedirs(os.path.dirname(STANLEY_CUP_LOCAL_PATH), exist_ok=True)

    if not os.path.exists(STANLEY_CUP_LOCAL_PATH):
        request = urllib.request.Request(
            STANLEY_CUP_IMAGE_URL,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            image_bytes = response.read()

        with open(STANLEY_CUP_LOCAL_PATH, "wb") as f:
            f.write(image_bytes)

    with open(STANLEY_CUP_LOCAL_PATH, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:image/png;base64,{encoded}"


def team_logo_html(team_code, size=42):
    uri = logo_data_uri(team_code)
    safe_code = html.escape(str(team_code))
    safe_name = html.escape(team_full_name(team_code))

    if uri:
        return (
            f'<img class="team-logo" src="{uri}" '
            f'alt="{safe_code}" title="{safe_name}" '
            f'style="width:{size}px;height:{size}px;" />'
        )

    return f'<div class="logo-fallback" title="{safe_name}">{safe_code}</div>'


def add_playoff_series_info(team_games):
    """
    Adds playoff series information for one selected team.
    This is used for the selected-team table and game-by-game chart.
    """
    df = team_games.sort_values(["gameDate", "gameId"]).copy()

    if df.empty:
        return df

    df["previous_opponent"] = df[OPP_COL].shift(1)
    df["new_series"] = (df[OPP_COL] != df["previous_opponent"]).astype(int)
    df.loc[df.index[0], "new_series"] = 1

    df["series_number"] = df["new_series"].cumsum()
    df["game_in_series"] = df.groupby("series_number").cumcount() + 1

    df["series_matchup"] = (
        "Series "
        + df["series_number"].astype(int).astype(str)
        + ": "
        + df[TEAM_COL].astype(str)
        + " vs "
        + df[OPP_COL].astype(str)
    )

    df["series_game_label"] = (
        "S"
        + df["series_number"].astype(int).astype(str)
        + " G"
        + df["game_in_series"].astype(int).astype(str)
    )

    return df.drop(columns=["previous_opponent", "new_series"])


def build_selected_team_playoff_series_summary(team_games):
    """
    Builds series summary for selected team only.
    """
    df = add_playoff_series_info(team_games)

    if df.empty:
        return pd.DataFrame()

    rows = []

    for series_number, s in df.groupby("series_number"):
        opponent = s[OPP_COL].iloc[0]

        team_wins = int(s["record_w"].sum())
        opponent_wins = int(len(s) - team_wins)

        if team_wins > opponent_wins:
            series_result = f"Won {team_wins}-{opponent_wins}"
            series_winner = s[TEAM_COL].iloc[0]
        else:
            series_result = f"Lost {team_wins}-{opponent_wins}"
            series_winner = opponent

        rows.append({
            "Series": int(series_number),
            "Matchup": f"{s[TEAM_COL].iloc[0]} vs {opponent}",
            "Opponent": opponent,
            "Games": int(len(s)),
            "Team wins": team_wins,
            "Opponent wins": opponent_wins,
            "Series result": series_result,
            "Series winner": series_winner,
            "Start date": s["gameDate"].min().date(),
            "End date": s["gameDate"].max().date()
        })

    return pd.DataFrame(rows)


def assign_playoff_rounds(series_summary):
    """
    Assign playoff rounds for visual bracket construction.

    Date-gap inference is not reliable because NHL rounds can overlap in time:
    a later round may start before every previous-round series has finished.
    This version uses series counts: standard NHL playoffs are 8 + 4 + 2 + 1.
    """
    if series_summary.empty:
        return series_summary

    df = series_summary.sort_values(["Start date", "End date", "Matchup"]).copy()
    n = len(df)

    if n == 15:
        round_sizes = [8, 4, 2, 1]
        labels = {
            1: "Round 1",
            2: "Round 2",
            3: "Conference Finals",
            4: "Stanley Cup Final"
        }
    elif n == 31:
        round_sizes = [16, 8, 4, 2, 1]
        labels = {
            1: "Qualifying Round",
            2: "Round 1",
            3: "Round 2",
            4: "Conference Finals",
            5: "Stanley Cup Final"
        }
    elif n == 7:
        round_sizes = [4, 2, 1]
        labels = {
            1: "Round 2",
            2: "Conference Finals",
            3: "Stanley Cup Final"
        }
    else:
        sizes = []
        remaining = n
        while remaining > 1:
            size = max(1, remaining // 2)
            sizes.append(size)
            remaining -= size
        sizes.append(1)
        round_sizes = sizes
        labels = {i: f"Playoff Round {i}" for i in range(1, len(round_sizes) + 1)}
        labels[len(round_sizes)] = "Stanley Cup Final"

    round_ids = []
    for round_number, size in enumerate(round_sizes, start=1):
        round_ids.extend([round_number] * size)

    if len(round_ids) < n:
        round_ids.extend([len(round_sizes)] * (n - len(round_ids)))

    df["round_order"] = round_ids[:n]
    df["Round"] = df["round_order"].map(labels)
    df["card_order"] = df.groupby("round_order").cumcount() + 1

    return df


def build_league_playoff_series_summary(league_playoff_games):
    """
    Builds full playoff series summary for a selected season.

    Stronger than the older version:
    - Uses one real game per gameId/matchup.
    - Splits the same matchup into a new series if the teams meet again
      after a long gap. This protects weird seasons / possible rematches.
    - Assigns visual rounds by timing rather than pretending the data contains
      official bracket metadata.
    """
    df = league_playoff_games.copy()

    if df.empty:
        return pd.DataFrame()

    df["team_a"] = df[[TEAM_COL, OPP_COL]].min(axis=1)
    df["team_b"] = df[[TEAM_COL, OPP_COL]].max(axis=1)
    df["matchup_key"] = df["team_a"] + "_" + df["team_b"]

    one_game = (
        df.sort_values(["matchup_key", "gameDate", "gameId", TEAM_COL])
        .drop_duplicates(["gameId", "matchup_key"])
        .copy()
    )

    one_game["gap_days"] = (
        one_game.groupby("matchup_key")["gameDate"]
        .diff()
        .dt.days
    )

    one_game["new_series_instance"] = (
        one_game["gap_days"].isna() | (one_game["gap_days"] > 10)
    ).astype(int)

    one_game["series_instance"] = (
        one_game.groupby("matchup_key")["new_series_instance"]
        .cumsum()
        .astype(int)
    )

    one_game["series_key"] = (
        one_game["matchup_key"]
        + "_"
        + one_game["series_instance"].astype(str)
    )

    rows = []

    for series_key, s in one_game.groupby("series_key"):
        team_a = s["team_a"].iloc[0]
        team_b = s["team_b"].iloc[0]
        game_ids = s["gameId"].unique().tolist()

        all_team_rows = df[df["gameId"].isin(game_ids)].copy()

        team_a_wins = int(
            all_team_rows[
                (all_team_rows[TEAM_COL] == team_a) &
                (all_team_rows["record_w"] == 1)
            ].shape[0]
        )

        team_b_wins = int(
            all_team_rows[
                (all_team_rows[TEAM_COL] == team_b) &
                (all_team_rows["record_w"] == 1)
            ].shape[0]
        )

        if team_a_wins > team_b_wins:
            winner = team_a
            loser = team_b
            winner_wins = team_a_wins
            loser_wins = team_b_wins
        elif team_b_wins > team_a_wins:
            winner = team_b
            loser = team_a
            winner_wins = team_b_wins
            loser_wins = team_a_wins
        else:
            winner = "Unknown"
            loser = "Unknown"
            winner_wins = team_a_wins
            loser_wins = team_b_wins

        rows.append({
            "Series key": series_key,
            "Matchup": f"{team_a} vs {team_b}",
            "Team A": team_a,
            "Team B": team_b,
            "Team A wins": team_a_wins,
            "Team B wins": team_b_wins,
            "Games": int(len(game_ids)),
            "Winner": winner,
            "Loser": loser,
            "Winner wins": winner_wins,
            "Loser wins": loser_wins,
            "Series result": (
                f"{winner} wins {winner_wins}-{loser_wins}"
                if winner != "Unknown"
                else f"Tied {team_a_wins}-{team_b_wins}"
            ),
            "Start date": s["gameDate"].min().date(),
            "End date": s["gameDate"].max().date()
        })

    summary = pd.DataFrame(rows)

    if summary.empty:
        return summary

    summary = assign_playoff_rounds(summary)
    summary = summary.sort_values(["round_order", "card_order", "Start date", "Matchup"]).reset_index(drop=True)
    summary["Series order"] = range(1, len(summary) + 1)

    return summary


def render_playoff_bracket(series_summary, selected_team, season_value=None):
    """
    Bigger, cleaner NHL-style playoff bracket.

    Cards use only:
    - winner banner
    - series score
    - team logos
    - team abbreviations

    Selected team path:
    - selected series cards are highlighted in gold
    - connectors between selected-team series are highlighted in gold
    """
    if series_summary.empty:
        return ""

    df = attach_bracket_conferences(series_summary)
    final_round_order = int(df["round_order"].max())

    west_df = df[(df["Conference"] == "Western") & (df["round_order"] < final_round_order)].copy()
    east_df = df[(df["Conference"] == "Eastern") & (df["round_order"] < final_round_order)].copy()
    final_df = df[df["round_order"] == final_round_order].copy()

    def round_records(side_df, round_order):
        out = side_df[side_df["round_order"] == round_order].copy()
        out = out.sort_values(["card_order", "Start date", "Matchup"])
        return out.to_dict("records")

    west_r1 = round_records(west_df, 1)
    west_r2 = round_records(west_df, 2)
    west_cf = round_records(west_df, 3)

    east_r1 = round_records(east_df, 1)
    east_r2 = round_records(east_df, 2)
    east_cf = round_records(east_df, 3)

    final_rows = final_df.sort_values(["card_order", "Start date", "Matchup"]).to_dict("records")

    svg_w = 1600
    svg_h = 800

    # Larger cards/logos/fonts, while keeping the same overall bracket footprint.
    card_w = 190
    card_h = 104
    header_h = 22

    X = {
        "west_r1": 55,
        "west_r2": 295,
        "west_cf": 535,
        "final": 705,
        "east_cf": 875,
        "east_r2": 1115,
        "east_r1": 1355,
    }

    Y = {
        "r1": [140, 265, 390, 515],
        "r2": [202, 452],
        "cf": [327],
        "final": [205],
    }

    def esc(x):
        return html.escape(str(x))

    cup_uri = stanley_cup_data_uri()

    def stanley_cup_image(cx=800, y=585, height=125):
        # Real transparent PNG image, centered at the bottom of the bracket.
        if not cup_uri:
            return ""

        # Original image is 672 x 1712.
        width = height * (672 / 1712)

        return f"""
        <g>
            <ellipse cx="{cx}" cy="{y + height + 4}" rx="{width * 0.62}" ry="8"
                     fill="rgba(0,0,0,0.42)" />
            <circle cx="{cx}" cy="{y + height * 0.45}" r="{height * 0.42}"
                    fill="rgba(255,255,255,0.10)" />
            <image href="{cup_uri}"
                   x="{cx - width/2}" y="{y}"
                   width="{width}" height="{height}"
                   preserveAspectRatio="xMidYMid meet" />
        </g>
        """

    def logo_svg(team_code, x, y, size=44):
        uri = logo_data_uri(team_code)
        if uri:
            return (
                f'<image href="{uri}" x="{x}" y="{y}" width="{size}" height="{size}" '
                f'preserveAspectRatio="xMidYMid meet" />'
            )
        return (
            f'<circle cx="{x + size/2}" cy="{y + size/2}" r="{size/2}" fill="#e5e7eb" />'
            f'<text x="{x + size/2}" y="{y + size/2 + 4}" text-anchor="middle" '
            f'font-size="11" font-weight="900" fill="#111827">{esc(team_code)}</text>'
        )

    def header_title(row):
        winner = row.get("Winner", "Unknown")
        if winner == "Unknown":
            return "SERIES"
        return f"{short_series_banner_name(winner).upper()} WINS"

    def side_color(side):
        if side == "west":
            return "#0b5f9e"
        if side == "east":
            return "#b91c1c"
        return "#c49a2c"

    def selected_in(row):
        return selected_team in [row.get("Team A"), row.get("Team B")]

    def card(row, x, y, side):
        team_a = row["Team A"]
        team_b = row["Team B"]
        winner = row["Winner"]
        a_wins = int(row["Team A wins"])
        b_wins = int(row["Team B wins"])
        selected = selected_in(row)

        stroke = "#facc15" if selected else "rgba(255,255,255,0.60)"
        stroke_w = 4 if selected else 1.3
        header = "#f59e0b" if selected else side_color(side)
        shadow = "filter: drop-shadow(0px 0px 10px rgba(250,204,21,0.95));" if selected else ""

        a_fill = "#111827" if team_a == winner else "#4b5563"
        b_fill = "#111827" if team_b == winner else "#4b5563"
        a_weight = "950" if team_a == winner else "800"
        b_weight = "950" if team_b == winner else "800"

        return f"""
        <g style="{shadow}">
            <rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="10" fill="rgba(248,250,252,0.95)"
                  stroke="{stroke}" stroke-width="{stroke_w}" />
            <rect x="{x}" y="{y}" width="{card_w}" height="{header_h}" rx="10" fill="{header}" />
            <rect x="{x}" y="{y + header_h - 7}" width="{card_w}" height="7" fill="{header}" />
            <text x="{x + card_w/2}" y="{y + 52}" text-anchor="middle"
                  font-size="32" font-weight="950" fill="#111827">{a_wins} - {b_wins}</text>
            {logo_svg(team_a, x + 30, y + 58, 40)}
            {logo_svg(team_b, x + card_w - 70, y + 58, 40)}
            <text x="{x + 50}" y="{y + 99}" text-anchor="middle"
                  font-size="12" font-weight="{a_weight}" fill="{a_fill}">{esc(team_a)}</text>
            <text x="{x + card_w - 50}" y="{y + 99}" text-anchor="middle"
                  font-size="12" font-weight="{b_weight}" fill="{b_fill}">{esc(team_b)}</text>
        </g>
        """

    def hline(x1, y, x2, color="#e5e7eb", w=4):
        return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="{w}" stroke-linecap="round" />'

    def vline(x, y1, y2, color="#e5e7eb", w=4):
        return f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{color}" stroke-width="{w}" stroke-linecap="round" />'

    def connector_style(rows_from, rows_to):
        rows_from = rows_from if isinstance(rows_from, list) else [rows_from]
        rows_to = rows_to if isinstance(rows_to, list) else [rows_to]
        involved = rows_from + rows_to
        if any(selected_in(row) for row in involved):
            return "#facc15", 6
        return "#e5e7eb", 4

    def west_pair_connector(x_from, y_top, y_bottom, x_to, y_target, rows_from=None, row_to=None):
        color, width = connector_style(rows_from or [], row_to or [])
        x_mid = x_from + card_w + 24
        return (
            hline(x_from + card_w, y_top + card_h/2, x_mid, color, width)
            + hline(x_from + card_w, y_bottom + card_h/2, x_mid, color, width)
            + vline(x_mid, y_top + card_h/2, y_bottom + card_h/2, color, width)
            + hline(x_mid, y_target + card_h/2, x_to, color, width)
        )

    def east_pair_connector(x_from, y_top, y_bottom, x_to, y_target, rows_from=None, row_to=None):
        color, width = connector_style(rows_from or [], row_to or [])
        x_mid = x_from - 24
        return (
            hline(x_from, y_top + card_h/2, x_mid, color, width)
            + hline(x_from, y_bottom + card_h/2, x_mid, color, width)
            + vline(x_mid, y_top + card_h/2, y_bottom + card_h/2, color, width)
            + hline(x_mid, y_target + card_h/2, x_to + card_w, color, width)
        )

    def west_direct_connector(x_from, y_from, x_to, y_to, row_from=None, row_to=None):
        color, width = connector_style(row_from or [], row_to or [])
        x_mid = x_from + card_w + 18
        return (
            hline(x_from + card_w, y_from + card_h/2, x_mid, color, width)
            + vline(x_mid, y_from + card_h/2, y_to + card_h/2, color, width)
            + hline(x_mid, y_to + card_h/2, x_to, color, width)
        )

    def east_direct_connector(x_from, y_from, x_to, y_to, row_from=None, row_to=None):
        color, width = connector_style(row_from or [], row_to or [])
        x_mid = x_from - 18
        return (
            hline(x_from, y_from + card_h/2, x_mid, color, width)
            + vline(x_mid, y_from + card_h/2, y_to + card_h/2, color, width)
            + hline(x_mid, y_to + card_h/2, x_to + card_w, color, width)
        )

    def draw_series_list(rows, x, ys, side):
        parts = []
        for row, y in zip(rows, ys):
            parts.append(card(row, x, y, side))
        return "".join(parts)

    season_text = season_label(season_value) if season_value is not None else ""

    parts = [f"""
    <div style="width:100%; overflow:hidden; background:transparent;">
    <svg xmlns="http://www.w3.org/2000/svg"
         width="100%" height="800" viewBox="0 0 {svg_w} {svg_h}"
         preserveAspectRatio="xMidYMid meet"
         style="display:block; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
        <defs>
            <linearGradient id="bg" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="#061426" />
                <stop offset="48%" stop-color="#111827" />
                <stop offset="100%" stop-color="#2a0a12" />
            </linearGradient>
            <radialGradient id="spot" cx="50%" cy="38%" r="55%">
                <stop offset="0%" stop-color="rgba(255,255,255,0.13)" />
                <stop offset="100%" stop-color="rgba(255,255,255,0)" />
            </radialGradient>
        </defs>

        <rect x="0" y="0" width="{svg_w}" height="{svg_h}" rx="20" fill="url(#bg)" />
        <rect x="0" y="0" width="{svg_w}" height="{svg_h}" rx="20" fill="url(#spot)" />

        <text x="800" y="45" text-anchor="middle"
              font-size="36" font-weight="950" fill="#ffffff" letter-spacing="4">
              PLAYOFF BRACKET
        </text>
        <text x="800" y="76" text-anchor="middle"
              font-size="15" font-weight="800" fill="#d1d5db">{esc(season_text)}</text>

        <text x="200" y="106" text-anchor="middle"
              font-size="19" font-weight="950" fill="#bfdbfe" letter-spacing="1.3">
              WESTERN CONFERENCE
        </text>
        <line x1="55" y1="126" x2="665" y2="126" stroke="#0b5f9e" stroke-width="7" stroke-linecap="round" />

        <text x="1400" y="106" text-anchor="middle"
              font-size="19" font-weight="950" fill="#fecdd3" letter-spacing="1.3">
              EASTERN CONFERENCE
        </text>
        <line x1="935" y1="126" x2="1545" y2="126" stroke="#b91c1c" stroke-width="7" stroke-linecap="round" />

        <text x="800" y="145" text-anchor="middle"
              font-size="18" font-weight="950" fill="#f8fafc" letter-spacing="1.5">
              STANLEY CUP FINAL
        </text>
    """]

    # West connectors
    if len(west_r1) >= 4 and len(west_r2) >= 2:
        parts.append(west_pair_connector(X["west_r1"], Y["r1"][0], Y["r1"][1], X["west_r2"], Y["r2"][0], [west_r1[0], west_r1[1]], west_r2[0]))
        parts.append(west_pair_connector(X["west_r1"], Y["r1"][2], Y["r1"][3], X["west_r2"], Y["r2"][1], [west_r1[2], west_r1[3]], west_r2[1]))
    if len(west_r2) >= 2 and len(west_cf) >= 1:
        parts.append(west_pair_connector(X["west_r2"], Y["r2"][0], Y["r2"][1], X["west_cf"], Y["cf"][0], [west_r2[0], west_r2[1]], west_cf[0]))
    if len(west_cf) >= 1 and final_rows:
        parts.append(west_direct_connector(X["west_cf"], Y["cf"][0], X["final"], Y["final"][0], west_cf[0], final_rows[0]))

    # East connectors
    if len(east_r1) >= 4 and len(east_r2) >= 2:
        parts.append(east_pair_connector(X["east_r1"], Y["r1"][0], Y["r1"][1], X["east_r2"], Y["r2"][0], [east_r1[0], east_r1[1]], east_r2[0]))
        parts.append(east_pair_connector(X["east_r1"], Y["r1"][2], Y["r1"][3], X["east_r2"], Y["r2"][1], [east_r1[2], east_r1[3]], east_r2[1]))
    if len(east_r2) >= 2 and len(east_cf) >= 1:
        parts.append(east_pair_connector(X["east_r2"], Y["r2"][0], Y["r2"][1], X["east_cf"], Y["cf"][0], [east_r2[0], east_r2[1]], east_cf[0]))
    if len(east_cf) >= 1 and final_rows:
        parts.append(east_direct_connector(X["east_cf"], Y["cf"][0], X["final"], Y["final"][0], east_cf[0], final_rows[0]))

    # Cards
    parts.append(draw_series_list(west_r1[:4], X["west_r1"], Y["r1"], "west"))
    parts.append(draw_series_list(west_r2[:2], X["west_r2"], Y["r2"], "west"))
    parts.append(draw_series_list(west_cf[:1], X["west_cf"], Y["cf"], "west"))

    if final_rows:
        parts.append(draw_series_list(final_rows[:1], X["final"], Y["final"], "final"))

    parts.append(draw_series_list(east_cf[:1], X["east_cf"], Y["cf"], "east"))
    parts.append(draw_series_list(east_r2[:2], X["east_r2"], Y["r2"], "east"))
    parts.append(draw_series_list(east_r1[:4], X["east_r1"], Y["r1"], "east"))

    parts.append(f"""
        {stanley_cup_image(cx=800, y=585, height=125)}

        <text x="800" y="730" text-anchor="middle"
              font-size="14" font-weight="900" fill="#facc15">
              Selected team path is highlighted in gold.
        </text>
        <text x="800" y="755" text-anchor="middle"
              font-size="11" font-weight="700" fill="#9ca3af">
              Visual order is inferred from available series data. Official seed slots require extra data-prep columns.
        </text>
    </svg>
    </div>
    """)

    return "".join(parts)



def render_regular_season_logo_table(ranking_table, selected_team):
    """
    HTML league table with logos and highlighted selected team.
    Used mainly for Regular season, where standings are more meaningful.
    """
    rows_html = []

    for _, row in ranking_table.iterrows():
        team_code = str(row["Team"])
        selected_class = " selected-row" if team_code == selected_team else ""
        logo = team_logo_html(team_code, size=32)

        rows_html.append(f"""
            <tr class="{selected_class}">
                <td class="rank-cell">{int(row["Rank"])}</td>
                <td class="logo-cell">{logo}</td>
                <td class="team-cell">
                    <div class="team-name-main">{html.escape(team_full_name(team_code))}</div>
                    <div class="team-code-sub">{html.escape(team_code)}</div>
                </td>
                <td class="pts-cell">{int(row["PTS"])}</td>
                <td>{int(row["W"])}</td>
                <td>{int(row["L"])}</td>
                <td>{int(row["OT"])}</td>
                <td>{int(row["GP"])}</td>
                <td>{int(row["GD"])}</td>
            </tr>
        """)

    return f"""
    <style>
        .standings-wrap {{
            width: 100%;
            overflow-x: auto;
            margin-top: 8px;
            border-radius: 16px;
            border: 1px solid rgba(148, 163, 184, 0.35);
        }}
        table.logo-standings {{
            width: 100%;
            border-collapse: collapse;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
        }}
        .logo-standings thead tr {{
            background: #0f172a;
            color: white;
        }}
        .logo-standings th {{
            text-align: left;
            padding: 10px 12px;
            font-weight: 800;
            letter-spacing: 0.4px;
            white-space: nowrap;
        }}
        .logo-standings td {{
            padding: 9px 12px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.25);
            vertical-align: middle;
            white-space: nowrap;
        }}
        .logo-standings tbody tr:nth-child(even) {{
            background: rgba(248, 250, 252, 0.75);
        }}
        .logo-standings tbody tr:nth-child(odd) {{
            background: rgba(255, 255, 255, 0.95);
        }}
        .logo-standings tr.selected-row {{
            background: rgba(250, 204, 21, 0.28) !important;
            outline: 2px solid #facc15;
            outline-offset: -2px;
            font-weight: 800;
        }}
        .rank-cell {{
            font-weight: 800;
            color: #0f172a;
            width: 48px;
        }}
        .logo-cell {{
            width: 46px;
        }}
        .team-cell {{
            min-width: 220px;
        }}
        .team-name-main {{
            font-weight: 800;
            color: #0f172a;
            line-height: 1.1;
        }}
        .team-code-sub {{
            font-size: 11px;
            color: #64748b;
            margin-top: 2px;
        }}
        .pts-cell {{
            font-weight: 900;
            color: #0f172a;
        }}
    </style>

    <div class="standings-wrap">
        <table class="logo-standings">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Logo</th>
                    <th>Team</th>
                    <th>PTS</th>
                    <th>W</th>
                    <th>L</th>
                    <th>OT</th>
                    <th>GP</th>
                    <th>GD</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """



def build_sortable_league_table(ranking, selected_team, playoff_teams=None):
    """
    Build a sortable Streamlit dataframe for league standings/stat comparison.
    Includes logos and all key stats from the app's ranking options.
    """
    table = ranking.copy()
    playoff_teams = set(playoff_teams or [])

    table["Logo"] = table[TEAM_COL].apply(lambda x: logo_data_uri(str(x)) or "")
    table["Team"] = table[TEAM_COL].astype(str)
    table["Team name"] = table[TEAM_COL].apply(team_full_name)

    show = pd.DataFrame({
        "Rank": table["rank"].astype(int),
        "Logo": table["Logo"],
        "Team": table["Team"],
        "Team name": table["Team name"],
        "Conference": table[TEAM_COL].apply(team_conference),
        "Division": table[TEAM_COL].apply(team_division),
        "Playoffs": table[TEAM_COL].astype(str).apply(lambda x: "Yes" if x in playoff_teams else "No"),
        "PTS": table["total_points"].round(0).astype(int),
        "W": table["W"].round(0).astype(int),
        "L": table["L"].round(0).astype(int),
        "OT": table["OT"].round(0).astype(int),
        "RW": table["RW"].round(0).astype(int),
        "ROW": table["ROW"].round(0).astype(int),
        "GP": table["games"].round(0).astype(int),
        "GD": table["goal_diff_total"].round(0).astype(int),
        "PTS/GP": table["points_per_game"].round(2),
        "GD/GP": table["goal_diff_per_game"].round(2),
        "GF/GP": table["goals_for_per_game"].round(2),
        "GA/GP": table["goals_against_per_game"].round(2),
        "SF/GP": table["shots_for_per_game"].round(2),
        "SA/GP": table["shots_against_per_game"].round(2),
        "Shot attempts/GP": table["shot_attempts_for_per_game"].round(2),
        "FO%": table["faceoff_pct"].round(2),
        "Giveaways/GP": table["giveaways_per_game"].round(2),
    })

    return show


def highlight_selected_team(row, selected_team):
    if str(row.get("Team", "")) == str(selected_team):
        return ["background-color: rgba(250, 204, 21, 0.42); font-weight: 900;"] * len(row)

    if str(row.get("Playoffs", "")) == "Yes":
        return ["background-color: rgba(34, 197, 94, 0.13);"] * len(row)

    return [""] * len(row)


def show_sortable_league_table(ranking, selected_team, season_type, view_mode, playoff_teams=None):
    table = build_sortable_league_table(ranking, selected_team, playoff_teams=playoff_teams)

    st.caption(
        "Click any column header to sort the table. "
        "Use the filters below to show only one conference or one division. "
        "NHL record format is W-L-OT, not draws."
        + (" Current table reflects the selected game situation." if view_mode != "Full game" else "")
    )

    f1, f2 = st.columns(2)

    conference_options = ["All"] + [
        c for c in sorted(table["Conference"].dropna().unique().tolist())
        if c != "Unknown"
    ]

    selected_conference = f1.selectbox(
        "Conference",
        options=conference_options,
        index=0,
        key=f"league_conference_filter_{season}_{season_type}_{view_mode}"
    )

    if selected_conference == "All":
        division_base = table.copy()
    else:
        division_base = table[table["Conference"] == selected_conference].copy()

    division_options = ["All"] + [
        d for d in sorted(division_base["Division"].dropna().unique().tolist())
        if d != "Unknown"
    ]

    selected_division = f2.selectbox(
        "Division",
        options=division_options,
        index=0,
        key=f"league_division_filter_{season}_{season_type}_{view_mode}_{selected_conference}"
    )

    filtered = table.copy()

    if selected_conference != "All":
        filtered = filtered[filtered["Conference"] == selected_conference]

    if selected_division != "All":
        filtered = filtered[filtered["Division"] == selected_division]

    # Re-number visible rows after filtering so the filtered table is readable.
    filtered = filtered.copy()
    filtered["Rank"] = range(1, len(filtered) + 1)

    styled_table = filtered.style.apply(
        lambda row: highlight_selected_team(row, selected_team),
        axis=1
    )

    st.dataframe(
        styled_table,
        use_container_width=True,
        hide_index=True,
        row_height=46,
        column_config={
            "Logo": st.column_config.ImageColumn("Logo", help="Team logo", width="small"),
            "Team name": st.column_config.TextColumn("Team name", width="medium"),
            "Conference": st.column_config.TextColumn("Conference", width="small"),
            "Division": st.column_config.TextColumn("Division", width="small"),
            "Data range": st.column_config.TextColumn("Data range", help="Seasons available for this team code in the dataset."),
            "Playoffs": st.column_config.TextColumn("Playoffs", help="Yes if the team qualified for the playoffs in the selected season."),
            "PTS": st.column_config.NumberColumn("PTS", help="Total NHL points."),
            "W": st.column_config.NumberColumn("W", help="Wins."),
            "L": st.column_config.NumberColumn("L", help="Regulation losses."),
            "OT": st.column_config.NumberColumn("OT", help="Overtime/shootout losses."),
            "RW": st.column_config.NumberColumn("RW", help="Regulation wins."),
            "ROW": st.column_config.NumberColumn("ROW", help="Regulation plus overtime wins, excluding shootout wins."),
            "FO%": st.column_config.NumberColumn("FO%", help="Faceoff win percentage."),
        }
    )



def add_official_like_standings_order(ranking):
    """
    Sort standings with unique positions using NHL-style available tiebreakers.

    Implemented from available columns:
    1) Points
    2) Fewer games played / better points percentage proxy
    3) Regulation wins (RW)
    4) Regulation + overtime wins, excluding shootout wins (ROW)
    5) Total wins (W)
    6) Goal differential (GD)
    7) Goals for (GF)

    Official NHL head-to-head points are not implemented here because they require
    pairwise schedule-level calculations for each tied group.
    """
    out = ranking.copy()

    # These columns are available in game-level data, so aggregate them before calling this
    # or default to safe fallback if an older table does not include them.
    for col in ["RW", "ROW", "GF", "GD"]:
        if col not in out.columns:
            out[col] = 0

    out = out.sort_values(
        by=["total_points", "games", "RW", "ROW", "W", "GD", "GF", TEAM_COL],
        ascending=[False, True, False, False, False, False, False, True],
        kind="mergesort"
    ).reset_index(drop=True)

    out["rank"] = np.arange(1, len(out) + 1)
    return out




# ============================================================
# ANALYTICAL SECTIONS HELPERS
# ============================================================

def selected_team_playoff_path_table(playoff_team_games, selected_team):
    """
    Create a readable playoff path summary:
    Round/Series, opponent, W/L, score, games, goals.
    """
    if playoff_team_games.empty:
        return pd.DataFrame()

    games = add_playoff_series_info(playoff_team_games.copy())

    if "series_number" not in games.columns:
        return pd.DataFrame()

    rows = []

    for series_number, group in games.groupby("series_number", sort=True):
        group = group.sort_values(["gameDate", "gameId"]).copy()

        opponents = group[OPP_COL].dropna().astype(str).unique().tolist()
        opponent = opponents[0] if opponents else "Unknown"

        wins = int((group["points"] == 2).sum())
        losses = int((group["points"] < 2).sum())

        gf = int(group["game_goals_for"].sum())
        ga = int(group["game_goals_against"].sum())

        result = "Won" if wins > losses else "Lost"
        score = f"{wins}-{losses}"

        # If the series summary is built correctly, series_number is chronological.
        rows.append({
            "Round / series": f"Series {int(series_number)}",
            "Opponent": opponent,
            "Result": result,
            "Series score": score,
            "Games": int(group["gameId"].nunique()),
            "Goals for": gf,
            "Goals against": ga
        })

    return pd.DataFrame(rows)


def render_playoff_path_cards(path_df, selected_team):
    if path_df.empty:
        st.info("No playoff path summary available for this team.")
        return

    cols = st.columns(min(len(path_df), 4))

    for i, (_, row) in enumerate(path_df.iterrows()):
        with cols[i % len(cols)]:
            won = str(row["Result"]) == "Won"
            icon = "✅" if won else "❌"
            st.markdown(
                f"""
                <div style="
                    border: 1px solid rgba(148,163,184,0.35);
                    border-radius: 16px;
                    padding: 14px 16px;
                    background: {'rgba(34,197,94,0.10)' if won else 'rgba(239,68,68,0.10)'};
                    min-height: 132px;
                ">
                    <div style="font-size: 13px; font-weight: 800; color: #64748b;">
                        {html.escape(str(row['Round / series']))}
                    </div>
                    <div style="font-size: 22px; font-weight: 950; margin-top: 4px;">
                        {icon} {html.escape(str(row['Result']))} {html.escape(str(row['Series score']))}
                    </div>
                    <div style="font-size: 15px; margin-top: 6px;">
                        vs <b>{html.escape(team_full_name(row['Opponent']))} ({html.escape(str(row['Opponent']))})</b>
                    </div>
                    <div style="font-size: 12px; margin-top: 8px; color: #64748b;">
                        Goals: {int(row['Goals for'])}–{int(row['Goals against'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


def build_head_to_head_summary(game_df, team_a, team_b, season, season_type):
    h2h = (
        game_df[
            (game_df["season"] == season) &
            (game_df["season_type"] == season_type) &
            (game_df[TEAM_COL] == team_a) &
            (game_df[OPP_COL] == team_b)
        ]
        .drop_duplicates(["gameId", TEAM_COL])
        .sort_values(["gameDate", "gameId"])
        .copy()
    )

    if h2h.empty:
        return h2h, {}

    summary = {
        "games": int(h2h["gameId"].nunique()),
        "wins": int(h2h["record_w"].sum()),
        "losses": int(h2h["record_l"].sum()),
        "ot_losses": int(h2h["record_ot"].sum()),
        "points": int(h2h["points"].sum()),
        "goals_for": int(h2h["game_goals_for"].sum()),
        "goals_against": int(h2h["game_goals_against"].sum())
    }

    summary["record"] = f"{summary['wins']}-{summary['losses']}-{summary['ot_losses']}"
    summary["goals"] = f"{summary['goals_for']}-{summary['goals_against']}"

    return h2h, summary


def add_conference_division_ranks(ranking):
    out = ranking.copy()
    out["Conference"] = out[TEAM_COL].apply(team_conference)
    out["Division"] = out[TEAM_COL].apply(team_division)

    out["Conference rank"] = (
        out.groupby("Conference")["rank"]
        .rank(method="first", ascending=True)
        .astype(int)
    )

    out["Division rank"] = (
        out.groupby("Division")["rank"]
        .rank(method="first", ascending=True)
        .astype(int)
    )

    return out


def playoff_race_summary_table(ranking, selected_team, playoff_teams_for_season):
    """
    Practical playoff race summary based on known playoff qualifiers in the dataset.
    The cutoff is inferred from the lowest-points playoff team in the selected team's conference.
    """
    if ranking.empty or selected_team not in ranking[TEAM_COL].values:
        return pd.DataFrame(), {}

    table = add_conference_division_ranks(ranking)

    selected_row = table.loc[table[TEAM_COL] == selected_team].iloc[0]
    selected_conf = selected_row["Conference"]

    conf_table = table[table["Conference"] == selected_conf].copy()

    conf_playoff = conf_table[conf_table[TEAM_COL].astype(str).isin(playoff_teams_for_season)].copy()

    if conf_playoff.empty:
        cutoff_points = np.nan
        points_above_cutoff = np.nan
    else:
        cutoff_points = float(conf_playoff["total_points"].min())
        points_above_cutoff = float(selected_row["total_points"] - cutoff_points)

    summary = {
        "conference": selected_conf,
        "division": selected_row["Division"],
        "conference_rank": int(selected_row["Conference rank"]),
        "division_rank": int(selected_row["Division rank"]),
        "qualified": str(selected_team) in playoff_teams_for_season,
        "points": int(selected_row["total_points"]),
        "cutoff_points": cutoff_points,
        "points_above_cutoff": points_above_cutoff
    }

    display = conf_table[[
        "rank", TEAM_COL, "Conference rank", "Division rank",
        "total_points", "W", "L", "OT", "goal_diff_total"
    ]].copy()

    display = display.rename(columns={
        "rank": "League rank",
        TEAM_COL: "Team",
        "total_points": "PTS",
        "goal_diff_total": "GD"
    })

    display["Team name"] = display["Team"].apply(team_full_name)
    display["Playoffs"] = display["Team"].astype(str).apply(
        lambda x: "Yes" if x in playoff_teams_for_season else "No"
    )

    display = display[[
        "Conference rank", "Division rank", "Team", "Team name",
        "PTS", "W", "L", "OT", "GD", "Playoffs"
    ]].sort_values("Conference rank")

    return display, summary



# ============================================================
# LOAD DATA
# ============================================================


@st.cache_data
def load_player_stats():
    """
    Player-level dataset created by data_preparation.py.
    all_top_skaters_by_points.csv is optional because the app can calculate leaders
    directly from all_team_player_stats.csv.
    """
    ensure_data_available()

    player_path = Path("all_team_player_stats.csv")
    top_path = Path("all_top_skaters_by_points.csv")

    player_stats = pd.read_csv(player_path) if player_path.exists() else pd.DataFrame()
    top_skaters = pd.read_csv(top_path) if top_path.exists() else pd.DataFrame()

    return player_stats, top_skaters


game_df, situation_df = load_data()
player_stats_df, top_skaters_df = load_player_stats()


# ============================================================
# REQUIRED COLUMN CHECKS
# ============================================================

required_cols = [
    TEAM_COL,
    OPP_COL,
    "season",
    "season_type",
    "gameId",
    "gameDate",
    "points",
    "record_w",
    "record_l",
    "record_ot",
    "game_result",
    "game_result_order",
    "game_goals_for",
    "game_goals_against",
    "game_goal_diff",
    "regulation_win",
    "ot_win",
    "so_win",
    "regulation_loss",
    "ot_loss",
    "so_loss"
]

missing_cols = [col for col in required_cols if col not in game_df.columns]

if missing_cols:
    st.error(
        "Your final_game_data.csv is missing required columns: "
        + ", ".join(missing_cols)
    )
    st.stop()



# ============================================================
# TEAM DATA AVAILABILITY / HISTORICAL TEAM NOTES
# ============================================================

@st.cache_data(show_spinner=False)
def build_team_availability_table(game_df):
    availability = (
        game_df
        .groupby(TEAM_COL)
        .agg(
            first_season=("season", "min"),
            last_season=("season", "max"),
            seasons_count=("season", "nunique"),
            regular_games=("gameId", lambda x: game_df.loc[x.index][game_df.loc[x.index, "season_type"] == "Regular season"]["gameId"].nunique()),
            playoff_games=("gameId", lambda x: game_df.loc[x.index][game_df.loc[x.index, "season_type"] == "Playoffs"]["gameId"].nunique())
        )
        .reset_index()
    )

    latest_season = int(game_df["season"].max())
    earliest_season = int(game_df["season"].min())

    availability["is_historical_or_partial"] = (
        (availability["last_season"].astype(int) < latest_season) |
        (availability["first_season"].astype(int) > earliest_season)
    )

    return availability


team_availability = build_team_availability_table(game_df)
availability_lookup = team_availability.set_index(TEAM_COL).to_dict("index")


def team_available_range_text(team_code):
    info = availability_lookup.get(str(team_code))

    if not info:
        return "No availability info"

    first = int(info["first_season"])
    last = int(info["last_season"])

    if first == last:
        return season_label(first)

    return f"{season_label(first)}–{season_label(last)}"


def is_historical_or_partial_team(team_code):
    info = availability_lookup.get(str(team_code))
    if not info:
        return False
    return bool(info["is_historical_or_partial"])


def format_team_selector_option(team_code):
    base = f"{team_full_name(team_code)} ({team_code})"

    if is_historical_or_partial_team(team_code):
        return f"{base} — data: {team_available_range_text(team_code)}"

    return base


def show_team_availability_note(team_code, selected_season):
    info = availability_lookup.get(str(team_code))

    if not info:
        return

    first = int(info["first_season"])
    last = int(info["last_season"])
    regular_games = int(info["regular_games"])
    playoff_games = int(info["playoff_games"])

    if is_historical_or_partial_team(team_code):
        st.sidebar.info(
            f"{team_full_name(team_code)} ({team_code}) is available in this dataset from "
            f"{season_label(first)} to {season_label(last)}. "
            f"Regular-season games: {regular_games}. Playoff games: {playoff_games}."
        )

    if int(selected_season) < first or int(selected_season) > last:
        st.warning(
            f"{team_full_name(team_code)} ({team_code}) has no data for {season_label(selected_season)} "
            f"in this dataset. Available seasons: {team_available_range_text(team_code)}."
        )




# ============================================================
# PLAYER STATS HELPERS
# ============================================================

# ============================================================
# PLAYOFF RESULT SEQUENCE HELPER
# ============================================================


def render_playoff_result_sequence(playoff_team_games):
    """
    Render a compact visual sequence of playoff game results.
    This replaces the old bar chart + plain W/L text.
    """
    if playoff_team_games.empty:
        return

    items = []

    for _, row in playoff_team_games.iterrows():
        result = str(row.get("game_result", ""))
        label = html.escape(str(row.get("series_game_label", "")))
        opponent = html.escape(str(row.get(OPP_COL, "")))

        if result == "W":
            bg = "rgba(34,197,94,0.14)"
            border = "#16a34a"
            text = "#166534"
        elif result in ["OTW", "SOW"]:
            bg = "rgba(59,130,246,0.13)"
            border = "#2563eb"
            text = "#1d4ed8"
        elif result in ["OTL", "SOL"]:
            bg = "rgba(245,158,11,0.15)"
            border = "#d97706"
            text = "#b45309"
        else:
            bg = "rgba(239,68,68,0.13)"
            border = "#dc2626"
            text = "#b91c1c"

        items.append(
            f'<div style="min-width:86px;border:2px solid {border};background:{bg};'
            f'border-radius:14px;padding:10px 8px;text-align:center;'
            f'box-shadow:0 4px 12px rgba(15,23,42,0.05);">'
            f'<div style="font-size:11px;color:#64748b;font-weight:800;">{label}</div>'
            f'<div style="font-size:22px;font-weight:950;color:{text};line-height:1.0;margin:4px 0 3px 0;">'
            f'{html.escape(result)}</div>'
            f'<div style="font-size:11px;color:#475569;font-weight:700;">vs {opponent}</div>'
            f'</div>'
        )

    html_block = (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:stretch;'
        'margin:6px 0 12px 0;">'
        + ''.join(items) +
        '</div>'
    )

    st.markdown("#### Playoff game sequence")
    st.markdown(html_block, unsafe_allow_html=True)

    st.caption(
        "Green = win, blue = overtime/shootout win, orange = overtime/shootout loss, red = regulation loss."
    )




def player_headshot_html(url, size=58):
    if pd.isna(url) or str(url).strip() == "":
        return (
            f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
            f'background:rgba(148,163,184,0.25);display:flex;align-items:center;'
            f'justify-content:center;font-weight:900;color:#64748b;">?</div>'
        )

    safe_url = html.escape(str(url))

    return (
        f'<img src="{safe_url}" width="{size}" height="{size}" '
        f'style="border-radius:50%;object-fit:cover;background:#e5e7eb;" />'
    )


def build_top_skaters_for_selection(player_stats, team_code, season, season_type, n=3, sort_by="points"):
    if player_stats.empty:
        return pd.DataFrame()

    needed_cols = {"team", "season", "season_type", "player_type", "player"}
    if not needed_cols.issubset(set(player_stats.columns)):
        return pd.DataFrame()

    df = player_stats[
        (player_stats["team"].astype(str) == str(team_code)) &
        (player_stats["season"].astype(int) == int(season)) &
        (player_stats["season_type"].astype(str) == str(season_type)) &
        (player_stats["player_type"].astype(str) == "skater")
    ].copy()

    if df.empty:
        return pd.DataFrame()

    for col in ["points", "goals", "assists", "games_played", "shots", "plus_minus"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if sort_by == "goals":
        sort_cols = ["goals", "points", "assists", "games_played", "player"]
        ascending = [False, False, False, True, True]
    elif sort_by == "assists":
        sort_cols = ["assists", "points", "goals", "games_played", "player"]
        ascending = [False, False, False, True, True]
    elif sort_by == "shots":
        sort_cols = ["shots", "points", "goals", "games_played", "player"]
        ascending = [False, False, False, True, True]
    else:
        sort_cols = ["points", "goals", "assists", "games_played", "player"]
        ascending = [False, False, False, True, True]

    df = df.sort_values(sort_cols, ascending=ascending).head(n).copy()
    df["Rank"] = range(1, len(df) + 1)

    return df



def build_league_skaters_for_selection(player_stats, season, season_type, n=50, sort_by="points"):
    """
    League-wide skater leaderboard for one season and season type.
    """
    if player_stats.empty:
        return pd.DataFrame()

    needed_cols = {"team", "season", "season_type", "player_type", "player"}
    if not needed_cols.issubset(set(player_stats.columns)):
        return pd.DataFrame()

    df = player_stats[
        (player_stats["season"].astype(int) == int(season)) &
        (player_stats["season_type"].astype(str) == str(season_type)) &
        (player_stats["player_type"].astype(str) == "skater")
    ].copy()

    if df.empty:
        return pd.DataFrame()

    for col in [
        "points", "goals", "assists", "games_played", "shots", "plus_minus",
        "power_play_goals", "power_play_points", "short_handed_goals",
        "short_handed_points", "game_winning_goals"
    ]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if sort_by == "goals":
        sort_cols = ["goals", "points", "assists", "games_played", "player"]
        ascending = [False, False, False, True, True]
    elif sort_by == "assists":
        sort_cols = ["assists", "points", "goals", "games_played", "player"]
        ascending = [False, False, False, True, True]
    elif sort_by == "shots":
        sort_cols = ["shots", "points", "goals", "games_played", "player"]
        ascending = [False, False, False, True, True]
    elif sort_by == "plus_minus":
        sort_cols = ["plus_minus", "points", "goals", "player"]
        ascending = [False, False, False, True]
    else:
        sort_cols = ["points", "goals", "assists", "games_played", "player"]
        ascending = [False, False, False, True, True]

    df = df.sort_values(sort_cols, ascending=ascending).head(n).copy()
    df["Rank"] = range(1, len(df) + 1)

    return df


def build_league_goalies_for_selection(player_stats, season, season_type, n=30, min_games=10):
    """
    League-wide goalie leaderboard for one season and season type.
    """
    if player_stats.empty:
        return pd.DataFrame()

    needed_cols = {"team", "season", "season_type", "player_type", "player"}
    if not needed_cols.issubset(set(player_stats.columns)):
        return pd.DataFrame()

    df = player_stats[
        (player_stats["season"].astype(int) == int(season)) &
        (player_stats["season_type"].astype(str) == str(season_type)) &
        (player_stats["player_type"].astype(str) == "goalie")
    ].copy()

    if df.empty:
        return pd.DataFrame()

    for col in ["games_played", "wins", "losses", "ot_losses", "save_pct", "goals_against_average", "shutouts"]:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["games_played"].fillna(0) >= int(min_games)].copy()

    if df.empty:
        return pd.DataFrame()

    df = df.sort_values(
        ["save_pct", "wins", "games_played", "player"],
        ascending=[False, False, False, True]
    ).head(n).copy()

    df["Rank"] = range(1, len(df) + 1)

    return df


def prepare_skaters_display_table(df):
    if df.empty:
        return df

    show_cols = [
        "Rank", "player", "team", "position", "games_played", "goals",
        "assists", "points", "shots", "plus_minus",
        "power_play_goals", "power_play_points",
        "short_handed_goals", "short_handed_points",
        "game_winning_goals"
    ]

    display = df[[c for c in show_cols if c in df.columns]].copy()

    display = display.rename(columns={
        "player": "Player",
        "team": "Team",
        "position": "Pos",
        "games_played": "GP",
        "goals": "G",
        "assists": "A",
        "points": "P",
        "shots": "S",
        "plus_minus": "+/-",
        "power_play_goals": "PPG",
        "power_play_points": "PPP",
        "short_handed_goals": "SHG",
        "short_handed_points": "SHP",
        "game_winning_goals": "GWG"
    })

    return display


def prepare_goalies_display_table(df):
    if df.empty:
        return df

    keep = [
        "Rank", "player", "team", "games_played", "wins", "losses", "ot_losses",
        "save_pct", "goals_against_average", "shutouts"
    ]

    display = df[[c for c in keep if c in df.columns]].copy()

    display = display.rename(columns={
        "player": "Player",
        "team": "Team",
        "games_played": "GP",
        "wins": "W",
        "losses": "L",
        "ot_losses": "OT",
        "save_pct": "SV%",
        "goals_against_average": "GAA",
        "shutouts": "SO"
    })

    for col in ["SV%", "GAA"]:
        if col in display.columns:
            display[col] = pd.to_numeric(display[col], errors="coerce").round(3)

    return display



def build_top_goalies_for_selection(player_stats, team_code, season, season_type, n=3):
    if player_stats.empty:
        return pd.DataFrame()

    needed_cols = {"team", "season", "season_type", "player_type", "player"}
    if not needed_cols.issubset(set(player_stats.columns)):
        return pd.DataFrame()

    df = player_stats[
        (player_stats["team"].astype(str) == str(team_code)) &
        (player_stats["season"].astype(int) == int(season)) &
        (player_stats["season_type"].astype(str) == str(season_type)) &
        (player_stats["player_type"].astype(str) == "goalie")
    ].copy()

    if df.empty:
        return pd.DataFrame()

    for col in ["games_played", "wins", "losses", "ot_losses", "save_pct", "goals_against_average", "shutouts"]:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(
        ["games_played", "wins", "save_pct", "player"],
        ascending=[False, False, False, True]
    ).head(n).copy()

    df["Rank"] = range(1, len(df) + 1)

    return df


def render_top_player_cards(players_df, title, subtitle=None):
    st.markdown(f"#### {title}")

    if subtitle:
        st.caption(subtitle)

    if players_df.empty:
        st.info("No player data available for this selection.")
        return

    cols = st.columns(len(players_df))

    for col, (_, row) in zip(cols, players_df.iterrows()):
        with col:
            headshot = player_headshot_html(row.get("headshot", ""), size=64)
            player = html.escape(str(row.get("player", "Unknown player")))
            position = html.escape(str(row.get("position", "")))
            gp = int(row.get("games_played", 0)) if pd.notna(row.get("games_played", np.nan)) else 0
            goals = int(row.get("goals", 0)) if pd.notna(row.get("goals", np.nan)) else 0
            assists = int(row.get("assists", 0)) if pd.notna(row.get("assists", np.nan)) else 0
            points = int(row.get("points", 0)) if pd.notna(row.get("points", np.nan)) else 0
            rank = int(row.get("Rank", 0))

            st.markdown(
                f"""
                <div style="
                    border:1px solid rgba(148,163,184,0.35);
                    border-radius:18px;
                    padding:14px 16px;
                    background:rgba(248,250,252,0.92);
                    min-height:188px;
                    box-shadow:0 8px 20px rgba(15,23,42,0.06);
                ">
                    <div style="display:flex;align-items:center;gap:12px;">
                        {headshot}
                        <div>
                            <div style="font-size:12px;font-weight:900;color:#64748b;">#{rank} {position}</div>
                            <div style="font-size:17px;font-weight:950;color:#0f172a;line-height:1.1;">{player}</div>
                        </div>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:16px;text-align:center;">
                        <div><div style="font-size:11px;color:#64748b;font-weight:800;">GP</div><div style="font-size:20px;font-weight:950;">{gp}</div></div>
                        <div><div style="font-size:11px;color:#64748b;font-weight:800;">G</div><div style="font-size:20px;font-weight:950;">{goals}</div></div>
                        <div><div style="font-size:11px;color:#64748b;font-weight:800;">A</div><div style="font-size:20px;font-weight:950;">{assists}</div></div>
                        <div><div style="font-size:11px;color:#64748b;font-weight:800;">P</div><div style="font-size:20px;font-weight:950;">{points}</div></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_goalie_table(goalies_df):
    st.markdown("#### Goalies")

    if goalies_df.empty:
        st.info("No goalie data available for this selection.")
        return

    display = goalies_df.copy()

    keep = [
        "Rank", "player", "games_played", "wins", "losses", "ot_losses",
        "save_pct", "goals_against_average", "shutouts"
    ]

    display = display[[c for c in keep if c in display.columns]].copy()

    display = display.rename(columns={
        "player": "Player",
        "games_played": "GP",
        "wins": "W",
        "losses": "L",
        "ot_losses": "OT",
        "save_pct": "SV%",
        "goals_against_average": "GAA",
        "shutouts": "SO"
    })

    for col in ["SV%", "GAA"]:
        if col in display.columns:
            display[col] = pd.to_numeric(display[col], errors="coerce").round(3)

    st.dataframe(display, use_container_width=True, hide_index=True)




# ============================================================
# SEASON OVERVIEW HELPERS
# ============================================================

def build_team_ranking_table_for_overview(league_games):
    """
    Build one row per team for league/season overview.
    Works with full-game or situation-filtered data.
    """
    if league_games.empty:
        return pd.DataFrame()

    ranking = (
        league_games
        .groupby(TEAM_COL)
        .agg(
            games=("gameId", "nunique"),
            total_points=("points", "sum"),
            W=("record_w", "sum"),
            L=("record_l", "sum"),
            OT=("record_ot", "sum"),
            RW=("regulation_win", "sum"),
            OTW=("ot_win", "sum"),
            SOW=("so_win", "sum"),
            ROW=("regulation_win", "sum"),
            goal_diff_total=("game_goal_diff", "sum"),
            goals_for_total=("game_goals_for", "sum"),
            goals_against_total=("game_goals_against", "sum"),
            shots_for_total=("shotsOnGoalFor", "sum"),
            shots_against_total=("shotsOnGoalAgainst", "sum"),
            shot_attempts_for_total=("shotAttemptsFor", "sum"),
            giveaways_total=("giveawaysFor", "sum"),
            faceoffs_won=("faceOffsWonFor", "sum"),
            faceoffs_total=("total_faceoffs", "sum")
        )
        .reset_index()
    )

    ranking["ROW"] = ranking["RW"] + ranking["OTW"]
    ranking["GD"] = ranking["goal_diff_total"]
    ranking["GF"] = ranking["goals_for_total"]

    ranking["record"] = (
        ranking["W"].fillna(0).astype(int).astype(str)
        + "-"
        + ranking["L"].fillna(0).astype(int).astype(str)
        + "-"
        + ranking["OT"].fillna(0).astype(int).astype(str)
    )

    ranking["points_per_game"] = ranking["total_points"] / ranking["games"]
    ranking["goal_diff_per_game"] = ranking["goal_diff_total"] / ranking["games"]
    ranking["goals_for_per_game"] = ranking["goals_for_total"] / ranking["games"]
    ranking["goals_against_per_game"] = ranking["goals_against_total"] / ranking["games"]
    ranking["shots_for_per_game"] = ranking["shots_for_total"] / ranking["games"]
    ranking["shots_against_per_game"] = ranking["shots_against_total"] / ranking["games"]
    ranking["shot_attempts_for_per_game"] = ranking["shot_attempts_for_total"] / ranking["games"]
    ranking["giveaways_per_game"] = ranking["giveaways_total"] / ranking["games"]
    ranking["faceoff_pct"] = ranking["faceoffs_won"] / ranking["faceoffs_total"] * 100

    ranking = add_official_like_standings_order(ranking)

    return ranking


def render_season_hero(season, season_type, view_mode, situation):
    situation_text = "Full game" if view_mode == "Full game" else str(situation)

    st.markdown(
        f"""
        <div style="
            border-radius:24px;
            padding:30px 34px;
            margin:6px 0 18px 0;
            background:linear-gradient(135deg,#061426 0%,#111827 52%,#7f1d1d 100%);
            color:white;
            box-shadow:0 14px 34px rgba(15,23,42,0.18);
        ">
            <div style="font-size:13px;font-weight:900;letter-spacing:2px;color:#bfdbfe;text-transform:uppercase;">
                NHL Season Overview
            </div>
            <div style="font-size:42px;font-weight:950;line-height:1.05;margin-top:8px;">
                {season_label(season)} {html.escape(str(season_type))}
            </div>
            <div style="font-size:16px;margin-top:10px;color:#d1d5db;">
                League table, player leaders, playoff bracket, scatter plots and season-level comparisons.
            </div>
            <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:18px;">
                <span style="background:rgba(255,255,255,0.12);padding:8px 12px;border-radius:999px;font-weight:800;">Scope: whole season</span>
                <span style="background:rgba(255,255,255,0.12);padding:8px 12px;border-radius:999px;font-weight:800;">View: {html.escape(situation_text)}</span>
                <span style="background:rgba(255,255,255,0.12);padding:8px 12px;border-radius:999px;font-weight:800;">Interactive filters</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_season_overview_dashboard(
    league_df,
    game_df,
    player_stats_df,
    season,
    season_type,
    view_mode,
    situation
):
    """
    Whole-season landing/dashboard mode.
    This intentionally ignores the selected team and focuses on league-wide outputs.
    """
    render_season_hero(season, season_type, view_mode, situation)

    st.markdown("#### Current season filters")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Season", season_label(season))
    f2.metric("Season type", season_type)
    f3.metric("Game view", "Full game" if view_mode == "Full game" else str(situation))
    f4.metric("Scope", "Whole league")

    st.caption(
        "Use the sidebar filters to switch between full-game and situation-specific views, "
        "regular season and playoffs, or back to a single-team dashboard."
    )

    if league_df.empty:
        st.warning("No league data available for this season/filter.")
        return

    ranking = build_team_ranking_table_for_overview(league_df)
    playoff_teams_for_season = set(
        game_df[
            (game_df["season"] == season) &
            (game_df["season_type"] == "Playoffs")
        ][TEAM_COL].dropna().astype(str).unique()
    )

    if ranking.empty:
        st.warning("Could not build league ranking table for this selection.")
        return

    unique_team_games = league_df.drop_duplicates(["gameId", TEAM_COL]).copy()
    unique_games = league_df.drop_duplicates("gameId").copy()

    total_games = int(unique_games["gameId"].nunique())
    total_teams = int(ranking[TEAM_COL].nunique())
    total_goals = int(unique_team_games["game_goals_for"].sum())
    avg_goals_per_game = total_goals / total_games if total_games else np.nan

    best_team = ranking.sort_values("rank").iloc[0]
    best_offense = ranking.sort_values("goals_for_per_game", ascending=False).iloc[0]
    best_defense = ranking.sort_values("goals_against_per_game", ascending=True).iloc[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Teams", total_teams)
    m2.metric("Games", total_games)
    m3.metric("Goals", total_goals)
    m4.metric("Goals/game", format_number(avg_goals_per_game, 2))

    h1, h2, h3 = st.columns(3)
    h1.metric("Best team", f"{best_team[TEAM_COL]} — {int(best_team['total_points'])} pts")
    h2.metric("Best offense", f"{best_offense[TEAM_COL]} — {format_number(best_offense['goals_for_per_game'], 2)} GF/GP")
    h3.metric("Best defense", f"{best_defense[TEAM_COL]} — {format_number(best_defense['goals_against_per_game'], 2)} GA/GP")

    tab_overview, tab_table, tab_players, tab_playoffs, tab_scatter = st.tabs([
        "Title page",
        "League table",
        "Player leaders",
        "Playoffs",
        "Scatter plots"
    ])

    with tab_overview:
        st.markdown("#### What this season page contains")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(
                """
                **Team tables**

                League standings with logos, conferences, divisions, playoff status, points, records, goals, shots and faceoff stats.
                """
            )

        with c2:
            st.markdown(
                """
                **Player leaders**

                League-wide skater and goalie leaderboards for the selected season and season type.
                """
            )

        with c3:
            st.markdown(
                """
                **Playoffs and plots**

                Playoff bracket, playoff series table and logo-based scatter plots for comparing team profiles.
                """
            )

        st.markdown("#### Quick season story")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("##### Top 5 teams")
            top5 = ranking.sort_values("rank").head(5).copy()
            top5_display = pd.DataFrame({
                "Rank": top5["rank"].astype(int),
                "Logo": top5[TEAM_COL].apply(lambda x: logo_data_uri(str(x)) or ""),
                "Team": top5[TEAM_COL].astype(str),
                "Team name": top5[TEAM_COL].apply(team_full_name),
                "Record": top5["record"],
                "PTS": top5["total_points"].round(0).astype(int),
                "GD": top5["goal_diff_total"].round(0).astype(int)
            })
            st.dataframe(
                top5_display,
                use_container_width=True,
                hide_index=True,
                row_height=46,
                column_config={
                    "Logo": st.column_config.ImageColumn("Logo", width="small"),
                    "Team name": st.column_config.TextColumn("Team name", width="medium"),
                }
            )

        with col_b:
            st.markdown("##### Playoff teams")
            if playoff_teams_for_season:
                playoff_display_raw = ranking[ranking[TEAM_COL].astype(str).isin(playoff_teams_for_season)].copy()
                playoff_display_raw = playoff_display_raw.sort_values("rank")
                playoff_display = pd.DataFrame({
                    "League rank": playoff_display_raw["rank"].astype(int),
                    "Logo": playoff_display_raw[TEAM_COL].apply(lambda x: logo_data_uri(str(x)) or ""),
                    "Team": playoff_display_raw[TEAM_COL].astype(str),
                    "Record": playoff_display_raw["record"],
                    "PTS": playoff_display_raw["total_points"].round(0).astype(int),
                    "GD": playoff_display_raw["goal_diff_total"].round(0).astype(int)
                })
                st.dataframe(
                    playoff_display,
                    use_container_width=True,
                    hide_index=True,
                    row_height=46,
                    column_config={
                        "Logo": st.column_config.ImageColumn("Logo", width="small"),
                    }
                )
            else:
                st.info("No playoff-team data found for this season.")

    with tab_table:
        st.markdown("#### League table")
        st.caption("This table uses the same logo/table style as the team dashboard and can be sorted by clicking column headers.")
        show_sortable_league_table(
            ranking=ranking,
            selected_team="",
            season_type=season_type,
            view_mode=view_mode,
            playoff_teams=playoff_teams_for_season
        )

    with tab_players:
        st.markdown("#### Player leaders")

        if player_stats_df.empty:
            st.info("Player stats file not found. Place all_team_player_stats.csv next to the app.")
        else:
            pc1, pc2 = st.columns([1.2, 0.8])
            skater_sort = pc1.selectbox(
                "Skater leaderboard",
                ["points", "goals", "assists", "shots", "plus_minus"],
                index=0,
                key=f"season_overview_skater_sort_{season}_{season_type}"
            )
            skater_rows = pc2.selectbox(
                "Rows",
                [10, 25, 50, 100],
                index=1,
                key=f"season_overview_skater_rows_{season}_{season_type}"
            )

            league_skaters = build_league_skaters_for_selection(
                player_stats=player_stats_df,
                season=season,
                season_type=season_type,
                n=int(skater_rows),
                sort_by=skater_sort
            )

            if league_skaters.empty:
                st.info("No skater leaderboard available for this filter.")
            else:
                player_display = pd.DataFrame({
                    "Rank": league_skaters["Rank"].astype(int),
                    "Headshot": league_skaters["headshot"] if "headshot" in league_skaters.columns else "",
                    "Player": league_skaters["player"].astype(str),
                    "Logo": league_skaters["team"].apply(lambda x: logo_data_uri(str(x)) or ""),
                    "Team": league_skaters["team"].astype(str),
                    "Pos": league_skaters["position"].astype(str),
                    "GP": league_skaters["games_played"].fillna(0).astype(int),
                    "G": league_skaters["goals"].fillna(0).astype(int),
                    "A": league_skaters["assists"].fillna(0).astype(int),
                    "P": league_skaters["points"].fillna(0).astype(int),
                    "S": league_skaters["shots"].fillna(0).astype(int) if "shots" in league_skaters.columns else 0,
                    "+/-": league_skaters["plus_minus"].fillna(0).astype(int) if "plus_minus" in league_skaters.columns else 0,
                })

                st.dataframe(
                    player_display,
                    use_container_width=True,
                    hide_index=True,
                    row_height=52,
                    column_config={
                        "Headshot": st.column_config.ImageColumn("Headshot", width="small"),
                        "Logo": st.column_config.ImageColumn("Logo", width="small"),
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                    }
                )

            goalie_min_games = st.slider(
                "Minimum goalie games played",
                min_value=1,
                max_value=40,
                value=10 if season_type == "Regular season" else 1,
                key=f"season_overview_goalie_min_{season}_{season_type}"
            )

            with st.expander("Goalie leaderboard", expanded=False):
                league_goalies = build_league_goalies_for_selection(
                    player_stats=player_stats_df,
                    season=season,
                    season_type=season_type,
                    n=50,
                    min_games=goalie_min_games
                )

                if league_goalies.empty:
                    st.info("No goalie leaderboard available for this filter.")
                else:
                    goalie_display = pd.DataFrame({
                        "Rank": league_goalies["Rank"].astype(int),
                        "Headshot": league_goalies["headshot"] if "headshot" in league_goalies.columns else "",
                        "Player": league_goalies["player"].astype(str),
                        "Logo": league_goalies["team"].apply(lambda x: logo_data_uri(str(x)) or ""),
                        "Team": league_goalies["team"].astype(str),
                        "GP": league_goalies["games_played"].fillna(0).astype(int),
                        "W": league_goalies["wins"].fillna(0).astype(int) if "wins" in league_goalies.columns else 0,
                        "SV%": pd.to_numeric(league_goalies["save_pct"], errors="coerce").round(3) if "save_pct" in league_goalies.columns else np.nan,
                        "GAA": pd.to_numeric(league_goalies["goals_against_average"], errors="coerce").round(3) if "goals_against_average" in league_goalies.columns else np.nan,
                        "SO": league_goalies["shutouts"].fillna(0).astype(int) if "shutouts" in league_goalies.columns else 0,
                    })

                    st.dataframe(
                        goalie_display,
                        use_container_width=True,
                        hide_index=True,
                        row_height=52,
                        column_config={
                            "Headshot": st.column_config.ImageColumn("Headshot", width="small"),
                            "Logo": st.column_config.ImageColumn("Logo", width="small"),
                            "Player": st.column_config.TextColumn("Player", width="medium"),
                        }
                    )

    with tab_playoffs:
        st.markdown("#### Playoff bracket")

        playoff_league_games = (
            game_df[
                (game_df["season"] == season) &
                (game_df["season_type"] == "Playoffs")
            ]
            .drop_duplicates(["gameId", TEAM_COL])
            .copy()
        )

        if playoff_league_games.empty:
            st.info("No playoff data available for this season.")
        else:
            full_series_summary = build_league_playoff_series_summary(playoff_league_games)

            if full_series_summary.empty:
                st.info("No playoff bracket could be built from the available data.")
            else:
                bracket_html = render_playoff_bracket(full_series_summary, "", season)
                components.html(bracket_html, height=850, scrolling=False)

                with st.expander("Show playoff series table"):
                    st.dataframe(full_series_summary, use_container_width=True, hide_index=True)

    with tab_scatter:
        st.markdown("#### Logo scatter plots")

        scatter_options = {
            "Total points": "total_points",
            "Points per game": "points_per_game",
            "Goal differential per game": "goal_diff_per_game",
            "Goals for per game": "goals_for_per_game",
            "Goals against per game": "goals_against_per_game",
            "Shots for per game": "shots_for_per_game",
            "Shots against per game": "shots_against_per_game",
            "Shot attempts for per game": "shot_attempts_for_per_game",
            "Faceoff %": "faceoff_pct",
            "Giveaways per game": "giveaways_per_game"
        }

        sx, sy = st.columns(2)
        x_name = sx.selectbox(
            "X-axis",
            list(scatter_options.keys()),
            index=8,
            key=f"season_scatter_x_{season}_{season_type}_{view_mode}_{situation}"
        )
        y_name = sy.selectbox(
            "Y-axis",
            list(scatter_options.keys()),
            index=1,
            key=f"season_scatter_y_{season}_{season_type}_{view_mode}_{situation}"
        )

        x_stat = scatter_options[x_name]
        y_stat = scatter_options[y_name]

        scatter_df = ranking.dropna(subset=[x_stat, y_stat]).copy()

        if scatter_df.empty:
            st.info("No scatter data available.")
        else:
            fig = px.scatter(
                scatter_df,
                x=x_stat,
                y=y_stat,
                hover_name=TEAM_COL,
                hover_data=["record", "games", "total_points"],
                title=f"{x_name} vs {y_name} — {season_label(season)} {season_type}",
                labels={x_stat: x_name, y_stat: y_name}
            )

            fig.update_traces(marker=dict(size=2, opacity=0.05), showlegend=False)

            x_min = float(scatter_df[x_stat].min())
            x_max = float(scatter_df[x_stat].max())
            y_min = float(scatter_df[y_stat].min())
            y_max = float(scatter_df[y_stat].max())

            x_span = max(x_max - x_min, 1e-6)
            y_span = max(y_max - y_min, 1e-6)

            fig.update_xaxes(range=[x_min - 0.08 * x_span, x_max + 0.08 * x_span])
            fig.update_yaxes(range=[y_min - 0.12 * y_span, y_max + 0.12 * y_span])

            logo_size_x = 0.04 * x_span
            logo_size_y = 0.08 * y_span

            for _, row in scatter_df.iterrows():
                team_code = str(row[TEAM_COL])
                uri = logo_data_uri(team_code)

                if not uri:
                    continue

                fig.add_layout_image(
                    dict(
                        source=uri,
                        x=float(row[x_stat]),
                        y=float(row[y_stat]),
                        xref="x",
                        yref="y",
                        sizex=logo_size_x,
                        sizey=logo_size_y,
                        xanchor="center",
                        yanchor="middle",
                        layer="above",
                        opacity=1.0
                    )
                )

            st.plotly_chart(fig, use_container_width=True)

            st.caption("This chart uses team logos as markers. Teams with missing local logo files may not show an image.")




# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("Filters")

teams = sorted(game_df[TEAM_COL].dropna().unique())
seasons = sorted(game_df["season"].dropna().unique(), reverse=True)
season_types = sorted(game_df["season_type"].dropna().unique())

dashboard_scope = st.sidebar.radio(
    "Dashboard scope",
    ["Season overview", "Team dashboard"],
    index=0,
    help="Season overview shows the whole league season. Team dashboard focuses on one selected team."
)

season = st.sidebar.selectbox(
    "Season",
    seasons,
    format_func=season_label
)

season_type = st.sidebar.selectbox("Season type", season_types)

view_mode = st.sidebar.radio(
    "Statistics view",
    ["Full game", "By game situation"]
)

if view_mode == "By game situation":
    situations = sorted(situation_df["situation"].dropna().unique())
    situation = st.sidebar.selectbox("Situation", situations)
else:
    situation = "Full game"

if dashboard_scope == "Team dashboard":
    team = st.sidebar.selectbox(
        "Team",
        teams,
        format_func=format_team_selector_option
    )
    show_team_availability_note(team, season)
else:
    # Season overview intentionally ignores the team filter, but team must still be defined
    # because some team-only code exists below. The app stops before reaching that code.
    team = teams[0] if teams else ""
    st.sidebar.info(
        "Season overview ignores the team filter and shows league-wide tables, players, playoffs and scatter plots."
    )


# ============================================================
# SELECT DATASET
# ============================================================

if view_mode == "Full game":
    df = game_df.copy()

    team_df = df[
        (df[TEAM_COL] == team) &
        (df["season"] == season) &
        (df["season_type"] == season_type)
    ].copy()

    league_df = df[
        (df["season"] == season) &
        (df["season_type"] == season_type)
    ].copy()

else:
    df = situation_df.copy()

    team_df = df[
        (df[TEAM_COL] == team) &
        (df["season"] == season) &
        (df["season_type"] == season_type) &
        (df["situation"] == situation)
    ].copy()

    league_df = df[
        (df["season"] == season) &
        (df["season_type"] == season_type) &
        (df["situation"] == situation)
    ].copy()


# ============================================================
# SEASON OVERVIEW MODE
# ============================================================

if dashboard_scope == "Season overview":
    render_season_overview_dashboard(
        league_df=league_df,
        game_df=game_df,
        player_stats_df=player_stats_df,
        season=season,
        season_type=season_type,
        view_mode=view_mode,
        situation=situation
    )
    st.stop()


if team_df.empty:
    if season_type == "Playoffs":
        logo_path = find_logo_path(team)
        full_team_name = team_full_name(team)

        col_logo, col_title = st.columns([1, 5])

        with col_logo:
            if logo_path is not None:
                st.image(logo_path, width=130)
            else:
                st.write(team)

        with col_title:
            st.header(f"{full_team_name} ({team})")
            st.subheader(f"{season_label(season)} | Playoffs")
            st.warning(f"{full_team_name} ({team}) did not make the {season_label(season)} playoffs.")

        playoff_league_games = (
            game_df[
                (game_df["season"] == season) &
                (game_df["season_type"] == "Playoffs")
            ]
            .drop_duplicates(["gameId", TEAM_COL])
            .copy()
        )

        if playoff_league_games.empty:
            st.info(f"No playoff data available for the {season_label(season)} season.")
        else:
            full_series_summary = build_league_playoff_series_summary(playoff_league_games)

            if full_series_summary.empty:
                st.info("No playoff bracket could be built from the available data.")
            else:
                st.markdown("### Playoff Bracket")
                bracket_html = render_playoff_bracket(full_series_summary, team, season)
                components.html(bracket_html, height=850, scrolling=False)

                with st.expander("Show full playoff series table"):
                    st.dataframe(full_series_summary, use_container_width=True)

        st.stop()

    availability_text = team_available_range_text(team)
    st.warning(
        f"No data available for this selection. "
        f"{team_full_name(team)} ({team}) is available in this dataset for: {availability_text}."
    )
    st.stop()


# ============================================================
# HEADER
# ============================================================

logo_path = find_logo_path(team)
full_team_name = team_full_name(team)

col_logo, col_title = st.columns([1, 5])

with col_logo:
    if logo_path is not None:
        st.image(logo_path, width=130)
    else:
        st.write(team)

with col_title:
    st.header(f"{full_team_name} ({team})")
    st.subheader(f"{season_label(season)} | {season_type} | {situation}")

note = season_note(season)

if note:
    st.info(note)

if is_historical_or_partial_team(team):
    with st.expander("Team data availability note", expanded=False):
        info = availability_lookup.get(str(team))
        if info:
            st.write(
                f"**{team_full_name(team)} ({team})** appears in this dataset from "
                f"**{season_label(int(info['first_season']))}** to "
                f"**{season_label(int(info['last_season']))}**."
            )
            st.write(
                "Use the season selector to choose a season inside that range. "
                "Outside that range, the app will show that no data is available for this team code."
            )


# ============================================================
# ONE ROW PER GAME
# ============================================================

team_games = (
    team_df
    .drop_duplicates(["gameId", TEAM_COL])
    .sort_values(["gameDate", "gameId"])
    .copy()
)

league_games = (
    league_df
    .drop_duplicates(["gameId", TEAM_COL])
    .copy()
)

games = team_games["gameId"].nunique()

if games == 0:
    st.warning("No games available for this selection.")
    st.stop()


# ============================================================
# TEAM OVERVIEW CALCULATIONS
# ============================================================

record_w = int(team_games["record_w"].sum())
record_l = int(team_games["record_l"].sum())
record_ot = int(team_games["record_ot"].sum())

points_total = int(team_games["points"].sum())

record_text = f"{record_w}-{record_l}-{record_ot}"

regulation_wins = int(team_games["regulation_win"].sum())
ot_wins = int(team_games["ot_win"].sum())
so_wins = int(team_games["so_win"].sum())

regulation_losses = int(team_games["regulation_loss"].sum())
ot_losses = int(team_games["ot_loss"].sum())
so_losses = int(team_games["so_loss"].sum())

detailed_record_text = (
    f"REG W: {regulation_wins}, "
    f"OTW: {ot_wins}, "
    f"SOW: {so_wins}, "
    f"REG L: {regulation_losses}, "
    f"OTL: {ot_losses}, "
    f"SOL: {so_losses}"
)

team_total_faceoffs = team_games["total_faceoffs"].sum()
team_faceoff_pct = (
    team_games["faceOffsWonFor"].sum() / team_total_faceoffs * 100
    if team_total_faceoffs > 0 else np.nan
)


# ============================================================
# TEAM PROFILE CARD
# ============================================================

profile_league = (
    league_games
    .groupby(TEAM_COL)
    .agg(
        games=("gameId", "nunique"),
        total_points=("points", "sum"),
        W=("record_w", "sum"),
        L=("record_l", "sum"),
        OT=("record_ot", "sum"),
        RW=("regulation_win", "sum"),
        OTW=("ot_win", "sum"),
        goal_diff_total=("game_goal_diff", "sum"),
        goals_for_total=("game_goals_for", "sum")
    )
    .reset_index()
)

if not profile_league.empty and team in profile_league[TEAM_COL].values:
    profile_league["ROW"] = profile_league["RW"] + profile_league["OTW"]
    profile_league["GD"] = profile_league["goal_diff_total"]
    profile_league["GF"] = profile_league["goals_for_total"]
    profile_league = add_official_like_standings_order(profile_league)

    profile_row = profile_league.loc[profile_league[TEAM_COL] == team].iloc[0]
    profile_rank = int(profile_row["rank"])
    profile_team_count = int(profile_league[TEAM_COL].nunique())

    playoff_teams_profile = set(
        game_df[
            (game_df["season"] == season) &
            (game_df["season_type"] == "Playoffs")
        ][TEAM_COL].dropna().astype(str).unique()
    )

    playoff_status = "Qualified" if team in playoff_teams_profile else "Did not qualify"
    profile_conference = team_conference(team)
    profile_division = team_division(team)

    st.markdown("### Team Profile")

    prof1, prof2, prof3, prof4, prof5 = st.columns(5)

    prof1.metric(
        "League rank",
        f"{profile_rank} / {profile_team_count}",
        help="Overall rank using NHL-style available tiebreakers."
    )
    prof2.metric(
        "Record",
        record_text,
        help=metric_help("Record")
    )
    prof3.metric(
        "Points",
        points_total,
        help=metric_help("Points")
    )
    prof4.metric(
        "Playoff status",
        playoff_status,
        help="Whether the team qualified for the playoffs in the selected season."
    )
    prof5.metric(
        "Division",
        profile_division,
        help=f"Conference: {profile_conference}. Division mapping uses the current app alignment table."
    )



# ============================================================
# PLAYER STATS
# ============================================================

st.markdown("### Player Stats")

if player_stats_df.empty:
    st.info(
        "Player stats file not found. Run data_preparation.py "
        "and make sure all_team_player_stats.csv is in the same folder as the app."
    )
else:
    scope_col, sort_col, n_col = st.columns([1.4, 1.2, 0.8])

    player_scope = scope_col.selectbox(
        "Player stats scope",
        ["Selected team", "Whole league season"],
        index=0,
        key=f"player_scope_{team}_{season}_{season_type}"
    )

    player_sort_choice = sort_col.selectbox(
        "Skaters by",
        ["points", "goals", "assists", "shots", "plus_minus"],
        index=0,
        key=f"top_players_sort_{team}_{season}_{season_type}"
    )

    top_n_choice = n_col.selectbox(
        "Rows",
        [3, 5, 10, 25, 50],
        index=0,
        key=f"top_players_n_{team}_{season}_{season_type}"
    )

    if player_scope == "Selected team":
        top_skaters = build_top_skaters_for_selection(
            player_stats=player_stats_df,
            team_code=team,
            season=season,
            season_type=season_type,
            n=int(top_n_choice),
            sort_by=player_sort_choice
        )

        render_top_player_cards(
            top_skaters.head(min(int(top_n_choice), 5)),
            title=f"Top {min(int(top_n_choice), 5)} skaters by {player_sort_choice}",
            subtitle=f"{team_full_name(team)} ({team}) — {season_label(season)} — {season_type}"
        )

        with st.expander("Show selected team skater table", expanded=int(top_n_choice) > 5):
            skater_table = build_top_skaters_for_selection(
                player_stats=player_stats_df,
                team_code=team,
                season=season,
                season_type=season_type,
                n=100,
                sort_by=player_sort_choice
            )

            skater_display = prepare_skaters_display_table(skater_table)

            if skater_display.empty:
                st.info("No skater data available.")
            else:
                st.dataframe(skater_display, use_container_width=True, hide_index=True)

        top_goalies = build_top_goalies_for_selection(
            player_stats=player_stats_df,
            team_code=team,
            season=season,
            season_type=season_type,
            n=3
        )

        with st.expander("Show selected team goalies", expanded=False):
            render_goalie_table(top_goalies)

    else:
        st.caption(
            f"League-wide player leaderboard for {season_label(season)} — {season_type}. "
            "This ignores the selected team filter."
        )

        league_skaters = build_league_skaters_for_selection(
            player_stats=player_stats_df,
            season=season,
            season_type=season_type,
            n=int(top_n_choice),
            sort_by=player_sort_choice
        )

        league_display = prepare_skaters_display_table(league_skaters)

        if league_display.empty:
            st.info("No league-wide skater data available for this selection.")
        else:
            st.dataframe(league_display, use_container_width=True, hide_index=True)

        goalie_min_games = st.slider(
            "Minimum goalie games played",
            min_value=1,
            max_value=40,
            value=10 if season_type == "Regular season" else 1,
            key=f"league_goalie_min_games_{season}_{season_type}"
        )

        league_goalies = build_league_goalies_for_selection(
            player_stats=player_stats_df,
            season=season,
            season_type=season_type,
            n=30,
            min_games=goalie_min_games
        )

        with st.expander("Show league goalie leaderboard", expanded=False):
            goalie_display = prepare_goalies_display_table(league_goalies)

            if goalie_display.empty:
                st.info("No goalie data available for this filter.")
            else:
                st.dataframe(goalie_display, use_container_width=True, hide_index=True)



# ============================================================
# TEAM OVERVIEW
# ============================================================

st.markdown("### Team Overview")

st.markdown("#### Full-game scoring and result stats")

fg1, fg2, fg3, fg4 = st.columns(4)

fg1.metric("Games", games, help=metric_help("Games"))
fg2.metric("Record", record_text, help=metric_help("Record"))
fg3.metric("Points", points_total, help=metric_help("Points"))
fg4.metric("Points per game", format_number(safe_divide(points_total, games), 2), help=metric_help("Points per game"))

fg5, fg6, fg7 = st.columns(3)

fg5.metric(
    "Goal differential/game",
    format_number(safe_divide(team_games["game_goal_diff"].sum(), games), 2),
    help=metric_help("Goal differential/game")
)
fg6.metric(
    "Goals for/game",
    format_number(safe_divide(team_games["game_goals_for"].sum(), games), 2),
    help=metric_help("Goals for/game")
)
fg7.metric(
    "Goals against/game",
    format_number(safe_divide(team_games["game_goals_against"].sum(), games), 2),
    help=metric_help("Goals against/game")
)

st.markdown("#### Situation-sensitive game stats")

st.caption(
    "These metrics change meaningfully when you switch between Full game, 5v5, 5v4, and 4v5."
)

sg1, sg2, sg3, sg4 = st.columns(4)

sg1.metric(
    "Shots for/game",
    format_number(safe_divide(team_games["shotsOnGoalFor"].sum(), games), 2),
    help=metric_help("Shots for/game")
)
sg2.metric(
    "Shots against/game",
    format_number(safe_divide(team_games["shotsOnGoalAgainst"].sum(), games), 2),
    help=metric_help("Shots against/game")
)
sg3.metric(
    "Shot attempts/game",
    format_number(safe_divide(team_games["shotAttemptsFor"].sum(), games), 2),
    help=metric_help("Shot attempts/game")
)
sg4.metric(
    "Faceoff %",
    format_number(team_faceoff_pct, 2),
    help=metric_help("Faceoff %")
)

sg5, sg6, sg7, sg8 = st.columns(4)

sg5.metric(
    "Giveaways/game",
    format_number(safe_divide(team_games["giveawaysFor"].sum(), games), 2),
    help=metric_help("Giveaways/game")
)

if "giveawaysAgainst" in team_games.columns:
    sg6.metric(
        "Opponent giveaways/game",
        format_number(safe_divide(team_games["giveawaysAgainst"].sum(), games), 2),
        help="Average opponent giveaways in games involving this team."
    )
else:
    sg6.metric("Opponent giveaways/game", "N/A", help="This column is not available in the selected dataset.")

if "shotAttemptsAgainst" in team_games.columns:
    sg7.metric(
        "Shot attempts against/game",
        format_number(safe_divide(team_games["shotAttemptsAgainst"].sum(), games), 2),
        help="Average shot attempts allowed per game."
    )
else:
    sg7.metric("Shot attempts against/game", "N/A", help="This column is not available in the selected dataset.")

sg8.metric(
    "Faceoffs/game",
    format_number(safe_divide(team_total_faceoffs, games), 2),
    help="Total faceoffs involving this team divided by games played."
)

st.markdown("#### Detailed result split")

rs1, rs2, rs3, rs4, rs5, rs6 = st.columns(6)

rs1.metric("REG W", regulation_wins, help="Regulation wins.")
rs2.metric("OTW", ot_wins, help="Overtime wins.")
rs3.metric("SOW", so_wins, help="Shootout wins.")
rs4.metric("REG L", regulation_losses, help="Regulation losses.")
rs5.metric("OTL", ot_losses, help="Overtime losses. These give 1 NHL point.")
rs6.metric("SOL", so_losses, help="Shootout losses. These give 1 NHL point.")

st.caption(f"NHL record format: W-L-OT. Detail: {detailed_record_text}")


# ============================================================
# REGULAR SEASON POINTS DEVELOPMENT
# ============================================================

if season_type == "Regular season":
    st.markdown("### Points Development")

    team_games["game_number"] = range(1, len(team_games) + 1)

    if "cumulative_points" not in team_games.columns:
        team_games["cumulative_points"] = team_games["points"].cumsum()

    fig_points = px.line(
        team_games,
        x="game_number",
        y="cumulative_points",
        markers=True,
        hover_data=[
            "gameDate",
            OPP_COL,
            "home_or_away",
            "game_result",
            "game_goals_for",
            "game_goals_against",
            "points",
            "record_string_after_game"
        ] if "record_string_after_game" in team_games.columns else [
            "gameDate",
            OPP_COL,
            "home_or_away",
            "game_result",
            "game_goals_for",
            "game_goals_against",
            "points"
        ],
        title=f"{full_team_name} ({team}) points development — {season_label(season)}",
        labels={
            "game_number": "Game number",
            "cumulative_points": "Cumulative points"
        }
    )

    st.plotly_chart(fig_points, use_container_width=True)

    st.markdown("### Rolling Form")

    rolling_games = team_games.sort_values(["gameDate", "gameId"]).copy()
    rolling_games["game_number"] = range(1, len(rolling_games) + 1)

    rolling_options = {
        "Points per game": "points",
        "Goal differential": "game_goal_diff",
        "Goals for": "game_goals_for",
        "Goals against": "game_goals_against",
        "Shots for": "shotsOnGoalFor",
        "Shots against": "shotsOnGoalAgainst",
        "Faceoff %": "faceoff_pct_100",
        "Giveaways": "giveawaysFor"
    }

    available_rolling_options = {
        label: col for label, col in rolling_options.items()
        if col in rolling_games.columns
    }

    rc1, rc2 = st.columns([2, 1])

    rolling_stat_name = rc1.selectbox(
        "Rolling metric",
        list(available_rolling_options.keys()),
        index=0,
        key=f"rolling_metric_{team}_{season}_{season_type}_{view_mode}_{situation}"
    )

    rolling_window = rc2.selectbox(
        "Rolling window",
        [5, 10, 15],
        index=1,
        key=f"rolling_window_{team}_{season}_{season_type}_{view_mode}_{situation}"
    )

    rolling_col = available_rolling_options[rolling_stat_name]
    rolling_games[f"Rolling {rolling_window}"] = (
        rolling_games[rolling_col]
        .rolling(window=rolling_window, min_periods=1)
        .mean()
    )

    fig_rolling = px.line(
        rolling_games,
        x="game_number",
        y=f"Rolling {rolling_window}",
        markers=True,
        hover_data=[
            "gameDate",
            OPP_COL,
            "home_or_away",
            "game_result",
            "game_goals_for",
            "game_goals_against"
        ],
        title=f"{full_team_name} ({team}) rolling {rolling_window}-game {rolling_stat_name.lower()} — {season_label(season)}",
        labels={
            "game_number": "Game number",
            f"Rolling {rolling_window}": f"Rolling {rolling_window}-game {rolling_stat_name}"
        }
    )

    st.plotly_chart(fig_rolling, use_container_width=True)


# ============================================================
# PLAYOFF BRACKET SECTION
# ============================================================

if season_type == "Playoffs":
    st.markdown("### Playoff Bracket")

    playoff_league_games = (
        game_df[
            (game_df["season"] == season) &
            (game_df["season_type"] == "Playoffs")
        ]
        .drop_duplicates(["gameId", TEAM_COL])
        .copy()
    )

    playoff_team_games = (
        game_df[
            (game_df[TEAM_COL] == team) &
            (game_df["season"] == season) &
            (game_df["season_type"] == "Playoffs")
        ]
        .drop_duplicates(["gameId", TEAM_COL])
        .sort_values(["gameDate", "gameId"])
        .copy()
    )

    if playoff_league_games.empty:
        st.info(f"No playoff data available for the {season_label(season)} season.")
    else:
        full_series_summary = build_league_playoff_series_summary(playoff_league_games)

        qualified_teams = sorted(
            set(playoff_league_games[TEAM_COL].dropna().astype(str).unique())
            | set(playoff_league_games[OPP_COL].dropna().astype(str).unique())
        )

        if team not in qualified_teams:
            st.warning(
                f"{team_full_name(team)} ({team}) did not qualify for the {season_label(season)} playoffs."
            )
        else:
            st.success(
                f"{team_full_name(team)} ({team}) qualified for the {season_label(season)} playoffs."
            )

        if full_series_summary.empty:
            st.info("No playoff series bracket could be built from the available data.")
        else:
            bracket_html = render_playoff_bracket(full_series_summary, team, season)
            components.html(bracket_html, height=850, scrolling=False)

            with st.expander("Show full playoff series table"):
                st.dataframe(full_series_summary, use_container_width=True)

        if not playoff_team_games.empty:
            st.markdown("### Selected Team Playoff Path")

            selected_series_summary = build_selected_team_playoff_series_summary(playoff_team_games)

            if not selected_series_summary.empty:
                st.dataframe(selected_series_summary, use_container_width=True)

            path_summary_df = selected_team_playoff_path_table(playoff_team_games, team)

            if not path_summary_df.empty:
                st.markdown("#### Playoff Path Summary")
                render_playoff_path_cards(path_summary_df, team)

            playoff_team_games = add_playoff_series_info(playoff_team_games)
            render_playoff_result_sequence(playoff_team_games)

        st.caption(
            "Bracket stages are inferred from the number and chronological order of playoff series. "
            "For perfect official accuracy, the data prep would still need explicit conference, seed, and bracket-position columns."
        )


# ============================================================
# LEAGUE RANKING
# ============================================================

st.markdown("### League Table")

ranking = (
    league_games
    .groupby(TEAM_COL)
    .agg(
        games=("gameId", "nunique"),
        total_points=("points", "sum"),
        W=("record_w", "sum"),
        L=("record_l", "sum"),
        OT=("record_ot", "sum"),
        RW=("regulation_win", "sum"),
        OTW=("ot_win", "sum"),
        SOW=("so_win", "sum"),
        ROW=("regulation_win", "sum"),
        goal_diff_total=("game_goal_diff", "sum"),
        goals_for_total=("game_goals_for", "sum"),
        goals_against_total=("game_goals_against", "sum"),
        shots_for_total=("shotsOnGoalFor", "sum"),
        shots_against_total=("shotsOnGoalAgainst", "sum"),
        shot_attempts_for_total=("shotAttemptsFor", "sum"),
        giveaways_total=("giveawaysFor", "sum"),
        faceoffs_won=("faceOffsWonFor", "sum"),
        faceoffs_total=("total_faceoffs", "sum")
    )
    .reset_index()
)

ranking["ROW"] = ranking["RW"] + ranking["OTW"]
ranking["GD"] = ranking["goal_diff_total"]
ranking["GF"] = ranking["goals_for_total"]

ranking["record"] = (
    ranking["W"].astype(int).astype(str)
    + "-"
    + ranking["L"].astype(int).astype(str)
    + "-"
    + ranking["OT"].astype(int).astype(str)
)

ranking["points_per_game"] = ranking["total_points"] / ranking["games"]
ranking["goal_diff_per_game"] = ranking["goal_diff_total"] / ranking["games"]
ranking["goals_for_per_game"] = ranking["goals_for_total"] / ranking["games"]
ranking["goals_against_per_game"] = ranking["goals_against_total"] / ranking["games"]
ranking["shots_for_per_game"] = ranking["shots_for_total"] / ranking["games"]
ranking["shots_against_per_game"] = ranking["shots_against_total"] / ranking["games"]
ranking["shot_attempts_for_per_game"] = ranking["shot_attempts_for_total"] / ranking["games"]
ranking["giveaways_per_game"] = ranking["giveaways_total"] / ranking["games"]
ranking["faceoff_pct"] = ranking["faceoffs_won"] / ranking["faceoffs_total"] * 100

stat_options = {
    "Total points": "total_points",
    "Points per game": "points_per_game",
    "Goal differential per game": "goal_diff_per_game",
    "Goals for per game": "goals_for_per_game",
    "Goals against per game": "goals_against_per_game",
    "Shots for per game": "shots_for_per_game",
    "Shots against per game": "shots_against_per_game",
    "Shot attempts for per game": "shot_attempts_for_per_game",
    "Faceoff %": "faceoff_pct",
    "Giveaways per game": "giveaways_per_game"
}

# Official-like standings order with unique ranks.
selected_stat_name = "Total points"
selected_stat = "total_points"

ranking = add_official_like_standings_order(ranking)

team_rank = int(ranking.loc[ranking[TEAM_COL] == team, "rank"].iloc[0])
number_of_teams = ranking[TEAM_COL].nunique()

league_average = ranking[selected_stat].mean()
team_value = ranking.loc[ranking[TEAM_COL] == team, selected_stat].iloc[0]
difference = team_value - league_average




# ============================================================
# LEAGUE TABLE
# ============================================================

st.markdown("#### League Table")

playoff_teams_for_season = set(
    game_df[
        (game_df["season"] == season) &
        (game_df["season_type"] == "Playoffs")
    ][TEAM_COL].dropna().astype(str).unique()
)

show_sortable_league_table(
    ranking=ranking,
    selected_team=team,
    season_type=season_type,
    view_mode=view_mode,
    playoff_teams=playoff_teams_for_season
)

st.caption(
    "Light green rows = teams that qualified for the playoffs. "
    "Standings order uses NHL-style available tiebreakers: points, fewer games played / points percentage, "
    "regulation wins (RW), regulation+overtime wins excluding shootouts (ROW), total wins, goal differential, "
    "and goals for. Official head-to-head points are noted but not calculated in this app yet."
)


# ============================================================
# PLAYOFF QUALIFICATION RACE
# ============================================================

if season_type == "Regular season":
    st.markdown("### Playoff Qualification Race")

    race_table, race_summary = playoff_race_summary_table(
        ranking=ranking,
        selected_team=team,
        playoff_teams_for_season=playoff_teams_for_season
    )

    if not race_summary:
        st.info("No playoff race summary available for this selection.")
    else:
        race1, race2, race3, race4 = st.columns(4)

        race1.metric(
            "Conference rank",
            f"{race_summary['conference_rank']}",
            help=f"Rank within the {race_summary['conference']} Conference."
        )
        race2.metric(
            "Division rank",
            f"{race_summary['division_rank']}",
            help=f"Rank within the {race_summary['division']} Division."
        )
        race3.metric(
            "Playoff status",
            "Qualified" if race_summary["qualified"] else "Missed",
            help="Based on actual playoff teams present in the playoff dataset for this season."
        )

        if pd.notna(race_summary["points_above_cutoff"]):
            diff = race_summary["points_above_cutoff"]
            race4.metric(
                "Vs playoff cutoff",
                f"{diff:+.0f} pts",
                help="Difference between selected team's points and the lowest-points playoff team in the same conference."
            )
        else:
            race4.metric("Vs playoff cutoff", "N/A")

        with st.expander("Show conference playoff race table", expanded=False):
            styled_race = race_table.style.apply(
                lambda row: [
                    "background-color: rgba(250, 204, 21, 0.42); font-weight: 900;"
                    if str(row.get("Team", "")) == str(team)
                    else (
                        "background-color: rgba(34, 197, 94, 0.13);"
                        if str(row.get("Playoffs", "")) == "Yes"
                        else ""
                    )
                ] * len(row),
                axis=1
            )
            st.dataframe(styled_race, use_container_width=True, hide_index=True)

        st.caption(
            "Playoff cutoff is inferred from actual playoff qualifiers in the dataset. "
            "This is practical for this app, but exact NHL qualification rules can differ in special seasons."
        )


# ============================================================
# TEAM STRENGTHS AND WEAKNESSES
# ============================================================

st.markdown("### Team Strengths and Weaknesses")

team_stat_rank_options = {
    "Points per game": ("points_per_game", False),
    "Goal differential/game": ("goal_diff_per_game", False),
    "Goals for/game": ("goals_for_per_game", False),
    "Goals against/game": ("goals_against_per_game", True),
    "Shots for/game": ("shots_for_per_game", False),
    "Shots against/game": ("shots_against_per_game", True),
    "Shot attempts/game": ("shot_attempts_for_per_game", False),
    "Faceoff %": ("faceoff_pct", False),
    "Giveaways/game": ("giveaways_per_game", True)
}

strength_rows = []

for label, (col, lower_is_better_stat) in team_stat_rank_options.items():
    if col not in ranking.columns:
        continue

    stat_values = ranking[[TEAM_COL, col]].dropna().copy()

    if stat_values.empty or team not in stat_values[TEAM_COL].values:
        continue

    stat_values["stat_rank"] = stat_values[col].rank(
        ascending=lower_is_better_stat,
        method="min"
    )

    selected_stat_row = stat_values.loc[stat_values[TEAM_COL] == team].iloc[0]
    n_teams_stat = int(stat_values[TEAM_COL].nunique())
    rank_value = int(selected_stat_row["stat_rank"])

    # 0 = best in league, 1 = worst in league.
    if n_teams_stat > 1:
        weakness_score = (rank_value - 1) / (n_teams_stat - 1)
    else:
        weakness_score = 0

    strength_rows.append({
        "Statistic": label,
        "Value": round(float(selected_stat_row[col]), 2),
        "Rank": rank_value,
        "Teams": n_teams_stat,
        "Rank text": f"{rank_value}/{n_teams_stat}",
        "Direction": "Lower is better" if lower_is_better_stat else "Higher is better",
        "Weakness score": round(float(weakness_score), 3)
    })

strength_df = pd.DataFrame(strength_rows)

if strength_df.empty:
    st.info("Not enough data to calculate strengths and weaknesses for this selection.")
else:
    # Strengths are genuinely good relative rankings.
    strengths = (
        strength_df[strength_df["Weakness score"] <= 0.35]
        .sort_values(["Weakness score", "Statistic"])
        .head(4)
        .copy()
    )

    # Weaknesses are only metrics where the team is clearly in the worse half.
    # This avoids calling a strong defensive stat a weakness just because it is included
    # in the bottom of an unfiltered list.
    weaknesses = (
        strength_df[strength_df["Weakness score"] >= 0.55]
        .sort_values(["Weakness score", "Statistic"], ascending=[False, True])
        .head(4)
        .copy()
    )

    display_cols = ["Statistic", "Value", "Rank text", "Direction"]

    sw1, sw2 = st.columns(2)

    with sw1:
        st.markdown("#### Strengths")
        st.caption("Only metrics where the team ranks clearly above average are shown.")
        if strengths.empty:
            st.info("No clear strengths among the tracked metrics.")
        else:
            st.dataframe(strengths[display_cols], use_container_width=True, hide_index=True)

    with sw2:
        st.markdown("#### Weaknesses")
        st.caption("Only metrics where the team ranks clearly below average are shown.")
        if weaknesses.empty:
            st.success("No clear weakness among the tracked metrics.")
        else:
            st.dataframe(weaknesses[display_cols], use_container_width=True, hide_index=True)



# ============================================================
# TEAM COMPARISON
# ============================================================

st.markdown("### Team Comparison")

comparison_candidates = sorted(
    [x for x in ranking[TEAM_COL].dropna().astype(str).unique().tolist() if x != team]
)

if comparison_candidates:
    default_compare_index = 0
    if len(comparison_candidates) > 1:
        default_compare_index = min(1, len(comparison_candidates) - 1)

    comparison_team = st.selectbox(
        "Compare selected team with",
        comparison_candidates,
        index=default_compare_index,
        format_func=lambda x: f"{team_full_name(x)} ({x})",
        key=f"comparison_team_{team}_{season}_{season_type}_{view_mode}_{situation}"
    )

    comparison_stats = {
        "Points": ("total_points", False),
        "Points/game": ("points_per_game", False),
        "Goal differential/game": ("goal_diff_per_game", False),
        "Goals for/game": ("goals_for_per_game", False),
        "Goals against/game": ("goals_against_per_game", True),
        "Shots for/game": ("shots_for_per_game", False),
        "Shots against/game": ("shots_against_per_game", True),
        "Shot attempts/game": ("shot_attempts_for_per_game", False),
        "Faceoff %": ("faceoff_pct", False),
        "Giveaways/game": ("giveaways_per_game", True)
    }

    selected_compare_row = ranking.loc[ranking[TEAM_COL] == team].iloc[0]
    other_compare_row = ranking.loc[ranking[TEAM_COL] == comparison_team].iloc[0]

    comparison_rows = []

    for label, (col, lower_is_better_stat) in comparison_stats.items():
        if col not in ranking.columns:
            continue

        selected_value = selected_compare_row[col]
        other_value = other_compare_row[col]

        if pd.isna(selected_value) or pd.isna(other_value):
            better = "N/A"
        elif abs(float(selected_value) - float(other_value)) < 1e-9:
            better = "Tie"
        elif lower_is_better_stat:
            better = team if selected_value < other_value else comparison_team
        else:
            better = team if selected_value > other_value else comparison_team

        comparison_rows.append({
            "Statistic": label,
            f"{team}": round(float(selected_value), 2) if pd.notna(selected_value) else np.nan,
            f"{comparison_team}": round(float(other_value), 2) if pd.notna(other_value) else np.nan,
            "Better": better,
            "Direction": "Lower is better" if lower_is_better_stat else "Higher is better"
        })

    comparison_df = pd.DataFrame(comparison_rows)

    cc1, cc2, cc3 = st.columns(3)

    cc1.metric(
        f"{team} record",
        selected_compare_row["record"] if "record" in selected_compare_row else record_text
    )
    cc2.metric(
        f"{comparison_team} record",
        other_compare_row["record"] if "record" in other_compare_row else "N/A"
    )
    cc3.metric(
        "Comparison season",
        season_label(season)
    )

    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    st.markdown("#### Head-to-Head in Selected Season")

    h2h_games, h2h_summary = build_head_to_head_summary(
        game_df=game_df,
        team_a=team,
        team_b=comparison_team,
        season=season,
        season_type=season_type
    )

    if not h2h_summary:
        st.info(
            f"No head-to-head games found for {team} vs {comparison_team} "
            f"in {season_label(season)} ({season_type})."
        )
    else:
        h1, h2, h3, h4 = st.columns(4)

        h1.metric(f"{team} H2H record", h2h_summary["record"])
        h2.metric(f"{team} H2H points", h2h_summary["points"])
        h3.metric("Goals", h2h_summary["goals"])
        h4.metric("Games", h2h_summary["games"])

        h2h_display = h2h_games[[
            "gameDate",
            "home_or_away",
            OPP_COL,
            "game_result",
            "game_goals_for",
            "game_goals_against",
            "points"
        ]].copy()

        h2h_display = h2h_display.rename(columns={
            "gameDate": "Date",
            "home_or_away": "Home/Away",
            OPP_COL: "Opponent",
            "game_result": "Result",
            "game_goals_for": "GF",
            "game_goals_against": "GA",
            "points": "PTS"
        })

        with st.expander("Show head-to-head games", expanded=False):
            st.dataframe(h2h_display, use_container_width=True, hide_index=True)
else:
    st.info("No other team is available for comparison in this selection.")



# ============================================================
# LEAGUE SCATTER PLOT
# ============================================================

st.markdown("### League Scatter Plot")

scatter_options = stat_options.copy()

x_stat_name = st.selectbox(
    "X-axis statistic",
    list(scatter_options.keys()),
    index=8
)

y_stat_name = st.selectbox(
    "Y-axis statistic",
    list(scatter_options.keys()),
    index=1
)

x_stat = scatter_options[x_stat_name]
y_stat = scatter_options[y_stat_name]

scatter_df = ranking.copy()
scatter_df = scatter_df.dropna(subset=[x_stat, y_stat])

if scatter_df.empty:
    st.info("No data available for this scatter plot.")
else:
    scatter_df["selected_team"] = scatter_df[TEAM_COL].apply(
        lambda x: "Selected team" if x == team else "Other teams"
    )

    fig_scatter = px.scatter(
        scatter_df,
        x=x_stat,
        y=y_stat,
        hover_name=TEAM_COL,
        hover_data=["record", "games", "total_points"],
        title=f"{x_stat_name} vs {y_stat_name}",
        labels={
            x_stat: x_stat_name,
            y_stat: y_stat_name,
            "selected_team": ""
        }
    )

    # Make normal markers nearly invisible; logos are added as layout images.
    fig_scatter.update_traces(
        marker=dict(size=2, opacity=0.05),
        text=None,
        showlegend=False
    )

    x_min = float(scatter_df[x_stat].min())
    x_max = float(scatter_df[x_stat].max())
    y_min = float(scatter_df[y_stat].min())
    y_max = float(scatter_df[y_stat].max())

    x_span = max(x_max - x_min, 1e-6)
    y_span = max(y_max - y_min, 1e-6)

    # Add a little axis padding so edge logos are not cut off.
    fig_scatter.update_xaxes(range=[x_min - 0.08 * x_span, x_max + 0.08 * x_span])
    fig_scatter.update_yaxes(range=[y_min - 0.12 * y_span, y_max + 0.12 * y_span])

    logo_size_x = 0.035 * x_span
    logo_size_y = 0.075 * y_span

    selected_logo_size_x = 0.052 * x_span
    selected_logo_size_y = 0.105 * y_span

    for _, row in scatter_df.iterrows():
        team_code = str(row[TEAM_COL])
        uri = logo_data_uri(team_code)

        if not uri:
            continue

        is_selected = team_code == team

        fig_scatter.add_layout_image(
            dict(
                source=uri,
                x=float(row[x_stat]),
                y=float(row[y_stat]),
                xref="x",
                yref="y",
                sizex=selected_logo_size_x if is_selected else logo_size_x,
                sizey=selected_logo_size_y if is_selected else logo_size_y,
                xanchor="center",
                yanchor="middle",
                layer="above",
                opacity=1.0
            )
        )

        # Add a gold ring around selected team.
        if is_selected:
            fig_scatter.add_shape(
                type="circle",
                xref="x",
                yref="y",
                x0=float(row[x_stat]) - selected_logo_size_x / 1.7,
                x1=float(row[x_stat]) + selected_logo_size_x / 1.7,
                y0=float(row[y_stat]) - selected_logo_size_y / 1.7,
                y1=float(row[y_stat]) + selected_logo_size_y / 1.7,
                line=dict(color="#facc15", width=3),
                fillcolor="rgba(250,204,21,0.12)"
            )

    st.plotly_chart(fig_scatter, use_container_width=True)

    st.caption(
        "The scatter uses team logos as markers. If a logo is missing from the local logos folder, "
        "that team will still appear in hover data but may not show as an image."
    )


# ============================================================
# TEAM VS LEAGUE AVERAGE
# ============================================================

st.markdown("### Team vs League Average")

comparison_stats = {
    "Points per game": "points_per_game",
    "Goal differential/game": "goal_diff_per_game",
    "Goals for/game": "goals_for_per_game",
    "Goals against/game": "goals_against_per_game",
    "Shots for/game": "shots_for_per_game",
    "Shots against/game": "shots_against_per_game",
    "Shot attempts/game": "shot_attempts_for_per_game",
    "Faceoff %": "faceoff_pct",
    "Giveaways/game": "giveaways_per_game"
}

comparison_rows = []

for label, col in comparison_stats.items():
    team_avg = ranking.loc[ranking[TEAM_COL] == team, col].iloc[0]
    league_avg = ranking[col].mean()

    comparison_rows.append({
        "Statistic": label,
        team: round(team_avg, 2),
        "League average": round(league_avg, 2),
        "Difference": round(team_avg - league_avg, 2)
    })

comparison_df = pd.DataFrame(comparison_rows)

st.dataframe(comparison_df, use_container_width=True)


# ============================================================
# MATCH-BY-MATCH DATA
# ============================================================

st.markdown("### Match-by-Match Data")

base_cols = [
    "gameDate",
    TEAM_COL,
    OPP_COL,
    "home_or_away",
    "season_type",
    "game_result",
    "official_last_period_type",
    "game_goals_for",
    "game_goals_against",
    "points",
    "record_string_after_game",
    "cumulative_points",
    "shotsOnGoalFor",
    "shotsOnGoalAgainst",
    "shotAttemptsFor",
    "shotAttemptsAgainst",
    "faceOffsWonFor",
    "faceOffsWonAgainst",
    "faceoff_pct_100",
    "giveawaysFor",
    "giveawaysAgainst"
]

if "situation" in team_df.columns:
    base_cols.insert(5, "situation")
    base_cols.insert(10, "goalsFor")
    base_cols.insert(11, "goalsAgainst")

show_cols = []

for col in base_cols:
    if col in team_df.columns and col not in show_cols:
        show_cols.append(col)

# Sort on the original dataframe first.
# In older versions this sorted after selecting show_cols, but gameId was not displayed,
# so pandas raised KeyError: 'gameId'.
sort_cols = [col for col in ["gameDate", "gameId"] if col in team_df.columns]

if sort_cols:
    match_table = team_df.sort_values(sort_cols)[show_cols].copy()
else:
    match_table = team_df[show_cols].copy()

st.dataframe(match_table, use_container_width=True)
