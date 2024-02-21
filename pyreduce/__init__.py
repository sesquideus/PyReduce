# Define Version
from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

# add logger to console
import logging
import tqdm


# We need to use this to have logging messages handle properly with the progressbar
class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def addLoggingLevel(levelName, levelNum, methodName=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError('{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)


addLoggingLevel('TRACE', 5, 'trace')


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.captureWarnings(True)

console = TqdmLoggingHandler()
console.setLevel(logging.TRACE)


def log_for_level(self, message, *args, **kwargs):
    if self.isEnabledFor(levelNum):
        self._log(levelNum, message, args, **kwargs)


def logToRoot(message, *args, **kwargs):
    logging.log(levelNum, message, *args, **kwargs)


setattr(logging, 'trace', lambda message, *a, **k: logging.log(logging.TRACE, message, *a, **k))
setattr(logging, 'trace', lambda message, *a, **k: logging.log(logging.TRACE, message, *a, **k))

try:
    import colorlog

    console.setFormatter(colorlog.ColoredFormatter("[{log_color}{asctime} {levelname:<3.3}{reset}]: {message}",
                                                   style='{',
                                                   datefmt="%Y-%m-%d %H:%M:%S",
                                                   ))
    del colorlog
except ImportError:
    console.setFormatter("%(levelname)s - %(message)s")
    print("Install colorlog for colored logging output")

logger.addHandler(console)

del logging
# do not del tqdm, it is needed in the Log Handler

# Load externally available modules
from . import configuration, datasets, reduce, util
