from __future__ import annotations

import os
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
LEVELS = ["ALL", "CRITICAL", "ERROR", "WARNING", "INFO"]


def _format_bytes(value: int | float | None) -> str:
    if value is None:
        return "-"
    size = float(value)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def _format_seconds(value: int | float | None) -> str:
    if value is None:
        return "-"
    if value < 1:
        return f"{value * 1000:.0f} ms"
    return f"{value:.2f} s"


def _format_number(value: int | float | None) -> str:
    if value is None:
        return "-"
    return f"{value:,}".replace(",", " ")


def _coverage_percent(stats: dict[str, Any]) -> str:
    total = stats.get("total_logs") or 0
    embedded = stats.get("embedded_logs") or 0
    if not total:
        return "0.0%"
    return f"{embedded / total * 100:.1f}%"


def _api_get(path: str, params: dict[str, Any] | None = None) -> Any:
    with httpx.Client(timeout=60.0) as client:
        response = client.get(f"{API_URL}{path}", params=params)
        response.raise_for_status()
        return response.json()


def _api_post(path: str, payload: dict[str, Any]) -> Any:
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{API_URL}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def _results_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("Aucun resultat.")
        return
    df = pd.DataFrame(rows)
    visible = [
        column
        for column in ["id", "line_id", "log_timestamp", "level", "event_id", "similarity", "raw_message"]
        if column in df.columns
    ]
    st.dataframe(df[visible], use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="TP5 Logs OpenSSH", layout="wide")
    st.title("TP5 - Logs OpenSSH")

    try:
        stats = _api_get("/stats")
    except Exception as exc:  # pragma: no cover - depend de l'API locale
        st.error(f"API indisponible: {exc}")
        return

    first_log = stats.get("first_log", "")[:10] if stats.get("first_log") else "-"
    last_log = stats.get("last_log", "")[:10] if stats.get("last_log") else "-"
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Logs", _format_number(stats["total_logs"]))
    col2.metric("Coverage", _coverage_percent(stats))
    col3.metric("Events", _format_number(stats["event_count"]))
    col4.metric("Period", f"{first_log} -> {last_log}")

    tabs = st.tabs(["Recherche", "Comparaison", "Logs similaires", "Analytique", "Benchmarks"])

    with tabs[0]:
        query_col, level_col, k_col = st.columns([3, 1, 1])
        query = query_col.text_input("Requete semantique", value="failed password for invalid user")
        level = level_col.selectbox("Niveau", LEVELS, key="semantic_level")
        top_k = k_col.slider("Resultats", 5, 100, 20, key="semantic_k")
        if st.button("Rechercher", type="primary"):
            rows = _api_post(
                "/search/semantic",
                {"query": query, "top_k": top_k, "level": None if level == "ALL" else level},
            )
            _results_table(rows)

    with tabs[1]:
        query_col, level_col, k_col = st.columns([3, 1, 1])
        compare_query = query_col.text_input("Requete", value="brute force ssh authentication failure")
        compare_level = level_col.selectbox("Niveau", LEVELS, key="compare_level")
        compare_k = k_col.slider("Resultats", 5, 50, 10, key="compare_k")
        if st.button("Comparer"):
            payload = {"query": compare_query, "top_k": compare_k, "level": None if compare_level == "ALL" else compare_level}
            data = _api_post("/search/compare", payload)
            left, right = st.columns(2)
            with left:
                st.subheader("Semantique")
                _results_table(data["semantic"])
            with right:
                st.subheader("Mots-cles")
                _results_table(data["keyword"])

    with tabs[2]:
        id_col, k_col = st.columns([1, 1])
        log_id = id_col.number_input("Identifiant du log", min_value=1, value=1, step=1)
        similar_k = k_col.slider("Logs voisins", 5, 100, 20, key="similar_k")
        if st.button("Trouver les voisins"):
            try:
                rows = _api_get(f"/logs/{int(log_id)}/similar", {"top_k": similar_k})
                _results_table(rows)
            except httpx.HTTPStatusError as exc:
                st.error(exc.response.json().get("detail", str(exc)))

    with tabs[3]:
        left, right = st.columns([1, 1])
        with left:
            frequent_level = st.selectbox("Niveau frequent", LEVELS, key="frequent_level")
            frequent = _api_get(
                "/analytics/frequent-errors",
                {"limit": 15, "level": None if frequent_level == "ALL" else frequent_level},
            )
            freq_df = pd.DataFrame(frequent)
            st.subheader("Groupes recurrents")
            if not freq_df.empty:
                st.plotly_chart(
                    px.bar(freq_df, x="count", y="event_id", color="level", orientation="h"),
                    use_container_width=True,
                )
                with st.expander("Details"):
                    st.dataframe(freq_df, use_container_width=True, hide_index=True)
        with right:
            query_col, granularity_col = st.columns([2, 1])
            timeline_query = query_col.text_input("Evolution d'une erreur", value="failed password invalid user")
            granularity = granularity_col.radio("Granularite", ["day", "hour"], horizontal=True)
            if st.button("Analyser l'evolution"):
                timeline_rows = _api_get(
                    "/analytics/timeline",
                    {"query": timeline_query, "granularity": granularity},
                )
                timeline_df = pd.DataFrame(timeline_rows)
                st.subheader("Evolution temporelle")
                if not timeline_df.empty:
                    st.plotly_chart(px.line(timeline_df, x="bucket", y="count", markers=True), use_container_width=True)
                    with st.expander("Details"):
                        st.dataframe(timeline_df, use_container_width=True, hide_index=True)

    with tabs[4]:
        benchmark = _api_get("/benchmark")
        counts = benchmark["counts"]
        storage = benchmark["storage"]
        latest_pipeline = benchmark.get("latest_pipeline")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Embeddings", _format_number(counts["embedding_rows"]))
        col2.metric("Base", _format_bytes(storage["database_bytes"]))
        col3.metric("Log table", _format_bytes(storage["log_entries_bytes"]))
        col4.metric("HNSW size", _format_bytes(storage["hnsw_index_bytes"]))

        timings = latest_pipeline.get("timings_seconds", {}) if latest_pipeline else {}
        time_cols = st.columns(4)
        time_cols[0].metric("Embedding time", _format_seconds(timings.get("embed")))
        time_cols[1].metric("Indexing time", _format_seconds(timings.get("index")))
        time_cols[2].metric("Load time", _format_seconds(timings.get("load_db")))
        time_cols[3].metric("Pipeline time", _format_seconds(timings.get("total")))

        query_col, level_col, k_col = st.columns([3, 1, 1])
        bench_query = query_col.text_input("Benchmark query", value="failed password invalid user")
        bench_level = level_col.selectbox("Level", LEVELS, key="benchmark_level")
        bench_k = k_col.slider("Top-k", 5, 100, 20, key="benchmark_k")
        if st.button("Mesurer", key="run_benchmark"):
            result = _api_post(
                "/benchmark/query",
                {"query": bench_query, "top_k": bench_k, "level": None if bench_level == "ALL" else bench_level},
            )
            quality = result["top_k_quality"]

            latency_cols = st.columns(4)
            latency_cols[0].metric("Semantic latency", f"{result['semantic_latency_ms']:.2f} ms")
            latency_cols[1].metric("Keyword latency", f"{result['keyword_latency_ms']:.2f} ms")
            latency_cols[2].metric("Top-k coherence", f"{quality['score']:.2f}")
            latency_cols[3].metric("Avg similarity", f"{quality['average_similarity']:.2f}")

            st.caption(
                "Top-k coherence = 0.65 x average similarity + 0.35 x dominant event share."
            )
            detail_cols = st.columns(4)
            detail_cols[0].metric("Dominant event", quality["dominant_event_id"] or "-")
            detail_cols[1].metric("Event share", f"{quality['dominant_event_share']:.2f}")
            detail_cols[2].metric("Distinct events", _format_number(quality["distinct_events"]))
            detail_cols[3].metric("Semantic results", _format_number(result["semantic_result_count"]))


if __name__ == "__main__":
    main()
