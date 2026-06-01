from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    """Configuration centrale du projet.

    Les valeurs par defaut correspondent au depot livre et peuvent etre
    surchargees via un fichier .env ou les variables d'environnement.
    """

    database_url: str = "postgresql://tp5:tp5pass@localhost:5432/logsdb"
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    log_year: int = 2024
    raw_log_path: Path = PROJECT_ROOT / "data/raw/OpenSSH/OpenSSH_full.log"
    structured_csv_path: Path = PROJECT_ROOT / "data/raw/OpenSSH/OpenSSH_full.log_structured.csv"
    templates_csv_path: Path = PROJECT_ROOT / "data/raw/OpenSSH/OpenSSH_full.log_templates.csv"
    processed_dir: Path = PROJECT_ROOT / "data/processed"
    embedding_batch_size: int = 128
    search_top_k: int = 20

    @property
    def log_entries_csv_dir(self) -> Path:
        return self.processed_dir / "log_entries_csv"

    @property
    def log_entries_parquet_dir(self) -> Path:
        return self.processed_dir / "log_entries_parquet"

    @property
    def event_templates_csv_dir(self) -> Path:
        return self.processed_dir / "event_templates_csv"


def load_settings(env_file: str | Path | None = None) -> Settings:
    if env_file is None:
        env_file = PROJECT_ROOT / ".env"

    load_dotenv(env_file)

    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.database_url),
        model_name=os.getenv("MODEL_NAME", Settings.model_name),
        log_year=int(os.getenv("LOG_YEAR", str(Settings.log_year))),
        raw_log_path=_project_path(os.getenv("RAW_LOG_PATH", "data/raw/OpenSSH/OpenSSH_full.log")),
        structured_csv_path=_project_path(
            os.getenv("STRUCTURED_CSV_PATH", "data/raw/OpenSSH/OpenSSH_full.log_structured.csv")
        ),
        templates_csv_path=_project_path(
            os.getenv("TEMPLATES_CSV_PATH", "data/raw/OpenSSH/OpenSSH_full.log_templates.csv")
        ),
        processed_dir=_project_path(os.getenv("PROCESSED_DIR", "data/processed")),
        embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", str(Settings.embedding_batch_size))),
        search_top_k=int(os.getenv("SEARCH_TOP_K", str(Settings.search_top_k))),
    )
