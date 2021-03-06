import logging
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

from smip_io import add_data_async, get_token


def sin_plot(rate: int, freq1: float) -> None:
    token = get_token("test", "smtamu_group", "parthdave", "parth1234")
    t = 0
    with requests.Session() as s:
        now = datetime.now(timezone.utc)
        while True:
            future = now + timedelta(seconds=1)

            time_range = pd.date_range(now, future, periods=rate)
            val_range = np.arange(t, t+rate, dtype=np.single)
            val_range *= 2*np.pi/rate
            val_range = np.sin(freq1 * val_range)
            payload = [{'timestamp': ts.isoformat(), 'value': str(val), 'status': 0}
                       for ts, val in zip(time_range, val_range)]
            add_data_async(5356, payload, token, s)
            t += rate
            now = future
            rest = future - datetime.now(timezone.utc)
            time.sleep(max(rest.total_seconds(), 0))
            logging.info('Sleeping for %s', rest)


if __name__ == "__main__":
    logging.basicConfig(filename='sin_plotter.log',
                        format='%(asctime)s %(levelname)s %(message)s', filemode='w', level=logging.DEBUG)
    sin_plot(15000, 20)
