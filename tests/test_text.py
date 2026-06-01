from datetime import datetime

from tp5_log_search.text import classify_level, normalize_message, parse_openssh_line, vector_to_pg


def test_parse_openssh_line() -> None:
    line = (
        "Dec 10 06:55:48 LabSZ sshd[24200]: "
        "Failed password for invalid user webmaster from 173.234.31.186 port 38926 ssh2"
    )

    parsed = parse_openssh_line(line, log_year=2024)

    assert parsed["month"] == "Dec"
    assert parsed["day"] == 10
    assert parsed["host"] == "LabSZ"
    assert parsed["service"] == "sshd"
    assert parsed["process_id"] == 24200
    assert parsed["log_timestamp"] == datetime(2024, 12, 10, 6, 55, 48)
    assert parsed["content"].startswith("Failed password")


def test_normalize_message() -> None:
    assert normalize_message("  Failed   Password  ") == "failed password"


def test_classify_level() -> None:
    assert classify_level("POSSIBLE BREAK-IN ATTEMPT!") == "CRITICAL"
    assert classify_level("Failed password for root") == "ERROR"
    assert classify_level("Connection closed by host [preauth]") == "WARNING"
    assert classify_level("Accepted publickey for user") == "INFO"


def test_vector_to_pg() -> None:
    assert vector_to_pg([0, 1.5, -2]) == "[0.0000000000,1.5000000000,-2.0000000000]"
