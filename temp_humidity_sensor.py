import Adafruit_DHT as ada
import sys
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import gspread
import os
import pytz

class TempHumidityRecorder():
    def __init__(self):
        creds_path = os.path.dirname(os.path.realpath(__file__)) + '/.credentials.json'
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        self.gc = gspread.authorize(creds)
        self.worksheet_id = '1uE9jnUvL0M4m0t6PIkac6OG8VP_Tzxu_DSIUQGA-lGU'

    def measure(self):
        humidity, temperature = ada.read_retry(ada.AM2302, 4)
        temperature = temperature * 9/5 + 32
        print("Humidity: " + str(humidity) + "%," "Temperature: " + str(temperature) + "F")
        return (humidity, temperature)

    def write_to_gdoc(self, vals):
        spreadsheet = self.gc.open_by_key(self.worksheet_id)
        tz = pytz.timezone("US/Pacific")
        fmt = "%Y-%m-%d %H:%M:%S"
        ws = spreadsheet.worksheet('Data')
        last_row = len(ws.get_all_values())
        ws.update_cell(last_row + 1, 1, datetime.now(pytz.timezone('UTC')).astimezone(tz).strftime(fmt))
        ws.update_cell(last_row + 1, 2, round(vals[1], 2))
        ws.update_cell(last_row + 1, 3, round(vals[0], 2))
    def run(self):
        self.write_to_gdoc(self.measure())

if __name__ == '__main__':
    TempHumidityRecorder().run()
