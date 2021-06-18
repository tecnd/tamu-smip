import math
from datetime import datetime, timedelta, timezone
import requests
from auth import update_token
import nidaqmx
# import matplotlib.pyplot as plt

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

def read_data(sample_rate:int, duration:int, channel:str, id:int):
    token = ''
    samples_to_take = math.floor(sample_rate * duration)
    time_step = timedelta(seconds=1/sample_rate)
    with requests.Session() as s:
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(channel)
            task.timing.cfg_samp_clk_timing(sample_rate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)
            task.timing.samp_quant_samp_per_chan = 200000 # Supposed to set the buffer, not sure if actually takes effect
            task.start()
            # x = list()
            ts = datetime.now(timezone.utc)
            while samples_to_take > 0:
                # Take 1 second of samples
                if samples_to_take > sample_rate:
                    buf = task.read(sample_rate)
                else:
                    buf = task.read(samples_to_take)
                # Format each sample into a GraphQL TimeSeriesEntryInput object
                points = list()
                for sample in buf:
                    points.append({
                        "timestamp": ts.isoformat(),
                        "value": str(sample),
                        "status": 0
                    })
                    ts += time_step
                # Test JWT validity
                token = update_token(token, 'test', 'smtamu_group', 'parthdave', 'parth1234')
                # Batch upload
                r = s.post(ENDPOINT, json={
                    "query": mutation,
                    "variables": {
                        "id": id,
                        "entries": points
                    }
                }, headers={"Authorization": f"Bearer {token}"})
                # Receive response
                print(datetime.now(), r.json(), 'Elapsed', r.elapsed)
                samples_to_take = samples_to_take - sample_rate
                # Plot locally
                # x.extend(buf)
                # plt.cla()
                # plt.plot(x)
                # plt.pause(0.01)
            task.stop()
    
if __name__ == '__main__':
    # plt.ion()
    read_data(1000, 60, 'cDAQ3Mod4/ai0', 5356)
    # plt.show(block=True)
    