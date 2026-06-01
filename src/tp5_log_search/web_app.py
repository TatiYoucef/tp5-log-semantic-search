from __future__ import annotations

import os
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
LEVELS = ["ALL", "CRITICAL", "ERROR", "WARNING", "INFO"]


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
    st.title("TP5 - Recherche semantique OpenSSH")

    try:
        stats = _api_get("/stats")
    except Exception as exc:  # pragma: no cover - depend de l'API locale
        st.error(f"API indisponible: {exc}")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Logs", f"{stats['total_logs']:,}".replace(",", " "))
    col2.metric("Vectorises", f"{stats['embedded_logs']:,}".replace(",", " "))
    col3.metric("Evenements", stats["event_count"])
    col4.metric("Index", "HNSW" if "message_embeddings_embedding_hnsw_idx" in stats["indexes"] else "Absent")

    tabs = st.tabs(["Recherche", "Comparaison", "Logs similaires", "Analytique"])

    with tabs[0]:
        query = st.text_input("Requete semantique", value="failed password for invalid user")
        level = st.selectbox("Niveau", LEVELS, key="semantic_level")
        top_k = st.slider("Nombre de resultats", 5, 100, 20, key="semantic_k")
        if st.button("Rechercher", type="primary"):
            rows = _api_post(
                "/search/semantic",
                {"query": query, "top_k": top_k, "level": None if level == "ALL" else level},
            )
            _results_table(rows)

    with tabs[1]:
        compare_query = st.text_input("Requete", value="brute force ssh authentication failure")
        compare_level = st.selectbox("Niveau", LEVELS, key="compare_level")
        compare_k = st.slider("Resultats par methode", 5, 50, 10, key="compare_k")
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
        log_id = st.number_input("Identifiant du log", min_value=1, value=1, step=1)
        similar_k = st.slider("Logs voisins", 5, 100, 20, key="similar_k")
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
            st.dataframe(freq_df, use_container_width=True, hide_index=True)
            if not freq_df.empty:
                st.plotly_chart(
                    px.bar(freq_df, x="count", y="event_id", color="level", orientation="h"),
                    use_container_width=True,
                )
        with right:
            timeline_query = st.text_input("Evolution d'une erreur", value="failed password invalid user")
            granularity = st.radio("Granularite", ["day", "hour"], horizontal=True)
            if st.button("Analyser l'evolution"):
                timeline_rows = _api_get(
                    "/analytics/timeline",
                    {"query": timeline_query, "granularity": granularity},
                )
                timeline_df = pd.DataFrame(timeline_rows)
                st.subheader("Evolution temporelle")
                st.dataframe(timeline_df, use_container_width=True, hide_index=True)
                if not timeline_df.empty:
                    st.plotly_chart(px.line(timeline_df, x="bucket", y="count", markers=True), use_container_width=True)


if __name__ == "__main__":
    main()
