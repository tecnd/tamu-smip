import sys
from datetime import datetime, timedelta, timezone
from typing import List

import nidaqmx
import requests
from nidaqmx.constants import AcquisitionType, LoggingMode, LoggingOperation

from smip_io import add_data, update_token


def read_data(sample_rate: int, channels: List[str], ids: List[int]):
    token = ''
    time_step = timedelta(seconds=1/sample_rate)
    with requests.Session() as s:
        with nidaqmx.Task() as task:
            task.in_stream.configure_logging(
                'log.tdms', logging_mode=LoggingMode.LOG_AND_READ, operation=LoggingOperation.CREATE_OR_REPLACE)
            for channel in channels:
                task.ai_channels.add_ai_voltage_chan(channel)
            task.timing.cfg_samp_clk_timing(
                sample_rate, sample_mode=AcquisitionType.CONTINUOUS)
            # Supposed to set the buffer, not sure if actually takes effect
            task.timing.samp_quant_samp_per_chan = 200000
            task.start()
            ts = datetime.now(timezone.utc)
            while True:
                # Take 1 second of samples
                buf = task.read(sample_rate)
                # Format each sample into a GraphQL TimeSeriesEntryInput object
                points = [[] for _ in range(len(ids))]
                for samples in zip(*buf):
                    for i in range(len(ids)):
                        points[i].append({
                            "timestamp": ts.isoformat(),
                            "value": str(samples[i]),
                            "status": 0
                        })
                    ts += time_step
                # Test JWT validity
                token = update_token(
                    token, 'test', 'smtamu_group', 'parthdave', 'parth1234')
                # Batch upload
                r_list = [add_data(id, entries, token, session=s)
                          for (entries, id) in zip(points, ids)]
                # Receive response
                for r in r_list:
                    print(datetime.now(), r.json(), 'Elapsed', r.elapsed)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        read_data(1024, ['cDAQ3Mod4/ai0', 'cDAQ3Mod3/ai0'], [5356, 5366])
    else:
        mod_list = sys.argv[2].split(',')
        id_list = [int(id) for id in sys.argv[3].split(',')]
        read_data(int(sys.argv[1]), mod_list, id_list)
