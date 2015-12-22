#!/usr/bin/env python
# coding=utf-8
from __future__ import unicode_literals

import argparse
import glob
import os
import random
import time
from decimal import Decimal

from retry import retry

from helpers import decimal_round, get_now, print_dict_as_utf_8_json

__author__ = 'Kimmo Ahola'
__license__ = 'MIT'
__version__ = '1.0'
__email__ = 'kimmo.ahola@gmail.com'

DEVICE_BASE_DIR = '/sys/bus/w1/devices/'
DELAY_BETWEEN_READS = 1  # Seconds


def read_device_file(device_file_name):
    with open(device_file_name, 'r') as f:
        return f.readlines()


@retry(ValueError, tries=50, delay=DELAY_BETWEEN_READS)
def read_temp(device_file_name):

    lines = read_device_file(device_file_name)

    if not lines or len(lines) != 2 or not lines[0].strip().endswith('YES'):
        raise ValueError()

    equals_pos = lines[1].find('t=')

    if equals_pos == -1:
        raise ValueError()

    temp_string = lines[1][equals_pos+2:].strip()

    if temp_string == '85000':
        raise ValueError('Sensor initializing.')

    temp_decimal = Decimal(temp_string) / Decimal(1000)
    return get_now(), decimal_round(temp_decimal)


def read_5_and_take_middle_value(device_id):

    device_file_name = device_id_to_device_file_name(device_id)

    readings = []
    for i in range(5):
        if i > 0:
            # Sleep only between reads
            time.sleep(DELAY_BETWEEN_READS)
        readings.append(read_temp(device_file_name))

    # Sort by temperature
    readings = sorted(readings, key=lambda r: r[1])

    # Take the middle value
    return readings[len(readings)//2]


def simulate():
    return get_now(), decimal_round(random.randint(-200, 200) * 0.1)


def device_id_to_device_file_name(device_id=None):

    if device_id is None:
        device_directories = glob.glob(DEVICE_BASE_DIR + '28-*')

        if len(device_directories) > 1:
            raise ValueError('Found more than one temperature device: %s.'
                             'Provide the device id by --device-id.' % device_directories)

        elif len(device_directories) < 1:
            raise ValueError('Did not find temperature devices.')

        device_id = os.path.basename(device_directories[0])

    elif not device_id.startswith('28-'):
        device_id = '28-' + device_id

    return DEVICE_BASE_DIR + device_id + '/w1_slave'


def main():

    parser = argparse.ArgumentParser(description='Read temperature from the 1-wire device file.')

    parser.add_argument('--device-id', required=False, type=str, help='Device ID.')
    parser.add_argument('--simulate', required=False, action='store_true', help='Return random values for testing.')

    args = parser.parse_args()

    if args.simulate:
        stuff = simulate()
    else:
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')

        stuff = read_5_and_take_middle_value(args.device_id)

    if stuff:

        now, temperature = stuff

        data_out = {
            'ts': now.isoformat(),
            'temperature': str(temperature),
        }

        print_dict_as_utf_8_json(data_out)
    else:
        raise SystemError()


if __name__ == '__main__':
    main()
