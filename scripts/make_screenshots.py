"""Render run-log excerpts as console-style PNG screenshots for the report."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("report/screenshots")
OUT.mkdir(parents=True, exist_ok=True)


def render(text: str, path: Path, title: str = "") -> None:
    lines = text.rstrip("\n").split("\n")
    h = max(2, len(lines) * 0.32 + 0.8)
    fig = plt.figure(figsize=(11, h), dpi=110, facecolor="#0c0c0c")
    fig.text(0.01, 0.955 if title else 0.99, text, va="top", ha="left", family="DejaVu Sans Mono",
             fontsize=9.5, color="#e8e8e8", wrap=False)
    if title:
        fig.suptitle(title, color="#7fd4ff", fontsize=11, family="DejaVu Sans Mono", x=0.01, ha="left")
    plt.axis("off")
    fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


# 1. Benchmark final summary (trial 1, from unified result JSON)
unified = sorted(Path("results/locomo").glob("locomo_results_*.json"))[0]
u = json.loads(unified.read_text(encoding="utf-8"))
mets = u["metrics_by_cutoff"]
lines = ["LOCOMO Benchmark | project=conv1_base (trial 1)",
         "  Answerer: deepseek-chat (openai)   Judge: deepseek-chat (openai)",
         "  Conversations: 1   Cutoffs: 10,200   Questions: %d" % u["metadata"]["total_questions"], ""]
for cutoff in mets:
    m = mets[cutoff]
    lines.append(f"--- {cutoff} ---")
    overall = m.get("overall", {})
    lines.append(f"  Overall: {overall.get('correct','?')}/{overall.get('total','?')} ({round(overall.get('accuracy',0),1)}%)")
    for cat, v in m.get("by_category", {}).items():
        lines.append(f"  {cat}: {v.get('correct','?')}/{v.get('total','?')} ({round(v.get('accuracy',0),1)}%)")
summary = "\n".join(lines)
render(summary, OUT / "shot1_benchmark_summary.png", "LoCoMo benchmark run (trial 1) - final summary")

# 2. Rejudge across-trials summary
rj = json.loads(Path("results/locomo/rejudge_trials.json").read_text(encoding="utf-8"))
render(json.dumps(rj["summary"], indent=2), OUT / "shot2_judge_trials.png",
       "Judge score across 3 independent trials (scripts/rejudge.py)")

# 3. One sample per-question result
sample = json.loads((Path("results/locomo/predicted_conv1_base") / "conv1_q12.json").read_text(encoding="utf-8"))
pretty = {
    "question_id": sample["question_id"],
    "category": sample["category_name"],
    "question": sample["question"],
    "top_2_retrieved_memories": [r["memory"] for r in (sample["retrieval"].get("search_results") or [])[:2]],
    "top_10_judgment": sample["cutoff_results"]["top_10"]["judgment"],
    "top_200_judgment": sample["cutoff_results"]["top_200"]["judgment"],
}
render(json.dumps(pretty, indent=2, ensure_ascii=False), OUT / "shot3_sample_question.png",
       "Sample per-question output (conv1_q12)")

# 4. mem0 memory extraction demo (real run)
mem_demo = """$ curl -X POST http://127.0.0.1:8888/memories \\
    -d '{"messages":[{"role":"user","content":"I live in Hong Kong and work as a data analyst."}],
         "user_id":"test_user"}'
{"results": [...]}

$ curl -X POST http://127.0.0.1:8888/search \\
    -d '{"query":"Where does the user live?","user_id":"test_user","limit":5}'
{"results": [{"memory": "User lives in Hong Kong and works as a data analyst",
              "score": 0.381, "user_id": "test_user", ...}]}"""
render(mem_demo, OUT / "shot4_mem0_demo.png", "Mem0 OSS memory extraction + retrieval (shim server)")

print("saved:", [p.name for p in OUT.glob("*.png")])
