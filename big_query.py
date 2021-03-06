from datetime import datetime
from time import perf_counter

from smip_io2 import SMIP

conn = SMIP("https://smtamu.cesmii.net/graphql", "test",
            "smtamu_group", "parthdave", "parth1234")
print(conn.token[-6:])
print(datetime.now(), 'Starting big download request')
start_timer = perf_counter()
r = conn.get_data(end_time='2021-07-01T21:22:51.984520+00:00',
                  start_time='2021-07-01T21:21:51.984520+00:00',
                  ids=[5356])
elapsed = perf_counter() - start_timer
print(len(r.json()['data']['getRawHistoryDataWithSampling']))
print(datetime.now(), f'Got {len(r.content)} bytes in {elapsed} seconds')
