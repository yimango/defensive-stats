import pandas as pd
import os
import requests
import time

SPORTSRADAR_BASE_URL  = "https://api.sportradar.us/nhl/production/v7/en"
SPORTSRADAR_API_KEY   = os.getenv("SPORTSRADAR_API_KEY")

# 1) Read in the shot‐data
df = pd.read_csv("nhl_defense_shot_data.csv")

# 2) Aggregate on/off ice xG totals
agg = (
    df
    .groupby(["player_id","on_off"])
    .agg(att=("xg","count"), xga=("xg","sum"))
    .unstack(fill_value=0)
)
agg.columns = [f"{side}_{metric}" for metric,side in agg.columns]

# 3) Compute exp aSV% and delta
agg["expASV_on"]   = 1 - agg["on_xga"]  / agg["on_att"]
agg["expASV_off"]  = 1 - agg["off_xga"] / agg["off_att"]
agg["delta_expASV"]= agg["expASV_on"]   - agg["expASV_off"]

# 4) Fetch player names from NHL Stats API
player_ids = agg.index.tolist()
name_map = {}
for pid in player_ids:
    url = f"{SPORTSRADAR_BASE_URL}/players/{pid}/profile.json"
    header = {
    "accept": "application/json",
    "x-api-key": SPORTSRADAR_API_KEY
    }
    resp = requests.get(url, headers=header)
    resp.raise_for_status()
    name = resp.json()["full_name"]
    name_map[pid] = name
    time.sleep(3)

# 5) Build final DataFrame and write to CSV
out = (
    agg
    .reset_index()
    .assign(player_name = lambda d: d["player_id"].map(name_map))
    .loc[:, ["player_name","expASV_on","expASV_off","delta_expASV"]]
)
out.to_csv("delta_exp_asv_results.csv", index=False)
print("Wrote", len(out), "rows to delta_exp_asv_results.csv")
