from auth import get_token
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import requests

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

def sin_plot(freq:float, duration:int):
    token = get_token("test", "smtamu_group", "parthdave", "parth1234")
    time_range = pd.date_range(datetime.now(timezone.utc), periods=duration, freq='L')
    val_range = np.arange(0,duration,dtype=np.single)
    val_range *= 2*np.pi/freq
    val_range = np.sin(val_range)
    payload = [{'timestamp': ts.isoformat(), 'value': str(val), 'status': 0} for ts, val in zip(time_range, val_range)]
    r = requests.post(ENDPOINT, json={
        "query": mutation,
        "variables": {
            "id": 5356,
            "entries": payload
        }
    }, headers={"Authorization": f"Bearer {token}"})
    print(r.elapsed, r.json())
        
            

if __name__ == "__main__":
    sin_plot(1000, 5000)