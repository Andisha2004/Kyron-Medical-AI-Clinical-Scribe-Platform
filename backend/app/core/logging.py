import logging
import logging.config

from pythonjsonlogger.json import JsonFormatter

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                    "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
                },
                "plain": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json" if settings.app_env != "development" else "plain",
                }
            },
            "root": {"level": settings.log_level.upper(), "handlers": ["default"]},
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
