from datetime import datetime
from time import perf_counter

import requests

from smip_io import ENDPOINT, QUERY_GETDATA, get_token

token = get_token("test", "smtamu_group", "parthdave", "parth1234")
print(token[-6:])
print(datetime.now(), 'Starting big download request')
start_timer = perf_counter()
r = requests.post(ENDPOINT, json={
    'query': QUERY_GETDATA,
    'variables': {
        'endTime': '2021-07-01T21:22:51.984520+00:00',
        'startTime': '2021-07-01T21:21:51.984520+00:00',
        'ids': [5356]
    }
}, headers={'Authorization': f'Bearer {token}'})
elapsed = perf_counter() - start_timer
print(len(r.json()['data']['getRawHistoryDataWithSampling']))
print(datetime.now(), f'Got {len(r.content)} bytes in {elapsed} seconds')
