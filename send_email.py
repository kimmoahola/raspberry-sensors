# coding=utf-8
from __future__ import print_function

import argparse
import json
import os
import smtplib
import sys
import tempfile
import time
from email.mime.text import MIMEText

from slugify import slugify

import helpers


def minutes_from_last_email(title):

    file_name_with_path = os.path.join(tempfile.gettempdir(), slugify(title))

    try:
        seconds = float(open(file_name_with_path).read().strip())
    except (IOError, ValueError):
        return 999999

    return (time.time() - seconds) / 60.0


def mark_last_email(title):

    file_name_with_path = os.path.join(tempfile.gettempdir(), slugify(title))

    with open(file_name_with_path, 'w') as f:
        f.write(str(time.time()))


def process_data(addresses, title, if_what, if_gt, if_lt, throttle, data_in):

    if minutes_from_last_email(title) < throttle:
        return

    message = ''

    timestamp = helpers.utc_string_datetime_to_local_string_datetime(data_in['ts'])

    if if_gt is not None and float(data_in[if_what]) > if_gt:
        message = '%s\n\n%s %s: %s > %s\n' % (timestamp, title, if_what, data_in[if_what], if_gt)

    if if_lt is not None and float(data_in[if_what]) < if_lt:
        message = '%s\n\n%s %s: %s < %s\n' % (timestamp, title, if_what, data_in[if_what], if_lt)

    if if_what and if_gt is None and if_lt is None:
        # Always send message
        message = '%s\n\n%s %s: %s\n' % (timestamp, title, if_what, data_in[if_what])

    if message:
        email(addresses, 'Alert of %s' % title, message)
        mark_last_email(title)


def send_email(address, mime_text):
    s = smtplib.SMTP('localhost')
    s.sendmail(address, [address], mime_text.as_string())
    s.quit()


def email(addresses, subject, message):

    for address in addresses:

        mime_text = MIMEText(message.encode('utf-8'), 'plain', 'utf-8')
        mime_text['Subject'] = subject
        mime_text['From'] = address
        mime_text['To'] = address

        send_email(address, mime_text)


def read_stdin():
    return json.loads(sys.stdin.read().decode('utf-8').strip())


def main():

    parser = argparse.ArgumentParser(
        description='Read temperature and humidity from stdin and write them to sqlite file.')

    parser.add_argument('--title', type=str, required=True, help='Title of the email.')
    parser.add_argument('--address', type=str, required=True, action='append',
                        help='Email address to send alerts. --address can be given multiple times.')
    parser.add_argument('--if-what', type=str, required=True, help='Parameter name.')
    parser.add_argument('--if-gt', type=float, help='Send email if parameter name is greater than a number.')
    parser.add_argument('--if-lt', type=float, help='Send email if parameter name is lower than a number.')
    parser.add_argument('--throttle', type=int, help='Send at most one email per THROTTLE minutes.')

    args = parser.parse_args()

    data_in = read_stdin()

    process_data(args.address, args.title, args.if_what, args.if_gt, args.if_lt, args.throttle, data_in)

    data_out = json.dumps(data_in)

    print(data_out.encode('utf-8'))


if __name__ == '__main__':
    main()
