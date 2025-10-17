# app/utils.py
"""Shared utilities such as logging and retry decorators.

Module-level documentation added for clarity without impacting behavior.
"""
import os
import logging
import time
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

def get_logger(name=__name__):
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        level=getattr(logging, level, logging.INFO)
    )
    return logging.getLogger(name)

logger = get_logger("car-service")

def retry(exceptions, tries=3, delay=1, backoff=2, logger=logger):
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    logger.warning("Retryable error: %s, retrying in %s sec", e, mdelay)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry
