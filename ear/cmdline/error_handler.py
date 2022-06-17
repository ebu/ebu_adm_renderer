from collections import defaultdict
import contextlib
import logging
import sys
import warnings
from ..fileio.adm.exceptions import AdmUnknownAttribute


class LimitedWarningPrint:
    """Utility to print a given number of warnings per line; to use, replace
    warnings.showwarning with self.showwarning.
    """

    def __init__(self, logger: logging.Logger, max_per_line=5):
        self.logger = logger
        self.max_per_line = max_per_line
        self.counts = defaultdict(lambda: 0)

    def showwarning(self, message, category, filename, lineno, file=None, line=None):
        self.counts[(filename, lineno)] += 1
        count = self.counts[(filename, lineno)]

        if count <= self.max_per_line:
            self.logger.warning(message)
        if count == self.max_per_line:
            self.logger.warning(
                "suppressing further messages like the above; use --debug to show more"
            )


@contextlib.contextmanager
def error_handler(logger: logging.Logger, debug: bool = False, strict: bool = False):
    """Context manager for use in CLIs which handles logging of exceptions and
    warnings.

    Parameters:
        logger: log to write to
        debug: should we be more verbose, printing full exceptions
        strict: turn unknown attribute warnings into errors
    """
    # debug: print every warning in full
    # no debug: just print message, stop after n
    if debug:

        def showwarning(message, category, filename, lineno, file=None, line=None):
            category = category.__name__
            msg = f"{filename}:{lineno}: {category}: {message}"
            logger.warning(msg)

    else:
        showwarning = LimitedWarningPrint(logger).showwarning

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
