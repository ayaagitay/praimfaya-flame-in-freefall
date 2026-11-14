"""
Flame in Freefall - dashboard skeleton (Person C).
Run:  pip install streamlit pandas plotly pyserial
      streamlit run app.py

Folder layout expected:
  data/            <- Person A drops cleaned CSVs here (e.g. bass2_clean.csv, flex_clean.csv)
  data/ranking.csv <- optional, Person A's ranking output
  advisory.py      <- optional, Person B's module exposing make_advisory(df) -> str

Nothing here assumes column names: you pick columns in the UI until A confirms the real ones.
"""
import json
import os
import re
import sys
import random
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path("psi_data/data_clean")
BASS_FILE = "bassii_clean.csv"
FLEX_FILE = "flex_clean.csv"
RANKING_FILE = "flex_condition_ranking.csv"
# Person B's AI code lives in psi_data/ai_tools.py
sys.path.insert(0, str(Path("psi_data").resolve()))
try:  # online (Streamlit Cloud): key comes from Secrets; locally: from psi_data/.env
    if "GEMINI_API_KEY" in st.secrets:
        os.environ.setdefault("GEMINI_API_KEY", st.secrets["GEMINI_API_KEY"])
except Exception:
    pass  # no secrets file locally: fine, ai_tools reads psi_data/.env
try:
    import ai_tools
    AI_IMPORT_ERROR = None
except Exception as e:
    ai_tools, AI_IMPORT_ERROR = None, e

st.set_page_config(page_title="Flame in Freefall", page_icon="🔥", layout="wide")

# ---------- source labels (every number shows where it came from) ----------
BADGES = {
    "real": ":green[REAL - NASA PSI data]",
    "model": ":orange[MODEL - computed by our risk index]",
    "sim": ":red[SIMULATED - not real data]",
    "sensor": ":blue[LIVE SENSOR - Arduino air temp + light node, not a fire detector]",
    "ai": ":violet[AI-GENERATED from real data rows - verify before use]",
    "template": ":orange[TEMPLATE - sentence built by code from real data rows, no AI]",
}


def badge(kind: str):
    st.caption(BADGES[kind])


# ---------- data loading ----------
@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def load(name: str):
    p = DATA_DIR / name
    return load_csv(str(p)) if p.exists() else None


def num(df, cols):
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def o2_range(col):
    """Slider limits = the oxygen range actually tested (rounded outward to 0.5)."""
    v = col.dropna()
    if v.empty:
        return 0.0, 100.0
    lo, hi = float(v.min()) // 0.5 * 0.5, -(-float(v.max()) // 0.5) * 0.5
    return (lo, hi) if lo < hi else (lo - 0.5, hi + 0.5)


def o2_bin_range(label: str):
    """'O2 12-17%' -> (12, 17). Returns None if the label has no range."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", str(label))
    return (float(m.group(1)), float(m.group(2))) if m else None


# ---------- sensor ----------
@st.cache_resource
def open_serial(port: str):
    # Cached on purpose: opening the port resets the Arduino UNO, so open it ONCE.
    import serial
    return serial.Serial(port, 9600, timeout=3)


def read_sensor_line(ser):
    raw = ser.readline().decode("utf-8", errors="ignore").strip()
    if not raw:
        return None
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return None  # partial line at startup, skip
    if "error" in msg:  # {"error":"dht"}
        return {"error": msg["error"]}
    return msg


# Simulator thresholds are OUR GUESSES until the hardware owner confirms the real ones.
SIM_TEMP_LIMIT = 35.0   # alarm (same as the old node)
SIM_TEMP_WARN = 32.0    # warning: "close to the limit" (guess)
SIM_RISE_WARN = 1.5     # warning: rise in C between two readings (guess)
SIM_LIGHT_LIMIT = 300   # alarm: node is for dark spaces, limit set low (guess)

# Which materials sit near each node. TEAM DECISION / ASSUMPTION, not NASA data.
# Names must match exactly: a "fuel" in flex_clean.csv (e.g. "Heptane") or a
# "material_group_calc" in bassii_clean.csv (e.g. "PMMA film/slab").
NODE_MATERIALS = {"01": []}

LEVEL_STYLE = {"safe": ("🟢", "green"), "warning": ("🟡", "orange"), "alarm": ("🔴", "red")}


def simulated_reading(prev_temp: float):
    temp = max(15.0, min(45.0, prev_temp + random.uniform(-0.8, 1.2)))
    light = random.randint(0, 40) if random.random() > 0.05 else random.randint(300, 700)
    rise = temp - prev_temp
    heat, bright = temp >= SIM_TEMP_LIMIT, light >= SIM_LIGHT_LIMIT
    if heat or bright:
        level = "alarm"
        reason = "both" if heat and bright else "heat" if heat else "light"
    elif rise >= SIM_RISE_WARN or temp >= SIM_TEMP_WARN:
        level, reason = "warning", "rise" if rise >= SIM_RISE_WARN else "heat"
    else:
        level, reason = "safe", "none"
    return {"node": "01", "temp": round(temp, 1), "light": light,
            "hazard": int(level == "alarm"), "level": level, "reason": reason}


def level_of(reading: dict) -> str:
    # Old firmware has no "level": fall back to hazard so both versions work.
    return reading.get("level") or ("alarm" if reading.get("hazard") else "safe")


# ---------- UI ----------
st.title("🔥 Flame in Freefall")
st.write("Real NASA fire experiments from the International Space Station, turned into fire-safety "
         "answers for Moon and Mars missions.")

flex = load(FLEX_FILE)
bass = load(BASS_FILE)
rank = load(RANKING_FILE)
if flex is not None:
    flex = num(flex, ["o2_pct_calc", "burn_rate_mm2s", "pressure_atm_calc", "droplet_d0_mm",
                      "burn_time_s", "suppressant_frac_calc"])
if bass is not None:
    bass = num(bass, ["o2_initial_pct", "o2_drop_pct_calc", "co_rise_ppm_calc", "air_start_cm_s_calc"])

tab_ask, tab_rank, tab_flex, tab_bass, tab_ai, tab_sensor, tab_about = st.tabs(
    ["Ask the data", "Fuel ranking", "FLEX explorer", "BASS-II explorer",
     "AI advisory", "Cabin sensor node", "Sources"]
)

# --- Ask the data: pick fuel/material + oxygen -> answer from real tests ---
with tab_ask:
    kind = st.radio("What is burning?", ["Liquid fuel (FLEX droplets)", "Solid material (BASS-II)"],
                    horizontal=True)

    if kind.startswith("Liquid"):
        if flex is None:
            st.info(f"{FLEX_FILE} not found in {DATA_DIR}.")
        else:
            c1, c2, c3 = st.columns(3)
            fuel = c1.selectbox("Fuel", sorted(flex["fuel"].dropna().unique()))
            lo, hi = o2_range(flex[flex["fuel"] == fuel]["o2_pct_calc"])
            o2 = c2.slider("Oxygen (%)", lo, hi, min(max(21.0, lo), hi), 0.5, key=f"o2_{fuel}")
            st.caption(f"{fuel} was tested on the ISS between {lo:.1f}% and {hi:.1f}% O2 "
                       "(Earth air is about 21%).")
            tol = c3.slider("Match tests within ± (% O2)", 1.0, 10.0, 3.0, 0.5)
            st.session_state["ask_fuel"] = fuel
            hit = flex[(flex["fuel"] == fuel) & (flex["o2_pct_calc"].sub(o2).abs() <= tol)]
            st.session_state["selected_rows"] = hit
            badge("real")
            if hit.empty:
                st.warning(f"No ISS tests of {fuel} near {o2:.1f}% O2. Widen the ± range. "
                           "We do not guess outside the tested conditions.")
            else:
                n = len(hit)
                br = hit["burn_rate_mm2s"].mean()
                ends = hit["test_end"].value_counts(normalize=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Matching ISS tests", n)
                m2.metric("Mean burning rate K (mm²/s)", f"{br:.2f}" if pd.notna(br) else "n/a")
                m3.metric("Ended in extinction", f"{ends.get('Extinction', 0):.0%}")
                if n < 3:
                    st.warning("Fewer than 3 matching tests: treat this answer as weak evidence.")
                ends_txt = ", ".join(f"{k} {v:.0%}" for k, v in ends.items())
                st.markdown(
                    f"**Answer:** In {n} ISS tests of **{fuel}** at {o2 - tol:.1f}-{o2 + tol:.1f}% O2, "
                    f"the mean burning-rate constant was **{br:.2f} mm²/s**. How the tests ended: {ends_txt}."
                )
                if rank is not None:
                    rows = rank[rank["fuel"] == fuel]
                    rows = rows[rows["o2_level"].map(
                        lambda s: (r := o2_bin_range(s)) is not None and r[0] <= o2 <= r[1])]
                    if not rows.empty:
                        st.write("Matching rows in the fuel ranking:")
                        badge("model")
                        st.dataframe(rows, width="stretch", hide_index=True)
                with st.expander("Show the matching tests"):
                    st.dataframe(hit[["test_id", "fuel", "o2_pct_calc", "pressure_atm_calc",
                                      "suppressant_frac_calc", "droplet_d0_mm", "burn_rate_mm2s",
                                      "test_end", "source"]], width="stretch", hide_index=True)
                st.caption("Pressure and diluent gases also differ between tests; see the table above.")

    else:
        if bass is None:
            st.info(f"{BASS_FILE} not found in {DATA_DIR}.")
        else:
            c1, c2, c3 = st.columns(3)
            mat = c1.selectbox("Material", sorted(bass["material_group_calc"].dropna().unique()))
            lo, hi = o2_range(bass[bass["material_group_calc"] == mat]["o2_initial_pct"])
            o2 = c2.slider("Oxygen (%)", lo, hi, min(max(21.0, lo), hi), 0.5, key=f"o2b_{mat}")
            st.caption(f"{mat} was tested on the ISS between {lo:.1f}% and {hi:.1f}% O2 at the start of a test "
                       "(Earth air is about 21%).")
            tol = c3.slider("Match tests within ± (% O2)", 1.0, 10.0, 3.0, 0.5, key="tolb")
            hit = bass[(bass["material_group_calc"] == mat) & (bass["o2_initial_pct"].sub(o2).abs() <= tol)]
            st.session_state["selected_rows"] = hit
            badge("real")
            st.info("BASS-II did not record flame-spread speed, so there is no burn-rate answer for solids. "
                    "It shows what the chamber gas did during the tests.")
            if hit.empty:
                st.warning(f"No ISS tests of {mat} near {o2:.1f}% O2. Widen the ± range.")
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric("Matching ISS tests", len(hit))
                m2.metric("Mean O2 drop (% points)", f"{hit['o2_drop_pct_calc'].mean():.2f}")
                m3.metric("Mean CO rise (ppm)", f"{hit['co_rise_ppm_calc'].mean():.1f}")
                st.caption("O2 drop and CO rise are calculated from start/end chamber readings. "
                           "They may also depend on how long and how many samples burned, so compare with care.")
                with st.expander("Show the matching tests"):
                    st.dataframe(hit[["test_no", "material_raw", "o2_initial_pct", "air_start_cm_s_calc",
                                      "o2_drop_pct_calc", "co_rise_ppm_calc", "source"]],
                                 width="stretch", hide_index=True)

# --- Fuel ranking (A's derived index) ---
with tab_rank:
    if rank is None:
        st.info(f"Waiting for {RANKING_FILE} from Person A.")
    else:
        badge("model")
        st.write("Fuel + atmosphere conditions from FLEX, ranked by flame intensity index (0-100). "
                 "Built from real ISS tests; the index itself is our calculation.")
        dil = st.multiselect("Diluent", sorted(rank["diluent"].dropna().unique()),
                             default=sorted(rank["diluent"].dropna().unique()))
        r = rank[rank["diluent"].isin(dil)].copy()
        r["condition"] = (r["fuel"] + " | " + r["diluent"] + " | " + r["o2_level"]
                          + r["low_data_flag"].map(lambda f: "  ⚠ few tests" if str(f) == "True" else ""))
        r = r.sort_values("flame_intensity_index_0_100")
        fig = px.bar(r, x="flame_intensity_index_0_100", y="condition", color="fuel", orientation="h",
                     hover_data=["n_tests", "mean_burn_rate_mm2s", "extinction_share", "completion_share"],
                     labels={"flame_intensity_index_0_100": "Flame intensity index (0-100, higher = more intense)",
                             "condition": ""})
        fig.update_layout(height=max(400, 28 * len(r)))
        st.plotly_chart(fig, width="stretch")
        st.caption("How the index is calculated: (Person A: paste the formula here). "
                   "⚠ = few tests behind this row (low_data_flag).")
        with st.expander("Full ranking table"):
            st.dataframe(rank, width="stretch", hide_index=True)

# --- FLEX explorer ---
with tab_flex:
    if flex is not None:
        badge("real")
        st.write(f"{len(flex)} droplet-burning tests on the ISS (FLEX, PSI-69).")
        fuels = st.multiselect("Fuels", sorted(flex["fuel"].dropna().unique()),
                               default=sorted(flex["fuel"].dropna().unique()))
        f = flex[flex["fuel"].isin(fuels)]
        st.plotly_chart(px.scatter(
            f, x="o2_pct_calc", y="burn_rate_mm2s", color="fuel", symbol="test_end",
            hover_data=["test_id", "pressure_atm_calc", "droplet_d0_mm"],
            labels={"o2_pct_calc": "Oxygen (%)", "burn_rate_mm2s": "Burning rate K (mm²/s)",
                    "test_end": "Outcome"},
            title="Burning rate vs oxygen"), width="stretch")
        st.plotly_chart(px.histogram(
            f, x="fuel", color="test_end", barmode="group",
            labels={"test_end": "Outcome", "fuel": "Fuel"}, title="How tests ended, by fuel"),
            width="stretch")
        with st.expander("Raw table"):
            st.dataframe(f, width="stretch", hide_index=True)

# --- BASS-II explorer ---
with tab_bass:
    if bass is not None:
        badge("real")
        st.write(f"{len(bass)} solid-material burning tests on the ISS (BASS-II, PSI-25). "
                 "No flame-spread speed was recorded in this table.")
        st.plotly_chart(px.histogram(
            bass, x="material_group_calc", labels={"material_group_calc": "Material"},
            title="Number of tests per material"), width="stretch")
        st.plotly_chart(px.scatter(
            bass, x="air_start_cm_s_calc", y="o2_drop_pct_calc", color="material_group_calc",
            hover_data=["test_no", "material_raw", "o2_initial_pct"],
            labels={"air_start_cm_s_calc": "Air speed at start (cm/s)",
                    "o2_drop_pct_calc": "O2 drop (% points)", "material_group_calc": "Material"},
            title="Chamber O2 drop vs air speed"), width="stretch")
        with st.expander("Raw table"):
            st.dataframe(bass, width="stretch", hide_index=True)

# --- AI advisory (Person B: psi_data/ai_tools.py) ---
with tab_ai:
    if ai_tools is None:
        st.warning(f"Could not load psi_data/ai_tools.py: {AI_IMPORT_ERROR}")
    elif rank is None:
        st.info(f"{RANKING_FILE} not found.")
    else:
        st.write("Pick a FLEX test condition. The advisory uses **only** the matching ranking rows below.")

        def pick(col, label, prefer=None):
            opts = ["Any"] + sorted(rank[col].dropna().unique())
            idx = opts.index(prefer) if prefer in opts else 0
            v = st.selectbox(label, opts, index=idx, key=f"ai_{col}")
            return None if v == "Any" else v

        c1, c2, c3 = st.columns(3)
        with c1:
            a_fuel = pick("fuel", "Fuel", st.session_state.get("ask_fuel"))
        with c2:
            a_dil = pick("diluent", "Added gas")
        with c3:
            a_o2 = pick("o2_level", "Oxygen level")
        rows = ai_tools.select_rows(rank, fuel=a_fuel, diluent=a_dil, o2_level=a_o2, top_n=3)
        badge("model")
        st.dataframe(rows, width="stretch", hide_index=True)

        use_ai = st.toggle("Use AI (Gemini)", value=True,
                           help="Off = a fixed sentence built from the rows, no AI.")
        if st.button("Generate mission safety advisory", disabled=rows.empty):
            with st.spinner("Writing advisory..."):
                result = ai_tools.advisory(rows, use_ai=use_ai)
            badge("ai" if result["mode"] == "ai" else "template")
            st.success(result["text"])
            st.caption(result["note"])

# --- Sensor node ---
with tab_sensor:
    st.write("Always-on watchdog node (concept prototype): air temperature and light only. **It does not detect fire or short circuits.**")
    mode = st.radio("Source", ["Simulated", "Live USB"], horizontal=True)
    port = st.text_input("Serial port", "COM3") if mode == "Live USB" else None
    live = st.toggle("Run")
    hist = st.session_state.setdefault("sensor_hist", [])

    if live:
        if mode == "Simulated":
            prev = hist[-1]["temp"] if hist else 24.0
            reading = simulated_reading(prev)
        else:
            try:
                reading = read_sensor_line(open_serial(port))
            except Exception as e:
                st.error(f"Serial error: {e}")
                reading = None
        if reading and "error" in reading:
            st.warning("DHT11 read failed, skipping this reading.")
        elif reading:
            reading["t"] = time.strftime("%H:%M:%S")
            reading["source"] = "sim" if mode == "Simulated" else "sensor"
            hist.append(reading)
            del hist[:-100]

    badge("sim" if mode == "Simulated" else "sensor")
    if hist:
        last = hist[-1]
        lvl = level_of(last)
        icon, color = LEVEL_STYLE.get(lvl, ("⚪", "gray"))
        st.markdown(f"### {icon} Node {last.get('node', '?')}: :{color}[{lvl.upper()}]"
                    f" (reason: {last.get('reason', 'n/a')})")
        m1, m2 = st.columns(2)
        m1.metric("Air temp (C)", last["temp"])
        m2.metric("Light (0-1023)", last["light"])

        # Event -> NASA insight (the sensor calls up the data, never the reverse)
        if lvl in ("warning", "alarm"):
            st.warning(f"{lvl.upper()} at node {last.get('node', '?')} ({last['t']}), reason: {last.get('reason')}")
            mats = NODE_MATERIALS.get(last.get("node", ""), [])
            if not mats:
                st.caption("No materials assigned to this node yet (NODE_MATERIALS in app.py).")
            else:
                st.write(f"NASA data for materials near this node: {', '.join(mats)}")
                if rank is not None and rank["fuel"].isin(mats).any():
                    badge("model")
                    st.dataframe(rank[rank["fuel"].isin(mats)].sort_values(
                        "flame_intensity_index_0_100", ascending=False),
                        width="stretch", hide_index=True)
                if bass is not None and bass["material_group_calc"].isin(mats).any():
                    badge("real")
                    st.dataframe(bass[bass["material_group_calc"].isin(mats)][
                        ["test_no", "material_raw", "o2_initial_pct", "o2_drop_pct_calc", "co_rise_ppm_calc"]],
                        width="stretch", hide_index=True)

        hdf = pd.DataFrame(hist)
        st.line_chart(hdf.set_index("t")[["temp"]])
        st.line_chart(hdf.set_index("t")[["light"]])
        events = [h for h in hist if level_of(h) != "safe"]
        if events:
            with st.expander(f"Event log ({len(events)})"):
                st.dataframe(pd.DataFrame(events)[::-1], width="stretch")

    if live:
        time.sleep(2)  # matches the Arduino's 2000 ms interval
        st.rerun()

# --- Sources ---
with tab_about:
    st.markdown(
        """
**Data**
- FLEX (Flame Extinguishment Experiment), NASA PSI-69, DOI 10.60555/mbq8-0451 - `flex_clean.csv`
- BASS-II (Burning and Suppression of Solids II), NASA PSI-25, DOI 10.60555/4qc4-de67 - `bassii_clean.csv`
- Downloaded from the NASA Physical Sciences Informatics (PSI) repository, cleaned by our team (`clean_data.py`)

**Background**
- *A Researcher's Guide to: Combustion Science*, NASA ISS Program Science Office, Oct 2015
- NASA Technical Reports Server (NTRS) papers used for AI summaries

**Labels used on every page**
- REAL = NASA flight data, MODEL = our calculation (ranking index), SIMULATED = generated test data,
  LIVE SENSOR = our Arduino node (air temperature + light only), AI = LLM-written text
"""
    )