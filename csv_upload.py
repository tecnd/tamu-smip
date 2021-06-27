import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from smip_io import ENDPOINT, MUTATION_ADDDATA, get_token


def csv_upload(file, rate: int, id: int) -> None:
    """Reads values from a csv file, adds timestamps at the rate specified, and uploads to SMIP."""
    timestamp = datetime.now(timezone.utc)
    inc = timedelta(seconds=1/rate)
    buf = list()
    token = get_token("test", "smtamu_group", "parthdave", "parth1234")
    with open(file, 'r') as f:
        with requests.Session() as s:
            now = datetime.now()
            future = now + timedelta(seconds=1)
            for val in f:
                data = {'timestamp': timestamp.isoformat(),
                        'value': val.strip(),
                        'status': 0}
                buf.append(data)
                if len(buf) >= rate:
                    r = s.post(ENDPOINT, json={
                        'query': MUTATION_ADDDATA,
                        'variables': {
                            'id': id,
                            'entries': buf
                        }
                    }, headers={"Authorization": f"Bearer {token}"})
                    r.raise_for_status()
                    print(r.elapsed, r.json())
                    buf.clear()
                    time.sleep(
                        max((future - datetime.now()).total_seconds(), 0))
                    future += timedelta(seconds=1)
                timestamp += inc
            if buf:
                r = s.post(ENDPOINT, json={
                    'query': MUTATION_ADDDATA,
                    'variables': {
                        'id': id,
                        'entries': buf
                    }
                }, headers={"Authorization": f"Bearer {token}"})
                r.raise_for_status()
                buf.clear()


if __name__ == "__main__":
    csv_upload(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
