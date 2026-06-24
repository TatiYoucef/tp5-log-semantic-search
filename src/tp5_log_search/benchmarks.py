from __future__ import annotations

from collections import Counter
from functools import lru_cache
import os
from time import perf_counter
from typing import Any, Callable, TypeVar

import numpy as np

from .config import Settings, load_settings
from .db import connect, database_stats
from .embeddings import EmbeddingService
from .search import keyword_search, semantic_search


T = TypeVar("T")
DEFAULT_COMPARISON_MODELS = (
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/multi-qa-MiniLM-L6-cos-v1",
    "sentence-transformers/all-mpnet-base-v2",
)
MODEL_ALIASES = {
    "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    "multi-qa-MiniLM-L6-cos-v1": "sentence-transformers/multi-qa-MiniLM-L6-cos-v1",
    "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2",
}


def timed_call(call: Callable[[], T]) -> tuple[T, float]:
    start = perf_counter()
    result = call()
    return result, perf_counter() - start


def normalize_model_name(model_name: str) -> str:
    return MODEL_ALIASES.get(model_name, model_name)


@lru_cache(maxsize=4)
def _load_sentence_transformer(model_name: str):
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device="cpu")


def storage_metrics(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    stats = database_stats(settings)
    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    pg_database_size(current_database()) AS database_bytes,
                    pg_total_relation_size('log_entries') AS log_entries_bytes,
                    pg_total_relation_size('message_embeddings') AS message_embeddings_bytes,
                    COALESCE(to_regclass('message_embeddings_embedding_hnsw_idx')::text, '') AS hnsw_index_name
                """
            )
            database_bytes, log_entries_bytes, message_embeddings_bytes, hnsw_index_name = cur.fetchone()

            hnsw_index_bytes = 0
            if hnsw_index_name:
                cur.execute("SELECT pg_relation_size('message_embeddings_embedding_hnsw_idx')")
                hnsw_index_bytes = cur.fetchone()[0]

            cur.execute(
                """
                SELECT command, details, finished_at
                FROM pipeline_runs
                WHERE status = 'SUCCESS'
                ORDER BY finished_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

    latest_pipeline = None
    if row:
        command, details, finished_at = row
        latest_pipeline = {
            "command": command,
            "finished_at": finished_at.isoformat() if finished_at else None,
            "timings_seconds": details.get("timings", {}) if isinstance(details, dict) else {},
            "details": details if isinstance(details, dict) else {},
        }

    return {
        "counts": {
            "total_logs": stats["total_logs"],
            "embedded_logs": stats["embedded_logs"],
            "embedding_rows": stats["embedded_messages"],
            "event_count": stats["event_count"],
        },
        "storage": {
            "database_bytes": database_bytes,
            "log_entries_bytes": log_entries_bytes,
            "message_embeddings_bytes": message_embeddings_bytes,
            "hnsw_index_bytes": hnsw_index_bytes,
        },
        "latest_pipeline": latest_pipeline,
    }


def top_k_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "score": 0.0,
            "average_similarity": 0.0,
            "dominant_event_id": None,
            "dominant_event_share": 0.0,
            "distinct_events": 0,
            "result_count": 0,
            "method": "proxy_similarity_event_concentration",
        }

    similarities = [float(row["similarity"]) for row in rows if row.get("similarity") is not None]
    average_similarity = sum(similarities) / len(similarities) if similarities else 0.0

    event_ids = [row.get("event_id") or "UNKNOWN" for row in rows]
    event_counts = Counter(event_ids)
    dominant_event_id, dominant_count = event_counts.most_common(1)[0]
    dominant_event_share = dominant_count / len(rows)

    score = (average_similarity * 0.65) + (dominant_event_share * 0.35)
    return {
        "score": round(score, 4),
        "average_similarity": round(average_similarity, 4),
        "dominant_event_id": dominant_event_id,
        "dominant_event_share": round(dominant_event_share, 4),
        "distinct_events": len(event_counts),
        "result_count": len(rows),
        "method": "proxy_similarity_event_concentration",
    }


def query_benchmark(
    query: str,
    top_k: int = 20,
    level: str | None = None,
    settings: Settings | None = None,
    embedder: EmbeddingService | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()

    semantic_rows, semantic_seconds = timed_call(
        lambda: semantic_search(query, top_k=top_k, level=level, settings=settings, embedder=embedder)
    )
    keyword_rows, keyword_seconds = timed_call(
        lambda: keyword_search(query, top_k=top_k, level=level, settings=settings)
    )

    return {
        "query": query,
        "top_k": top_k,
        "level": level or "ALL",
        "semantic_latency_ms": round(semantic_seconds * 1000, 2),
        "keyword_latency_ms": round(keyword_seconds * 1000, 2),
        "semantic_result_count": len(semantic_rows),
        "keyword_result_count": len(keyword_rows),
        "top_k_quality": top_k_quality(semantic_rows),
    }


def _comparison_candidates(
    top_k: int,
    level: str | None = None,
    candidate_limit: int = 500,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    params: list[Any] = []
    where = ""
    if level and level != "ALL":
        where = "WHERE level = %s"
        params.append(level)
    params.append(max(candidate_limit, top_k))

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    normalized_message,
                    MIN(event_id) AS event_id,
                    MIN(level) AS level,
                    COUNT(*) AS occurrences
                FROM log_entries
                {where}
                GROUP BY normalized_message
                ORDER BY COUNT(*) DESC
                LIMIT %s
                """,
                params,
            )
            return [
                {
                    "normalized_message": row[0],
                    "event_id": row[1],
                    "level": row[2],
                    "occurrences": row[3],
                }
                for row in cur.fetchall()
            ]


def compare_semantic_models(
    query: str,
    top_k: int = 10,
    level: str | None = None,
    models: list[str] | None = None,
    candidate_limit: int = 500,
    batch_size: int = 64,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Compare plusieurs Sentence-Transformers sans dependance a la dimension pgvector."""

    settings = settings or load_settings()
    selected_models = [normalize_model_name(model) for model in (models or list(DEFAULT_COMPARISON_MODELS))]
    candidates = _comparison_candidates(
        top_k=top_k,
        level=level,
        candidate_limit=candidate_limit,
        settings=settings,
    )
    texts = [candidate["normalized_message"] for candidate in candidates]
    results = []

    for model_name in selected_models:
        started = perf_counter()
        model = _load_sentence_transformer(model_name)
        load_ready = perf_counter()
        if texts:
            text_vectors = model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            query_vector = model.encode(
                [query],
                batch_size=1,
                normalize_embeddings=True,
                show_progress_bar=False,
            )[0]
            scores = np.asarray(text_vectors) @ np.asarray(query_vector)
            order = np.argsort(-scores)[:top_k]
        else:
            text_vectors = np.empty((0, 0))
            scores = np.asarray([])
            order = np.asarray([], dtype=int)

        rows = [
            {
                "event_id": candidates[index]["event_id"],
                "level": candidates[index]["level"],
                "normalized_message": candidates[index]["normalized_message"],
                "occurrences": candidates[index]["occurrences"],
                "similarity": round(float(scores[index]), 4),
            }
            for index in order
        ]
        finished = perf_counter()
        quality = top_k_quality(rows)
        dimension = int(text_vectors.shape[1]) if len(text_vectors) else None

        results.append(
            {
                "model": model_name,
                "dimension": dimension,
                "candidate_count": len(candidates),
                "load_seconds": round(load_ready - started, 3),
                "latency_ms": round((finished - started) * 1000, 2),
                "top_k_coherence": quality["score"],
                "average_similarity": quality["average_similarity"],
                "dominant_event_id": quality["dominant_event_id"],
                "dominant_event_share": quality["dominant_event_share"],
                "distinct_events": quality["distinct_events"],
                "top_results": rows,
            }
        )

    return {
        "query": query,
        "top_k": top_k,
        "level": level or "ALL",
        "candidate_limit": candidate_limit,
        "models": results,
        "note": "In-memory comparison over distinct normalized messages/templates; pgvector remains indexed with the configured production model.",
    }
