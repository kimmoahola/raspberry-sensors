#!/usr/bin/env python
# coding=utf-8
from __future__ import unicode_literals

import argparse
import gc
import random
import time

from retry import retry

from helpers import decimal_round, get_now, print_dict_as_utf_8_json

__author__ = 'Kimmo Ahola'
__license__ = 'MIT'
__version__ = '1.0'
__email__ = 'kimmo.ahola@gmail.com'

SENSOR_DHT11 = 1  # DHT11
SENSOR_DHT22 = 2  # DHT22 and also at least DHT21, AM2301, AM2302 and AM2321

DELAY_BETWEEN_READS = 3  # Seconds


def read_bit(data_iter):

    while next(data_iter) == 0:
        pass

    one_count = 1

    while next(data_iter) == 1:
        one_count += 1

    return int(one_count > 3)


def read_bits(data):
    bits = ''
    data_iter = iter(data)

    try:
        while True:
            bits += str(read_bit(data_iter))
    except StopIteration:
        pass

    return bits


def bin2dec(string_num):
    return int(string_num, 2)


def guess_sensor_type(hum_hi, hum_lo, temp_hi, temp_lo):
    """
    Returns a guess of sensor type.
    """
    if temp_hi & 128:
        # This is for sure.
        # Only DHT22 can measure temperatures below zero.
        sensor_type = SENSOR_DHT22

    elif hum_lo != 0 or temp_lo != 0:
        # This is for sure.
        # Only DHT22 can have non-zero lower bytes.
        sensor_type = SENSOR_DHT22

    else:
        # Positive or zero temperature, or lower bytes are zero.

        # With DHT11 the lower bytes are always zero.
        # With DHT22 the lower bytes can be zero.

        if hum_hi < 4 and temp_hi < 4:
            # This is a guess but the sensor is most likely DHT22.
            # After this point the actual humidity is 0-3 (DHT11) or one of 25.6, 51.2 and 76.8 (DHT22).
            # After this point the actual temperature is 0-3 (DHT11) or one of 25.6, 51.2 and 76.8 (DHT22).
            sensor_type = SENSOR_DHT22
        else:
            sensor_type = SENSOR_DHT11

    return sensor_type


def humidity_bits_to_decimal(sensor_type, hum_hi, hum_lo):
    if sensor_type == SENSOR_DHT11:
        humidity = hum_hi
    else:
        humidity = ((hum_hi << 8) + hum_lo) * 0.1
    return decimal_round(humidity)


def temperature_bits_to_decimal(sensor_type, temp_hi, temp_lo):
    if sensor_type == SENSOR_DHT11:
        temperature = temp_hi
    else:
        if temp_hi & 128:  # Negative temperature.
            multiply = -0.1
            temp_hi &= 127
        else:
            multiply = 0.1
        temperature = ((temp_hi << 8) + temp_lo) * multiply
    return decimal_round(temperature)


@retry(ValueError, tries=80, delay=DELAY_BETWEEN_READS)
def read_temperature_and_humidity(pin):

    import RPi.GPIO as GPIO

    now = get_now()

    data = []

    GPIO.setmode(GPIO.BCM)

    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(0.025)
    GPIO.output(pin, GPIO.LOW)
    time.sleep(0.02)
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    for i in range(500):
        data.append(GPIO.input(pin))

    GPIO.cleanup()

    bits = read_bits(data)

    if len(bits) < 40:
        raise ValueError('Not enough bits. Need 40 bits. Got %d bits.' % len(bits))

    hum_hi = bin2dec(bits[-40:-32])
    hum_lo = bin2dec(bits[-32:-24])
    temp_hi = bin2dec(bits[-24:-16])
    temp_lo = bin2dec(bits[-16:-8])
    crc = bin2dec(bits[-8:])

    if (hum_hi + hum_lo + temp_hi + temp_lo) & 255 != crc:
        raise ValueError('Checksum fail.')

    sensor_type = guess_sensor_type(hum_hi, hum_lo, temp_hi, temp_lo)

    humidity = humidity_bits_to_decimal(sensor_type, hum_hi, hum_lo)

    if humidity < 0 or humidity > 100:
        raise ValueError('Humidity out of range. Was %s %%.' % humidity)

    temperature = temperature_bits_to_decimal(sensor_type, temp_hi, temp_lo)

    return now, temperature, humidity


def read_3_and_take_middle_value(pin):

    readings = []
    for i in range(3):
        if i > 0:
            # Sleep only between reads
            time.sleep(DELAY_BETWEEN_READS)
        readings.append(read_temperature_and_humidity(pin))

    # Sort by temperature
    readings = sorted(readings, key=lambda r: r[1])

    # Take the middle value
    return readings[len(readings)//2]


def simulate():
    return get_now(), decimal_round(random.randint(-200, 200) * 0.1), decimal_round(random.randint(200, 800) * 0.1)


def main():

    parser = argparse.ArgumentParser(description='Read temperature and humidity.')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pin', type=int, help='Input pin number in BCM mode.')
    group.add_argument('--simulate', action='store_true', help='Return random values for testing.')

    args = parser.parse_args()

    if args.simulate:
        stuff = simulate()
    else:
        gc.disable()
        stuff = read_3_and_take_middle_value(args.pin)

    if stuff:

        now, temperature, humidity = stuff

        data_out = {
            'ts': now.isoformat(),
            'temperature': str(temperature),
            'humidity': str(humidity),
        }

        print_dict_as_utf_8_json(data_out)
    else:
        raise SystemError()


if __name__ == '__main__':
    main()
