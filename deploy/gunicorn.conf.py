# JTech Tally Bridge - Gunicorn config
# Used by Dockerfile CMD and systemd service.

import multiprocessing
import os

# Recommended: (2 x cores) + 1
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.environ.get("GUNICORN_THREADS", "2"))
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

worker_class = "sync"

limit_request_line = 8190
limit_request_fields = 100

max_requests = 1000
max_requests_jitter = 50
