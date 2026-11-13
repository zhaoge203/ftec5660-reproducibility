"""Minimal self-hosted Mem0 OSS HTTP shim.

Exposes the two endpoints used by mem0ai/memory-benchmarks LoCoMo harness:
  POST /memories   {"messages": [...], "user_id": str, "timestamp": int?}
  POST /search     {"query": str, "user_id": str, "limit": int}

Implemented directly on the `mem0` OSS Python SDK (mem0ai), so behaviour is
the open-source Mem0 pipeline (extract -> embed -> store), matching what the
benchmark expects from a self-hosted server, without requiring Docker.

LLM: DeepSeek (OpenAI-compatible), model deepseek-chat
Embedder: fastembed BAAI/bge-small-en-v1.5 (local, no external API)
Vector store: local Qdrant (directory from env QDRANT_PATH, default ./qdrant)
"""

from __future__ import annotations

import os
import asyncio
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

CONFIG = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": LLM_MODEL,
            "api_key": LLM_API_KEY,
            "openai_base_url": LLM_BASE_URL,
            "temperature": 0.0,
        },
    },
    "embedder": {
        "provider": "fastembed",
        "config": {"model": "BAAI/bge-small-en-v1.5", "embedding_dims": 384},
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0",
            "path": QDRANT_PATH,
            "on_disk": False,
            "embedding_model_dims": 384,
        },
    },
}

from mem0 import Memory  # noqa: E402

memory = Memory.from_config(CONFIG)
app = FastAPI(title="mem0-oss-shim")


class AddRequest(BaseModel):
    messages: list[dict[str, Any]]
    user_id: str
    timestamp: int | None = None
    custom_instructions: str | None = None
    metadata: dict[str, Any] | None = None


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 200


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "llm_model": LLM_MODEL, "qdrant_path": QDRANT_PATH}


@app.post("/memories")
async def add_memory(req: AddRequest) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"user_id": req.user_id}
    if req.timestamp is not None:
        kwargs["metadata"] = {"timestamp": req.timestamp}
    if req.custom_instructions:
        kwargs["custom_instructions"] = req.custom_instructions
    try:
        result = await asyncio.to_thread(memory.add, req.messages, **kwargs)
    except Exception as exc:  # surface a 500 so the harness retry logic kicks in
        raise HTTPException(status_code=500, detail=str(exc)[:500])
    return {"results": result if isinstance(result, list) else result.get("results", [])}


@app.post("/search")
async def search_memory(req: SearchRequest) -> dict[str, Any]:
    try:
        results = await asyncio.to_thread(
            memory.search,
            req.query,
            filters={"user_id": req.user_id},
            limit=req.limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:500])
    if isinstance(results, dict):
        return results
    return {"results": results}
