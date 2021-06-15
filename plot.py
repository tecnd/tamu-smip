from datetime import datetime, timedelta
import time

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
from dash.dependencies import Input, Output, State

import requests
from auth import update_token

ENDPOINT = "https://smtamu.cesmii.net/graphql"

query = '''
query GetData($startTime: Datetime, $endTime: Datetime) {
  getRawHistoryDataWithSampling(
    endTime: $endTime
    startTime: $startTime
    ids: "5356"
    maxSamples: 0
  ) {
    floatvalue
    ts
  }
}
'''

# token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic210YW11X2dyb3VwIiwiZXhwIjoxNjIzMjc4NzU1LCJ1c2VyX25hbWUiOiJwYXJ0aGRhdmUiLCJhdXRoZW50aWNhdG9yIjoidGVzdCIsImF1dGhlbnRpY2F0aW9uX2lkIjoiMTA5NTEiLCJpYXQiOjE2MjMyNzY5NTUsImF1ZCI6InBvc3RncmFwaGlsZSIsImlzcyI6InBvc3RncmFwaGlsZSJ9.mqiiNxFPegL3b45-FWTXiAYpHjIBc5xLCc5hruhTkEg'

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(
    html.Div([
        html.H4('Dashboard'),
        html.Div(id='live-update-text'),
        dcc.Graph(id='live-update-graph',animate=False),
        dcc.Interval(
            id='interval-component',
            interval=2*1000, # in milliseconds
            n_intervals=0
        ),
        dcc.Store(id='jwt', storage_type='session', data=''),
        dcc.Store(id='data', data=[{'ts': datetime.utcnow().isoformat() + '+0000', 'floatvalue': '0'}])
    ])
)

# Callback to display the current time
@app.callback(Output('live-update-text', 'children'),
              Input('interval-component', 'n_intervals'))
def update_metrics(n):
    now = datetime.now().isoformat()
    style = {'padding': '5px', 'fontSize': '16px'}
    return html.Span(now, style=style)

# Callback to get data and draw the graph every second
@app.callback(Output('live-update-graph', 'figure'),
              Output('jwt', 'data'),
              Output('data', 'data'),
              Input('interval-component', 'n_intervals'),
              State('jwt', 'data'),
              State('data', 'data'))
def update_graph_live(n, token, data):
    end_time = datetime.utcnow() - timedelta(seconds=0.5)
    start_time = end_time - timedelta(seconds=1)
    called = datetime.now()
    # Check token is still valid
    token = update_token(token, 'test', 'smtamu_group', 'parthdave', 'parth1234')
    # Query data from SMIP
    r = requests.post(ENDPOINT, json={
        "query": query,
        "variables": {
            "endTime": end_time.isoformat(),
            "startTime": start_time.isoformat()
        }
    }, headers={"Authorization": f"Bearer {token}"})
    data_get = r.json()['data']['getRawHistoryDataWithSampling']
    print(len(data_get))
    query_response = datetime.now()
    data_get.pop(0)
    data.extend(data_get)
    data = data[-5000:]
    # Ideally this would work, but if timestamp is at 0 microseconds then server returns time in %S%z instead of %S.%f%z, which breaks things
    # time_list = [datetime.strptime(i['ts'], '%Y-%m-%dT%H:%M:%S.%f%z') for i in data]
    data_start = datetime.now()
    time_list = list()
    for item in data:
        ts = item['ts']
        fmt = ''
        if len(ts) > 26:
            fmt = '%Y-%m-%dT%H:%M:%S.%f%z'
        elif len(ts) == 25:
            fmt = '%Y-%m-%dT%H:%M:%S%z'
        else:
            raise ValueError('Unrecognized timestamp: ' + ts)
        time_list.append(datetime.strptime(ts, fmt))
    val_list = [i['floatvalue'] for i in data]
    data_processed = datetime.now()
    # Make the plot
    fig = px.line(x=time_list, y=val_list, range_x=[end_time - timedelta(seconds=20), end_time])
    figure_drawn = datetime.now()
    print(datetime.now(), 'Total', figure_drawn - called, 'Query', query_response - called, 'Data processing', data_processed - query_response, 'Plotting', figure_drawn - data_processed, 'Buffer size', len(data))
    return fig, token, data

if __name__ == '__main__':
    app.run_server(debug=True)
