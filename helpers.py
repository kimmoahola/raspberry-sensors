# coding=utf-8
from decimal import Decimal, ROUND_HALF_UP

import datetime

import pytz

__author__ = 'Kimmo Ahola'
__license__ = 'MIT'
__version__ = '1.0'
__email__ = 'kimmo.ahola@gmail.com'


def get_now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc, microsecond=0)


def decimal_round(value):

    if not isinstance(value, Decimal):
        value = Decimal(value)

    return value.quantize(Decimal('.1'), rounding=ROUND_HALF_UP)

