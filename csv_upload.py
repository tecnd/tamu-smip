import sys
import time
from concurrent.futures import as_completed
from datetime import datetime, timedelta, timezone

from requests_futures.sessions import FuturesSession

from smip_io import add_data, batcher, get_token


def csv_upload(file, rate: int, id: int) -> None:
    """Reads values from a csv file, adds timestamps at the rate specified, and uploads to SMIP."""
    timestamp = datetime.now(timezone.utc)
    inc = timedelta(seconds=1/rate)
    buf = list()
    token = get_token("test", "smtamu_group", "parthdave", "parth1234")

    def _batch_upload():
        posts = [add_data(id, batch, token, s) for batch in batcher(buf, 1000)]
        for res in as_completed(posts):  # type: ignore
            resp = res.result()
            print(datetime.now(), resp.elapsed, resp.json())  # type: ignore
        buf.clear()
    with open(file, 'r') as f:
        with FuturesSession() as s:
            now = datetime.now()
            future = now + timedelta(seconds=1)
            for val in f:
                data = {'timestamp': timestamp.isoformat(),
                        'value': val.strip(),
                        'status': 0}
                buf.append(data)
                if len(buf) >= rate:
                    _batch_upload()
                    time.sleep(
                        max((future - datetime.now()).total_seconds(), 0))
                    future += timedelta(seconds=1)
                timestamp += inc
            if buf:
                _batch_upload()
                buf.clear()


if __name__ == "__main__":
    csv_upload(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
