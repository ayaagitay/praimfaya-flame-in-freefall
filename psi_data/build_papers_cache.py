"""Builds data_clean/papers_cache.json: NTRS records with an abstract + AI summary of that abstract.
Run once from psi_data:  python build_papers_cache.py   (dashboard reads the JSON, never calls the AI per click)"""
import json, time
from pathlib import Path
from ai_tools import search_papers, summarize_paper

QUERIES = [
    "microgravity flame spread",
    "spacecraft fire detection smoke",
    "spacecraft fire suppression",
    "droplet combustion extinction microgravity",
    "solid fuel burning International Space Station",
    "Saffire spacecraft fire experiment",
]
OUT = Path("data_clean") / "papers_cache.json"
OUT.parent.mkdir(exist_ok=True)

seen_ids, seen_titles, papers = set(), set(), []
for q in QUERIES:
    try:
        found = search_papers(q, 8)
    except Exception as e:
        print("search failed:", q, type(e).__name__)
        continue
    for p in found:
        title = (p["title"] or "").strip()
        if p["id"] in seen_ids or title.lower() in seen_titles or not p.get("abstract"):
            continue
        seen_ids.add(p["id"]); seen_titles.add(title.lower())
        s = summarize_paper(p)
        time.sleep(1)  # be gentle with rate limits
        papers.append({"id": p["id"], "title": title, "url": p["url"], "query": q,
                       "summary": s, "summary_mode": "ai" if s else "none",
                       "abstract": p["abstract"],
                       "source": "NASA NTRS (real paper record)"})

OUT.write_text(json.dumps(papers, indent=1, ensure_ascii=False), encoding="utf-8")
print(len(papers), "papers saved;", sum(1 for x in papers if x["summary"]), "with AI summary ->", OUT)
for x in papers[:3]:
    print("\n", x["title"][:90], "\n ", x["summary"])
