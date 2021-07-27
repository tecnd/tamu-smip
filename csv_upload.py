import sys
from datetime import datetime, timezone

from smip_io2 import SMIP


def csv_upload(file, rate: int, id: int) -> None:
    """Reads values from a csv file, adds timestamps at the rate specified, and uploads to SMIP."""
    conn = SMIP("https://smtamu.cesmii.net/graphql", "test",
                "smtamu_group", "parthdave", "parth1234")
    with open(file, 'r') as f:
        conn.add_data_from_ts(id=id,
                              entries=f.readlines(),
                              startTime=datetime.now(timezone.utc),
                              freq=rate,
                              async_mode=True)


if __name__ == "__main__":
    csv_upload(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
