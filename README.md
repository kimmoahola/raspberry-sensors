# raspberry-sensors

Python scripts to read various temperature sensors, and to upload them to google sheets.

## Install

- Copy `crontab_example` to `crontab`: `cp crontab_example crontab`

- Modify `crontab` to your needs. See "Configuring crontab"

- Get `client_secret.json` for google sheet communication using these instructions https://pygsheets.readthedocs.io/en/latest/authorizing.html Rename the downloaded file to `client_secret.json` and copy it to this directory

- Setup pyenv or just install required packages globally: `pip install -r requirements.txt`

- Run `python to_sheet.py ...` with correct arguments (see crontab_example)

- Follow the printed link

- Run the following 

    <pre>
    sudo chmod u+rw-x,go+r-wx crontab
    sudo chown root:root crontab
    sudo ln -sf $PWD/crontab /etc/cron.d/raspberry-sensors$(echo "$PWD" | sed -r s/[^a-zA-Z0-9]+/-/g)</pre>
  
### Configuring `crontab`

#### Setup backup

To get credentials for google drive communication, follow these instructions: https://pythonhosted.org/PyDrive/quickstart.html Rename the downloaded file to `pydrive_secrets.json` and copy it to this directory

Then enable backup by uncommenting and modifying the backup line in crontab
