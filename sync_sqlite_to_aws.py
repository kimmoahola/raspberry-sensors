# coding=utf-8
import argparse
import json
import logging
import sqlite3

import requests

import helpers

logger = logging.getLogger('to_aws')
handler = logging.FileHandler('to_aws.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.info('----- START -----')


def sqlite_get_rows_after_ts(cursor, table_name, start_ts, limit):
    if start_ts:
        cursor.execute(
            'SELECT ts, temperature FROM %s WHERE ts>? GROUP BY ts LIMIT ?' % table_name, (start_ts, str(limit)))
    else:
        cursor.execute(
            'SELECT ts, temperature FROM %s GROUP BY ts LIMIT ?' % table_name, (str(limit), ))
    return cursor.fetchall()


def main():

    parser = argparse.ArgumentParser(
        description='Sync sqlite to Google spreadsheet.')

    parser.add_argument('--file-name', type=str, required=True, help='Sqlite database file name.')
    parser.add_argument('--table-name', type=str, required=True, help='Sqlite database table name.')

    args = parser.parse_args()

    conn = sqlite3.connect(args.file_name)
    cursor = conn.cursor()

    logging.captureWarnings(True)
    logging.getLogger().setLevel(logging.WARNING)

    sensor_id = args.table_name

    r = requests.get(helpers.STORAGE_ROOT_URL + 'status', params={'sensorId': sensor_id})
    if r.status_code == 200:
        j = r.json()
        latest_item_ts = j.get('latestItem')
        max_batch = j['config']['maxAddBatchSize']
        rows = sqlite_get_rows_after_ts(cursor, args.table_name, latest_item_ts, max_batch)

        if rows:
            data = {
                'sensorId': sensor_id,
                'items': [
                    {'ts': row[0], 'temperature': str(row[1])}
                    for row
                    in rows
                ],
            }

            requests.post(helpers.STORAGE_ROOT_URL + 'add', data=json.dumps(data))

    conn.close()
    logger.info('-----  END  -----')


if __name__ == '__main__':
    main()
