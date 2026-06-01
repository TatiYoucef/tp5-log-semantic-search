from __future__ import annotations

from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .analytics import frequent_errors, stats, timeline
from .config import load_settings
from .embeddings import EmbeddingService
from .search import compare_search, keyword_search, semantic_search, similar_logs


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=20, ge=1, le=200)
    level: str | None = None


class SimilarRequest(BaseModel):
    log_id: int = Field(ge=1)
    top_k: int = Field(default=20, ge=1, le=200)


@lru_cache(maxsize=1)
def get_settings():
    return load_settings()


@lru_cache(maxsize=1)
def get_embedder() -> EmbeddingService:
    settings = get_settings()
    return EmbeddingService(settings.model_name)


app = FastAPI(
    title="TP5 Log Semantic Search",
    description="API de recherche semantique et analytique sur logs OpenSSH.",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stats")
def get_stats():
    return stats(get_settings())


@app.post("/search/semantic")
def post_semantic_search(request: SearchRequest):
    return semantic_search(
        request.query,
        top_k=request.top_k,
        level=request.level,
        settings=get_settings(),
        embedder=get_embedder(),
    )


@app.post("/search/keyword")
def post_keyword_search(request: SearchRequest):
    return keyword_search(request.query, top_k=request.top_k, level=request.level, settings=get_settings())


@app.post("/search/compare")
def post_compare_search(request: SearchRequest):
    return compare_search(
        request.query,
        top_k=request.top_k,
        level=request.level,
        settings=get_settings(),
        embedder=get_embedder(),
    )


@app.get("/logs/{log_id}/similar")
def get_similar_logs(log_id: int, top_k: int = Query(default=20, ge=1, le=200)):
    results = similar_logs(log_id, top_k=top_k, settings=get_settings())
    if not results:
        raise HTTPException(status_code=404, detail="Log introuvable ou non vectorise")
    return results


@app.get("/analytics/frequent-errors")
def get_frequent_errors(limit: int = Query(default=15, ge=1, le=100), level: str | None = None):
    return frequent_errors(limit=limit, level=level, settings=get_settings())


@app.get("/analytics/timeline")
def get_timeline(
    query: str | None = None,
    event_id: str | None = None,
    level: str | None = None,
    granularity: Literal["hour", "day"] = "day",
):
    return timeline(
        query=query,
        event_id=event_id,
        level=level,
        granularity=granularity,
        settings=get_settings(),
        embedder=get_embedder() if query else None,
    )
