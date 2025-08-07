import logging
import os
from logging.handlers import RotatingFileHandler

def _parse_level(level: "str | int | None") -> int:
    if level is None:
        return logging.INFO
    if isinstance(level, int):
        return level
    name = str(level).strip().upper()
    return getattr(logging, name, logging.INFO)


def setup_logging(level: "str | int | None" = None) -> logging.Logger:
    """Configure and return the application logger.

    Level precedence: explicit `level` arg > env LOG_LEVEL > INFO.
    Also quiets noisy third-party loggers.
    """
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("finbot")

    # Determine desired level
    env_level = os.getenv("LOG_LEVEL")
    desired_level = _parse_level(level if level is not None else env_level)

    if logger.handlers:
        # Logger already initialized: allow dynamic level updates
        logger.setLevel(desired_level)
        return logger

    logger.setLevel(desired_level)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s - %(message)s")

    file_handler = RotatingFileHandler(
        filename=os.path.join("logs", "app.log"),
        maxBytes=2_000_000,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Quiet noisy dependencies unless explicitly overridden
    for noisy in ["openai", "httpx", "urllib3", "yfinance", "tenacity"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logger
