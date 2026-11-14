"""
Visual style for the Flame in Freefall dashboard (Person C).
Look: dark space UI, thermal-camera colours (cool blue -> hot red), glass cards,
wide uppercase headings, and an animated spherical flame (microgravity flames are spherical).
Change the colours in the :root block or in the lists below.
"""
import math
import random

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Thermal scale, cool -> hot. Used where "more = hotter/more intense".
THERMAL = ["#1B1464", "#3A3AFF", "#1FB6FF", "#FFD23F", "#FF8A2B", "#FF3B2F"]
# Distinct colours for categories (fuels, materials, outcomes).
CATEGORICAL = ["#FF5A36", "#FFC83D", "#2EC5FF", "#8B7BFF", "#3DDC97", "#FF4FA3", "#FF8A2B", "#B9C2D0"]
# Warm red ramp (deep crimson -> red -> coral -> amber) for charts that should feel like one family.
RED_RAMP = ["#6E1426", "#97192F", "#BE2436", "#E0353B", "#F5503F", "#FF6B4F"]
OUTCOME_COLORS = {"Disruption": "#9E1F33", "Extinction": "#E3443A", "Completion": "#FF8F57"}
LEVEL_COLORS = {"safe": "#3DDC97", "warning": "#FFC83D", "alarm": "#FF3B2F"}
BADGE_COLORS = {"real": "#3DDC97", "model": "#FF8A2B", "sim": "#FF4FA3", "sensor": "#2EC5FF",
                "ai": "#8B7BFF", "template": "#FFC83D"}

_TEX1 = "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='240'><filter id='n' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' baseFrequency='0.011 0.045' numOctaves='5' seed='7' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/><feComponentTransfer><feFuncR type='linear' slope='2.2' intercept='-0.6'/><feFuncG type='linear' slope='2.2' intercept='-0.6'/><feFuncB type='linear' slope='2.2' intercept='-0.6'/><feFuncA type='linear' slope='0' intercept='1'/></feComponentTransfer></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\")"
_TEX2 = "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='1100' height='420'><filter id='n' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' baseFrequency='0.005 0.022' numOctaves='5' seed='21' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/><feComponentTransfer><feFuncR type='linear' slope='2.2' intercept='-0.6'/><feFuncG type='linear' slope='2.2' intercept='-0.6'/><feFuncB type='linear' slope='2.2' intercept='-0.6'/><feFuncA type='linear' slope='0' intercept='1'/></feComponentTransfer></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\")"

_ROCK = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='900' height='600'>"
         "<filter id='r' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' "
         "baseFrequency='0.0035 0.055' numOctaves='4' seed='11' stitchTiles='stitch'/>"
         "<feColorMatrix type='saturate' values='0'/><feComponentTransfer>"
         "<feFuncR type='linear' slope='3' intercept='-1'/><feFuncG type='linear' slope='3' intercept='-1'/>"
         "<feFuncB type='linear' slope='3' intercept='-1'/><feFuncA type='linear' slope='0' intercept='1'/>"
         "</feComponentTransfer></filter><rect width='100%' height='100%' filter='url(%23r)'/></svg>\")")

_GRAIN = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'>"
          "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/>"
          "</filter><rect width='100%' height='100%' filter='url(%23n)' opacity='.55'/></svg>\")")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Michroma&family=Inter:wght@300;400;500;600&display=swap');
:root {
  --bg: #07080D; --panel: rgba(255,255,255,0.035); --line: rgba(255,255,255,0.09);
  --text: #E9ECF2; --muted: #8B93A7; --hot: #FF5A36; --amber: #FFC83D; --cool: #2EC5FF;
}
.stApp {
  background:
    radial-gradient(1100px 560px at 88% -12%, rgba(255,90,54,.11), transparent 60%),
    radial-gradient(900px 520px at -12% 112%, rgba(58,58,255,.12), transparent 60%),
    var(--bg);
  font-family: 'Inter', sans-serif;
}
.stApp::before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image: GRAIN; opacity: .045;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stStatusWidget"] { display: none !important; }   /* hides the running icon + Stop */
[role="tab"]:focus, [role="tab"]:focus-visible { outline: none !important; box-shadow: none !important; }
.block-container { padding-top: 1.2rem; max-width: 1280px; }
h1, h2, h3 { letter-spacing: .02em; font-weight: 500; }

/* top bar */
.topbar { display:flex; justify-content:space-between; align-items:center; margin: .2rem 0 1.1rem; }
.logo { font-family:'Michroma', sans-serif; letter-spacing:.32em; font-size:.85rem; color:#fff; }
.logo b { color: var(--hot); }
.topbar .meta { font-size:.7rem; letter-spacing:.18em; text-transform:uppercase; color:var(--muted); }

/* tabs: small uppercase, orange underline */
[role="tablist"] { gap: .55rem; border-bottom: none; padding: .2rem 0 .7rem; }
[role="tab"] { padding: .7rem 1.05rem !important; border-radius: 999px; height: auto !important;
  background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.28);
  box-shadow: 0 2px 10px rgba(0,0,0,.25); transition: all .15s; }
[role="tab"] p { text-transform: uppercase; letter-spacing: .09em; font-size: .82rem !important; font-weight: 600;
  color: #E3E9F5; }
[role="tab"]:hover { background: rgba(255,255,255,.16); border-color: #FF5A36; transform: translateY(-1px); }
[role="tab"][aria-selected="true"] { background: linear-gradient(90deg, #FF6A36, #E0353B); border-color: #FF9A6B;
  box-shadow: 0 4px 18px rgba(255,90,54,.45); }
[role="tab"][aria-selected="true"] p { color: #fff; }
[data-baseweb="tab-highlight"], .react-aria-SelectionIndicator, [data-baseweb="tab-border"] { display: none !important; }

/* glass cards */
[data-testid="stMetric"], [data-testid="stPlotlyChart"], [data-testid="stExpander"] details {
  background: var(--panel); border: 1px solid var(--line); border-radius: 18px;
  backdrop-filter: blur(12px);
}
[data-testid="stMetric"] { padding: 1rem 1.25rem; }
[data-testid="stMetricLabel"] p { text-transform: uppercase; letter-spacing: .14em; font-size: .68rem; color: var(--muted); }
[data-testid="stMetricValue"] { font-weight: 300; font-size: 2.3rem; color: #fff; }
[data-testid="stPlotlyChart"] { padding: .6rem; }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }

/* multiselect chips: quiet glass instead of solid orange */
[data-baseweb="tag"], [data-testid="stMultiSelectTagsContainer"] [data-tag] {
  background: rgba(255,90,54,.14) !important; border: 1px solid rgba(255,90,54,.45) !important;
  border-radius: 999px !important; }
[data-baseweb="tag"] span, [data-testid="stMultiSelectTagsContainer"] [data-tag] span,
[data-testid="stMultiSelectTagsContainer"] [data-tag] button { color: #F3D6CC !important; }

/* buttons: pill with glow */
.stButton > button {
  border-radius: 999px; border: 1px solid rgba(255,90,54,.7); color: var(--text);
  background: linear-gradient(90deg, rgba(255,90,54,.20), rgba(255,200,61,.10));
  letter-spacing: .06em; padding: .55rem 1.4rem;
}
.stButton > button:hover { border-color: var(--amber); box-shadow: 0 0 26px rgba(255,90,54,.45); color:#fff; }

/* data-source pills */
.src { display:inline-flex; align-items:center; gap:.5rem; border:1px solid var(--line); border-radius:999px;
  padding:.28rem .8rem; font-size:.68rem; letter-spacing:.14em; text-transform:uppercase; color:#C9CFDA;
  background: rgba(255,255,255,.035); margin: .2rem 0 .7rem; }
.src i { width:.5rem; height:.5rem; border-radius:50%; background: var(--c); box-shadow: 0 0 10px var(--c); }

/* hero */
.hero { position:relative; overflow:hidden; border:1px solid var(--line); border-radius:28px; isolation: isolate;
  padding: 2.1rem 2.6rem 0; margin-bottom: 1.6rem;
  background: linear-gradient(180deg, rgba(255,255,255,.025), rgba(255,255,255,0)); }
.hero-copy { position:relative; z-index:2; max-width: 58%; min-height: 340px; }
.pill { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:.32rem .85rem;
  font-size:.68rem; letter-spacing:.16em; text-transform:uppercase; color:#C9CFDA; background: rgba(255,255,255,.04); }
.kicker { margin-top: 1.2rem; font-size: .8rem; letter-spacing: .3em; text-transform: uppercase; color: #C9CFDA; }
.hero h1 { font-family:'Michroma', sans-serif; font-size: clamp(2rem, 4.4vw, 3.7rem); line-height: 1.05;
  letter-spacing: .04em; margin: .5rem 0 1rem; text-transform: uppercase; color:#fff; padding:0; }
.hero .lead { color:#B8BFCE; font-size: 1rem; line-height: 1.65; max-width: 34rem; }

/* comet flame: flame-shaped head leads, vivid wavering tail follows (infinity loop, then a circle) */
.flight { position:absolute; right: 7%; top: 1.4rem; width: 270px; height: 325px;
  z-index: 1; pointer-events: none; }
.flight svg.guide { position:absolute; inset:0; width:100%; height:100%; overflow: visible; }
.flight svg.guide path { fill:none; stroke: rgba(255,255,255,.07); stroke-width: 1; stroke-dasharray: 2 7; }
.flight .p { position:absolute; left:0; top:0; offset-path: path("M66.0,18.9 C75.0,18.7 86.4,22.5 94.3,26.7 C102.2,30.9 106.9,40.9 113.2,44.0 C119.4,47.1 125.2,48.2 132.0,45.6 C138.8,43.0 146.2,33.7 154.0,28.3 C161.9,22.9 168.7,15.8 179.2,13.2 C189.6,10.6 205.4,8.5 216.9,12.6 C228.4,16.7 241.9,29.1 248.3,37.7 C254.7,46.4 256.0,57.6 255.2,64.4 C254.4,71.2 253.7,74.6 243.6,78.6 C233.5,82.5 213.5,85.7 194.9,88.0 C176.3,90.4 149.6,92.1 132.0,92.7 C114.5,93.4 98.1,90.4 89.6,91.8 C81.1,93.2 80.3,97.5 81.1,101.2 C81.9,104.9 86.9,110.0 94.3,113.8 C101.7,117.6 114.2,121.4 125.7,124.2 C137.3,126.9 149.8,129.5 163.4,130.4 C177.1,131.3 195.1,126.9 207.4,129.5 C219.8,132.1 229.6,137.6 237.3,146.2 C245.1,154.7 250.8,168.9 254.0,180.7 C257.1,192.5 257.2,208.8 256.2,216.9 C255.1,225.0 251.3,229.2 247.7,229.4 C244.0,229.7 239.0,224.5 234.2,218.4 C229.3,212.4 224.7,199.0 218.4,193.3 C212.2,187.6 204.6,185.8 196.4,184.5 C188.3,183.2 175.9,183.5 169.7,185.4 C163.5,187.4 158.6,190.7 159.4,196.4 C160.1,202.2 167.7,212.0 174.4,220.0 C181.1,228.0 194.2,236.4 199.6,244.5 C204.9,252.7 207.2,261.6 206.5,268.7 C205.8,275.9 202.4,284.2 195.5,287.6 C188.6,291.0 172.5,291.4 165.0,289.2 C157.6,286.9 156.1,277.6 150.9,274.1 C145.6,270.5 141.2,267.4 133.6,267.8 C126.0,268.2 115.2,272.8 105.3,276.6 C95.3,280.4 84.3,288.6 73.9,290.7 C63.4,292.8 51.2,292.5 42.4,289.2 C33.7,285.9 24.7,277.2 21.4,270.9 C18.1,264.7 18.3,257.7 22.6,251.5 C26.9,245.2 37.0,236.6 47.1,233.2 C57.3,229.8 73.4,233.6 83.3,231.0 C93.1,228.4 102.7,224.3 106.2,217.5 C109.7,210.7 107.8,198.0 104.4,190.2 C100.9,182.3 93.5,174.5 85.5,170.4 C77.5,166.2 66.0,166.3 56.6,165.3 C47.1,164.4 36.1,169.6 28.9,164.7 C21.7,159.8 16.7,147.5 13.2,135.8 C9.7,124.0 7.0,107.5 7.9,94.3 C8.7,81.1 12.8,67.7 18.2,56.6 C23.6,45.5 32.3,33.9 40.2,27.7 C48.2,21.4 57.0,19.0 66.0,18.9 Z"); offset-rotate: auto;
  offset-anchor: center; mix-blend-mode: screen; border-radius: 50%;
  animation: fly 15s linear infinite, wob var(--w, .4s) ease-in-out infinite alternate; }
.flight .glow { width: 110px; height: 110px; opacity: .4;
  background: radial-gradient(circle, rgba(255,110,40,.55) 0%, rgba(255,50,30,.16) 42%, transparent 70%); }
/* head: round, white-hot centre fading out inside the circle (no clipped corners) */
.flight .head { width: 50px; height: 50px; border-radius: 50%; offset-anchor: center;
  background: radial-gradient(circle closest-side, #FFFFFF 0%, #FFF4B8 20%, #FFD43A 40%, #FF9A1C 60%,
              rgba(255,80,20,.5) 80%, rgba(255,40,20,0) 100%);
  filter: drop-shadow(0 0 8px rgba(255,150,40,.9)) drop-shadow(0 0 20px rgba(255,60,30,.55));
  animation: fly 15s linear infinite, lickhead .22s ease-in-out infinite alternate; }
.flight .tongue { height: 12px; offset-anchor: 100% 50%;
  background: linear-gradient(90deg, rgba(255,60,20,0), rgba(255,140,30,.85) 55%, #FFE27A);
  border-radius: 100% 60% 60% 100% / 50%; filter: blur(2px); }
@keyframes fly { from { offset-distance: 0%; } to { offset-distance: 100%; } }
@keyframes wob { from { transform: translateY(calc(var(--a, 2px) * -1)) scale(.86); }
                 to   { transform: translateY(var(--a, 2px)) scale(1.14); } }
@keyframes lickhead { from { transform: scale(.93); } to { transform: scale(1.08); } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0%,100% { opacity:.25; transform: scale(1); } 50% { opacity:.7; transform: scale(1.05); } }
@media (max-width: 1100px) { .flight { transform: scale(.8); transform-origin: top right; } }

/* stats strip */
.stats { position:relative; z-index:2; display:grid; grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid var(--line); margin: 1.8rem -2.6rem 0; background: rgba(7,8,13,.35); }
.stat { padding: 1.05rem 1.2rem; border-left: 1px solid var(--line); text-align: center; }
.stat:first-child { border-left: none; }
.stat .lbl { font-size: .64rem; letter-spacing: .17em; text-transform: uppercase; color: var(--muted); }
.stat .val { font-family:'Michroma', sans-serif; font-size: 1.3rem; color:#fff; margin-top: .35rem; }

/* sensor status panel */
.status { display:flex; align-items:center; gap: 1.8rem; background: var(--panel); border:1px solid var(--line);
  border-radius: 22px; padding: 1.4rem 1.8rem; margin: .4rem 0 1rem; }
.sorb { flex: 0 0 132px; height: 132px; border-radius: 50%; position: relative; display:grid; place-items:center;
  background: radial-gradient(circle, color-mix(in srgb, var(--c) 55%, transparent) 0%, transparent 68%); }
.sorb::before { content:""; position:absolute; inset:6px; border-radius:50%; border:1px dashed color-mix(in srgb, var(--c) 60%, transparent);
  animation: spin 18s linear infinite; }
.sorb::after { content:""; position:absolute; inset:-4px; border-radius:50%; box-shadow: 0 0 34px var(--c);
  opacity:.45; animation: pulse var(--speed) ease-in-out infinite; }
.sorb .t { font-size: 1.9rem; font-weight: 300; color:#fff; }
.sorb .u { font-size: .62rem; letter-spacing:.14em; text-transform:uppercase; color: var(--muted); text-align:center; }
.status .lvl { font-family:'Michroma', sans-serif; font-size: 1.6rem; letter-spacing:.08em; color: var(--c); }
.status .row { display:flex; gap: 2.2rem; margin-top: .7rem; }
.status .k { font-size:.62rem; letter-spacing:.16em; text-transform:uppercase; color: var(--muted); }
.status .v { font-size: 1.15rem; color:#fff; font-weight: 400; }
@keyframes pulse { 0%,100% { opacity:.25; transform: scale(1); } 50% { opacity:.7; transform: scale(1.05); } }

@media (max-width: 820px) {
  .hero-copy { max-width: 100%; } .flight { opacity: .35; }
  .stats { grid-template-columns: repeat(2, 1fr); }
}
@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
</style>
""".replace("GRAIN", _GRAIN).replace("ROCKTEX", _ROCK).replace("TEX1", _TEX1).replace("TEX2", _TEX2)


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)
    tpl = go.layout.Template(layout=dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#C9CFDA", size=13),
        title=dict(font=dict(size=14, color="#E9ECF2"), x=0.01),
        colorway=CATEGORICAL,
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.1)",
                   linecolor="rgba(255,255,255,0.12)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.1)",
                   linecolor="rgba(255,255,255,0.12)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12), orientation="h",
                    yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="#12141C", bordercolor="#FF5A36", font=dict(color="#E9ECF2")),
        margin=dict(l=10, r=30, t=90, b=10),
    ))
    pio.templates["flame"] = tpl
    pio.templates.default = "plotly_dark+flame"


def chart(fig):
    """Show a Plotly figure with our theme (theme=None stops Streamlit overriding it)."""
    st.plotly_chart(fig, width="stretch", theme=None)


def source_pill(kind: str, text: str):
    st.markdown(f'<div class="src" style="--c:{BADGE_COLORS.get(kind, "#B9C2D0")}"><i></i>{text}</div>',
                unsafe_allow_html=True)


def topbar(team: str, meta: str):
    st.markdown(f'<div class="topbar"><div class="logo"><b>▚</b> {team}</div>'
                f'<div class="meta">{meta}</div></div>', unsafe_allow_html=True)


def _decor():
    rnd = random.Random(7)  # fixed seed: same layout every run
    stars = []
    for _ in range(90):
        x, y = rnd.uniform(0, 100), rnd.uniform(0, 60)
        sz = rnd.choice([1, 1, 1, 1.5, 2, 2.5])
        stars.append(f'<i class="star" style="left:{x:.1f}%;top:{y:.1f}%;width:{sz}px;height:{sz}px;'
                     f'--d:{rnd.uniform(1.5, 4.5):.1f}s;animation-delay:{-rnd.uniform(0, 4):.1f}s"></i>')
    flames = []
    for _ in range(48):
        x = rnd.uniform(18, 100)                      # mostly on the bright right side
        hot = (x - 18) / 82                           # 0 left .. 1 right
        h = rnd.uniform(60, 110) + 150 * hot
        w = h * rnd.uniform(.28, .45)
        flames.append(f'<i class="tongue" style="left:{x:.1f}%;width:{w:.0f}px;height:{h:.0f}px;margin-left:{-w/2:.0f}px;'
                      f'filter:blur({rnd.uniform(1.5, 4):.1f}px);--o:{.5 + .45 * hot * rnd.uniform(.7, 1):.2f};'
                      f'--d:{rnd.uniform(2.6, 5.2):.1f}s;--delay:{-rnd.uniform(0, 5):.1f}s;--sk:{rnd.uniform(-14, 14):.0f}deg"></i>')
    for _ in range(26):
        x = rnd.uniform(30, 100)
        flames.append(f'<i class="spark" style="left:{x:.1f}%;--d:{rnd.uniform(3, 7):.1f}s;'
                      f'--delay:{-rnd.uniform(0, 7):.1f}s;--dx:{rnd.uniform(-40, 40):.0f}px"></i>')
    return "".join(stars), "".join(flames)


def _flame_html(n_tail: int = 64, step: float = 0.05):
    """Flame head + tail particles on one path; each particle runs a little later, so the tail follows."""
    colors = ["#FFF2A8", "#FFE066", "#FFC42E", "#FFA51F", "#FF8717", "#FF6A12", "#FF4D12", "#FF3318",
              "#F02222", "#D0182C", "#A81436", "#7A1040"]
    rnd = random.Random(3)
    base = -6.0  # start mid-flight
    parts = []
    for i in range(n_tail, 0, -1):
        length = max(12, 56 - i * 0.6)           # stretched along the path = streaks, not dots
        height = max(6, 36 - i * 0.42)
        col = colors[min(len(colors) - 1, int(i * len(colors) / (n_tail * 0.7)))]   # turns orange/red sooner
        op = 0.95 * math.exp(-i / 36)             # smooth fade to transparent
        parts.append(
            f'<span class="p" style="width:{length:.0f}px;height:{height:.0f}px;'
            f'background:radial-gradient(ellipse closest-side,{col} 0%,transparent 100%);opacity:{op:.2f};'
            f'filter:blur({1.5 + i * 0.22:.1f}px);--a:{1.5 + i * 0.4:.1f}px;--w:{rnd.uniform(.22, .55):.2f}s;'
            f'animation-delay:{base + i * step:.3f}s,{-rnd.uniform(0, 1):.2f}s"></span>')
    parts.append(f'<span class="p glow" style="--a:0px;animation-delay:{base}s,0s"></span>')
    parts.append(f'<span class="p head" style="animation-delay:{base}s,0s"></span>')
    return ('<div class="flight" aria-hidden="true"><svg class="guide" viewBox="0 0 270 325">'
            '<path d="M66.0,18.9 C75.0,18.7 86.4,22.5 94.3,26.7 C102.2,30.9 106.9,40.9 113.2,44.0 C119.4,47.1 125.2,48.2 132.0,45.6 C138.8,43.0 146.2,33.7 154.0,28.3 C161.9,22.9 168.7,15.8 179.2,13.2 C189.6,10.6 205.4,8.5 216.9,12.6 C228.4,16.7 241.9,29.1 248.3,37.7 C254.7,46.4 256.0,57.6 255.2,64.4 C254.4,71.2 253.7,74.6 243.6,78.6 C233.5,82.5 213.5,85.7 194.9,88.0 C176.3,90.4 149.6,92.1 132.0,92.7 C114.5,93.4 98.1,90.4 89.6,91.8 C81.1,93.2 80.3,97.5 81.1,101.2 C81.9,104.9 86.9,110.0 94.3,113.8 C101.7,117.6 114.2,121.4 125.7,124.2 C137.3,126.9 149.8,129.5 163.4,130.4 C177.1,131.3 195.1,126.9 207.4,129.5 C219.8,132.1 229.6,137.6 237.3,146.2 C245.1,154.7 250.8,168.9 254.0,180.7 C257.1,192.5 257.2,208.8 256.2,216.9 C255.1,225.0 251.3,229.2 247.7,229.4 C244.0,229.7 239.0,224.5 234.2,218.4 C229.3,212.4 224.7,199.0 218.4,193.3 C212.2,187.6 204.6,185.8 196.4,184.5 C188.3,183.2 175.9,183.5 169.7,185.4 C163.5,187.4 158.6,190.7 159.4,196.4 C160.1,202.2 167.7,212.0 174.4,220.0 C181.1,228.0 194.2,236.4 199.6,244.5 C204.9,252.7 207.2,261.6 206.5,268.7 C205.8,275.9 202.4,284.2 195.5,287.6 C188.6,291.0 172.5,291.4 165.0,289.2 C157.6,286.9 156.1,277.6 150.9,274.1 C145.6,270.5 141.2,267.4 133.6,267.8 C126.0,268.2 115.2,272.8 105.3,276.6 C95.3,280.4 84.3,288.6 73.9,290.7 C63.4,292.8 51.2,292.5 42.4,289.2 C33.7,285.9 24.7,277.2 21.4,270.9 C18.1,264.7 18.3,257.7 22.6,251.5 C26.9,245.2 37.0,236.6 47.1,233.2 C57.3,229.8 73.4,233.6 83.3,231.0 C93.1,228.4 102.7,224.3 106.2,217.5 C109.7,210.7 107.8,198.0 104.4,190.2 C100.9,182.3 93.5,174.5 85.5,170.4 C77.5,166.2 66.0,166.3 56.6,165.3 C47.1,164.4 36.1,169.6 28.9,164.7 C21.7,159.8 16.7,147.5 13.2,135.8 C9.7,124.0 7.0,107.5 7.9,94.3 C8.7,81.1 12.8,67.7 18.2,56.6 C23.6,45.5 32.3,33.9 40.2,27.7 C48.2,21.4 57.0,19.0 66.0,18.9 Z"/></svg>' + "".join(parts) + "</div>")


def hero(pill: str, kicker: str, title: str, lead: str, stats: list):
    cells = "".join(f'<div class="stat"><div class="lbl">{k}</div><div class="val">{v}</div></div>'
                    for k, v in stats)
    st.markdown(f"""
<div class="hero">
  <div class="hero-copy">
    <span class="pill">{pill}</span>
    <div class="kicker">{kicker}</div>
    <h1>{title}</h1>
    <div class="lead">{lead}</div>
  </div>
  {_flame_html()}
  <div class="stats">{cells}</div>
</div>""", unsafe_allow_html=True)


def status_panel(level: str, temp, light, node, reason, when):
    c = LEVEL_COLORS.get(level, "#B9C2D0")
    speed = {"alarm": "0.9s", "warning": "1.8s"}.get(level, "3.5s")
    st.markdown(f"""
<div class="status" style="--c:{c}; --speed:{speed}">
  <div class="sorb"><div><div class="t">{temp}°</div><div class="u">air temp C</div></div></div>
  <div>
    <div class="k">Node {node} · {when}</div>
    <div class="lvl">{level.upper()}</div>
    <div class="row">
      <div><div class="k">Reason</div><div class="v">{reason}</div></div>
      <div><div class="k">Light (0-1023)</div><div class="v">{light}</div></div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)