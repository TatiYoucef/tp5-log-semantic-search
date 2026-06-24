from tp5_log_search.cli import build_parser


def test_cli_parses_prepare_limit() -> None:
    parser = build_parser()
    args = parser.parse_args(["prepare-data", "--limit", "100"])
    assert args.command == "prepare-data"
    assert args.limit == 100


def test_cli_parses_benchmark_query() -> None:
    parser = build_parser()
    args = parser.parse_args(["benchmark", "--query", "failed password", "--top-k", "10", "--level", "ERROR"])
    assert args.command == "benchmark"
    assert args.query == "failed password"
    assert args.top_k == 10
    assert args.level == "ERROR"


def test_cli_parses_compare_models() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "compare-models",
            "--query",
            "authentication failure",
            "--models",
            "all-MiniLM-L6-v2",
            "all-mpnet-base-v2",
        ]
    )
    assert args.command == "compare-models"
    assert args.query == "authentication failure"
    assert args.models == ["all-MiniLM-L6-v2", "all-mpnet-base-v2"]
