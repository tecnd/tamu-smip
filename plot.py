# Dash imports
import dash
import dash_core_components as dcc
import dash_html_components as html
# Technically we are plotting with plotly, but we can write basic graphs
# as dictionaries so no need to import a whole module
# import plotly.express as px
from dash.dependencies import Input, Output, State
# Library imports
import requests
from datetime import datetime, timedelta, timezone
# Local imports
from auth import update_token
from strptime_fix import strptime_fix

# Define constants
ENDPOINT = "https://smtamu.cesmii.net/graphql"
QUERY = '''
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

# All requests go through a single session for network efficiency
s = requests.Session()

# Page layout stuff
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(
    html.Div([
        html.H4('Dashboard'),
        html.Div(id='live-update-text'),
        dcc.Graph(id='live-update-graph', animate=False, figure={
            'data': [{'x': [], 'y': []}],
            'layout': {
                'xaxis': {'rangemode': 'tozero'},
                'yaxis': {'rangemode': 'tozero'}
            }
        }, config={'displayModeBar': False}),
        dcc.Interval(
            id='interval-component',
            interval=1*1000,  # in milliseconds
            n_intervals=0
        ),
        dcc.Store(id='jwt', storage_type='session', data=''),  # Persistently store JWT
        dcc.Store(id='last_time', data=datetime.now(timezone.utc).isoformat())
    ])
)

# Callback to display the current time


@app.callback(Output('live-update-text', 'children'),
              Input('interval-component', 'n_intervals'))
def update_metrics(n):
    now = datetime.now().isoformat()
    style = {'padding': '5px', 'fontSize': '16px'}
    return html.Span(now, style=style)

# Callback to get data and update the graph every second


@app.callback(Output('live-update-graph', 'extendData'),
              Output('jwt', 'data'),
              Output('last_time', 'data'),
              Input('interval-component', 'n_intervals'),
              State('jwt', 'data'),
              State('last_time', 'data')
              )
def update_graph_live(n, token, last_time):
    called = datetime.now(timezone.utc)
    # 1 sec delay so server has time to add live data
    end_time = called - timedelta(seconds=1)
    # Check if token is still valid
    token = update_token(token, 'test', 'smtamu_group',
                         'parthdave', 'parth1234')
    # Query data from SMIP
    print(datetime.now(), 'start_time', last_time, 'end_time', end_time)
    r = s.post(ENDPOINT, json={
        "query": QUERY,
        "variables": {
            "endTime": end_time.isoformat(),
            "startTime": last_time
        }
    }, headers={"Authorization": f"Bearer {token}"}, timeout=1)
    r.raise_for_status()
    data = r.json()['data']['getRawHistoryDataWithSampling']
    print(datetime.now(), 'Responses', len(data))
    # Take timestamps and values out of response, format

    # Used for measuring performance
    start_processing = datetime.now(timezone.utc)

    # SMIP always returns one entry before the start time, we don't need this
    data.pop(0)
    # Ideally this would work, but if timestamp is at 0 microseconds then server
    # returns time with %S%z instead of %S.%f%z, which breaks things
    #   UPDATE: Marked as SMIP bug, hopefully fixed some day
    # time_list = [datetime.strptime(i['ts'], '%Y-%m-%dT%H:%M:%S.%f%z') for i in data]
    time_list = [strptime_fix(i['ts']) for i in data]
    val_list = [i['floatvalue'] for i in data]

    # Used for measuring performance
    data_processed = datetime.now(timezone.utc)
    print(datetime.now(), 'Total', data_processed - called, 'Query', r.elapsed,
          'Processing', data_processed - start_processing)

    return (dict(x=[time_list], y=[val_list]), [0], 30000), token, end_time.isoformat()


if __name__ == '__main__':
    app.run_server(debug=True)
