from datetime import datetime, timedelta, timezone
from random import random
from time import perf_counter

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from smip_io import ENDPOINT, MUTATION_ADDDATA, QUERY_GETDATA, get_token


def batcher(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def stress(duration: int, rate: int, batch_size: int) -> None:
    """Sends data to SMIP for the specified duration, rate, and batch size and checks integrity"""
    # Get session and token from global context
    global s
    global token

    # Create date range and fill with random data
    now = datetime.now(timezone.utc)
    future = now + timedelta(seconds=duration)
    print(future)
    time_range = pd.date_range(start=now, end=future, periods=rate*duration)
    entries = [{'timestamp': ts.isoformat(), 'value': str(random()), 'status': 0}
               for ts in time_range]

    # Upload
    upload_thruput = list()
    start_time = perf_counter()
    for batch in batcher(entries, batch_size):
        r = s.post(ENDPOINT, json={
            'query': MUTATION_ADDDATA,
            'variables': {
                "id": 5356,
                "entries": batch
            }
        }, headers={'Authorization': f'Bearer {token}'})
        r.raise_for_status()
        print(r.elapsed, r.json())
        upload_thruput.append(len(batch) / r.elapsed.total_seconds())

    elapsed = perf_counter() - start_time
    print('Upload:', timedelta(seconds=elapsed),
          f'{round(duration / elapsed, 2)}x realtime')

    # Download
    timer_download_start = perf_counter()
    r = s.post(ENDPOINT, json={
        "query": QUERY_GETDATA,
        "variables": {
            "endTime": future.isoformat(),
            "startTime": now.isoformat(),
            "ids": [5356]
        }
    }, headers={"Authorization": f"Bearer {token}"})
    download_elapsed_true = perf_counter() - timer_download_start
    r.raise_for_status()
    print('Download:', r.elapsed,
          f'{round(duration / r.elapsed.total_seconds(), 2)}x realtime')
    print('Download (true):', timedelta(seconds=download_elapsed_true),
          f'{round(duration / download_elapsed_true, 2)}x realtime')
    data = r.json()['data']['getRawHistoryDataWithSampling']

    print(len(entries), len(data))
    assert len(data) == len(entries)

    # Create dataframes
    expected_df = pd.DataFrame(entries).drop(columns='status').rename(
        columns={'timestamp': 'expected_ts', 'value': 'expected_value'})
    expected_df['expected_ts'] = pd.to_datetime(
        expected_df['expected_ts'], infer_datetime_format=True)
    expected_df['expected_value'] = pd.to_numeric(
        expected_df['expected_value'])
    got_df = pd.DataFrame(data).drop(columns='id').rename(
        columns={'ts': 'got_ts', 'floatvalue': 'got_value'})
    got_df['got_ts'] = pd.to_datetime(
        got_df['got_ts'], infer_datetime_format=True)
    df = expected_df.join(got_df)

    # Check data variation
    df2 = pd.DataFrame()
    df2['d_ts'] = (df['got_ts'] - df['expected_ts']).dt.total_seconds()
    df2['d_value'] = df['got_value'] - df['expected_value']
    avg_thruput = np.mean(upload_thruput)
    print('Upload throughput:', avg_thruput)
    print('Download throughput:', len(data) / r.elapsed.total_seconds())
    print('Download throughput (true):', len(data) / download_elapsed_true)

    # Plot
    plt.subplot(2, 2, 1)
    plt.plot(upload_thruput)
    plt.axhline(y=avg_thruput, linestyle='dashed')
    plt.title('Upload throughput')
    plt.ylabel('samples/second')
    plt.subplot(2, 2, 3)
    df2['d_ts'].plot(kind='hist')
    plt.title('Timestamp variation')
    plt.subplot(2, 2, 4)
    df2['d_value'].plot(kind='hist')
    plt.title('Float variation')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    token = get_token("test", "smtamu_group", "parthdave", "parth1234")
    with requests.Session() as s:
        stress(30, 8000, 8000)
