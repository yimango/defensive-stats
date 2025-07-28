import pandas as pd

df = pd.read_csv("nhl_defense_shot_data.csv")
agg = df.groupby(["player_id","on_off"]).agg(
    att=("xg","count"),
    xga=("xg","sum"),
).unstack(fill_value=0)

agg.columns = [f"{side}_{metric}" for metric,side in agg.columns]
agg["expASV_on"]  = 1 - agg["on_xga"]/agg["on_att"]
agg["expASV_off"] = 1 - agg["off_xga"]/agg["off_att"]
agg["delta_expASV"] = agg["expASV_on"] - agg["expASV_off"]

print(agg["delta_expASV"].sort_values(ascending=False).head(20))
