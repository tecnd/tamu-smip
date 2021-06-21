from auth import update_token
from datetime import datetime, timedelta, timezone
import time
import numpy as np
import pandas as pd
import requests

ENDPOINT = "https://smtamu.cesmii.net/graphql"

MUTATION = """
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


def sin_plot(freq1: float, freq2: float) -> None:
    token = ''
    t = 0
    with requests.Session() as s:
        while True:
            now = datetime.now(timezone.utc)
            future = now + timedelta(seconds=1)
            token = update_token(
                token, "test", "smtamu_group", "parthdave", "parth1234")
            time_range = pd.date_range(now, future, periods=1024)
            val_range = np.arange(t, t+1024, dtype=np.single)
            val_range *= 2*np.pi/1024
            val_range = np.sin(freq1 * val_range) + 0.5 * \
                np.sin(freq2 * val_range)
            payload = [{'timestamp': ts.isoformat(), 'value': str(val), 'status': 0}
                       for ts, val in zip(time_range, val_range)]
            r = s.post(ENDPOINT, json={
                "query": MUTATION,
                "variables": {
                    "id": 5356,
                    "entries": payload
                }
            }, headers={"Authorization": f"Bearer {token}"})
            print(r.elapsed, r.json())
            t += 1024
            freq2 += 10
            if freq2 > 500:
                freq2 = 0
            time.sleep(
                max((future - datetime.now(timezone.utc)).total_seconds(), 0))


if __name__ == "__main__":
    sin_plot(100, 80)
