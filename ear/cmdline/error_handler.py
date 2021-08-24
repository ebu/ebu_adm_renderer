import contextlib
import logging
import sys
import warnings
from ..fileio.adm.exceptions import AdmUnknownAttribute


@contextlib.contextmanager
def error_handler(logger: logging.Logger, debug: bool = False, strict: bool = False):
    """Context manager for use in CLIs which handles logging of exceptions and
    warnings.

    Parameters:
        logger: log to write to
        debug: should we be more verbose, printing full exceptions
        strict: turn unknown attribute warnings into errors
    """
    if debug:

        def showwarning(message, category, filename, lineno, file=None, line=None):
            category = category.__name__
            msg = f"{filename}:{lineno}: {category}: {message}"
            logger.warning(msg)

    else:

        def showwarning(message, category, filename, lineno, file=None, line=None):
            logger.warning(message)

    try:
        with warnings.catch_warnings():
            warnings.showwarning = showwarning  # documentation says this is allowed
            if strict:
                warnings.filterwarnings("error", category=AdmUnknownAttribute)
            yield
    except Exception as error:
        if debug:
            raise
        else:
            logger.error(error)
            sys.exit(1)
