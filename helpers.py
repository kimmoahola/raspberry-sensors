# coding=utf-8
from __future__ import unicode_literals

import datetime
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

import arrow
import pytz

__author__ = 'Kimmo Ahola'
__license__ = 'MIT'
__version__ = '1.1'
__email__ = 'kimmo.ahola@gmail.com'


TARGET_TIMEZONE = 'Europe/Helsinki'


def get_now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc, microsecond=0)


def utc_string_datetime_to_local_string_datetime(utc_string_datetime):
    local_aware = utc_string_datetime_to_local_arrow(utc_string_datetime)
    return local_aware.format('YYYY-MM-DD HH:mm')


def utc_string_datetime_to_local_arrow(utc_string_datetime):
    utc_aware = arrow.get(utc_string_datetime)
    local_aware = utc_aware.to(TARGET_TIMEZONE)
    return local_aware


def decimal_round(value, decimals=1):

    if not isinstance(value, Decimal):
        value = Decimal(value)

    rounder = '.' + ('0' * (decimals - 1)) + '1'

    return value.quantize(Decimal(rounder), rounding=ROUND_HALF_UP)


def print_dict_as_utf_8_json(data_out):

    if sys.version_info.major < 3:
        stdout = sys.stdout
    else:
        stdout = sys.stdout.buffer

    stdout.write(json.dumps(data_out, ensure_ascii=False).encode('utf-8'))
    stdout.write(b'\n')


def exception(logger):
    def exception_inner(f):

        @wraps(f)
        def exception_wrap(*args, **kw):
            # noinspection PyBroadException
            try:
                return f(*args, **kw)
            except Exception as e:
                logger.exception(e)
                exit(1)

        return exception_wrap

    return exception_inner


def read_stdin():
    return json.loads(sys.stdin.read().decode('utf-8').strip())
