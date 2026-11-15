"""
Flame in Freefall - dashboard (Team Praimfaya).
Run:  python -m pip install -r requirements.txt
      python -m streamlit run app.py
Data: psi_data/data_clean/*.csv   AI: psi_data/ai_tools.py   Style: theme.py
"""
import json
import os
import re
import collections
import sys
import random
import threading
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import theme

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
theme.apply_theme()

# ---------- source labels (every number shows where it came from) ----------
BADGES = {
    "real": "Real · NASA PSI flight data",
    "model": "Model · our calculation from real data",
    "sim": "Simulated · not real data",
    "sensor": "Live sensor · air temp + light, not a fire detector",
    "ai": "AI-generated from real data rows · verify before use",
    "template": "Template · built by code from real data rows, no AI",
}


def badge(kind: str):
    theme.source_pill(kind, BADGES[kind])


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
class SerialReader:
    """Reads the Arduino in a background thread, all the time, so no line ever waits on the port.
    Each line is time-stamped the moment it arrives."""

    def __init__(self, port: str):
        import serial
        self.ser = serial.Serial(port, 9600, timeout=1)
        self.queue = collections.deque(maxlen=300)
        self.error = None
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            try:
                raw = self.ser.readline().decode("utf-8", errors="ignore").strip()
            except Exception as e:      # cable unplugged, port closed...
                self.error = e
                return
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue                # partial line at startup, skip
            if isinstance(msg, dict):
                msg["t"] = time.strftime("%H:%M:%S")
                self.queue.append(msg)

    def drain(self):
        out = []
        while self.queue:
            out.append(self.queue.popleft())
        return out


@st.cache_resource
def open_serial(port: str):
    # Cached on purpose: opening the port resets the Arduino UNO, so open it ONCE.
    return SerialReader(port)


# Simulator thresholds = the real node's values (hardware/.ino):
SIM_TEMP_LIMIT = 35.0   # alarm at or above (C)
SIM_TEMP_WARN = 32.0    # warning at or above (C)
SIM_RISE_WARN = 2.0     # warning if temp rose this much vs. 5 readings (~10 s) ago
SIM_LIGHT_LIMIT = 800   # alarm at or above (0-1023, higher = brighter)
SIM_HISTORY = 5

# Which materials sit near each node. TEAM DECISION / ASSUMPTION, not NASA data.
# Names must match exactly: a "fuel" in flex_clean.csv (e.g. "Heptane") or a
# "material_group_calc" in bassii_clean.csv (e.g. "PMMA film/slab").
NODE_MATERIALS = {"01": []}

LEVEL_STYLE = {"safe": ("🟢", "green"), "warning": ("🟡", "orange"), "alarm": ("🔴", "red")}


def simulated_reading(hist: list):
    """Same rules as the Arduino sketch, on made-up numbers."""
    prev = hist[-1]["temp"] if hist else 24.0
    # Hovers around 25 C; now and then a short heat event pushes it up.
    event = st.session_state.get("sim_event", 0)
    if event == 0 and random.random() < 0.03:
        event = random.randint(4, 8)  # readings of heating
    st.session_state["sim_event"] = max(0, event - 1)
    drift = random.uniform(1.0, 2.5) if event else 0.2 * (25.0 - prev)
    temp = round(max(15.0, min(45.0, prev + drift + random.uniform(-0.3, 0.3))), 1)
    light = random.randint(150, 500) if random.random() > 0.05 else random.randint(820, 950)
    past = [h["temp"] for h in hist if "temp" in h][-SIM_HISTORY:]
    rise = temp - past[0] if len(past) == SIM_HISTORY else 0.0
    heat, bright = temp >= SIM_TEMP_LIMIT, light >= SIM_LIGHT_LIMIT
    if heat or bright:
        level = "alarm"
        reason = "both" if heat and bright else "heat" if heat else "light"
    elif rise >= SIM_RISE_WARN:
        level, reason = "warning", "rise"
    elif temp >= SIM_TEMP_WARN:
        level, reason = "warning", "heat"
    else:
        level, reason = "safe", "none"
    return {"node": "01", "temp": temp, "light": light,
            "hazard": int(level == "alarm"), "level": level, "reason": reason}


def sensor_chart(hdf, col, title, color, limits):
    """Line + soft fill, with the node's limits drawn as dashed lines."""
    fig = go.Figure(go.Scatter(x=hdf["t"], y=hdf[col], mode="lines", line=dict(color=color, width=2.5),
                               fill="tozeroy", fillcolor="rgba(255,255,255,0.03)", name=col))
    for y, lvl in limits:
        fig.add_hline(y=y, line=dict(color=theme.LEVEL_COLORS[lvl], dash="dash", width=1),
                      annotation_text=f"{lvl} {y:g}", annotation_font_color=theme.LEVEL_COLORS[lvl])
    fig.update_layout(title=title, height=280, showlegend=False)
    return fig


def level_of(reading: dict) -> str:
    # Old firmware has no "level": fall back to hazard so both versions work.
    return reading.get("level") or ("alarm" if reading.get("hazard") else "safe")


# ---------- UI ----------
flex = load(FLEX_FILE)
bass = load(BASS_FILE)
rank = load(RANKING_FILE)
if flex is not None:
    flex = num(flex, ["o2_pct_calc", "burn_rate_mm2s", "pressure_atm_calc", "droplet_d0_mm",
                      "burn_time_s", "suppressant_frac_calc"])
if bass is not None:
    bass = num(bass, ["o2_initial_pct", "o2_drop_pct_calc", "co_rise_ppm_calc", "air_start_cm_s_calc"])

theme.topbar("PRAIMFAYA", "NASA Space Apps 2026 · Tashkent")
theme.hero(
    pill="NASA PSI · ISS combustion data",
    kicker="Mission: fire safety beyond Earth",
    title="Flame in<br>Freefall",
    lead="Real fire experiments from the International Space Station, ranked and explained "
         "to inform fire safety for Moon and Mars missions.",
    stats=[
        ("FLEX droplet tests", len(flex) if flex is not None else "-"),
        ("BASS-II solid tests", len(bass) if bass is not None else "-"),
        ("Fuels tested", flex["fuel"].nunique() if flex is not None else "-"),
        ("Ranked conditions", len(rank) if rank is not None else "-"),
    ],
)

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
        dil = st.multiselect("Added gas (diluent)", sorted(rank["diluent"].dropna().unique()),
                             default=sorted(rank["diluent"].dropna().unique()))
        r = rank[rank["diluent"].isin(dil)].copy()
        r["condition"] = (r["fuel"] + " | " + r["diluent"] + " | " + r["o2_level"]
                          + r["low_data_flag"].map(lambda f: "  ⚠ few tests" if str(f) == "True" else ""))
        r = r.sort_values("flame_intensity_index_0_100")
        fig = px.bar(r, x="flame_intensity_index_0_100", y="condition", orientation="h",
                     color="flame_intensity_index_0_100", color_continuous_scale=theme.THERMAL,
                     range_color=[0, 100],
                     hover_data=["n_tests", "mean_burn_rate_mm2s", "extinction_share", "completion_share"],
                     labels={"flame_intensity_index_0_100": "Flame intensity index (0-100, higher = more intense)",
                             "condition": ""})
        fig.update_layout(height=max(400, 30 * len(r)), margin=dict(r=70),
                          coloraxis_colorbar=dict(title="Index", thickness=12))
        theme.chart(fig)
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
        theme.chart(px.scatter(
            f, x="o2_pct_calc", y="burn_rate_mm2s", color="fuel", symbol="test_end",
            hover_data=["test_id", "pressure_atm_calc", "droplet_d0_mm"],
            labels={"o2_pct_calc": "Oxygen (%)", "burn_rate_mm2s": "Burning rate K (mm²/s)",
                    "test_end": "Outcome", "fuel": "Fuel"},
            title="Burning rate vs oxygen"))
        fig = px.histogram(
            f, x="fuel", color="test_end", barmode="group",
            color_discrete_map=theme.OUTCOME_COLORS,
            category_orders={"test_end": list(theme.OUTCOME_COLORS)},
            labels={"test_end": "Outcome", "fuel": "Fuel"}, title="How tests ended, by fuel")
        fig.update_traces(marker_line_width=0, opacity=0.92)
        fig.update_layout(bargap=0.28, bargroupgap=0.06, yaxis_title="Number of tests")
        theme.chart(fig)
        with st.expander("Raw table"):
            st.dataframe(f, width="stretch", hide_index=True)

# --- BASS-II explorer ---
with tab_bass:
    if bass is not None:
        badge("real")
        st.write(f"{len(bass)} solid-material burning tests on the ISS (BASS-II, PSI-25). "
                 "No flame-spread speed was recorded in this table.")
        counts = (bass["material_group_calc"].value_counts()
                  .rename_axis("Material").reset_index(name="Tests"))
        fig = px.bar(counts, x="Material", y="Tests", color="Tests",
                     color_continuous_scale=theme.RED_RAMP, title="Number of tests per material")
        fig.update_traces(marker_line_width=0)
        fig.update_layout(coloraxis_showscale=False, bargap=0.35)
        theme.chart(fig)
        theme.chart(px.scatter(
            bass, x="air_start_cm_s_calc", y="o2_drop_pct_calc", color="material_group_calc",
            hover_data=["test_no", "material_raw", "o2_initial_pct"],
            labels={"air_start_cm_s_calc": "Air speed at start (cm/s)",
                    "o2_drop_pct_calc": "O2 drop (% points)", "material_group_calc": "Material"},
            title="Chamber O2 drop vs air speed"))
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
    port = st.text_input("Serial port", "COM6") if mode == "Live USB" else None
    live = st.toggle("Run")
    hist = st.session_state.setdefault("sensor_hist", [])

    # Only this panel refreshes (not the whole page): every 0.3 s for the live node, every 2 s simulated.
    every = (2.0 if mode == "Simulated" else 0.3) if live else None

    @st.fragment(run_every=every)
    def sensor_panel():
        if live:
            if mode == "Simulated":
                readings = [simulated_reading(hist)]
            else:
                try:
                    reader = open_serial(port)
                    readings = reader.drain()
                    if reader.error:
                        st.error(f"Lost the sensor: {reader.error}. Check the cable, then switch Run off and on.")
                        open_serial.clear()
                except Exception as e:
                    st.error(f"Serial error: {e}")
                    readings = []
            for reading in readings:
                if "error" in reading:
                    st.warning("DHT11 read failed, skipping this reading.")
                    continue
                reading.setdefault("t", time.strftime("%H:%M:%S"))
                reading["source"] = "sim" if mode == "Simulated" else "sensor"
                hist.append(reading)
            del hist[:-100]

        badge("sim" if mode == "Simulated" else "sensor")
        if hist:
            last = hist[-1]
            lvl = level_of(last)
            theme.status_panel(lvl, last["temp"], last["light"], last.get("node", "?"),
                               last.get("reason", "n/a"), last["t"])

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
            c1, c2 = st.columns(2)
            with c1:
                theme.chart(sensor_chart(hdf, "temp", "Air temperature (C)", theme.THERMAL[4],
                                         [(SIM_TEMP_WARN, "warning"), (SIM_TEMP_LIMIT, "alarm")]))
            with c2:
                theme.chart(sensor_chart(hdf, "light", "Light (0-1023)", theme.THERMAL[2],
                                         [(SIM_LIGHT_LIMIT, "alarm")]))
            events = [h for h in hist if level_of(h) != "safe"]
            if events:
                with st.expander(f"Event log ({len(events)})"):
                    st.dataframe(pd.DataFrame(events)[::-1], width="stretch")


    sensor_panel()

# --- Sources ---
with tab_about:
    st.markdown(
        """
**Data**
- FLEX (Flame Extinguishment Experiment), NASA PSI-69,
  [DOI 10.60555/mbq8-0451](https://doi.org/10.60555/mbq8-0451) - `flex_clean.csv`
- BASS-II (Burning and Suppression of Solids II), NASA PSI-25,
  [DOI 10.60555/4qc4-de67](https://doi.org/10.60555/4qc4-de67) - `bassii_clean.csv`
- Downloaded from the [NASA Physical Sciences Informatics (PSI) repository](https://science.nasa.gov/biological-physical/data),
  cleaned by our team (`clean_data.py`)

**AI**
- Advisory text: Google Gemini (`gemini-3.5-flash-lite`), given only the selected ranking rows.
  Text with a number that is not in the data is rejected and a template sentence is used instead.

**Sensor**
- Our own Arduino UNO node (DHT11 temperature sensor + light sensor). Concept prototype, not a fire detector.

**Project**
- Code: [github.com/ayaagitay/praimfaya-flame-in-freefall](https://github.com/ayaagitay/praimfaya-flame-in-freefall)

**Labels used on every page**
- REAL = NASA flight data, MODEL = our calculation (ranking index), SIMULATED = generated test data,
  LIVE SENSOR = our Arduino node (air temperature + light only), AI-GENERATED = LLM-written text,
  TEMPLATE = sentence built by our code from real data rows
"""
    )