"""Durable worker entrypoint for local-record archive exports.

Run this as a separate, single-replica service in production. It is intentionally
not a FastAPI BackgroundTask: export generation must survive API restarts.
"""

import logging
import time

from .config import get_settings
from .db import SessionLocal
from .services.data_exports import expire_exports, process_one_export


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pimascor.data_export_worker")


def main() -> None:
    settings = get_settings()
    if settings.app_env == "production" and not settings.b2_bucket:
        raise RuntimeError("Private object storage is required for the data export worker")
    while True:
        with SessionLocal() as db:
            expired = expire_exports(db)
            processed = process_one_export(db)
        if expired:
            logger.info("Expired %s local-record archives", expired)
        time.sleep(5 if processed else 30)


if __name__ == "__main__":
    main()
