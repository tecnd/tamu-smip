# Standard library imports
import logging
from datetime import datetime, timedelta, timezone
from math import nan
from time import perf_counter
from typing import List

# External imports
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import matlab
import matlab.engine
import numpy as np
# import plotly.express as px
import plotly.graph_objects as go
import requests
from dash.dependencies import MATCH, Input, Output, State
from dash.exceptions import PreventUpdate
from pandas import to_datetime
from scipy import signal

# Local imports
from smip_io import get_data, update_token
from strptime_fix import strptime_fix

# Define constants
GRAPH_MARGIN = {'l': 40, 'r': 10, 't': 50, 'b': 50}

# Set up logging
fh = logging.FileHandler(filename='plot.log', mode='w')
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=logging.DEBUG,
                    handlers=[fh, sh])

# All requests go through a single session for network efficiency
s = requests.Session()

# Start MATLAB engine
eng = matlab.engine.start_matlab()

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
        dbc.Form([
            dbc.FormGroup([
                dbc.Label('ID', html_for=f'id{i}'),
                dbc.Input(id=f'id{i}', type="number",
                          min=0, max=10000, value=id)
            ]),
            dbc.FormGroup([
                dbc.Label('Show last samples', html_for={
                          'type': 'keep_last', 'index': i}),
                dbc.Input(id={'type': 'keep_last', 'index': i}, type="number",
                          min=10, max=10000, value=1024, persistence=True)
            ]),
            dbc.FormGroup([
                dbc.Label('Frequency bins', html_for={
                          'type': 'nperseg', 'index': i}),
                dbc.Input(id={'type': 'nperseg', 'index': i}, type="number",
                          min=1, max=1000, value=250, persistence=True)
            ]),
            dbc.FormGroup([
                dbc.Label('Window type', html_for={
                          'type': 'window', 'index': i}),
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
                ], value='hamming', persistence=True)
            ])
        ])
    )


def _FormGroupMaker(labels: List[str]) -> List[dbc.FormGroup]:
    """Internal function to make lists of FormGroups from a list of string labels."""
    groups = list()
    for label in labels:
        slug = ''.join(ch for ch in label if ch.isalnum())
        fg = dbc.FormGroup([
            dbc.Label(label, html_for=slug),
            dbc.Input(id=slug, disabled=True)
        ])
        groups.append(fg)
    return groups


app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                meta_tags=[{
                    "name": "viewport",
                    "content": "width=device-width, initial-scale=1"
                }])
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1('Dashboard')),
        dbc.Col(html.P(id='info'), className='col-md-auto'),
        dbc.Col([
            dbc.Button('Settings', id='settings', outline=False,
                color='primary', className='float-right mt-2'),
            dbc.Button('Power', id='power', outline=True,
                color='primary', className='float-right mt-2 mr-2')
        ])
    ]),
    dbc.Row([
        _graphs(1),
        _graphs(2),
        dbc.Col([
            dbc.Collapse(
                dbc.Row([_settings(1, 5356), _settings(2, 5366)], form=True),
                id='collapse', is_open=True
            ),
            html.Hr(),
            html.Form([
                dbc.Row([
                    dbc.Col(_FormGroupMaker(['Elapsed Time'])),
                    dbc.Col(_FormGroupMaker(['Machine State']))
                ], form=True),
                html.Hr(),
                html.H5('Quality Metrics'),
                dbc.Row([
                    dbc.Col(_FormGroupMaker(
                        ['Surface Roughness Ra (um)', 'Grinding Burns'])),
                    dbc.Col(_FormGroupMaker(['Anomalous Parts', 'Good Parts']))
                ], form=True),
                html.Hr(),
                html.H5('Productivity Metrics'),
                dbc.Row([
                    dbc.Col(_FormGroupMaker(['Part Count', 'Idle Time (s)'])),
                    dbc.Col(_FormGroupMaker(['Run Time (s)', 'Down Time (s)']))
                ], form=True)
            ])
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
        dcc.Store(id='timer_start'),
        dcc.Store(id='anomaly_flag', data=False),
        dcc.Store(id={'type': 'intermediate-data', 'index': 1}),
        dcc.Store(id={'type': 'intermediate-data', 'index': 2})
    ])
], fluid=True)


@app.callback(Output('power', 'outline'),
              Input('power', 'n_clicks'),
              Input('power', 'outline'), prevent_initial_call=True)
def power_button(n, outline):
    return not outline


@app.callback(Output('settings', 'outline'),
              Output('collapse', 'is_open'),
              Input('settings', 'n_clicks'),
              Input('settings', 'outline'), prevent_initial_call=True)
def collapse(n, outline):
    return not outline, outline


@app.callback(Output('ElapsedTime', 'value'),
              Output('timer_start', 'data'),
              Input('interval-component', 'n_intervals'),
              Input('power', 'outline'),
              Input('timer_start', 'data'))
def timer(n, power, timer_start):
    if power:
        raise PreventUpdate
    ctx = dash.callback_context
    if ctx.triggered:
        if ctx.triggered[0]['prop_id'] == 'power.outline' and power == False:
            timer_start = datetime.now()
    timer_start = to_datetime(timer_start)
    return str((datetime.now() - timer_start).to_pytimedelta()), timer_start # type: ignore


@app.callback(Output('SurfaceRoughnessRaum', 'value'),
              Input({'type': 'intermediate-data', 'index': 1}, 'data'),
              Input({'type': 'intermediate-data', 'index': 2}, 'data'))
def surface_roughness(power, acc):
    if power is None or acc is None or power['val_list'] is None or acc['val_list'] is None:
        raise PreventUpdate
    feed_rate = 0.4
    wheel_speed = 45.0
    work_speed = 100.0
    power = matlab.double(power['val_list'])
    acc_n = matlab.double(acc['val_list'])
    acc_t = acc_n
    return eng.sr_predictor(feed_rate, wheel_speed, work_speed, power, acc_n, acc_t) # type: ignore


@app.callback(Output({'type': 'intermediate-data', 'index': 1}, 'data'),
              Output({'type': 'intermediate-data', 'index': 2}, 'data'),
              Output('jwt', 'data'),
              Output('last_time', 'data'),
              Output('info', 'children'),
              Input('interval-component', 'n_intervals'),
              State('jwt', 'data'),
              State('last_time', 'data'),
              State('id1', 'value'),
              State('id2', 'value'),
              State('power', 'outline')
              )
def update_live_data(n, token, last_time, id1, id2, power):
    """Callback to get data every second."""
    if power:
        raise PreventUpdate

    timer_start = perf_counter()
    # 1 sec delay so server has time to add live data
    end_time = datetime.now(timezone.utc) - timedelta(seconds=1)

    # Initialization and lag prevention
    if last_time is None or end_time - strptime_fix(last_time) > timedelta(seconds=2):
        logging.warning('Falling behind!')
        last_time = end_time.isoformat()

    # Check if token is still valid
    token = update_token(token, 'test', 'smtamu_group',
                         'parthdave', 'parth1234')
    # Query data from SMIP
    logging.info(f'start_time {last_time} end_time {end_time}')
    timer_query_start = perf_counter()
    r = get_data(last_time, end_time.isoformat(),
                 [id1, id2], token, s, timeout=1)
    timer_query_end = perf_counter()
    r.raise_for_status()
    response_json = r.json()
    if 'errors' in response_json:
        logging.error(response_json)
        raise Exception()
    data = response_json['data']['getRawHistoryDataWithSampling']
    logging.info('Got %s responses in %s seconds', len(
        data), timer_query_end - timer_query_start)

    # Take timestamps and values out of response, format

    # Used for measuring performance
    start_processing = perf_counter()

    # SMIP always returns one entry before the start time, we don't need this
    if data:
        data.pop(0)

    # Unpack data
    def unpack(id: int):
        """Unpacks return data into time and value lists"""
        time_list = [i['ts'] for i in data if int(i['id']) == id]
        val_list = [i['floatvalue'] for i in data if int(i['id']) == id]
        if not time_list:
            return dash.no_update

        # Measure sampling rate
        rate = nan
        if len(time_list) > 1:
            rate = (strptime_fix(time_list[1])
                    - strptime_fix(time_list[0])).total_seconds()
        return {'time_list': time_list, 'val_list': val_list, 'rate': rate}

    # Used for measuring performance
    data_processed = perf_counter()
    logging.info('Total %s Query %s Processing %s', data_processed - timer_start, timer_query_end - timer_query_start,
                 data_processed - start_processing)

    return unpack(id1), unpack(id2), token, end_time.isoformat(), \
        f'Last updated {end_time.astimezone()}, received {len(data)} samples in {data_processed - timer_start} seconds'


@app.callback(Output('MachineState', 'value'),
              Output('PartCount', 'value'),
              Output('AnomalousParts', 'value'),
              Output('anomaly_flag', 'data'),
              Input({'type': 'intermediate-data', 'index': 1}, 'data'),
              Input('power', 'outline'),
              State('MachineState', 'value'),
              State('PartCount', 'value'),
              State('AnomalousParts', 'value'),
              State('anomaly_flag', 'data'))
def machine_state(data, power, state, count, anomalous, flag):
    if power:
        raise PreventUpdate
    ctx = dash.callback_context
    if ctx.triggered:
        if ctx.triggered[0]['prop_id'] == 'power.outline' and power == False:
            return None, 0, 0, False
    if data is None or not data['val_list']:
        raise PreventUpdate
    average = np.mean(data['val_list'])
    if average == 0:
        new_state = 'MACHINE STOP'
    elif average < 100:
        new_state = 'MACHINE IDLE'
    elif average > 5800:
        new_state = 'ABNORMAL OPERATION'
    else:
        new_state = 'NORMAL OPERATION'
    if state == 'MACHINE STOP' and new_state != 'MACHINE STOP':
        count += 1
        flag = False
    if new_state == 'ABNORMAL OPERATION':
        if not flag:
            anomalous += 1
        flag = True
    return new_state, count, anomalous, flag


@app.callback(Output('GoodParts', 'value'),
              Input('PartCount', 'value'),
              State('AnomalousParts', 'value'))
def good_parts(count, anomalous):
    return count - anomalous


@app.callback(Output('RunTimes', 'value'),
              Output('IdleTimes', 'value'),
              Output('DownTimes', 'value'),
              Input({'type': 'intermediate-data', 'index': 1}, 'data'),
              Input('power', 'outline'),
              State('RunTimes', 'value'),
              State('IdleTimes', 'value'),
              State('DownTimes', 'value'))
def calculate_times(data, power, run, idle, down):
    if power:
        raise PreventUpdate
    ctx = dash.callback_context
    if ctx.triggered:
        if ctx.triggered[0]['prop_id'] == 'power.outline' and power == False:
            return 0, 0, 0
    if data is None or not data['val_list'] or not data['rate']:
        raise PreventUpdate
    if run is None:
        run = 0
    if idle is None:
        idle = 0
    if down is None:
        down = 0
    arr = np.array(data['val_list'])
    run_c = len(data['val_list'])
    idle_c = np.count_nonzero(arr < 100)
    run_c -= idle_c
    down_c = np.count_nonzero(arr == 0)
    idle_c -= down_c
    return run + run_c * data['rate'], idle + idle_c * data['rate'], down + down_c * data['rate']


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
