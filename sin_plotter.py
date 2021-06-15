from auth import update_token
import time, datetime
import math
import requests, jwt

ENDPOINT = "https://smtamu.cesmii.net/graphql"

mutation = """
mutation AddData($id: BigInt, $entries: [TimeSeriesEntryInput]) {
  replaceTimeSeriesRange(
    input: {
        attributeOrTagId: $id,
        entries: $entries
    }
  ) {
    json
  }
}
"""

def sin_plot():
    token = ''
    with requests.Session() as s:
        for i in range(10):
            now = datetime.datetime.utcnow()
            next_time = now + datetime.timedelta(seconds=1)
            # Check if JWT is still valid
            token = update_token(token, 'test', 'smtamu_group', 'parthdave', 'parth1234')
            r = s.post(ENDPOINT, json={
                "query": mutation,
                "variables": {
                    "id": 5356,
                    "entries": {
                        "timestamp": now.isoformat(),
                        "value": str(math.sin(datetime.datetime.timestamp(now))),
                        "status": 0
                    }
                }
            }, headers={"Authorization": f"Bearer {token}"})
            # Receive response
            print(now, r.json(), 'Elapsed', r.elapsed)
            # Sleep until next cycle
            time.sleep(datetime.timedelta.total_seconds(next_time - datetime.datetime.utcnow()))
            

if __name__ == "__main__":
    sin_plot()