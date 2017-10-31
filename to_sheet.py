# coding=utf-8
import argparse
import httplib
import itertools
import logging
import socket
import sqlite3
import time
from decimal import Decimal
from functools import wraps
from operator import itemgetter

import arrow
import httplib2
import pygsheets
import requests
from OpenSSL import SSL
from retry import retry

import helpers

logger = logging.getLogger('to_sheet')
handler = logging.FileHandler('to_sheet.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.info('----- START -----')


def timing(f):
    @wraps(f)
    def timing_wrap(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logger.debug('func:%r args:[%r, %r] took: %2.4f sec' % (f.__name__, args, kw, te-ts))
        return result
    return timing_wrap


def sqlite_get_rows_between_ts(cursor, table_name, start_ts, end_ts):
    cursor.execute(
        'SELECT id, ts, temperature FROM %s WHERE ts>? and ts<=? ORDER BY id' % table_name, (start_ts, end_ts))
    return cursor.fetchall()


def sqlite_get_last_row(cursor, table_name):
    cursor.execute('SELECT id, ts, temperature FROM %s ORDER BY id DESC LIMIT 1' % table_name)
    return cursor.fetchone()


def sqlite_get_last_two_rows(cursor, table_name):
    cursor.execute('SELECT id, ts, temperature FROM %s ORDER BY id DESC LIMIT 2' % table_name)
    return cursor.fetchall()


def highest_and_lowest_temperature(cursor, table_name, start_datetime, end_datetime, average_minutes):

    sqlite_rows = sqlite_get_rows_between_ts(
        cursor,
        table_name,
        datetime_to_utc_string_datetime(start_datetime),
        datetime_to_utc_string_datetime(end_datetime))

    if not sqlite_rows:
        return [[]] * 2

    min_temperature_sqlite_row = min(sqlite_rows, key=itemgetter(2))
    max_temperature_sqlite_row = max(sqlite_rows, key=itemgetter(2))

    min_row_average = average(cursor, table_name, min_temperature_sqlite_row[1], average_minutes)
    max_row_average = average(cursor, table_name, max_temperature_sqlite_row[1], average_minutes)

    min_temperature_sqlite_row += (min_row_average,)
    max_temperature_sqlite_row += (max_row_average,)

    if min_temperature_sqlite_row[1] > max_temperature_sqlite_row[1]:
        return min_temperature_sqlite_row, max_temperature_sqlite_row
    else:
        return max_temperature_sqlite_row, min_temperature_sqlite_row


def filtered_sqlite_rows(cursor, table_name, average_minutes):

    latest_sqlite_row = sqlite_get_last_row(cursor, table_name)
    last_row_average = average(cursor, table_name, latest_sqlite_row[1], average_minutes)
    yield latest_sqlite_row + (last_row_average,)
    start_datetime = arrow.get(latest_sqlite_row[1]).to(helpers.TARGET_TIMEZONE).ceil('day')

    interval = 3
    for i in range(1 * 7 * 24/interval):  # 1 week, 3 hour intervals
        start_datetime, row1, row2 = sqlite_rows_for_time_range(cursor, table_name, start_datetime, interval,
                                                                average_minutes)
        yield row1
        yield row2

    interval = 6
    for i in range(1 * 7 * 24/interval):  # 1 week, 6 hour intervals
        start_datetime, row1, row2 = sqlite_rows_for_time_range(cursor, table_name, start_datetime, interval,
                                                                average_minutes)
        yield row1
        yield row2

    interval = 24
    for i in range(10 * 7 * 24/interval):  # 10 weeks, 24 hour intervals
        start_datetime, row1, row2 = sqlite_rows_for_time_range(cursor, table_name, start_datetime, interval,
                                                                average_minutes)
        yield row1
        yield row2


def sqlite_rows_for_time_range(cursor, table_name, start_datetime, hours, average_minutes):
    end_datetime = start_datetime
    start_datetime = end_datetime.replace(hours=-hours)
    min_max_rows = highest_and_lowest_temperature(cursor, table_name, start_datetime, end_datetime, average_minutes)
    return start_datetime, min_max_rows[0], min_max_rows[1]


def average(cursor, table_name, sqlite_ts, average_minutes):
    utc_aware = arrow.get(sqlite_ts).shift(minutes=-average_minutes)

    sqlite_rows = sqlite_get_rows_between_ts(
        cursor,
        table_name,
        datetime_to_utc_string_datetime(utc_aware),
        sqlite_ts)

    temperatures = map(itemgetter(2), sqlite_rows)

    return helpers.decimal_round(Decimal(sum(temperatures)) / Decimal(len(temperatures)), decimals=2)


def convert_sqlite_row_to_gspread(sqlite_row, num_of_columns):

    gspread_row = list(sqlite_row)

    if len(gspread_row) >= 2:
        gspread_row[1] = helpers.utc_string_datetime_to_local_string_datetime(sqlite_row[1])

    for i in range(num_of_columns):
        try:
            gspread_row[i] = str(gspread_row[i])
        except IndexError:
            gspread_row.append('')

    return gspread_row


@retry(tries=3, delay=30)
def write_to_gspread(wks, sqlite_rows):
    num_of_columns = max(map(len, sqlite_rows))

    gspread_rows = [convert_sqlite_row_to_gspread(sqlite_row, num_of_columns) for sqlite_row in sqlite_rows]

    start_row = 2

    resize_sheet(wks, len(gspread_rows) + start_row - 1, num_of_columns)

    wks.update_cells((start_row, 1), [gspread_rows[0]])
    logger.info('Manually updated %s', gspread_rows[0])
    gspread_rows = gspread_rows[1:]
    start_row += 1

    logger.info('Updating %d rows', len(gspread_rows))
    wks.update_cells((start_row, 1), gspread_rows)


def resize_sheet(wks, row_count, col_count):
    if wks.rows < row_count:
        logger.info('Resize rows %d -> %d', wks.rows, row_count)
        wks.rows = row_count
    if wks.cols < col_count:
        logger.info('Resize cols %d -> %d', wks.cols, col_count)
        wks.cols = col_count


@retry(tries=3, delay=30)
@timing
def get_worksheet(sheet_key, sheet_name):
    gc = pygsheets.authorize(outh_file='client_secret.json', outh_nonlocal=True)
    sh = gc.open_by_key(sheet_key)

    wks = sh.worksheet_by_title(sheet_name)
    return wks


def datetime_to_utc_string_datetime(utc_aware):
    return utc_aware.to('utc').format('YYYY-MM-DDTHH:mm:ssZZ')  # 2016-09-21T08:50:28+00:00


def main():

    parser = argparse.ArgumentParser(
        description='Sync sqlite to Google spreadsheet.')

    parser.add_argument('--file-name', type=str, required=True, help='Sqlite database file name.')
    parser.add_argument('--table-name', type=str, required=True, help='Sqlite database table name.')
    parser.add_argument('--sheet-key', type=str, required=True, help='Google spreadsheet sheet key.')
    parser.add_argument('--sheet-name', type=str, required=True, help='Google spreadsheet sheet name.')
    parser.add_argument('--average-minutes', type=int, default=1440, help='Period in minutes to calculate average.')

    args = parser.parse_args()

    conn = sqlite3.connect(args.file_name)
    cursor = conn.cursor()

    logging.captureWarnings(True)
    logging.getLogger().setLevel(logging.WARNING)

    try:
        do_gspread_stuff(args, cursor)
    except (httplib.HTTPException, httplib2.HttpLib2Error, socket.error, requests.RequestException, SSL.Error,
            pygsheets.exceptions.RequestError):
        # pygsheets.exceptions.RequestError usually means Timeout
        pass

    conn.close()
    logger.info('-----  END  -----')


@timing
def do_gspread_stuff(args, cursor):
    wks = get_worksheet(args.sheet_key, args.sheet_name)

    sqlite_rows = get_sqlite_rows(args, cursor)

    write_to_gspread(wks, list(sqlite_rows))


@timing
def get_sqlite_rows(args, cursor):

    last_two_sqlite_rows = sqlite_get_last_two_rows(cursor, args.table_name)

    sqlite_rows = filtered_sqlite_rows(cursor, args.table_name, args.average_minutes)

    if len(last_two_sqlite_rows) >= 2 \
            and arrow.get(last_two_sqlite_rows[0][1]).hour != arrow.get(last_two_sqlite_rows[1][1]).hour \
            and helpers.utc_string_datetime_to_local_arrow(last_two_sqlite_rows[0][1]).hour % 4 == 0:
        # Update all
        pass
    else:
        # Update only first few rows

        def has_num_rows(rows, num):
            return len(filter(lambda r: r, rows)) >= num

        rows_to_update = []

        sliced_sqlite_rows = itertools.islice(sqlite_rows, 18)

        for row in sliced_sqlite_rows:
            if not has_num_rows(rows_to_update, 3):
                rows_to_update.append(row)

        sqlite_rows = rows_to_update

    return sqlite_rows


if __name__ == '__main__':
    main()
