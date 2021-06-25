# Standard library imports
import logging
from datetime import datetime, timedelta, timezone

# External imports
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from scipy import signal

# Local imports
from smip_io import ENDPOINT, QUERY_GETDATA, update_token
from strptime_fix import strptime_fix

# Define constants
DEBUG = True

# Set up logging
logging.basicConfig(filename='plot.log', format='%(asctime)s %(levelname)s %(message)s',
                    filemode='w', level=logging.DEBUG)

# All requests go through a single session for network efficiency
s = requests.Session()

# Page layout stuff
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container([
    dbc.Row(
        dbc.Col(html.H1('Dashboard'))
    ),
    dbc.Row(
        dbc.Col(html.P(id='info'))
    ),
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='live-update-graph', animate=False, figure={
                'data': [{'x': [], 'y': []}],
                'layout': {
                    'title': 'Time portrait',
                    'xaxis': {'rangemode': 'tozero'},
                    'yaxis': {'rangemode': 'tozero'},
                    'margin': {'l': 10, 'r': 10, 't': 50, 'b': 50}
                }
            }, config={'displayModeBar': False}),
            daq.NumericInput(  # pylint: disable=not-callable
                id='keep_last',
                label='Show last samples',
                min=10,
                value=1024
            )
        ], lg=4),
        dbc.Col(
            dcc.Graph(id='fft-graph', animate=False, config={'displayModeBar': False}), lg=4
        ),
        dbc.Col([
            dcc.Graph(id='spectrogram', animate=False,
                      config={'displayModeBar': False}),
            dbc.Row([
                dbc.Col([
                    html.P('Frequency bins'),
                    daq.NumericInput(  # pylint: disable=not-callable
                        id='nperseg',
                        min=1,
                        max=1000,
                        value=500
                    )
                ]),
                dbc.Col([
                    html.P('Window type'),
                    dcc.Dropdown(id='window', options=[
                        {'label': 'Boxcar', 'value': 'boxcar'},
                        {'label': 'Triangular', 'value': 'triang'},
                        {'label': 'Blackman', 'value': 'blackman'},
                        {'label': 'Hamming', 'value': 'hamming'},
                        {'label': 'Hann', 'value': 'hann'},
                        {'label': 'Bartlett', 'value': 'bartlett'},
                        {'label': 'Flat top', 'value': 'flattop'},
                        {'label': 'Parzen', 'value': 'parzen'},
                        {'label': 'Bohman', 'value': 'bohman'},
                        {'label': 'Blackman-Harris', 'value': 'blackmanharris'},
                        {'label': 'Nuttall', 'value': 'nuttall'},
                        {'label': 'Bartlett-Hann', 'value': 'barthann'}
                    ], value='hamming', clearable=False)
                ])
            ])
        ], lg=4)
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


@app.callback(Output('intermediate-data', 'data'),
              Output('jwt', 'data'),
              Output('last_time', 'data'),
              Output('info', 'children'),
              Input('interval-component', 'n_intervals'),
              State('jwt', 'data'),
              State('last_time', 'data')
              )
def update_live_data(n, token, last_time):
    """Callback to get data every second."""
    called = datetime.now(timezone.utc)
    # 1 sec delay so server has time to add live data
    end_time = called - timedelta(seconds=1)

    # Initialization and lag prevention
    if last_time is None or end_time - strptime_fix(last_time) > timedelta(seconds=2):
        logging.warning('Falling behind!')
        last_time = end_time.isoformat()

    # Check if token is still valid
    token = update_token(token, 'test', 'smtamu_group',
                         'parthdave', 'parth1234')
    # Query data from SMIP
    logging.info(f'start_time {last_time} end_time {end_time}')
    r = s.post(ENDPOINT, json={
        "query": QUERY_GETDATA,
        "variables": {
            "endTime": end_time.isoformat(),
            "startTime": last_time
        }
    }, headers={"Authorization": f"Bearer {token}"}, timeout=1)
    r.raise_for_status()
    data = r.json()['data']['getRawHistoryDataWithSampling']
    logging.info('Got %s responses', len(data))
    # Take timestamps and values out of response, format

    # Used for measuring performance
    start_processing = datetime.now(timezone.utc)

    # SMIP always returns one entry before the start time, we don't need this
    if data:
        data.pop(0)
    # Ideally this would work, but if timestamp is at 0 microseconds then server
    # returns time with %S%z instead of %S.%f%z, which breaks things
    #   UPDATE: Marked as SMIP bug, hopefully fixed some day
    # time_list = [datetime.strptime(i['ts'], '%Y-%m-%dT%H:%M:%S.%f%z') for i in data]
    time_list = [strptime_fix(i['ts']) for i in data]
    val_list = [i['floatvalue'] for i in data]

    # Used for measuring performance
    data_processed = datetime.now(timezone.utc)
    logging.info('Total %s Query %s Processing %s', data_processed - called, r.elapsed,
                 data_processed - start_processing)

    return {'time_list': time_list, 'val_list': val_list}, token, end_time.isoformat(), \
        f'Last updated {end_time.astimezone()}, received {len(data)} samples in {(data_processed - called).total_seconds()} seconds'


@app.callback(Output('live-update-graph', 'extendData'),
              Input('intermediate-data', 'data'),
              State('keep_last', 'value'))
def update_graph(data, keep_last):
    """Callback that graphs the data."""
    if data is None or not data['val_list']:
        raise PreventUpdate
    return {'x': [data['time_list']], 'y': [data['val_list']]}, [0], keep_last


@app.callback(Output('fft-graph', 'figure'),
              Input('intermediate-data', 'data'))
def update_fft(data):
    """Callback that calculates and plots FFT."""
    if data is None or not data['val_list']:
        raise PreventUpdate
    fig = px.line(x=np.fft.rfftfreq(len(data['val_list']), d=1/1024),
                  y=np.abs(np.fft.rfft(data['val_list'])), log_x=True)
    fig.update_layout(title={
        'text': 'FFT, last second',
        'x': 0.5,
        'xanchor': 'center'
    }, xaxis_rangemode='tozero', xaxis_title='Frequency (Hz)', yaxis_rangemode='tozero', yaxis_title='', margin={'l': 10, 'r': 10, 't': 50, 'b': 50})
    return fig


@app.callback(Output('spectrogram', 'figure'),
              Input('intermediate-data', 'data'),
              State('nperseg', 'value'))
def update_spec(data, nperseg):
    """Callback that calculates and plots spectrogram."""
    if data is None or not data['val_list']:
        raise PreventUpdate
    f, t, Sxx = signal.spectrogram(np.asarray(
        data['val_list']), 1024, nperseg=nperseg, window='hamming')
    fig = go.Figure(data=go.Heatmap(z=Sxx, y=f, x=t))  # type: ignore
    fig.update_layout(title={
        'text': 'Spectrogram, last second',
        'x': 0.5,
        'xanchor': 'center'
    }, margin={'l': 10, 'r': 10, 't': 50, 'b': 50})
    # fig.update_yaxes(type="log")
    return fig


if __name__ == '__main__':
    app.run_server(debug=DEBUG)
