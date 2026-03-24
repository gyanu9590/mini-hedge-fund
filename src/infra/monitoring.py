"""
src/infra/monitoring.py

System monitoring utilities.
- Structured logging setup
- Pipeline step timer
- Slack/webhook alert (optional)
"""

import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path

import requests


def setup_logging(level: str = "INFO", log_file: str = "logs/system.log") -> None:
    """Call once at application startup."""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        ],
    )


@contextmanager
def timer(label: str):
    """Context manager that logs elapsed time for a pipeline step."""
    logger = logging.getLogger("monitor")
    t0 = time.perf_counter()
    logger.info("START  %s", label)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - t0
        logger.info("END    %s  (%.1fs)", label, elapsed)


def send_alert(message: str, level: str = "INFO") -> None:
    """
    Send a Slack / webhook alert.
    Set SLACK_WEBHOOK_URL in .env to enable.
    """
    url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not url:
        return
    emoji = {"INFO": ":information_source:", "WARNING": ":warning:", "ERROR": ":red_circle:"}.get(level, "")
    try:
        requests.post(url, json={"text": f"{emoji} *MiniHedgeFund* {level}: {message}"}, timeout=5)
    except Exception as e:
        logging.getLogger("monitor").warning("Slack alert failed: %s", e)