from __future__ import annotations

from typing import Any

from .config import Settings, load_settings
from .db import connect, database_stats
from .embeddings import EmbeddingService
from .search import semantic_event_ids


def stats(settings: Settings | None = None) -> dict[str, Any]:
    return database_stats(settings)


def frequent_errors(
    limit: int = 15,
    level: str | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    where = ["level IN ('ERROR', 'CRITICAL', 'WARNING')"]
    params: list[Any] = []
    if level and level != "ALL":
        where = ["level = %s"]
        params.append(level)
    params.append(limit)

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    event_id,
                    COALESCE(event_template, normalized_message) AS template,
                    level,
                    COUNT(*) AS count
                FROM log_entries
                WHERE {" AND ".join(where)}
                GROUP BY event_id, COALESCE(event_template, normalized_message), level
                ORDER BY count DESC
                LIMIT %s
                """,
                params,
            )
            return [
                {"event_id": row[0], "template": row[1], "level": row[2], "count": row[3]}
                for row in cur.fetchall()
            ]


def timeline(
    query: str | None = None,
    event_id: str | None = None,
    level: str | None = None,
    granularity: str = "day",
    settings: Settings | None = None,
    embedder: EmbeddingService | None = None,
) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    if granularity not in {"hour", "day"}:
        raise ValueError("granularity doit etre 'hour' ou 'day'")

    where = ["log_timestamp IS NOT NULL"]
    params: list[Any] = []
    event_ids: list[str] = []
    if event_id:
        where.append("event_id = %s")
        params.append(event_id)
    elif query:
        event_ids = semantic_event_ids(query, settings=settings, embedder=embedder)
        if event_ids:
            placeholders = ", ".join(["%s"] * len(event_ids))
            where.append(f"event_id IN ({placeholders})")
            params.extend(event_ids)

    if level and level != "ALL":
        where.append("level = %s")
        params.append(level)

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT date_trunc('{granularity}', log_timestamp) AS bucket, COUNT(*) AS count
                FROM log_entries
                WHERE {" AND ".join(where)}
                GROUP BY bucket
                ORDER BY bucket
                """
                ,
                params,
            )
            return [
                {
                    "bucket": row[0].isoformat() if row[0] else None,
                    "count": row[1],
                    "matched_event_ids": event_ids,
                }
                for row in cur.fetchall()
            ]
