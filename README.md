# FTEC5660 Reproducibility Work — Mem0 on LoCoMo

Reproducing a reported result from **Mem0: Building Production-Ready AI Agents with
Scalable Long-Term Memory** (arXiv:2504.19413, ECAI 2025) using the authors'
open-source stack, then applying one small, measurable modification.

- **Reproduction target**: Mem0's overall LLM-as-a-Judge score on the LoCoMo
  benchmark (paper reports **66.88 ± 0.15** for Mem0 with GPT-4o-mini).
- **Controlled variable (documented swap)**: the original pipeline uses
  OpenAI models, which are not accessible here. All LLM calls
  (memory extraction/update, answer generation, judging) were switched to
  **DeepSeek (`deepseek-chat`)** via its OpenAI-compatible API, with
  `temperature = 0`. Results are therefore **not directly comparable** to the
  paper; we compare against the paper's numbers as a reference point only.
- **Modification (one isolated change)**: retrieval budget ablation —
  answering questions with the top-`k` retrieved memories at
  **`k = 10` vs `k = 200`** (the harness-native default is 200), measuring the
  accuracy/token trade-off.

## Layout

```
server/shim_server.py   Minimal HTTP shim exposing POST /memories + POST /search,
                        implemented directly on the mem0 OSS Python SDK
                        (mem0ai 2.2.1). Replaces the Docker-based self-hosted
                        server; LLM = DeepSeek, embedder = fastembed
                        BAAI/bge-small-en-v1.5 (local), vector store = local Qdrant.
run_shim.bat            Start the shim (loads .env, sets HF_ENDPOINT mirror).
run_bench.bat           Run the LoCoMo benchmark subset
                        (wraps mem0ai/memory-benchmarks benchmarks.locomo.run).
results/                Raw per-question outputs + unified result JSONs (gitignored).
report/                 Brief report, key-result screenshots, presentation script.
```

## Setup

1. Python 3.12, create a venv and install:

   ```bat
   python -m venv .venv
   .venv\Scripts\pip install mem0ai fastapi "uvicorn[standard]" aiohttp aiolimiter fastembed python-dotenv tqdm openai
   ```

2. Copy `.env.example` to `.env` and fill in your `DEEPSEEK_API_KEY`.
   Never commit `.env`.

3. Clone the benchmark harness next to this repo (or set `PYTHONPATH`):

   ```bat
   git clone https://github.com/mem0ai/memory-benchmarks.git
   ```

4. Start the memory backend:

   ```bat
   run_shim.bat
   ```

5. Download the LoCoMo-10 dataset (auto-downloaded by the harness, or place
   `locomo10.json` under `datasets/locomo/`).

## Run (reproduce)

Conversation 1 (smallest, 105 QA pairs), retrieval cutoffs k=10 and k=200:

```bat
run_bench.bat conv1_base 1 10_200
```

The judge phase is stochastic; repeat it with `--evaluate-only --rejudge`
(trials 2 and 3) to obtain mean ± std.

## Results (summary)

See `report/` for the full tables, screenshots and analysis. Headline numbers
(Conversation 1 subset, DeepSeek as answerer + judge, temperature 0):

| Run | Retrieval k | Judge score (J) |
|-----|-------------|-----------------|
| 1   | 200         | see report      |
| 1   | 10          | see report      |

## Notes / differences from the paper

- LLM swapped GPT-4o-mini → DeepSeek `deepseek-chat` (controlled variable).
- Subset evaluation: 1 of 10 conversations instead of the full dataset.
- Local embedder (bge-small-en-v1.5) instead of OpenAI text-embedding-3-small.
- No secrets are committed; `.env` is gitignored.
