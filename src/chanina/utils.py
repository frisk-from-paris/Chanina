import logging
import datetime

from colorama import Fore, Style
from celery import signals


def s_now() -> str: return datetime.datetime.strftime(datetime.datetime.now(), "%H:%M:%S")


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.LIGHTWHITE_EX,
        "INFO": Fore.CYAN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": "\033[41m"
    }
    RESET = Style.RESET_ALL

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        formatted = super().format(record)
        return f"{color}{formatted}{self.RESET}"

@signals.after_setup_logger.connect

def setup_logging(logger, *_, **__):
    for handler in logger.handlers:
        handler.setFormatter(
            ColorFormatter(
                "[%(asctime)s %(levelname)-8s] [%(module)s] %(message)s",
                "%m-%d-%Y %H:%M:%S"
            )
        )

    logger.setLevel(logging.INFO)
