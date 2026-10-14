import logging
import os


def setup_logging() -> logging.Logger:
    level = logging.DEBUG if os.getenv("VLADMIR_DEBUG", "").lower() in {"1", "true", "yes"} else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    return logging.getLogger("vladmir")
