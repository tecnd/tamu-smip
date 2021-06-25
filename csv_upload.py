import sys
from datetime import datetime, timedelta, timezone

import requests

from smip_io import ENDPOINT, MUTATION_ADDDATA, get_token


def csv_upload(file, rate: int) -> None:
    """Reads values from a csv file, adds timestamps at the rate specified, and uploads to SMIP."""
    timestamp = datetime.now(timezone.utc)
    inc = timedelta(seconds=1/rate)
    buf = list()
    token = get_token("test", "smtamu_group", "parthdave", "parth1234")
    with open(file, 'r') as f:
        with requests.Session() as s:
            for val in f:
                data = {'timestamp': timestamp.isoformat(),
                        'value': val.strip(),
                        'status': 0}
                buf.append(data)
                if len(buf) > 5000:
                    r = s.post(ENDPOINT, json={
                        'query': MUTATION_ADDDATA,
                        'variables': {
                            'id': 5356,
                            'entries': buf
                        }
                    }, headers={"Authorization": f"Bearer {token}"})
                    r.raise_for_status()
                    buf.clear()
                timestamp += inc
            if buf:
                r = s.post(ENDPOINT, json={
                    'query': MUTATION_ADDDATA,
                    'variables': {
                        'id': 5356,
                        'entries': buf
                    }
                }, headers={"Authorization": f"Bearer {token}"})
                r.raise_for_status()
                buf.clear()


if __name__ == "__main__":
    csv_upload(sys.argv[1], int(sys.argv[2]))
