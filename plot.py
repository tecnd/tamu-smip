# Dash imports
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
# Library imports
import requests
from datetime import datetime, timedelta, timezone
import numpy as np
from scipy import signal
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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container([
    dbc.Row(
        dbc.Col(html.H1('Dashboard'), width=12)
    ),
    dbc.Row([
        dbc.Col(
            dcc.Graph(id='live-update-graph', animate=False, figure={
                'data': [{'x': [], 'y': []}],
                'layout': {
                    'title': 'Time portrait, last 5000 samples',
                    'xaxis': {'rangemode': 'tozero'},
                    'yaxis': {'rangemode': 'tozero'}
                }
            }, config={'displayModeBar': False}), md=4
        ),
        dbc.Col(
            dcc.Graph(id='fft-graph', animate=False, config={'displayModeBar': False}), md=4
        ),
        dbc.Col(
            dcc.Graph(id='spectrogram', animate=False, config={'displayModeBar': False}), md=4
        )
    ], no_gutters=True),
    html.Div([
        # Timer to get new data every second
        dcc.Interval(
            id='interval-component',
            interval=1*1000,  # in milliseconds
            n_intervals=0
        ),
        # Store JWT in local memory, saved across browser closes
        dcc.Store(id='jwt', storage_type='local', data=''),
        dcc.Store(id='last_time'),
        dcc.Store(id='intermediate-data')
    ])
], fluid=True)

# Callback to get data every second


@app.callback(Output('intermediate-data', 'data'),
              Output('jwt', 'data'),
              Output('last_time', 'data'),
              Input('interval-component', 'n_intervals'),
              State('jwt', 'data'),
              State('last_time', 'data')
              )
def update_live_data(n, token, last_time):
    called = datetime.now(timezone.utc)
    # 1 sec delay so server has time to add live data
    end_time = called - timedelta(seconds=1)
    
    # Initialization and lag prevention
    if last_time is None or strptime_fix(last_time) - end_time > timedelta(seconds=2):
        last_time = end_time.isoformat()
    
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

    return {'time_list': time_list, 'val_list': val_list}, token, end_time.isoformat()

# Callback that graphs the data


@app.callback(Output('live-update-graph', 'extendData'),
              Input('intermediate-data', 'data'))
def update_graph(data):
    if data is None or not data['val_list']:
        raise PreventUpdate
    return {'x': [data['time_list']], 'y':[data['val_list']]}, [0], 5000

# Callback that calculates and plots FFT

@app.callback(Output('fft-graph', 'figure'),
              Input('intermediate-data', 'data'))
def update_fft(data):
    if data is None or not data['val_list']:
        raise PreventUpdate
    fig = px.line(x=np.fft.rfftfreq(len(data['val_list']), d=1/1000),
                  y=np.abs(np.fft.rfft(data['val_list'])), log_x=True)
    fig.update_layout(title={
        'text': 'FFT, last second',
        'x': 0.5,
        'xanchor': 'center'
    }, xaxis_rangemode='tozero', yaxis_rangemode='tozero')
    return fig

# Callback that calculates and plots spectrogram

@app.callback(Output('spectrogram', 'figure'),
              Input('intermediate-data', 'data'))
def update_spec(data):
    if data is None or not data['val_list']:
        raise PreventUpdate
    f, t, Sxx = signal.spectrogram(np.asarray(data['val_list']), 1000)
    fig = go.Figure(data=go.Heatmap(z=Sxx, y=f, x=t))
    fig.update_layout(title={
        'text': 'Spectrogram, last second',
        'x': 0.5,
        'xanchor': 'center'
    })
    # fig.update_yaxes(type="log")
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
