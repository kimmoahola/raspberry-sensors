# coding=utf-8
from __future__ import unicode_literals

import datetime
import json
import sys
from decimal import Decimal, ROUND_HALF_UP

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


def print_dict_as_utf_8_json(data_out):

    if sys.version_info.major < 3:
        stdout = sys.stdout
    else:
        stdout = sys.stdout.buffer

    stdout.write(json.dumps(data_out, ensure_ascii=False).encode('utf-8'))
    stdout.write(b'\n')
