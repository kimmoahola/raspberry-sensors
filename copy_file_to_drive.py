# coding=utf-8
import argparse
import httplib
import os

import httplib2
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from retry.api import retry


def main():

    parser = argparse.ArgumentParser(description='Copy a file to Google Drive.')
    parser.add_argument('--file-name', type=str, required=True, help='File name to copy.')
    parser.add_argument('--folder-id', type=str, default='root',
                        help='Google Drive folder ID to copy file to. Defaults to "root".')
    args = parser.parse_args()

    try:
        upload_file(args.folder_id, args.file_name)
    except (httplib.HTTPException, httplib2.HttpLib2Error):
        pass


@retry(tries=10, delay=30)
def upload_file(folder_id, file_name):
    gauth = GoogleAuth(settings_file='pydrive_settings.yaml')
    gauth.CommandLineAuth()
    drive = GoogleDrive(gauth)
    title = os.path.basename(file_name)

    metadata = {
        'parents': [{'kind': 'drive#fileLink', 'id': folder_id}],
    }

    file_list = drive.ListFile({'q': "'%s' in parents and trashed=false and title='%s'" % (folder_id, title)}).GetList()

    if file_list:

        if len(file_list) == 1:
            metadata.update(id=file_list[0]['id'])
        else:
            raise LookupError(
                'Found more than one file with title "%s" in folder "%s". Aborting.' % (title, folder_id))
    else:
        print('Did not find any file with title "%s" in folder "%s". Creating a new file.' % (title, folder_id))
        metadata.update(title=title)

    drive_file = drive.CreateFile(metadata)
    drive_file.SetContentFile(file_name)
    drive_file.Upload()


if __name__ == '__main__':
    main()
