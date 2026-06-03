"""Worker entrypoint compatible with Python 3.14 (asyncio.get_event_loop removed)."""

import asyncio

asyncio.set_event_loop(asyncio.new_event_loop())

from arq.worker import run_worker  # noqa: E402
from app.worker_settings import WorkerSettings  # noqa: E402

run_worker(WorkerSettings)
