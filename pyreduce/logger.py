import logging

from datetime import time

from . import colour as c


class Formatter(logging.Formatter):
    def format(self, record) -> str:
        record.level = {
            'DEBUG':    c.debug,
            'INFO':     c.ok,
            'WARNING':  c.warn,
            'ERROR':    c.err,
            'CRITICAL': c.critical,
        }[record.levelname](record.levelname[:3])
        return super().format(record)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        ct = self.converter(record.created)
        return f"{time.strftime(format, ct)}.{int(record.msecs):03d}"


class ShortFormatter(Formatter):
    def format(self, record) -> str:
        record.asctime = {
            'DEBUG':    c.debug,
            'INFO':     c.ok,
            'WARNING':  c.warn,
            'ERROR':    c.err,
            'CRITICAL': c.critical,
        }[record.levelname](record.created)
        return super().format(record)


def setup_log(name, *, output=None, fmt='[{asctime} {level}] {message}', timefmt='%Y-%m-%d %H:%M:%S'):
    formatter = ShortFormatter('[{asctime}] {message}', timefmt, '{')

    if isinstance(output, str):
        handler = logging.FileHandler(output)
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    log.addHandler(handler)

    return log
