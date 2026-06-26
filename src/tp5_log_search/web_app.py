from __future__ import annotations

import os
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
LEVELS = ["ALL", "CRITICAL", "ERROR", "WARNING", "INFO"]
MODEL_OPTIONS = [
    "all-MiniLM-L6-v2",
    "multi-qa-MiniLM-L6-cos-v1",
    "all-mpnet-base-v2",
]


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
    with httpx.Client(timeout=300.0) as client:
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


def _candidate_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        records.append(
            {
                "rang": index,
                "id": row.get("id"),
                "date": str(row.get("log_timestamp") or "").replace("T", " "),
                "niveau": row.get("level"),
                "event": row.get("event_id"),
                "similarite": row.get("similarity"),
                "message": row.get("raw_message"),
            }
        )
    return pd.DataFrame(records)


def _selected_log_panel(row: dict[str, Any]) -> None:
    with st.container(border=True):
        st.subheader("Log de depart")
        meta_cols = st.columns(4)
        meta_cols[0].metric("ID", _format_number(row.get("id")))
        meta_cols[1].metric("Niveau", row.get("level") or "-")
        meta_cols[2].metric("Evenement", row.get("event_id") or "-")
        meta_cols[3].metric("Similarite", f"{row['similarity']:.2f}" if row.get("similarity") is not None else "-")
        st.write(row.get("raw_message") or "-")
        if row.get("event_template"):
            st.caption(f"Template: {row['event_template']}")


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
        search_col, level_col, k_col = st.columns([3, 1, 1])
        seed_query = search_col.text_input("Recherche texte", value="wrong password")
        seed_level = level_col.selectbox("Niveau", LEVELS, key="similar_seed_level")
        candidate_k = k_col.slider("Resultats", 5, 50, 10, key="similar_candidate_k")

        if st.button("Rechercher des logs", type="primary"):
            st.session_state.pop("similar_reference", None)
            st.session_state.pop("similar_neighbors", None)
            st.session_state["similar_candidates"] = _api_post(
                "/search/semantic",
                {
                    "query": seed_query,
                    "top_k": candidate_k,
                    "level": None if seed_level == "ALL" else seed_level,
                },
            )

        candidates = st.session_state.get("similar_candidates", [])
        selected_log: dict[str, Any] | None = None
        if candidates:
            st.subheader("Resultats de recherche")
            selection = st.dataframe(
                _candidate_rows(candidates),
                use_container_width=True,
                hide_index=True,
                height=300,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "rang": st.column_config.NumberColumn("Rang", width="small"),
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "date": st.column_config.TextColumn("Date", width="medium"),
                    "niveau": st.column_config.TextColumn("Niveau", width="small"),
                    "event": st.column_config.TextColumn("Event", width="small"),
                    "similarite": st.column_config.NumberColumn("Similarite", format="%.3f", width="small"),
                    "message": st.column_config.TextColumn("Message", width="large"),
                },
            )
            selected_rows = selection.selection.rows
            if selected_rows:
                selected_log = candidates[selected_rows[0]]
                st.session_state["similar_reference"] = selected_log
            else:
                selected_log = st.session_state.get("similar_reference")
                st.info("Selectionne une ligne dans le tableau pour choisir le log de depart.")
        elif "similar_candidates" in st.session_state:
            st.info("Aucun resultat.")

        selected_log = selected_log or st.session_state.get("similar_reference")
        if selected_log:
            _selected_log_panel(selected_log)
            action_col, k_col = st.columns([1, 3])
            similar_k = k_col.slider("Nombre de voisins", 5, 100, 20, key="similar_k")
            if action_col.button("Chercher les similarites", type="primary"):
                try:
                    st.session_state["similar_neighbors"] = _api_get(
                        f"/logs/{int(selected_log['id'])}/similar",
                        {"top_k": similar_k},
                    )
                except httpx.HTTPStatusError as exc:
                    st.error(exc.response.json().get("detail", str(exc)))

        neighbors = st.session_state.get("similar_neighbors", [])
        if neighbors:
            st.subheader("Logs voisins")
            _results_table(neighbors)

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
        st.subheader("Comparaison des modeles")
        model_query_col, model_level_col, model_k_col = st.columns([3, 1, 1])
        model_query = model_query_col.text_input("Requete", value="failed password invalid user")
        model_level = model_level_col.selectbox("Niveau", LEVELS, key="model_compare_level")
        model_k = model_k_col.slider("Top-k", 3, 30, 10, key="model_compare_k")
        selected_models = st.multiselect("Modeles", MODEL_OPTIONS, default=MODEL_OPTIONS)
        candidate_limit = st.slider("Templates candidats", 10, 1000, 500, step=10)

        if not selected_models:
            st.warning("Selectionne au moins un modele.")
        elif st.button("Benchmarker les modeles", type="primary", key="compare_models"):
            comparison = _api_post(
                "/benchmark/models",
                {
                    "query": model_query,
                    "top_k": model_k,
                    "level": None if model_level == "ALL" else model_level,
                    "candidate_limit": candidate_limit,
                    "models": selected_models,
                },
            )
            model_rows = comparison["models"]
            summary_df = pd.DataFrame(
                [
                    {
                        "model": row["model"].replace("sentence-transformers/", ""),
                        "dimension": row["dimension"],
                        "latency_ms": row["latency_ms"],
                        "coherence": row["top_k_coherence"],
                        "avg_similarity": row["average_similarity"],
                        "dominant_event": row["dominant_event_id"],
                        "event_share": row["dominant_event_share"],
                        "distinct_events": row["distinct_events"],
                    }
                    for row in model_rows
                ]
            )
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            chart_left, chart_right = st.columns(2)
            with chart_left:
                st.plotly_chart(
                    px.bar(summary_df, x="model", y="coherence", color="model"),
                    use_container_width=True,
                )
            with chart_right:
                st.plotly_chart(
                    px.bar(summary_df, x="model", y="latency_ms", color="model"),
                    use_container_width=True,
                )

            with st.expander("Top resultats par modele"):
                for row in model_rows:
                    st.markdown(f"**{row['model'].replace('sentence-transformers/', '')}**")
                    st.dataframe(pd.DataFrame(row["top_results"]), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
