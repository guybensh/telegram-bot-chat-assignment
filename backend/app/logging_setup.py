import logging

from config import Settings, load_bot_config_entries


class _RedactTokenFilter(logging.Filter):
    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if self._token in message:
            record.msg = message.replace(self._token, "<token>")
            record.args = ()
        return True


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(level=logging.INFO)
    for entry in load_bot_config_entries(settings):
        logging.getLogger("httpx").addFilter(_RedactTokenFilter(entry.token))
