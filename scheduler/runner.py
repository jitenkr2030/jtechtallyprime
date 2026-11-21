"""
JTech Tally Bridge - Scheduler runner

Lightweight loop-based scheduler. Each registered task has an
interval (seconds) and last-run timestamp; the loop fires any
task whose interval has elapsed since its last run.

For production use with multiple workers, replace this with
APScheduler + a job store (Redis or SQLAlchemy).
"""

import time
from datetime import datetime

from scheduler.tasks import TASKS
from config.logging_config import get_logger

log = get_logger(__name__)


def run_scheduler():
    log.info("Scheduler started. Registered tasks: %s", list(TASKS.keys()))

    last_run = {name: None for name in TASKS}

    try:
        while True:
            now = datetime.utcnow()
            for name, (fn, interval) in TASKS.items():
                last = last_run[name]
                if last is None or (now - last).total_seconds() >= interval:
                    log.info("Firing task: %s", name)
                    try:
                        fn()
                    except Exception as exc:
                        log.error("Task %s raised: %s", name, exc, exc_info=True)
                    last_run[name] = now

            time.sleep(30)
    except KeyboardInterrupt:
        log.info("Scheduler stopped by user.")
