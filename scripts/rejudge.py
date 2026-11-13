"""Re-run ONLY the judge on saved per-question results (trial repeats).

The paper evaluates J with repeated independent judge runs; this script
repeats the judging step N times on the answers generated in the main run,
using the exact same judge prompt / system prompt / model as the harness.
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.getenv("BENCHMARKS_ROOT", r"F:\cuhk\5510A\5660\memory-benchmarks"))

from benchmarks.common.llm_client import LLMClient
from benchmarks.locomo.prompts import JUDGE_SYSTEM_PROMPT, get_judge_prompt, preprocess_answer

PREDICT_DIR = sys.argv[1] if len(sys.argv) > 1 else r"results\locomo\predicted_conv1_base"
DATASET = r"datasets\locomo\locomo10.json"
CONV = 1
CATEGORIES = {1, 2, 3, 4}
TRIALS = int(os.getenv("TRIALS", "3"))
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "deepseek-chat")


async def judge_trial(trial: int) -> dict:
    dataset = json.load(open(DATASET, encoding="utf-8"))
    qa_list = dataset[CONV]["qa"]

    judge = LLMClient(model=JUDGE_MODEL, provider="openai", rpm=120, timeout=120.0)
    sem = asyncio.Semaphore(8)

    async def one(path: Path, qa: dict):
        data = json.loads(path.read_text(encoding="utf-8"))
        processed_gt = preprocess_answer(qa["category"], qa["answer"])
        for label, cr in data["cutoff_results"].items():
            prompt = get_judge_prompt(qa["category"], qa["question"], processed_gt, cr["generated_answer"])

            async def call():
                async with sem:
                    return await judge.generate_structured(system=JUDGE_SYSTEM_PROMPT, user=prompt)

            try:
                raw = await asyncio.wait_for(call(), timeout=180)
                correct = isinstance(raw, dict) and raw.get("label", "").upper() == "CORRECT"
            except Exception as exc:
                print(f"trial{trial} {path.stem} {label} judge error: {exc}")
                correct = False
            cr["judgment"] = "CORRECT" if correct else "WRONG"
            cr["score"] = 1.0 if correct else 0.0
            cr["reason"] = raw.get("reasoning", "") if isinstance(raw, dict) else ""
        return data

    files = sorted(Path(PREDICT_DIR).glob("conv*_q*.json"), key=lambda p: int(p.stem.split("_q")[1]))
    results = await asyncio.gather(*[one(f, qa_list[int(f.stem.split("_q")[1])]) for f in files])

    # aggregate per cutoff
    agg = defaultdict(lambda: defaultdict(list))
    for data in results:
        cat = data["category"]
        for label, cr in data["cutoff_results"].items():
            agg[label][data["category_name"]].append(cr["score"])
            agg[label]["__all__"].append(cr["score"])

    summary = {}
    for label, cats in agg.items():
        summary[label] = {
            "overall": round(100 * statistics.mean(cats["__all__"]), 2),
            "n": len(cats["__all__"]),
            "per_category": {k: round(100 * statistics.mean(v), 2) for k, v in cats.items() if k != "__all__"},
        }
    return summary


async def main():
    all_trials = []
    for t in range(1, TRIALS + 1):
        s = await judge_trial(t)
        all_trials.append(s)
        print(f"--- Trial {t} ---")
        print(json.dumps(s, indent=2))

    # mean/std across trials per cutoff
    out = {}
    for label in all_trials[0]:
        vals = [tr[label]["overall"] for tr in all_trials]
        out[label] = {
            "mean": round(statistics.mean(vals), 2),
            "std": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0.0,
            "trials": vals,
            "per_category_trial1": all_trials[0][label]["per_category"],
        }
    print("=== J across trials ===")
    print(json.dumps(out, indent=2))
    with open(os.path.join(PREDICT_DIR, "..", "rejudge_trials.json"), "w", encoding="utf-8") as f:
        json.dump({"trials": all_trials, "summary": out}, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
