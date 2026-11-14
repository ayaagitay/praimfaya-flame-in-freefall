"""
Part B tools: AI mission advisory (Gemini, with a no-AI fallback) + NASA NTRS paper search.
Put this file in psi_data/ next to risk_index.py.   pip install pandas requests
Key: create psi_data/.env containing one line:   GEMINI_API_KEY=your_key_here
Optional second line to change the model:        GEMINI_MODEL=gemini-3.5-flash-lite
Run a demo:   python ai_tools.py            (add --no-ai to skip Gemini)
"""
import os
import re
import sys
from pathlib import Path
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
RANKING = HERE / "data_clean" / "flex_condition_ranking.csv"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _load_env():
    p = HERE / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()


def load_ranking():
    return pd.read_csv(RANKING)


def select_rows(df, fuel=None, diluent=None, o2_level=None, top_n=3):
    d = df
    if fuel: d = d[d.fuel == fuel]
    if diluent: d = d[d.diluent == diluent]
    if o2_level: d = d[d.o2_level == o2_level]
    return d.sort_values("flame_intensity_index_0_100", ascending=False).head(top_n)


def facts_text(rows):
    lines = []
    for r in rows.itertuples():
        lines.append(
            f"fuel={r.fuel}; added gas={r.diluent}; oxygen={r.o2_level}; tests={r.n_tests}; "
            f"mean burning rate={r.mean_burn_rate_mm2s:.2f} mm^2/s; "
            f"flame intensity index={r.flame_intensity_index_0_100:.0f} of 100; "
            f"low data warning={'yes' if r.low_data_flag else 'no'}; source={r.data_label}")
    return "\n".join(lines)


def template_advisory(rows):
    """No-AI advisory built only from the rows. Always works."""
    parts = []
    for r in rows.itertuples():
        gas = "no added gas" if str(r.diluent).startswith("none") else r.diluent
        parts.append(f"{r.fuel} with {gas} at {r.o2_level} ({r.n_tests} tests): "
                     f"mean burning rate {r.mean_burn_rate_mm2s:.2f} mm^2/s, index {r.flame_intensity_index_0_100:.0f}/100")
    warn = ", and some of these groups have very few tests, so treat them with caution" if rows.low_data_flag.any() else ""
    s1 = "Real ISS droplet-flame tests (NASA PSI-69 FLEX) show: " + "; ".join(parts) + "."
    s2 = ("The index is a derived ranking of test conditions by burning rate, not a fire probability "
          "or a material-safety rating" + warn + ".")
    return s1 + " " + s2


def call_gemini(prompt, timeout=30):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("no GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    r = requests.post(GEMINI_URL.format(model=model),
                      headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                      json={"contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.2}},
                      timeout=timeout)
    r.raise_for_status()
    cand = r.json()["candidates"][0]
    if cand.get("finishReason") not in (None, "STOP"):
        raise RuntimeError(f"incomplete answer: {cand.get('finishReason')}")
    return "".join(p.get("text", "") for p in cand["content"]["parts"]).strip()


def numbers_ok(output, source_text):
    """True only if every number in the AI text also appears in the facts we gave it."""
    allowed = set(re.findall(r"\d+(?:\.\d+)?", source_text)) | {"2"}
    return all(n in allowed for n in re.findall(r"\d+(?:\.\d+)?", output))


def advisory(rows, use_ai=True):
    """Returns {'text', 'mode', 'note'}.  mode is 'ai' or 'template' - show it on the dashboard."""
    facts = facts_text(rows)
    if use_ai:
        top = rows.head(1)
        facts = facts_text(top)
        tail = ("These are real ISS test results (NASA PSI-69 FLEX); the index is a derived ranking "
                "of test conditions by burning rate, not a fire probability"
                + (", and this group has very few tests, so treat it with caution" if top.low_data_flag.any() else "")
                + ".")
        prompt = (
            "Write exactly ONE complete sentence for a student fire-safety dashboard. "
            "Use ONLY the facts below. Name the fuel, the added gas and the oxygen range in natural words, "
            "then the mean burning rate and the flame intensity index, quoting numbers exactly as given. "
            "Do not convert units, do not add any other numbers, do not repeat column names or labels, "
            "and do not claim anything is safe.\n\n"
            f"FACTS:\n{facts}")
        try:
            text = call_gemini(prompt)
            if numbers_ok(text, facts):
                return {"text": text + " " + tail, "mode": "ai", "note": "Written by an AI model from real data rows"}
            return {"text": template_advisory(rows), "mode": "template",
                    "note": "AI text rejected (it contained a number not in the data); template used"}
        except Exception as e:
            return {"text": template_advisory(rows), "mode": "template", "note": f"AI unavailable ({type(e).__name__}); template used"}
    return {"text": template_advisory(rows), "mode": "template", "note": "Template (AI off)"}


def search_papers(query, n=5):
    """NASA NTRS search. Returns [{'id','title','url','abstract'}]. Check the first results by eye."""
    r = requests.get("https://ntrs.nasa.gov/api/citations/search",
                     params={"q": query, "page.size": n}, timeout=60)
    r.raise_for_status()
    out = []
    for rec in r.json().get("results", []):
        out.append({"id": rec.get("id"), "title": rec.get("title", ""),
                    "url": f"https://ntrs.nasa.gov/citations/{rec.get('id')}",
                    "abstract": rec.get("abstract")})
    return out


def summarize_paper(paper):
    """2-sentence AI summary of the ABSTRACT only. Returns None if no abstract or AI fails."""
    if not paper.get("abstract"):
        return None
    prompt = ("Summarize this NASA paper abstract in exactly 2 plain sentences for a student. "
              "Use only the abstract; add no numbers or facts that are not in it. Do not use words like clearly, confirmed, proved or demonstrated, and do not describe any result unless the abstract states it. If the abstract only describes the setup, say what was studied and nothing else.\n\n"
              f"TITLE: {paper['title']}\nABSTRACT: {paper['abstract']}")
    try:
        text = call_gemini(prompt)
        return text if numbers_ok(text, paper["abstract"] + paper["title"]) else None
    except Exception:
        return None


if __name__ == "__main__":
    ai = "--no-ai" not in sys.argv
    df = load_ranking()
    for label, rows in [("Top 3 overall", select_rows(df)),
                        ("Enriched oxygen, heptane", select_rows(df, fuel="Heptane", o2_level="O2 23-34% (enriched)"))]:
        a = advisory(rows, use_ai=ai)
        print(f"\n== {label} ==\n{a['text']}\n[{a['mode']}] {a['note']}")
    try:
        print("\n== NTRS test ==")
        for p in search_papers("microgravity flame spread spacecraft fire safety", 3):
            print(p["id"], "|", p["title"][:90], "|", p["url"])
    except Exception as e:
        print("NTRS search failed:", type(e).__name__, e)
