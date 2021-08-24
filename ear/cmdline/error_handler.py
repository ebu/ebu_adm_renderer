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
    try:
        with warnings.catch_warnings():
            if strict:
                warnings.filterwarnings("error", category=AdmUnknownAttribute)
            yield
    except Exception as error:
        if debug:
            raise
        else:
            logger.error(error)
            sys.exit(1)
