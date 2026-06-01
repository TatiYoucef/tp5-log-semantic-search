from __future__ import annotations

import re
from datetime import datetime
from typing import Any


MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

OPENSSH_PREFIX_RE = re.compile(
    r"^(?P<month>[A-Z][a-z]{2})\s+"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<time_text>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<service>[^\[]+)\[(?P<process_id>\d+)\]:\s+"
    r"(?P<content>.*)$"
)


def normalize_message(message: str | None) -> str:
    """Normalise un message pour la vectorisation semantique."""

    if not message:
        return ""
    return re.sub(r"\s+", " ", message).strip().lower()


def classify_level(message: str | None) -> str:
    """Classe un message OpenSSH avec une heuristique reproductible."""

    text = normalize_message(message)
    if not text:
        return "INFO"
    critical_markers = ("possible break-in attempt", "too many authentication failures")
    error_markers = (
        "failed password",
        "authentication failure",
        "fatal",
        "error",
        "invalid user",
        "user unknown",
    )
    warning_markers = ("disconnect", "closed by", "preauth", "reverse mapping")

    if any(marker in text for marker in critical_markers):
        return "CRITICAL"
    if any(marker in text for marker in error_markers):
        return "ERROR"
    if any(marker in text for marker in warning_markers):
        return "WARNING"
    return "INFO"


def parse_openssh_line(line: str, log_year: int = 2024) -> dict[str, Any]:
    """Parse le prefixe syslog d'une ligne OpenSSH brute."""

    match = OPENSSH_PREFIX_RE.match(line)
    if not match:
        return {
            "month": None,
            "day": None,
            "time_text": None,
            "host": None,
            "service": None,
            "process_id": None,
            "content": line,
            "log_timestamp": None,
        }

    values = match.groupdict()
    month_num = MONTHS.get(values["month"])
    timestamp = None
    if month_num is not None:
        timestamp = datetime.strptime(
            f"{log_year}-{month_num:02d}-{int(values['day']):02d} {values['time_text']}",
            "%Y-%m-%d %H:%M:%S",
        )

    return {
        "month": values["month"],
        "day": int(values["day"]),
        "time_text": values["time_text"],
        "host": values["host"],
        "service": values["service"].strip(),
        "process_id": int(values["process_id"]),
        "content": values["content"],
        "log_timestamp": timestamp,
    }


def vector_to_pg(values: list[float] | tuple[float, ...]) -> str:
    """Convertit un vecteur Python en litteral pgvector."""

    return "[" + ",".join(f"{float(value):.10f}" for value in values) + "]"
