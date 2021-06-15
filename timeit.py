from auth import get_token
import time, datetime
import requests, jwt

ENDPOINT = "https://smtamu.cesmii.net/graphql"

query = '''
query GetData($startTime: Datetime, $endTime: Datetime) {
  getRawHistoryDataWithSampling(
    endTime: $endTime
    startTime: $startTime
    ids: "5356"
    maxSamples: 0
  ) {
    floatvalue
    ts
  }
}
'''

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic210YW11X2dyb3VwIiwiZXhwIjoxNjIzMjc4NzU1LCJ1c2VyX25hbWUiOiJwYXJ0aGRhdmUiLCJhdXRoZW50aWNhdG9yIjoidGVzdCIsImF1dGhlbnRpY2F0aW9uX2lkIjoiMTA5NTEiLCJpYXQiOjE2MjMyNzY5NTUsImF1ZCI6InBvc3RncmFwaGlsZSIsImlzcyI6InBvc3RncmFwaGlsZSJ9.mqiiNxFPegL3b45-FWTXiAYpHjIBc5xLCc5hruhTkEg'

def timeit():
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(minutes=1)

    r = requests.post(ENDPOINT, json={
        "query": query,
        "variables": {
            "endTime": end_time.isoformat(),
            "startTime": start_time.isoformat()
        }
    }, headers={"Authorization": f"Bearer {token}"})
    data = r.json()['data']['getRawHistoryDataWithSampling']
    # Ideally this would work, but if timestamp is at 0 microseconds then server returns time in %S%z instead of %S.%f%z, which breaks things
    # time_list = [datetime.datetime.strptime(i['ts'], '%Y-%m-%dT%H:%M:%S.%f%z') for i in data]
    time_list = list()
    for item in data:
        ts = item['ts']
        fmt = ''
        if len(ts) > 26:
            fmt = '%Y-%m-%dT%H:%M:%S.%f%z'
        elif len(ts) == 25:
            fmt = '%Y-%m-%dT%H:%M:%S%z'
        else:
            raise ValueError('Unrecognized timestamp: ' + ts)
        time_list.append(datetime.datetime.strptime(ts, fmt))
    val_list = [i['floatvalue'] for i in data]
    
    print(time_list)
    print(val_list)

if __name__ == '__main__':
    timeit()