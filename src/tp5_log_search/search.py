from __future__ import annotations

from typing import Any

from .config import Settings, load_settings
from .db import connect
from .embeddings import EmbeddingService


RESULT_COLUMNS = (
    "id",
    "line_id",
    "log_timestamp",
    "level",
    "event_id",
    "raw_message",
    "event_template",
)


def _row_to_dict(row: tuple[Any, ...], include_similarity: bool = False) -> dict[str, Any]:
    keys = list(RESULT_COLUMNS)
    if include_similarity:
        keys.append("similarity")
    data = dict(zip(keys, row))
    if data.get("log_timestamp") is not None:
        data["log_timestamp"] = data["log_timestamp"].isoformat()
    return data


def semantic_search(
    query: str,
    top_k: int | None = None,
    level: str | None = None,
    settings: Settings | None = None,
    embedder: EmbeddingService | None = None,
) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    top_k = top_k or settings.search_top_k
    embedder = embedder or EmbeddingService(settings.model_name)
    query_vector = embedder.encode_one(query)

    where: list[str] = []
    params: list[Any] = [query_vector, query_vector, max(top_k, 20)]
    if level and level != "ALL":
        where.append("le.level = %s")
        params.append(level)
    params.append(top_k)
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        WITH matches AS (
            SELECT
                normalized_message,
                1 - (embedding <=> %s::vector) AS similarity,
                embedding <=> %s::vector AS distance
            FROM message_embeddings
            WHERE embedding IS NOT NULL
            ORDER BY distance
            LIMIT %s
        )
        SELECT {", ".join("le." + column for column in RESULT_COLUMNS)}, matches.similarity
        FROM matches
        JOIN log_entries le
            ON le.normalized_message = matches.normalized_message
        {where_clause}
        ORDER BY matches.distance, le.log_timestamp NULLS LAST, le.line_id
        LIMIT %s
    """

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_row_to_dict(row, include_similarity=True) for row in cur.fetchall()]


def keyword_search(
    query: str,
    top_k: int | None = None,
    level: str | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    top_k = top_k or settings.search_top_k

    where = ["raw_message ILIKE %s"]
    params: list[Any] = [f"%{query}%"]
    if level and level != "ALL":
        where.append("level = %s")
        params.append(level)
    params.append(top_k)

    sql = f"""
        SELECT {", ".join(RESULT_COLUMNS)}
        FROM log_entries
        WHERE {" AND ".join(where)}
        ORDER BY log_timestamp NULLS LAST, line_id
        LIMIT %s
    """

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_row_to_dict(row) for row in cur.fetchall()]


def similar_logs(
    log_id: int,
    top_k: int | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or load_settings()
    top_k = top_k or settings.search_top_k

    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT me.embedding::text
                FROM log_entries le
                JOIN message_embeddings me
                    ON me.normalized_message = le.normalized_message
                WHERE le.id = %s
                """,
                (log_id,),
            )
            row = cur.fetchone()
            if not row:
                return []
            vector = row[0]
            cur.execute(
                f"""
                WITH matches AS (
                    SELECT
                        normalized_message,
                        1 - (embedding <=> %s::vector) AS similarity,
                        embedding <=> %s::vector AS distance
                    FROM message_embeddings
                    WHERE embedding IS NOT NULL
                    ORDER BY distance
                    LIMIT %s
                )
                SELECT {", ".join("le." + column for column in RESULT_COLUMNS)}, matches.similarity
                FROM matches
                JOIN log_entries le
                    ON le.normalized_message = matches.normalized_message
                WHERE le.id <> %s
                ORDER BY matches.distance, le.log_timestamp NULLS LAST, le.line_id
                LIMIT %s
                """,
                (vector, vector, max(top_k, 20), log_id, top_k),
            )
            return [_row_to_dict(item, include_similarity=True) for item in cur.fetchall()]


def compare_search(
    query: str,
    top_k: int | None = None,
    level: str | None = None,
    settings: Settings | None = None,
    embedder: EmbeddingService | None = None,
) -> dict[str, list[dict[str, Any]]]:
    settings = settings or load_settings()
    return {
        "semantic": semantic_search(query, top_k=top_k, level=level, settings=settings, embedder=embedder),
        "keyword": keyword_search(query, top_k=top_k, level=level, settings=settings),
    }


def semantic_event_ids(
    query: str,
    top_k: int = 200,
    max_events: int = 5,
    settings: Settings | None = None,
    embedder: EmbeddingService | None = None,
) -> list[str]:
    results = semantic_search(query, top_k=top_k, settings=settings, embedder=embedder)
    event_ids: list[str] = []
    for row in results:
        event_id = row.get("event_id")
        if event_id and event_id not in event_ids:
            event_ids.append(event_id)
        if len(event_ids) >= max_events:
            break
    return event_ids
