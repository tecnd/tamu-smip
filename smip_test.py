import csv
import sys
from random import random
from time import perf_counter, sleep
from typing import Tuple

import pandas as pd
from requests import Session

import smip_io

START = pd.to_datetime('2021-07-20T00:00:00')
END = pd.to_datetime('2021-07-21T00:00:00')
ID = 5356


def upload(samples: int, token: str, session: Session = None, quiet: bool = True) -> Tuple[float, float]:
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
    smip_io.add_data_async(ID, entries, token, session)
    upload_timer_stop = perf_counter()
    if not quiet: print('Downloading data')
    download_timer_start = perf_counter()
    r = smip_io.get_data(START.isoformat(), END.isoformat(), [ID], token, session)
    download_timer_stop = perf_counter()
    if not quiet: print('Verifying data')
    data = r.json()['data']['getRawHistoryDataWithSampling']
    assert len(data) == len(entries)

    upload_t = upload_timer_stop - upload_timer_start
    download_t = download_timer_stop - download_timer_start
    return round(upload_t, 3), round(download_t, 3)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        with open('smip_test.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(('Size', 'Upload time', 'Download time'))
            token = smip_io.get_token("test", "smtamu_group", "parthdave", "parth1234")
            with Session() as s:
                for size in range(1000, 100001, 1000):
                    for i in range(3):
                        writer.writerow((size, *upload(size, token, s)))
                        print(size, i)
                        sleep(1)
    else:
        filename = sys.argv[1] if len(sys.argv) > 1 else 'smip_test.csv'
        import pandas as pd
        import matplotlib.pyplot as plt
        df = pd.read_csv(filename)
        ax = df.plot.scatter(x='Size', y='Upload time', label='Upload')
        df.plot.scatter(x='Size', y='Download time', color='Orange', label='Download', ax=ax)
        plt.ylabel('Transfer time (s)')
        plt.show()
