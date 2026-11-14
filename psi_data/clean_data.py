"""
Loads the two REAL PSI tables and writes clean copies.
Run from the folder that contains the 'nasa' folder:   python clean_data.py
Needs:  pip install pandas
Nothing here is invented: every output column comes from a real column
(or a simple calculation from it, named *_calc).
"""
import re
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE if (HERE / "PSI-25").exists() else HERE / "nasa"
OUT = HERE / "data_clean"; OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- FLEX (PSI-69)
f = pd.read_csv(RAW / "PSI-69" / "PSI-69_Experimental table_FLEX.csv", encoding="latin-1")
f = f.rename(columns={
    "FLEX Test #": "test_no", "FLEX Identifier": "test_id", "Test Date": "date",
    "Test GMT": "gmt_time", "Fuel": "fuel",
    "Ambient pressure; mmHg": "pressure_mmhg",
    "O initial ambient composition; mole fraction": "o2_frac",
    "N initial ambient composition; mole fraction": "n2_frac",
    "CO initial ambient composition; mole fraction": "co2_frac",   # header says CO, but test sheet FLEX-131 shows this value as CO2 (matched on that 1 row)
    "He initial ambient composition; mole fraction": "he_frac",
    "Droplet initial diameter; mm": "droplet_d0_mm",
    "Visible flame extinction diameter; mm": "ext_diameter_mm",
    "Burning rate; mm": "burn_rate_mm2s",   # header says mm; test sheet FLEX-131 shows the same 0.61 as kavg in mm^2/s (matched on that 1 row)
    "Burn time; s": "burn_time_raw", "Test end": "test_end",
})
f["date"] = pd.to_datetime(f["date"], format="%m/%d/%Y", errors="coerce")
f["burn_time_is_approx"] = f["burn_time_raw"].astype(str).str.contains("~")
f["burn_time_s"] = pd.to_numeric(f["burn_time_raw"].astype(str).str.replace("~", "", regex=False), errors="coerce")
for c in ["droplet_d0_mm", "ext_diameter_mm"]:
    f[c] = pd.to_numeric(f[c], errors="coerce")
f["pressure_mmhg_is_zero"] = f["pressure_mmhg"] == 0                 # 0 is almost surely 'missing'
f.loc[f["pressure_mmhg"] == 0, "pressure_mmhg"] = np.nan
f["pressure_atm_calc"] = f["pressure_mmhg"] / 760.0                   # 760 mmHg = 1 atm
f["o2_pct_calc"] = f["o2_frac"] * 100
f["suppressant_frac_calc"] = f["co2_frac"] + f["he_frac"]         # diluent that is neither O2 nor N2
f["burned_to_completion"] = f["test_end"].eq("Completion")
# NOTE: ext_diameter_mm == 0 appears on 8 tests (4 Completion, 4 Disruption). Meaning not confirmed; kept as 0, not treated as missing.
# NOTE: one test_id repeats, so use test_no as the unique key.
f["source"] = "PSI-69 FLEX (real flight data)"
f.to_csv(OUT / "flex_clean.csv", index=False)

# ---------------------------------------------------------------- BASS-II (PSI-25)
b = pd.read_csv(RAW / "PSI-25" / "PSI-25_Experimental table_BASS-II.csv")
b.columns = [re.sub(r"\s+", " ", c).strip() for c in b.columns]       # fix messy header spaces
b = b.rename(columns={
    "PI": "pi", "Test #": "test_no", "Date": "date", "GMT": "gmt_day_of_year",
    "Sample #": "sample_no", "Fuel Sample Material": "material_raw",
    "Flow restrictor": "flow_restrictor",
    "Fan display": "fan_display_raw", "Air display": "air_display_raw",
    "Radiometer gain (1000 250 50 10)": "radiometer_gain",
    "Total Frames Shot": "frames_raw",
    "Calibrated initial O2 % by vol": "o2_initial_pct",
    "Calibrated final O2 % by vol": "o2_final_raw",
    "Initial CO2 % by vol": "co2_initial_raw", "Final CO2 % by vol": "co2_final_raw",
    "Initial CO (ppm)": "co_initial_raw", "Final CO (ppm)": "co_final_raw",
})
b["date"] = pd.to_datetime(b["date"], format="%m/%d/%Y", errors="coerce")
for raw, new in [("o2_final_raw", "o2_final_pct"), ("co2_initial_raw", "co2_initial_pct"),
                 ("co2_final_raw", "co2_final_pct"), ("co_initial_raw", "co_initial_ppm"),
                 ("co_final_raw", "co_final_ppm"), ("frames_raw", "frames")]:
    b[new] = pd.to_numeric(b[raw], errors="coerce")                   # 'none','OR','over','>500' -> NaN
b["co_final_over_range"] = b["co_final_raw"].astype(str).str.strip().isin([">500", "over", "OR"])
b["co_rise_ppm_calc"] = b["co_final_ppm"] - b["co_initial_ppm"]       # proxy for 'something burned'
b["o2_drop_pct_calc"] = b["o2_initial_pct"] - b["o2_final_pct"]

def group(m):
    s = str(m).lower()
    if "sibal" in s: return "SIBAL fabric"
    if "nomex" in s: return "Nomex fabric"
    if "wax" in s or "candle" in s: return "Wax candle"
    if "spherical" in s: return "Spherical section"
    if "rod" in s: return "PMMA rod (black/clear)"   # BASS-II report: rods are cast PMMA, black or clear
    if any(k in s for k in ["pmma", "micron", "film", "mm", "slab"]): return "PMMA film/slab"
    return "Other"
b["material_group_calc"] = b["material_raw"].map(group)
b["rod_color_calc"] = np.where(b["material_raw"].str.lower().str.contains("rod") & b["material_raw"].str.lower().str.contains("bla"), "black",
                      np.where(b["material_raw"].str.lower().str.contains("rod") & b["material_raw"].str.lower().str.contains("clear"), "clear", ""))
# 'Air display' = air-velocity transducer reading in cm/s (BASS-II report, TM-20210011385). Resolution +-0.5 cm/s, ~1 min response.
# Many tests step the flow down, so the cell holds several numbers. We keep the FIRST one as the STARTING reading only.
def first_air(v):
    t = str(v).strip().lower()
    if t in ("", "nan") or t.startswith("pot") or "see notes" in t: return np.nan
    m = re.search(r"\d+(?:\.\d+)?", t)
    return float(m.group()) if m else np.nan
b["air_start_cm_s_calc"] = b["air_display_raw"].map(first_air)
b["air_multi_step"] = b["air_display_raw"].astype(str).str.count(r"\d+(?:\.\d+)?") > 1
b["source"] = "PSI-25 BASS-II (real flight data)"
b.to_csv(OUT / "bassii_clean.csv", index=False)

# ---------------------------------------------------------------- quick report
print("FLEX  rows:", len(f), "| BASS-II rows:", len(b))
print("\nFLEX columns:", list(f.columns))
print("\nBASS-II columns:", list(b.columns))
print("\nFLEX fuel:\n", f["fuel"].value_counts().to_string())
print("\nFLEX test_end:\n", f["test_end"].value_counts().to_string())
print("\nFLEX pressure==0 rows:", int(f["pressure_mmhg_is_zero"].sum()))
print("FLEX burn_rate nulls:", int(f["burn_rate_mm2s"].isna().sum()))
print("\nBASS-II material groups:\n", b["material_group_calc"].value_counts().to_string())
print("\nBASS-II o2_initial_pct range:", b["o2_initial_pct"].min(), "-", b["o2_initial_pct"].max())
print("BASS-II air_start parsed:", int(b["air_start_cm_s_calc"].notna().sum()), "of", len(b), "| multi-step rows:", int(b["air_multi_step"].sum()))
print("BASS-II air_start range:", b["air_start_cm_s_calc"].min(), "-", b["air_start_cm_s_calc"].max())
print("BASS-II rod colors:", b["rod_color_calc"].value_counts().to_dict())
print("BASS-II co_final over range:", int(b["co_final_over_range"].sum()))
print("\nSaved to", OUT.resolve())
