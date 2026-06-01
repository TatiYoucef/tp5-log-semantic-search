from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import psycopg

from .config import PROJECT_ROOT, Settings, load_settings


SCHEMA_PATH = PROJECT_ROOT / "sql/schema.sql"

SECONDARY_INDEXES = (
    "message_embeddings_embedding_hnsw_idx",
    "log_entries_level_idx",
    "log_entries_event_id_idx",
    "log_entries_time_idx",
    "log_entries_line_id_idx",
    "log_entries_normalized_message_idx",
    "log_entries_raw_message_trgm_idx",
)


def drop_secondary_indexes(conn: psycopg.Connection) -> None:
    for index_name in SECONDARY_INDEXES:
        conn.execute(f"DROP INDEX IF EXISTS {index_name}")


def create_relational_indexes(conn: psycopg.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS log_entries_level_idx ON log_entries(level)")
    conn.execute("CREATE INDEX IF NOT EXISTS log_entries_event_id_idx ON log_entries(event_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS log_entries_time_idx ON log_entries(log_timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS log_entries_line_id_idx ON log_entries(line_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS log_entries_normalized_message_idx ON log_entries(normalized_message)"
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS log_entries_raw_message_trgm_idx
            ON log_entries USING gin (raw_message gin_trgm_ops)
        """
    )


def connect(settings: Settings | None = None) -> psycopg.Connection:
    settings = settings or load_settings()
    return psycopg.connect(settings.database_url)


def init_database(settings: Settings | None = None) -> None:
    """Recree le schema applicatif PostgreSQL/pgvector."""

    settings = settings or load_settings()
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(settings) as conn:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)


def _csv_parts(directory: Path) -> list[Path]:
    parts = sorted(directory.glob("part-*.csv"))
    if not parts:
        raise FileNotFoundError(f"Aucun fichier part-*.csv trouve dans {directory}")
    return parts


def _copy_csv_parts(conn: psycopg.Connection, sql: str, directory: Path) -> int:
    rows = 0
    for part in _csv_parts(directory):
        with conn.cursor() as cur:
            with cur.copy(sql) as copy:
                with part.open("r", encoding="utf-8") as handle:
                    header = handle.readline()
                    if header:
                        rows_in_file = sum(1 for _ in handle)
                        handle.seek(0)
                        rows += rows_in_file
                    while chunk := handle.read(1024 * 1024):
                        copy.write(chunk)
    return rows


def load_processed_data(settings: Settings | None = None, reset: bool = True) -> dict[str, int]:
    """Charge les CSV produits par Spark dans PostgreSQL avec COPY."""

    settings = settings or load_settings()
    template_copy_sql = """
        COPY event_templates (event_id, event_template, occurrences)
        FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')
    """
    log_copy_sql = """
        COPY log_entries (
            line_id, source, log_timestamp, month, day, time_text, host, service,
            process_id, level, event_id, raw_message, normalized_message, event_template
        )
        FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')
    """

    with connect(settings) as conn:
        drop_secondary_indexes(conn)
        if reset:
            conn.execute("TRUNCATE log_entries, event_templates, message_embeddings RESTART IDENTITY CASCADE")

        template_rows = _copy_csv_parts(conn, template_copy_sql, settings.event_templates_csv_dir)
        log_rows = _copy_csv_parts(conn, log_copy_sql, settings.log_entries_csv_dir)
        create_relational_indexes(conn)

    return {"event_templates": template_rows, "log_entries": log_rows}


def refresh_vector_index(settings: Settings | None = None) -> None:
    settings = settings or load_settings()
    with connect(settings) as conn:
        conn.execute("DROP INDEX IF EXISTS message_embeddings_embedding_hnsw_idx")
        conn.execute(
            """
            CREATE INDEX message_embeddings_embedding_hnsw_idx
                ON message_embeddings USING hnsw (embedding vector_cosine_ops)
            """
        )


def database_stats(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    with connect(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_logs,
                    COUNT(DISTINCT event_id) AS event_count,
                    MIN(log_timestamp) AS first_log,
                    MAX(log_timestamp) AS last_log
                FROM log_entries
                """
            )
            total_logs, event_count, first_log, last_log = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*)
                FROM log_entries le
                JOIN message_embeddings me
                    ON me.normalized_message = le.normalized_message
                """
            )
            embedded_logs = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM message_embeddings")
            embedded_messages = cur.fetchone()[0]

            cur.execute("SELECT level, COUNT(*) FROM log_entries GROUP BY level ORDER BY COUNT(*) DESC")
            levels = [{"level": level, "count": count} for level, count in cur.fetchall()]

            cur.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename IN ('log_entries', 'message_embeddings')
                ORDER BY indexname
                """
            )
            indexes = [row[0] for row in cur.fetchall()]

    return {
        "total_logs": total_logs,
        "embedded_logs": embedded_logs,
        "embedded_messages": embedded_messages,
        "event_count": event_count,
        "first_log": first_log.isoformat() if first_log else None,
        "last_log": last_log.isoformat() if last_log else None,
        "levels": levels,
        "indexes": indexes,
    }


def record_pipeline_run(
    command: str,
    status: str,
    details: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> None:
    settings = settings or load_settings()
    details = details or {}
    with connect(settings) as conn:
        conn.execute(
            """
            INSERT INTO pipeline_runs (command, status, details, finished_at)
            VALUES (%s, %s, %s::jsonb, NOW())
            """,
            (command, status, json.dumps(details, ensure_ascii=False)),
        )
