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
