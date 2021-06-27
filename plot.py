# Standard library imports
import logging
from datetime import datetime, timedelta, timezone

# External imports
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
# import plotly.express as px
import plotly.graph_objects as go
import requests
from dash.dependencies import MATCH, Input, Output, State
from dash.exceptions import PreventUpdate
from scipy import signal

# Local imports
from smip_io import ENDPOINT, QUERY_GETDATA, update_token
from strptime_fix import strptime_fix

# Define constants
GRAPH_MARGIN = {'l': 40, 'r': 10, 't': 50, 'b': 50}

# Set up logging
logging.basicConfig(filename='plot.log', format='%(asctime)s %(levelname)s %(message)s',
                    filemode='w', level=logging.DEBUG)

# All requests go through a single session for network efficiency
s = requests.Session()

# Page layout stuff


def _graphs(i: int) -> dbc.Col:
    return dbc.Col([
        dcc.Graph(id={'type': 'time-graph', 'index': i}, animate=False, figure={
            'data': [{'x': [], 'y': []}],
            'layout': {
                'title': 'Time portrait',
                'xaxis': {'rangemode': 'tozero'},
                'yaxis': {'rangemode': 'tozero'},
                'margin': GRAPH_MARGIN
            }
        }, style={'height': '30vh'}, config={'displayModeBar': False}),
        dcc.Graph(id={'type': 'fft-graph', 'index': i}, animate=False, figure={
            'data': [{'x': [], 'y': []}],
            'layout': {
                'title': {
                    'text': 'FFT, last second',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                'xaxis': {'title': 'Frequency (Hz)', 'rangemode': 'tozero'},
                'yaxis': {'rangemode': 'tozero'},
                'margin': GRAPH_MARGIN
            }
        }, style={'height': '30vh'}, config={'displayModeBar': False}),
        dcc.Graph(id={'type': 'spectrogram', 'index': i}, animate=False, style={'height': '30vh'},
                  config={'displayModeBar': False})
    ], lg=4)


def _settings(i: int, id: int) -> dbc.Col:
    return dbc.Col(
        dbc.FormGroup([
            dbc.Label('ID', html_for=f'id{i}'),
            dbc.Input(id=f'id{i}', type="number",
                      min=0, max=10000, value=id),
            dbc.Label('Show last samples', html_for={
                      'type': 'keep_last', 'index': i}),
            dbc.Input(id={'type': 'keep_last', 'index': i}, type="number",
                      min=10, max=10000, value=1024),
            dbc.Label('Frequency bins', html_for={
                      'type': 'nperseg', 'index': i}),
            dbc.Input(id={'type': 'nperseg', 'index': i}, type="number",
                      min=1, max=1000, value=250),
            dbc.Label('Window type', html_for={'type': 'window', 'index': i}),
            dbc.Select(id={'type': 'window', 'index': i}, options=[
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
            ], value='hamming')
        ])
    )


app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                meta_tags=[{
                    "name": "viewport",
                    "content": "width=device-width, initial-scale=1"
                }])
app.layout = dbc.Container([
    dbc.Row(
        dbc.Col(html.H1('Dashboard'))
    ),
    dbc.Row(
        dbc.Col(html.P(id='info'))
    ),
    dbc.Row([
        _graphs(1),
        _graphs(2),
        dbc.Col([
            dbc.Row([_settings(1, 5356), _settings(2, 5366)]),
            html.Hr(),
            html.P('Other stuff goes here')
        ], lg=4)
    ]),
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
        dcc.Store(id={'type': 'intermediate-data', 'index': 1}),
        dcc.Store(id={'type': 'intermediate-data', 'index': 2})
    ])
], fluid=True)


@app.callback(Output({'type': 'intermediate-data', 'index': 1}, 'data'),
              Output({'type': 'intermediate-data', 'index': 2}, 'data'),
              Output('jwt', 'data'),
              Output('last_time', 'data'),
              Output('info', 'children'),
              Input('interval-component', 'n_intervals'),
              State('jwt', 'data'),
              State('last_time', 'data'),
              State('id1', 'value'),
              State('id2', 'value')
              )
def update_live_data(n, token, last_time, id1, id2):
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
            "startTime": last_time,
            "ids": [id1, id2]
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

    # Unpack data
    def unpack(id: int) -> dict:
        """Unpacks return data into time and value lists"""
        time_list = [i['ts'] for i in data if int(i['id']) == id]
        val_list = [i['floatvalue'] for i in data if int(i['id']) == id]

        # Measure sampling rate
        rate = float('nan')
        if len(time_list) > 1:
            rate = (strptime_fix(time_list[1])
                    - strptime_fix(time_list[0])).total_seconds()
        return {'time_list': time_list, 'val_list': val_list, 'rate': rate}

    # Used for measuring performance
    data_processed = datetime.now(timezone.utc)
    logging.info('Total %s Query %s Processing %s', data_processed - called, r.elapsed,
                 data_processed - start_processing)

    return unpack(id1), unpack(id2), token, end_time.isoformat(), \
        f'Last updated {end_time.astimezone()}, received {len(data)} samples in {(data_processed - called).total_seconds()} seconds'


@app.callback(Output({'type': 'time-graph', 'index': MATCH}, 'extendData'),
              Input({'type': 'intermediate-data', 'index': MATCH}, 'data'),
              State({'type': 'keep_last', 'index': MATCH}, 'value'))
def update_graph(data, keep_last):
    """Callback that graphs the data."""
    if data is None or not data['val_list']:
        raise PreventUpdate
    if keep_last is None:
        keep_last = 1024
    return {'x': [data['time_list']], 'y': [data['val_list']]}, [0], keep_last


@app.callback(Output({'type': 'fft-graph', 'index': MATCH}, 'extendData'),
              Input({'type': 'intermediate-data', 'index': MATCH}, 'data'))
def update_fft(data):
    """Callback that calculates and plots FFT."""
    if data is None or data['rate'] is None:
        raise PreventUpdate
    x = np.fft.rfftfreq(len(data['val_list']), d=data['rate'])[10:]
    y = np.abs(np.fft.rfft(data['val_list']))[10:]
    return {'x': [x], 'y': [y]}, [0], len(y)


@app.callback(Output({'type': 'spectrogram', 'index': MATCH}, 'figure'),
              Input({'type': 'intermediate-data', 'index': MATCH}, 'data'),
              State({'type': 'nperseg', 'index': MATCH}, 'value'),
              State({'type': 'window', 'index': MATCH}, 'value'))
def update_spec(data, nperseg, window):
    """Callback that calculates and plots spectrogram."""
    if data is None or data['rate'] is None:
        raise PreventUpdate
    f, t, Sxx = signal.spectrogram(np.asarray(
        data['val_list']), round(1/data['rate']), nperseg=nperseg, window=window)
    fig = go.Figure(data=go.Heatmap(z=Sxx, y=f, x=t))  # type: ignore
    fig.update_layout(title={
        'text': 'Spectrogram, last second',
        'x': 0.5,
        'xanchor': 'center'
    }, margin=GRAPH_MARGIN)
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
