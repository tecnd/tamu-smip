from datetime import datetime
from time import perf_counter, sleep
from math import nan

import requests
import matplotlib.pyplot as plt

from smip_io import ENDPOINT, QUERY_GETDATA, get_token

token = get_token("test", "smtamu_group", "parthdave", "parth1234")
print(token[-6:])
elapsed_times = list()
start_times = list()
try:
    with requests.Session() as s:
        while True:
            start_ts = datetime.now()
            print(start_ts, 'Starting little download request')
            start_timer = perf_counter()
            try:
                r = s.post(ENDPOINT, json={
                    'query': QUERY_GETDATA,
                    'variables': {
                        'endTime': '2021-07-01T21:22:53.000000+00:00',
                        'startTime': '2021-07-01T21:22:52.000000+00:00',
                        'ids': [5356]
                    }
                }, headers={'Authorization': f'Bearer {token}'})
            except requests.exceptions.ConnectionError:
                print(datetime.now(), 'Connection failed')
                start_times.append(start_ts)
                elapsed_times.append(nan)
                continue
            elapsed = perf_counter() - start_timer
            start_times.append(start_ts)
            elapsed_times.append(elapsed)
            print(datetime.now(), f'Got {len(r.content)} bytes in {elapsed} seconds')
            sleep(1)
except KeyboardInterrupt:
    plt.plot(start_times, elapsed_times, 'o-')
    plt.xlabel('Time started')
    plt.ylabel('Elapsed time (s)')
    plt.title('Little queries elapsed times')
    plt.show()
    raise
