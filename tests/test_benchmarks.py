from tp5_log_search.benchmarks import normalize_model_name, top_k_quality


def test_normalize_model_name_accepts_short_names() -> None:
    assert normalize_model_name("all-MiniLM-L6-v2") == "sentence-transformers/all-MiniLM-L6-v2"
    assert normalize_model_name("custom/model") == "custom/model"


def test_top_k_quality_scores_similarity_and_event_concentration() -> None:
    rows = [
        {"event_id": "E1", "similarity": 0.9},
        {"event_id": "E1", "similarity": 0.8},
        {"event_id": "E2", "similarity": 0.7},
    ]

    quality = top_k_quality(rows)

    assert quality["score"] == 0.7533
    assert quality["average_similarity"] == 0.8
    assert quality["dominant_event_id"] == "E1"
    assert quality["dominant_event_share"] == 0.6667
    assert quality["distinct_events"] == 2


def test_top_k_quality_handles_empty_results() -> None:
    quality = top_k_quality([])

    assert quality["score"] == 0.0
    assert quality["result_count"] == 0
    assert quality["dominant_event_id"] is None
