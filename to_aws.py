# coding=utf-8
import argparse
import json
import logging

from retry import retry

import helpers
import requests


logger = logging.getLogger('to_sqlite')
handler = logging.FileHandler('to_sqlite.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.info('----- START -----')


ROOT_URL = 'https://eqoypr4x73.execute-api.eu-north-1.amazonaws.com/production/'


@retry(tries=10, delay=20)
def send_to_aws(name, data_in):
    data = {
        'sensorId': name,
        'ts': data_in['ts'],
        'temperature': data_in['temperature'],
    }

    requests.post(ROOT_URL + 'addOne', data=json.dumps(data))


@helpers.exception(logger=logger)
def main():

    parser = argparse.ArgumentParser(
        description='Read temperature from stdin and send it to AWS.')

    parser.add_argument('--name', type=str, help='Name of the sensor.')

    args = parser.parse_args()

    data_in = helpers.read_stdin()

    send_to_aws(args.name, data_in)

    # data_out = json.dumps(data_in)

    # print(data_out.encode('utf-8'))

    logger.info('-----  END  -----')


if __name__ == '__main__':
    main()
