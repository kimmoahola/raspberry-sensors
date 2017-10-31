# coding=utf-8
import argparse
import json
import sys
import sqlite3


def init_sqlite(c, table_name):
    c.execute("""CREATE TABLE IF NOT EXISTS %s
                  (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      ts DATETIME NOT NULL,
                      temperature DECIMAL(6,2) NOT NULL
                  )""" % table_name)


def write_to_sqlite(file_name, table_name, data_in):
    conn = sqlite3.connect(file_name)
    c = conn.cursor()

    init_sqlite(c, table_name)

    c.execute('INSERT INTO %s (ts, temperature) VALUES (?, ?)' % table_name,
              (data_in['ts'], data_in['temperature']))

    conn.commit()
    conn.close()


def read_stdin():
    return json.loads(sys.stdin.read().decode('utf-8').strip())


def main():

    parser = argparse.ArgumentParser(
        description='Read temperature from stdin and write them to sqlite file.')

    parser.add_argument('--file-name', type=str, required=True, help='Sqlite database file name.')
    parser.add_argument('--table-name', type=str, default='sensor1',
                        help='Sqlite database table name. Defaults to "sensor1".')

    args = parser.parse_args()

    data_in = read_stdin()

    write_to_sqlite(args.file_name, args.table_name, data_in)

    data_out = json.dumps(data_in)

    print(data_out.encode('utf-8'))


if __name__ == '__main__':
    main()
