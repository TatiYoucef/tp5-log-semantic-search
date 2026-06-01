from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .config import PROJECT_ROOT, load_settings
from .db import database_stats, init_database, load_processed_data, record_pipeline_run, refresh_vector_index
from .embeddings import generate_embeddings
from .spark_pipeline import prepare_dataset


def _print_dict(data: dict) -> None:
    for key, value in data.items():
        print(f"{key}: {value}")


def cmd_prepare_data(args: argparse.Namespace) -> None:
    result = prepare_dataset(limit=args.limit, partitions=args.partitions)
    _print_dict(result.__dict__)


def cmd_init_db(args: argparse.Namespace) -> None:
    init_database()
    print("Schema PostgreSQL/pgvector initialise.")


def cmd_load_db(args: argparse.Namespace) -> None:
    result = load_processed_data(reset=not args.no_reset)
    _print_dict(result)


def cmd_embed(args: argparse.Namespace) -> None:
    settings = load_settings()
    result = generate_embeddings(settings=settings, batch_size=args.batch_size, limit_texts=args.limit_texts)
    _print_dict(result)


def cmd_index(args: argparse.Namespace) -> None:
    refresh_vector_index()
    print("Index vectoriel HNSW reconstruit.")


def cmd_stats(args: argparse.Namespace) -> None:
    _print_dict(database_stats())


def cmd_run_pipeline(args: argparse.Namespace) -> None:
    command = "run-pipeline"
    try:
        init_database()
        prepared = prepare_dataset(limit=args.limit, partitions=args.partitions)
        loaded = load_processed_data(reset=True)
        embedded = generate_embeddings(batch_size=args.batch_size)
        refresh_vector_index()
        details = {"prepared": prepared.__dict__, "loaded": loaded, "embedded": embedded}
        record_pipeline_run(command, "SUCCESS", details)
        _print_dict(details)
    except Exception as exc:
        record_pipeline_run(command, "FAILED", {"error": str(exc)})
        raise


def cmd_serve_api(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("tp5_log_search.api:app", host=args.host, port=args.port, reload=args.reload)


def cmd_serve_web(args: argparse.Namespace) -> None:
    app_path = Path(__file__).with_name("web_app.py")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            str(args.port),
            "--server.address",
            args.host,
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        check=True,
    )


def cmd_build_report(args: argparse.Namespace) -> None:
    report = PROJECT_ROOT / "reports/rapport_tp5.tex"
    subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", str(report)], cwd=PROJECT_ROOT / "reports", check=True)
    print("Rapport compile: reports/rapport_tp5.pdf")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TP5 recherche semantique sur logs OpenSSH")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare-data", help="Pretraiter le dataset avec Spark")
    prepare.add_argument("--limit", type=int, default=None, help="Limiter le nombre de lignes pour un test rapide")
    prepare.add_argument("--partitions", type=int, default=8)
    prepare.set_defaults(func=cmd_prepare_data)

    init = subparsers.add_parser("init-db", help="Initialiser le schema PostgreSQL")
    init.set_defaults(func=cmd_init_db)

    load = subparsers.add_parser("load-db", help="Charger les CSV traites dans PostgreSQL")
    load.add_argument("--no-reset", action="store_true", help="Ne pas vider les tables avant le chargement")
    load.set_defaults(func=cmd_load_db)

    embed = subparsers.add_parser("embed", help="Generer les embeddings manquants")
    embed.add_argument("--batch-size", type=int, default=None)
    embed.add_argument("--limit-texts", type=int, default=None)
    embed.set_defaults(func=cmd_embed)

    index = subparsers.add_parser("index", help="Reconstruire l'index HNSW pgvector")
    index.set_defaults(func=cmd_index)

    stats = subparsers.add_parser("stats", help="Afficher les statistiques de la base")
    stats.set_defaults(func=cmd_stats)

    pipeline = subparsers.add_parser("run-pipeline", help="Executer tout le pipeline")
    pipeline.add_argument("--limit", type=int, default=None)
    pipeline.add_argument("--partitions", type=int, default=8)
    pipeline.add_argument("--batch-size", type=int, default=None)
    pipeline.set_defaults(func=cmd_run_pipeline)

    api = subparsers.add_parser("serve-api", help="Lancer l'API FastAPI")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)
    api.add_argument("--reload", action="store_true")
    api.set_defaults(func=cmd_serve_api)

    web = subparsers.add_parser("serve-web", help="Lancer l'interface Streamlit")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8501)
    web.set_defaults(func=cmd_serve_web)

    report = subparsers.add_parser("build-report", help="Compiler le rapport LaTeX")
    report.set_defaults(func=cmd_build_report)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
