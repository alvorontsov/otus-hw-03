import functools
import logging
import sys

logger = logging.getLogger("Cases")
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                try:
                    f(*new_args)
                except Exception:
                    logger.error("Got Error Test with args: {0}".format(new_args))
                    raise

        return wrapper

    return decorator
