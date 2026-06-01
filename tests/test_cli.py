from tp5_log_search.cli import build_parser


def test_cli_parses_prepare_limit() -> None:
    parser = build_parser()
    args = parser.parse_args(["prepare-data", "--limit", "100"])
    assert args.command == "prepare-data"
    assert args.limit == 100
