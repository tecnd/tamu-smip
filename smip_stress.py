from smip_io import MUTATION_ADDDATA, QUERY_GETDATA, get_token, ENDPOINT
import pandas as pd
import requests
from random import random
from datetime import datetime, timedelta, timezone
from time import perf_counter
import matplotlib.pyplot as plt

def batcher(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

def stress(duration:int, rate: int, batch_size: int) -> None:
    """Sends data to SMIP for the specified duration, rate, and batch size and checks integrity"""
    global s
    global token
    now = datetime.now(timezone.utc)
    future = now + timedelta(seconds=duration)
    print(future)
    time_range = pd.date_range(start=now, end=future, periods=rate*duration)
    entries = [{'timestamp': ts.isoformat(), 'value':str(random()), 'status': 0} for ts in time_range]
    upload_times = list()
    start_time = perf_counter()
    for batch in batcher(entries, batch_size):
        r = s.post(ENDPOINT, json={
            'query': MUTATION_ADDDATA,
            'variables':{
                "id": 5356,
                "entries": batch
            }
        }, headers={'Authorization': f'Bearer {token}'})
        r.raise_for_status()
        print(r.elapsed, r.json())
        upload_times.append(len(batch) / r.elapsed.total_seconds())

    elapsed = perf_counter() - start_time
    print('Upload:', elapsed, f'{duration / elapsed}x realtime')

    r = s.post(ENDPOINT, json={
        "query": QUERY_GETDATA,
        "variables": {
            "endTime": future.isoformat(),
            "startTime": now.isoformat(),
            "ids": [5356]
        }
    }, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    print('Download:', r.elapsed, f'{duration / r.elapsed.total_seconds()}x realtime')
    data = r.json()['data']['getRawHistoryDataWithSampling']
    
    print(len(entries), len(data))
    assert len(data) == len(entries)

    expected_df = pd.DataFrame(entries).drop(columns='status').rename(columns={'timestamp': 'expected_ts', 'value': 'expected_value'})
    expected_df['expected_ts'] = pd.to_datetime(expected_df['expected_ts'], infer_datetime_format=True)
    expected_df['expected_value'] = pd.to_numeric(expected_df['expected_value'])
    got_df = pd.DataFrame(data).drop(columns='id').rename(columns={'ts': 'got_ts', 'floatvalue': 'got_value'})
    got_df['got_ts'] = pd.to_datetime(got_df['got_ts'], infer_datetime_format=True)
    df = expected_df.join(got_df)
    
    df2 = pd.DataFrame()
    df2['d_ts'] = (df['got_ts'] - df['expected_ts']).dt.total_seconds()
    df2['d_value'] = df['got_value'] - df['expected_value']

    print('Download throughput', len(data) / r.elapsed.total_seconds())
    
    plt.plot(upload_times)
    plt.title('Upload throughput (samples/second)')
    plt.figure()
    df2['d_ts'].plot(kind='hist')
    plt.title('Timestamp variation')
    plt.figure()
    df2['d_value'].plot(kind='hist')
    plt.title('Float variation')
    plt.show()

if __name__ == "__main__":
    token = get_token("test", "smtamu_group", "parthdave", "parth1234")
    with requests.Session() as s:
        stress(30, 1000, 1000)
