import sys
from smip_io import update_token
from datetime import datetime, timedelta, timezone


def csv_upload(file, rate: int) -> None:
    """Reads values from a csv file, adds timestamps at the rate specified, and uploads to SMIP."""
    timestamp = datetime.now(timezone.utc)
    inc = timedelta(seconds=1/rate)
    buf = list()
    with open(file, 'r') as f:
        for val in f:
            data = {'timestamp': timestamp.isoformat(),
                    'val': val.strip(),
                    'status': 0}
            buf.append(data)
            if len(buf) > 5000:
                # TODO: upload data and clear buf
                pass
            timestamp += inc


if __name__ == "__main__":
    csv_upload(sys.argv[1], 1000)
