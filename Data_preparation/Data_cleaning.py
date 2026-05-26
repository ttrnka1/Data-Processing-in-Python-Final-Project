#!/usr/bin/env python
# coding: utf-8

# In[3]:


import pandas as pd
import requests
from io import StringIO

url = "https://moneypuck.com/moneypuck/playerData/careers/gameByGame/all_teams.csv"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)

df = pd.read_csv(StringIO(response.text))

print(df.head())


# In[4]:


# necháme jen celkové statistiky za zápas a jen regular season
nhl = df[df["situation"] == "all"].copy()
nhl = nhl[nhl["playoffGame"] == 0].copy()

nhl.shape


# In[5]:


faceoff_data = nhl[[
    "season",
    "gameId",
    "gameDate",
    "team",
    "opposingTeam",
    "home_or_away",
    "goalsFor",
    "goalsAgainst",
    "faceOffsWonFor",
    "faceOffsWonAgainst"
]].copy()

faceoff_data.head()


# In[6]:


faceoff_data.groupby("gameId").size().value_counts()


# In[7]:


faceoff_data["total_faceoffs"] = (
    faceoff_data["faceOffsWonFor"] + faceoff_data["faceOffsWonAgainst"]
)

faceoff_data["faceoff_pct"] = (
    faceoff_data["faceOffsWonFor"] / faceoff_data["total_faceoffs"]
)

faceoff_data["faceoff_pct_100"] = faceoff_data["faceoff_pct"] * 100

faceoff_data.head()


# In[8]:


faceoff_data["win"] = (faceoff_data["goalsFor"] > faceoff_data["goalsAgainst"]).astype(int)

faceoff_data["goal_diff"] = faceoff_data["goalsFor"] - faceoff_data["goalsAgainst"]

faceoff_data.head()


# In[9]:


faceoff_data[[
    "team",
    "opposingTeam",
    "goalsFor",
    "goalsAgainst",
    "win",
    "goal_diff",
    "faceOffsWonFor",
    "faceOffsWonAgainst",
    "faceoff_pct_100"
]].head(10)


# In[10]:


faceoff_data = nhl[[
    "season",
    "gameId",
    "gameDate",
    "team",
    "opposingTeam",
    "home_or_away",
    "goalsFor",
    "goalsAgainst",
    "faceOffsWonFor",
    "faceOffsWonAgainst"
]].copy()

faceoff_data["total_faceoffs"] = (
    faceoff_data["faceOffsWonFor"] + faceoff_data["faceOffsWonAgainst"]
)

faceoff_data["faceoff_pct"] = (
    faceoff_data["faceOffsWonFor"] / faceoff_data["total_faceoffs"]
)

faceoff_data["faceoff_pct_100"] = faceoff_data["faceoff_pct"] * 100

faceoff_data.shape


# In[33]:


faceoff_data.groupby("gameId").size().value_counts()


# In[12]:


faceoff_check = (
    faceoff_data
    .groupby("gameId")["faceoff_pct_100"]
    .sum()
    .reset_index(name="sum_faceoff_pct")
)

faceoff_check["sum_faceoff_pct"].describe()


# In[13]:


bad_faceoff_games = faceoff_check[
    abs(faceoff_check["sum_faceoff_pct"] - 100) > 0.000001
]

bad_faceoff_games


# In[34]:


faceoff_data[faceoff_data["total_faceoffs"] == 0]


# In[35]:


faceoff_data["faceoff_pct_100"].describe()


# In[16]:


faceoff_situations = df[
    (df["situation"].isin(["5on5", "5on4", "4on5"])) &
    (df["playoffGame"] == 0)
].copy()

faceoff_situations = faceoff_situations[[
    "season",
    "gameId",
    "gameDate",
    "team",
    "opposingTeam",
    "home_or_away",
    "situation",
    "goalsFor",
    "goalsAgainst",
    "faceOffsWonFor",
    "faceOffsWonAgainst"
]].copy()

faceoff_situations.head(15)


# In[17]:


faceoff_situations["total_faceoffs"] = (
    faceoff_situations["faceOffsWonFor"] + 
    faceoff_situations["faceOffsWonAgainst"]
)

faceoff_situations["faceoff_pct"] = (
    faceoff_situations["faceOffsWonFor"] / 
    faceoff_situations["total_faceoffs"]
)

faceoff_situations["faceoff_pct_100"] = (
    faceoff_situations["faceoff_pct"] * 100
)

faceoff_situations.head(15)


# In[18]:


faceoff_situations[faceoff_situations["total_faceoffs"] == 0].shape


# In[37]:


faceoff_situations[
    faceoff_situations["total_faceoffs"] == 0
]["situation"].value_counts()


# In[38]:


import numpy as np

faceoff_situations["faceoff_pct"] = np.where(
    faceoff_situations["total_faceoffs"] > 0,
    faceoff_situations["faceOffsWonFor"] / faceoff_situations["total_faceoffs"],
    np.nan
)

faceoff_situations["faceoff_pct_100"] = faceoff_situations["faceoff_pct"] * 100

faceoff_situations[[
    "season",
    "gameId",
    "team",
    "opposingTeam",
    "situation",
    "faceOffsWonFor",
    "faceOffsWonAgainst",
    "total_faceoffs",
    "faceoff_pct_100"
]].head(20)


# In[39]:


summary_by_situation = (
    faceoff_situations
    .groupby("situation")
    .agg(
        rows=("gameId", "count"),
        games=("gameId", "nunique"),
        zero_faceoff_rows=("total_faceoffs", lambda x: (x == 0).sum()),
        avg_total_faceoffs=("total_faceoffs", "mean"),
        median_total_faceoffs=("total_faceoffs", "median"),
        avg_faceoff_pct=("faceoff_pct_100", "mean"),
        median_faceoff_pct=("faceoff_pct_100", "median")
    )
    .reset_index()
)

summary_by_situation


# In[22]:


situation_check = (
    faceoff_situations
    .groupby(["gameId", "situation"])["total_faceoffs"]
    .sum()
    .unstack()
)

situation_check.head()


# In[23]:


[col for col in df.columns if "shot" in col.lower()]


# In[40]:


shots_data = nhl[[
    "season",
    "gameId",
    "gameDate",
    "team",
    "opposingTeam",
    "home_or_away",
    "goalsFor",
    "goalsAgainst",
    "shotsOnGoalFor",
    "shotsOnGoalAgainst",
    "shotAttemptsFor",
    "shotAttemptsAgainst",
    "highDangerShotsFor",
    "highDangerShotsAgainst"
]].copy()

shots_data.head()


# In[25]:


game_situation_data = df[
    (df["situation"].isin(["5on5", "5on4", "4on5"])) &
    (df["playoffGame"] == 0)
].copy()

game_situation_data = game_situation_data[[
    "season",
    "gameId",
    "gameDate",
    "team",
    "opposingTeam",
    "home_or_away",
    "situation",

    # result in that situation
    "goalsFor",
    "goalsAgainst",

    # faceoffs
    "faceOffsWonFor",
    "faceOffsWonAgainst",

    # shots
    "shotsOnGoalFor",
    "shotsOnGoalAgainst",
    "shotAttemptsFor",
    "shotAttemptsAgainst",

    # giveaways
    "giveawaysFor",
    "giveawaysAgainst"
]].copy()

game_situation_data.head(15)


# In[26]:


df["season"].min(), df["season"].max()


# In[27]:


final_game_situation_data = df[
    (df["season"] < 2025) &
    (df["playoffGame"] == 0) &
    (df["situation"].isin(["5on5", "5on4", "4on5"]))
].copy()

final_game_situation_data = final_game_situation_data[[
    "season",
    "gameId",
    "gameDate",
    "team",
    "opposingTeam",
    "home_or_away",
    "situation",

    # goals in given situation
    "goalsFor",
    "goalsAgainst",

    # faceoffs
    "faceOffsWonFor",
    "faceOffsWonAgainst",

    # shots
    "shotsOnGoalFor",
    "shotsOnGoalAgainst",
    "shotAttemptsFor",
    "shotAttemptsAgainst",

    # giveaways
    "giveawaysFor",
    "giveawaysAgainst"
]].copy()

final_game_situation_data["win"] = (
    final_game_situation_data["goalsFor"] > final_game_situation_data["goalsAgainst"]
).astype(int)

final_game_situation_data["goal_diff"] = (
    final_game_situation_data["goalsFor"] - final_game_situation_data["goalsAgainst"]
)

final_game_situation_data.head(15)


# In[28]:


final_game_situation_data.sort_values(
    ["season", "gameDate", "gameId", "team", "situation"]
).tail(20)


# In[29]:


summary_by_situation = (
    final_game_situation_data
    .groupby("situation")
    .agg(
        games=("gameId", "nunique"),
        rows=("gameId", "count"),

        avg_goals_for=("goalsFor", "mean"),
        avg_goals_against=("goalsAgainst", "mean"),

        avg_faceoffs_won_for=("faceOffsWonFor", "mean"),
        avg_faceoffs_won_against=("faceOffsWonAgainst", "mean"),

        avg_shots_on_goal_for=("shotsOnGoalFor", "mean"),
        avg_shots_on_goal_against=("shotsOnGoalAgainst", "mean"),

        avg_shot_attempts_for=("shotAttemptsFor", "mean"),
        avg_shot_attempts_against=("shotAttemptsAgainst", "mean"),

        avg_giveaways_for=("giveawaysFor", "mean"),
        avg_giveaways_against=("giveawaysAgainst", "mean")
    )
    .reset_index()
)

summary_by_situation


# In[30]:


[col for col in final_game_situation_data.columns if "win" in col.lower()]


# In[31]:


game_results = df[
    (df["season"] < 2025) &
    (df["playoffGame"] == 0) &
    (df["situation"] == "all")
].copy()

game_results = game_results[[
    "gameId",
    "team",
    "goalsFor",
    "goalsAgainst"
]].copy()

game_results = game_results.rename(columns={
    "goalsFor": "game_goals_for",
    "goalsAgainst": "game_goals_against"
})

# win / draw / lose za celý zápas
game_results["win"] = 0
game_results["draw"] = 0
game_results["lose"] = 0

game_results.loc[
    game_results["game_goals_for"] > game_results["game_goals_against"],
    "win"
] = 1

game_results.loc[
    game_results["game_goals_for"] == game_results["game_goals_against"],
    "draw"
] = 1

game_results.loc[
    game_results["game_goals_for"] < game_results["game_goals_against"],
    "lose"
] = 1

# points: NHL tabulkové body
# výhra = 2 body, remíza = 1 bod, prohra = 0 bodů
game_results["points"] = (
    game_results["win"] * 2 +
    game_results["draw"] * 1
)

game_results["game_goal_diff"] = (
    game_results["game_goals_for"] - game_results["game_goals_against"]
)

game_results.head()


# In[41]:


final_game_situation_data = final_game_situation_data.drop(
    columns=[
        "win", 
        "draw", 
        "lose", 
        "points",
        "game_goals_for",
        "game_goals_against",
        "game_goal_diff"
    ],
    errors="ignore"
)

# merge do hlavního working datasetu
final_game_situation_data = final_game_situation_data.merge(
    game_results,
    on=["gameId", "team"],
    how="left"
)

final_game_situation_data.tail(10)

