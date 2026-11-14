"""
FLEX 'flame intensity index' built ONLY from real FLEX columns.
Run AFTER clean_data.py:   python risk_index.py
Needs: pip install pandas
What it is:  condition groups (fuel x diluent x oxygen level) ranked by the mean
             burning rate K (mm^2/s) measured on the ISS. Higher K = faster-burning droplet flame.
What it is NOT: a probability of fire, and not a material-safety rating.
Why not use 'Completion' rate in the score: the FLEX tests were designed to hunt extinction limits,
so completion counts depend on test design, not only on hazard. They are shown as context only.
"""
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
f = pd.read_csv(HERE / "data_clean" / "flex_clean.csv")

def diluent(r):
    if r.co2_frac > 0 and r.he_frac > 0: return "CO2+He"
    if r.co2_frac > 0: return "CO2 added"
    if r.he_frac > 0: return "He added"
    return "none (O2/N2 only)"

def o2_level(p):
    if p <= 17: return "O2 12-17%"
    if p <= 20.5: return "O2 18-20%"
    if p <= 22: return "O2 21% (air)"
    return "O2 23-34% (enriched)"          # Moon-base planning is 30%+ ; FLEX has 15 tests at 30% and 9 at 34%

f["diluent"] = f.apply(diluent, axis=1)
f["o2_level"] = f["o2_pct_calc"].map(o2_level)

g = (f.groupby(["fuel", "diluent", "o2_level"])
       .agg(n_tests=("test_no", "size"),
            mean_burn_rate_mm2s=("burn_rate_mm2s", "mean"),
            n_with_burn_rate=("burn_rate_mm2s", "count"),
            extinction_share=("test_end", lambda s: (s == "Extinction").mean()),
            completion_share=("test_end", lambda s: (s == "Completion").mean()),
            disruption_share=("test_end", lambda s: (s == "Disruption").mean()))
       .reset_index())

ok = g[g.n_with_burn_rate >= 5]["mean_burn_rate_mm2s"]       # scale using groups with enough data
lo, hi = ok.min(), ok.max()
g["flame_intensity_index_0_100"] = (100 * (g["mean_burn_rate_mm2s"] - lo) / (hi - lo)).clip(0, 100).round(0)
g["low_data_flag"] = g["n_with_burn_rate"] < 5               # show a warning in the dashboard
g["data_label"] = "REAL ISS data (PSI-69 FLEX), derived index"
g = g.sort_values("flame_intensity_index_0_100", ascending=False)
g.round(3).to_csv(HERE / "data_clean" / "flex_condition_ranking.csv", index=False)

print(g.round(2).to_string(index=False))
print("\nTests used:", len(f), "| tests with burn rate:", int(f.burn_rate_mm2s.notna().sum()))
print("Saved: data_clean/flex_condition_ranking.csv")
