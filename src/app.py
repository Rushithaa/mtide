import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from pymongo import MongoClient
import pandas as pd
from datetime import datetime, timedelta
import pytz
import urllib.parse

# MongoDB connection setup
username = urllib.parse.quote_plus("mohands")
password = urllib.parse.quote_plus("mohands")
uri = f"mongodb+srv://{username}:{password}@database.wvpwt.mongodb.net/?retryWrites=true&w=majority&appName=database"

client = MongoClient(uri)
db = client['market_data']

# Initialize the Dash app
app = dash.Dash(__name__, meta_tags=[
    {"name": "viewport", "content": "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"}
])
server = app.server

# Define the color scheme
colors = {
    'background': '#1e222d',
    'text': '#ffffff',
    'grid': '#2c3040',
    'line1': '#00ffff',  # Cyan
    'line2': '#ff69b4',  # Pink
    'line3': '#9370db',  # Purple
    'line4': '#ffa500',  # Orange
}

# New function to calculate PCR_OI metrics
def calculate_pcr_oi_metrics(df, window=30):
    df['PCR_OI_Rolling_High'] = df['PCR_OI'].rolling(window=window).max()
    df['PCR_OI_Rolling_Low'] = df['PCR_OI'].rolling(window=window).min()
    df['PCR_OI_Fall_From_High'] = df['PCR_OI_Rolling_High'] - df['PCR_OI']
    df['PCR_OI_Rise_From_Low'] = df['PCR_OI'] - df['PCR_OI_Rolling_Low']
    df['PCR_OI_Combined_Metric'] = df['PCR_OI_Fall_From_High'] + df['PCR_OI_Rise_From_Low']
    return df

# App layout
app.layout = html.Div(style={'backgroundColor': colors['background'], 'color': colors['text'], 'fontFamily': 'Arial, sans-serif'}, children=[
    html.H1("Market Data Dashboard", style={'textAlign': 'center', 'padding': '20px'}),
    dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0),
    dcc.Dropdown(
        id='index-dropdown',
        options=[
            {'label': 'NIFTY', 'value': 'nifty'},
            {'label': 'BANKNIFTY', 'value': 'banknifty'},
            {'label': 'FINNIFTY', 'value': 'finnifty'},
            {'label': 'MIDCPNIFTY', 'value': 'midcpnifty'}
        ],
        value='nifty',
        style={
            'width': '50%', 
            'margin': '0 auto 20px', 
            'backgroundColor': colors['background'], 
            'color': 'black'
        }
    ),
    html.Div([
        html.Div([
            html.Div([dcc.Graph(id='total-oi-chart')], className='chart-container'),
            html.Div(id='total-oi-values', className='values-container')
        ], className='chart-value-container'),
        html.Div([
            html.Div([dcc.Graph(id='oi-change-chart')], className='chart-container'),
            html.Div(id='oi-change-values', className='values-container')
        ], className='chart-value-container'),
        html.Div([
            html.Div([dcc.Graph(id='power-chart')], className='chart-container'),
            html.Div(id='power-values', className='values-container')
        ], className='chart-value-container'),
        html.Div([
            html.Div([dcc.Graph(id='pcr-chart')], className='chart-container'),
            html.Div(id='pcr-values', className='values-container')
        ], className='chart-value-container'),
        html.Div([
            html.Div([dcc.Graph(id='pcr-oi-metrics-chart')], className='chart-container'),
            html.Div(id='pcr-oi-metrics-values', className='values-container')
        ], className='chart-value-container'),
    ], id='charts-container', style={'paddingTop': '50px'})
])

# Add this CSS to make the layout responsive and style the value displays
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            #charts-container {
                display: flex;
                flex-wrap: wrap;
            }
            .chart-value-container {
                width: 100%;
                display: flex;
                flex-direction: column;
                align-items: center;
                margin-bottom: 20px;
            }
            .chart-container {
                width: 100%;
            }
            .values-container {
                width: 100%;
                padding: 10px;
                background-color: #2c3040;
                border-radius: 5px;
                margin-top: 10px;
                text-align: center;
            }
            @media (min-width: 768px) {
                .chart-value-container {
                    width: 50%;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

def get_current_date():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    if now.time() < datetime.strptime("09:15", "%H:%M").time():
        now = now - timedelta(days=1)
    return now.strftime("%d-%m-%Y")

@app.callback(
    [Output('total-oi-chart', 'figure'),
     Output('oi-change-chart', 'figure'),
     Output('power-chart', 'figure'),
     Output('pcr-chart', 'figure'),
     Output('pcr-oi-metrics-chart', 'figure'),
     Output('total-oi-values', 'children'),
     Output('oi-change-values', 'children'),
     Output('power-values', 'children'),
     Output('pcr-values', 'children'),
     Output('pcr-oi-metrics-values', 'children')],
    [Input('index-dropdown', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_charts(selected_index, n):
    current_date = get_current_date()
    collection = db[selected_index]
    
    data = list(collection.find({"date": current_date}))
    
    if not data:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            plot_bgcolor=colors['background'],
            paper_bgcolor=colors['background'],
            font={'color': colors['text']},
            xaxis={'gridcolor': colors['grid']},
            yaxis={'gridcolor': colors['grid']},
        )
        return [empty_fig] * 5 + ["No data"] * 5
    
    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['timestamp'], format='%d-%m-%Y %I:%M:%S %p')
    df = df.sort_values('datetime')

    # Calculate PCR_OI metrics
    df = calculate_pcr_oi_metrics(df)

    layout = go.Layout(
        plot_bgcolor=colors['background'],
        paper_bgcolor=colors['background'],
        font={'color': colors['text']},
        xaxis={'gridcolor': colors['grid']},
        yaxis={'gridcolor': colors['grid']},
        legend={
            'font': {'color': colors['text']},
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': -0.2,
            'xanchor': 'center',
            'x': 0.5
        },
        margin={'l': 40, 'b': 80, 't': 40, 'r': 0},
        title={'x': 0.5},
        dragmode=False,
    )

    total_oi_fig = go.Figure(layout=layout)
    total_oi_fig.add_trace(go.Scatter(x=df['datetime'], y=df['Total_Call_OI'], mode='lines', name='Total Call OI', line={'color': colors['line1']}))
    total_oi_fig.add_trace(go.Scatter(x=df['datetime'], y=df['Total_Put_OI'], mode='lines', name='Total Put OI', line={'color': colors['line2']}))
    total_oi_fig.update_layout(title=f'{selected_index.upper()} - Total OI')

    oi_change_fig = go.Figure(layout=layout)
    oi_change_fig.add_trace(go.Scatter(x=df['datetime'], y=df['Call_OI_Change'], mode='lines', name='Call OI Change', line={'color': colors['line1']}))
    oi_change_fig.add_trace(go.Scatter(x=df['datetime'], y=df['Put_OI_Change'], mode='lines', name='Put OI Change', line={'color': colors['line2']}))
    oi_change_fig.update_layout(title=f'{selected_index.upper()} - OI Change')

    power_fig = go.Figure(layout=layout)
    power_fig.add_trace(go.Scatter(x=df['datetime'], y=df['Bull_Power'], mode='lines', name='Bull Power', line={'color': colors['line1']}))
    power_fig.add_trace(go.Scatter(x=df['datetime'], y=df['Bear_Power'], mode='lines', name='Bear Power', line={'color': colors['line2']}))
    power_fig.update_layout(title=f'{selected_index.upper()} - Power')

    pcr_fig = go.Figure(layout=layout)
    pcr_fig.add_trace(go.Scatter(x=df['datetime'], y=df['PCR_OI'], mode='lines', name='PCR OI', line={'color': colors['line3']}))
    pcr_fig.add_trace(go.Scatter(x=df['datetime'], y=df['PCR_Volume'], mode='lines', name='PCR Volume', line={'color': colors['line4']}))
    pcr_fig.update_layout(title=f'{selected_index.upper()} - PCR')

    pcr_oi_metrics_fig = go.Figure(layout=layout)
    pcr_oi_metrics_fig.add_trace(go.Scatter(x=df['datetime'], y=df['PCR_OI_Combined_Metric'], mode='lines', name='PCR OI Combined Metric', line={'color': colors['line3']}))
    pcr_oi_metrics_fig.update_layout(title=f'{selected_index.upper()} - PCR OI Metrics')

    # Get latest values
    latest = df.iloc[-1]
    total_oi_values = html.Div([
        html.P(f"Total Call OI: {latest['Total_Call_OI']:,.0f}"),
        html.P(f"Total Put OI: {latest['Total_Put_OI']:,.0f}")
    ])
    oi_change_values = html.Div([
        html.P(f"Call OI Change: {latest['Call_OI_Change']:,.0f}"),
        html.P(f"Put OI Change: {latest['Put_OI_Change']:,.0f}")
    ])
    power_values = html.Div([
        html.P(f"Bull Power: {latest['Bull_Power']:.2f}"),
        html.P(f"Bear Power: {latest['Bear_Power']:.2f}")
    ])
    pcr_values = html.Div([
        html.P(f"PCR OI: {latest['PCR_OI']:.2f}"),
        html.P(f"PCR Volume: {latest['PCR_Volume']:.2f}")
    ])
    pcr_oi_metrics_values = html.Div([
        html.P(f"PCR OI Combined Metric: {latest['PCR_OI_Combined_Metric']:.2f}"),
        html.P(f"Fall from High: {latest['PCR_OI_Fall_From_High']:.2f}"),
        html.P(f"Rise from Low: {latest['PCR_OI_Rise_From_Low']:.2f}")
    ])

    return total_oi_fig, oi_change_fig, power_fig, pcr_fig, pcr_oi_metrics_fig, total_oi_values, oi_change_values, power_values, pcr_values, pcr_oi_metrics_values

if __name__ == '__main__':
    app.run_server(debug=False)
