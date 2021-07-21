import csv
from random import random
from time import perf_counter
from typing import Tuple

import pandas as pd

import smip_io

START = pd.to_datetime('2021-07-20T00:00:00')
END = pd.to_datetime('2021-07-21T00:00:00')
ID = 5356


def upload(samples: int, quiet: bool = True) -> Tuple[float, float]:
    token = smip_io.get_token("test", "smtamu_group", "parthdave", "parth1234")
    if not quiet: print('Clearing data')
    r = smip_io.clear_data(START.isoformat(), END.isoformat(), ID, token)
    if not quiet:
        print(r.json())
        print('Generating data')
    time_range = pd.date_range(
        start=START, end=END, periods=samples, normalize=True, tz='UTC')
    entries = [{'timestamp': ts.isoformat(), 'value': str(random()), 'status': 0}
               for ts in time_range]
    if not quiet: print('Uploading data')
    upload_timer_start = perf_counter()
    smip_io.add_data_async(ID, entries, token)
    upload_timer_stop = perf_counter()
    if not quiet: print('Downloading data')
    download_timer_start = perf_counter()
    r = smip_io.get_data(START.isoformat(), END.isoformat(), [ID], token)
    download_timer_stop = perf_counter()
    if not quiet: print('Verifying data')
    data = r.json()['data']['getRawHistoryDataWithSampling']
    assert len(data) == len(entries)

    upload_t = upload_timer_stop - upload_timer_start
    download_t = download_timer_stop - download_timer_start
    return round(upload_t, 3), round(download_t, 3)


if __name__ == "__main__":
    with open('smip_test.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(('Size', 'Upload time', 'Download time'))
        for size in range(1000, 1000001, 1000):
            for i in range(3):
                writer.writerow((size, *upload(size)))
