"""
Columbus Traffic Growth Predictor - Dash Web Application

A multi-page interactive dashboard for exploring 2026 traffic growth scenarios
across Columbus District 6 road segments.
"""

import os
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import dash_leaflet as dl

# ============================================================================
# CONFIGURATION
# ============================================================================

# Use absolute path from project root (parent of app/ directory)
DATA_DIR = Path(__file__).parent.parent / "backend" / "data" / "predictions"
SCENARIOS_DIR = DATA_DIR / "scenarios"

SCENARIO_OPTIONS = [
    {"label": "Baseline (0% growth)", "value": "baseline"},
    {"label": "Conservative (+2% growth)", "value": "conservative"},
    {"label": "Moderate (+5% growth)", "value": "moderate"},
    {"label": "Aggressive (+10% growth)", "value": "aggressive"},
    {"label": "Post-Pandemic Boom (+15% growth)", "value": "post_pandemic_boom"},
]

COLORS = {
    'primary': '#1f77b4',
    'success': '#2ca02c',
    'warning': '#ff7f0e',
    'danger': '#d62728',
    'info': '#17a2b8'
}

# ============================================================================
# DATA LOADING
# ============================================================================

def load_scenario_data(scenario_name):
    """Load prediction data for a specific scenario."""
    file_path = SCENARIOS_DIR / f"predicted_cms_2026_{scenario_name}.csv"
    if file_path.exists():
        return pd.read_csv(file_path)
    else:
        print(f"⚠️  File not found: {file_path}")
    return pd.DataFrame()

def load_all_scenarios():
    """Load all scenario data into a dictionary."""
    scenarios = {}
    print(f"Looking for scenarios in: {SCENARIOS_DIR}")
    print(f"Directory exists: {SCENARIOS_DIR.exists()}")
    if SCENARIOS_DIR.exists():
        print(f"Files in directory: {list(SCENARIOS_DIR.glob('*.csv'))}")
    
    for option in SCENARIO_OPTIONS:
        scenarios[option['value']] = load_scenario_data(option['value'])
    return scenarios

# Load data once at startup
print("Loading scenario data...")
SCENARIOS_DATA = load_all_scenarios()
print(f"Loaded {len(SCENARIOS_DATA)} scenarios")
for key, df in SCENARIOS_DATA.items():
    print(f"  - {key}: {len(df)} rows")
print("Data loading complete!")

# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Columbus Traffic Predictor"
)

server = app.server  # For deployment

# ============================================================================
# LAYOUT COMPONENTS
# ============================================================================

def create_navbar():
    """Create navigation bar."""
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-traffic-light me-2"),
                        dbc.NavbarBrand("Columbus Traffic Growth Predictor", className="ms-2")
                    ])
                ], width="auto"),
            ], align="center", className="g-0")
        ], fluid=True),
        color="dark",
        dark=True,
        className="mb-4"
    )

def create_scenario_selector(dropdown_id="scenario-dropdown"):
    """Create scenario selection dropdown."""
    return dbc.Card([
        dbc.CardBody([
            html.Label("Select Scenario:", className="fw-bold"),
            dcc.Dropdown(
                id=dropdown_id,
                options=SCENARIO_OPTIONS,
                value="baseline",
                clearable=False,
                className="mt-2"
            )
        ])
    ])

def create_stats_card(title, value, icon, color="primary"):
    """Create a statistics card."""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"fas {icon} fa-2x", style={'color': COLORS[color]}),
                html.Div([
                    html.H6(title, className="text-muted mb-0"),
                    html.H3(value, className="mb-0")
                ], className="ms-3")
            ], className="d-flex align-items-center")
        ])
    ], className="mb-3")

# ============================================================================
# MAIN LAYOUT
# ============================================================================

app.layout = html.Div([
    create_navbar(),
    
    dbc.Container([
        # Header Section
        dbc.Row([
            dbc.Col([
                html.H2("2026 Traffic Growth Scenarios - District 6"),
                html.P(
                    "Explore predictions for 3,570 road segments across five growth scenarios. "
                    "Model trained on 2019-2023 data, validated on 2024.",
                    className="text-muted"
                )
            ])
        ], className="mb-4"),
        
        # Controls Row
        dbc.Row([
            dbc.Col(create_scenario_selector(), md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Label("Search Route:", className="fw-bold"),
                        html.P("Enter route number (e.g., 70 for I-70, 315, 23)", className="small text-muted mb-2"),
                        dbc.Input(
                            id='route-search',
                            type='text',
                            placeholder='Enter route number...',
                            debounce=True
                        )
                    ])
                ])
            ], md=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Label("Car Growth Threshold:", className="fw-bold"),
                        dcc.Slider(
                            id='growth-slider',
                            min=0,
                            max=3,
                            step=0.1,
                            value=1.0,
                            marks={i: f"{i}x" for i in range(0, 4)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ])
                ])
            ], md=6)
        ], className="mb-4"),
        
        # Multi-Scenario Comparison Toggle
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Checkbox(
                                id='comparison-mode',
                                label="Enable Multi-Scenario Comparison",
                                value=False,
                                className="d-inline me-3"
                            ),
                            html.Span("Compare multiple scenarios side-by-side", className="text-muted small")
                        ])
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Multi-Scenario Selectors (hidden by default)
        html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Label("Compare Scenarios:", className="fw-bold"),
                            dcc.Dropdown(
                                id='comparison-scenarios',
                                options=SCENARIO_OPTIONS,
                                value=['baseline', 'moderate', 'aggressive'],
                                multi=True,
                                placeholder="Select up to 3 scenarios..."
                            )
                        ])
                    ])
                ])
            ], className="mb-4")
        ], id='comparison-controls', style={'display': 'none'}),
        
        # Statistics Cards Row (Single Scenario)
        html.Div([
            dbc.Row([
                dbc.Col(html.Div(id='stats-cards'), md=12)
            ], className="mb-4")
        ], id='single-stats'),
        
        # Comparison Statistics (Multi-Scenario)
        html.Div([
            dbc.Row([
                dbc.Col(html.Div(id='comparison-stats'), md=12)
            ], className="mb-4")
        ], id='comparison-stats-container', style={'display': 'none'}),
        
        # Main Charts Row (Single Scenario)
        html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Traffic Volume vs Car Growth", className="mb-0")),
                        dbc.CardBody([
                            dcc.Graph(id='scatter-chart', style={'height': '400px'})
                        ])
                    ])
                ], md=8),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Growth Distribution", className="mb-0")),
                        dbc.CardBody([
                            dcc.Graph(id='histogram-chart', style={'height': '400px'})
                        ])
                    ])
                ], md=4)
            ], className="mb-4")
        ], id='single-charts'),
        
        # Comparison Charts (Multi-Scenario)
        html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Scenario Comparison", className="mb-0")),
                        dbc.CardBody([
                            dcc.Graph(id='comparison-chart', style={'height': '500px'})
                        ])
                    ])
                ])
            ], className="mb-4")
        ], id='comparison-charts', style={'display': 'none'}),
        
        # Data Table Row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.H5("Segment Details", className="mb-0 d-inline"),
                            dbc.Button(
                                [html.I(className="fas fa-download me-2"), "Download CSV"],
                                id="btn-download",
                                color="primary",
                                size="sm",
                                className="float-end"
                            )
                        ])
                    ]),
                    dbc.CardBody([
                        html.Div(id='data-table')
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Download Component
        dcc.Download(id="download-csv"),
        
        # Leaflet Map of Columbus
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Columbus District 6 Interactive Map", className="mb-0")),
                    dbc.CardBody([
                        dl.Map(
                            id="columbus-leaflet-map",
                            style={'width': '100%', 'height': '500px'},
                            center=[39.9612, -82.9988],
                            zoom=12,
                            children=[
                                dl.TileLayer(),  # OpenStreetMap default
                                html.Div(id='map-markers')  # Placeholder for dynamic markers
                            ]
                        )
                    ])
                ])
            ])
        ], className="mb-4"),
        
        # Footer
        dbc.Row([
            dbc.Col([
                html.Hr(),
                html.P(
                    "Columbus Traffic Growth Predictor | Model: XGBoost (R²=0.304) | Data: ODOT CMS 2019-2024",
                    className="text-center text-muted small"
                )
            ])
        ])
        
    ], fluid=True)
])

# ============================================================================
# CALLBACKS
# ============================================================================

@callback(
    [Output('comparison-controls', 'style'),
     Output('single-stats', 'style'),
     Output('comparison-stats-container', 'style'),
     Output('single-charts', 'style'),
     Output('comparison-charts', 'style')],
    [Input('comparison-mode', 'value')]
)
def toggle_comparison_mode(comparison_enabled):
    """Show/hide comparison controls and charts."""
    if comparison_enabled:
        return (
            {'display': 'block'},  # Show comparison controls
            {'display': 'none'},   # Hide single stats
            {'display': 'block'},  # Show comparison stats
            {'display': 'none'},   # Hide single charts
            {'display': 'block'}   # Show comparison charts
        )
    else:
        return (
            {'display': 'none'},   # Hide comparison controls
            {'display': 'block'},  # Show single stats
            {'display': 'none'},   # Hide comparison stats
            {'display': 'block'},  # Show single charts
            {'display': 'none'}    # Hide comparison charts
        )


@callback(
    [Output('stats-cards', 'children'),
     Output('scatter-chart', 'figure'),
     Output('histogram-chart', 'figure'),
     Output('data-table', 'children')],
    [Input('scenario-dropdown', 'value'),
     Input('growth-slider', 'value'),
     Input('route-search', 'value')]
)
def update_dashboard(scenario, threshold, route_search):
    """Update all dashboard components based on scenario, threshold, and route search."""
    
    # Load scenario data
    df = SCENARIOS_DATA.get(scenario, pd.DataFrame())
    
    if df.empty:
        return [html.Div("No data available")], {}, {}, html.Div("No data")
    
    # Filter by threshold
    filtered = df[df['predicted_car_growth_nbr'] >= threshold].copy()
    
    # Filter by route if search provided
    if route_search and route_search.strip():
        route_search = route_search.strip()
        filtered = filtered[
            filtered['route_nbr'].astype(str).str.contains(route_search, case=False, na=False)
        ]
        if filtered.empty:
            no_results = html.Div([
                html.I(className="fas fa-search fa-3x text-muted mb-3"),
                html.H5(f"No segments found for route '{route_search}'"),
                html.P("Try a different route number (e.g., 70, 315, 23)", className="text-muted")
            ], className="text-center py-5")
            return [no_results], {}, {}, no_results
    
    # Calculate statistics
    total_segments = len(filtered)
    avg_growth = filtered['predicted_car_growth_nbr'].mean()
    high_growth_pct = (filtered['predicted_car_growth_nbr'] > 1.0).mean() * 100
    total_volume = filtered['total_volume_nbr'].sum()
    
    # Create stats cards
    stats_cards = dbc.Row([
        dbc.Col(create_stats_card(
            "Total Segments",
            f"{total_segments:,}",
            "fa-road",
            "primary"
        ), md=3),
        dbc.Col(create_stats_card(
            "Avg Car Growth",
            f"{avg_growth:.3f}x",
            "fa-chart-line",
            "success"
        ), md=3),
        dbc.Col(create_stats_card(
            "High Growth %",
            f"{high_growth_pct:.1f}%",
            "fa-exclamation-triangle",
            "warning"
        ), md=3),
        dbc.Col(create_stats_card(
            "Total Volume",
            f"{total_volume/1e6:.1f}M",
            "fa-car",
            "info"
        ), md=3),
    ])
    
    # Create scatter chart
    scatter_fig = px.scatter(
        filtered,
        x='total_volume_nbr',
        y='predicted_car_growth_nbr',
        color='functional_class_cd',
        hover_data=['route_nbr', 'section_length_nbr', 'capacity_nbr'],
        labels={
            'total_volume_nbr': 'Traffic Volume',
            'predicted_car_growth_nbr': 'Predicted Car Growth',
            'functional_class_cd': 'Functional Class'
        },
        title=f"{scenario.replace('_', ' ').title()} Scenario"
    )
    scatter_fig.update_layout(
        hovermode='closest',
        template='plotly_white',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    # Create histogram
    hist_fig = px.histogram(
        filtered,
        x='predicted_car_growth_nbr',
        nbins=40,
        labels={'predicted_car_growth_nbr': 'Car Growth'},
        color_discrete_sequence=[COLORS['primary']]
    )
    hist_fig.add_vline(x=1.0, line_dash="dash", line_color="red",
                       annotation_text="100% Growth Threshold")
    hist_fig.update_layout(
        showlegend=False,
        template='plotly_white',
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    # Create data table with better column names and descriptions
    table_df = filtered[[
        'route_nbr', 'predicted_car_growth_nbr', 'total_volume_nbr',
        'capacity_nbr', 'congestion_index_nbr', 'functional_class_cd'
    ]].head(100).round(3)
    
    column_labels = {
        'route_nbr': 'Route',
        'predicted_car_growth_nbr': 'Car Growth',
        'total_volume_nbr': 'Traffic Volume',
        'capacity_nbr': 'Capacity',
        'congestion_index_nbr': 'Congestion',
        'functional_class_cd': 'Type'
    }
    
    data_table = dash_table.DataTable(
        data=table_df.to_dict('records'),
        columns=[{"name": column_labels.get(i, i), "id": i} for i in table_df.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '10px'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'column_id': 'predicted_car_growth_nbr',
                       'filter_query': '{predicted_car_growth_nbr} > 1'},
                'backgroundColor': '#ffcccc',
                'color': 'darkred',
                'fontWeight': 'bold'
            }
        ],
        sort_action='native',
        filter_action='native',
        tooltip_header={
            'route_nbr': 'Road/Highway number (e.g., 70 = I-70)',
            'predicted_car_growth_nbr': 'Predicted growth rate (>1.0 = over capacity)',
            'total_volume_nbr': 'Current daily traffic volume',
            'capacity_nbr': 'Maximum designed capacity',
            'congestion_index_nbr': 'Congestion level (higher = more congested)',
            'functional_class_cd': 'Highway classification'
        },
        tooltip_delay=0,
        tooltip_duration=None
    )
    
    return stats_cards, scatter_fig, hist_fig, data_table


@callback(
    [Output('comparison-stats', 'children'),
     Output('comparison-chart', 'figure')],
    [Input('comparison-scenarios', 'value'),
     Input('growth-slider', 'value'),
     Input('route-search', 'value')]
)
def update_comparison(scenarios, threshold, route_search):
    """Update comparison view with multiple scenarios."""
    
    if not scenarios or len(scenarios) == 0:
        empty_msg = html.Div([
            html.I(className="fas fa-chart-bar fa-3x text-muted mb-3"),
            html.H5("Select scenarios to compare"),
            html.P("Choose up to 3 scenarios from the dropdown above", className="text-muted")
        ], className="text-center py-5")
        return empty_msg, {}
    
    # Limit to 3 scenarios
    scenarios = scenarios[:3]
    
    # Prepare comparison data
    comparison_data = []
    stats_data = []
    
    for scenario in scenarios:
        df = SCENARIOS_DATA.get(scenario, pd.DataFrame())
        if df.empty:
            continue
        
        # Apply filters
        filtered = df[df['predicted_car_growth_nbr'] >= threshold].copy()
        
        if route_search and route_search.strip():
            filtered = filtered[
                filtered['route_nbr'].astype(str).str.contains(route_search.strip(), case=False, na=False)
            ]
        
        # Calculate stats
        total_segments = len(filtered)
        avg_growth = filtered['predicted_car_growth_nbr'].mean()
        high_growth_pct = (filtered['predicted_car_growth_nbr'] > 1.0).mean() * 100
        
        stats_data.append({
            'scenario': scenario.replace('_', ' ').title(),
            'segments': total_segments,
            'avg_growth': avg_growth,
            'high_growth_pct': high_growth_pct
        })
        
        # Add to comparison data
        filtered['scenario'] = scenario.replace('_', ' ').title()
        comparison_data.append(filtered)
    
    if not comparison_data:
        return html.Div("No data matches filters"), {}
    
    # Create comparison stats cards
    stats_cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(stat['scenario'], className="text-center mb-3"),
                    html.Div([
                        html.Div([
                            html.Small("Segments", className="text-muted d-block"),
                            html.H5(f"{stat['segments']:,}")
                        ], className="text-center mb-2"),
                        html.Div([
                            html.Small("Avg Growth", className="text-muted d-block"),
                            html.H5(f"{stat['avg_growth']:.3f}x")
                        ], className="text-center mb-2"),
                        html.Div([
                            html.Small("High Growth", className="text-muted d-block"),
                            html.H5(f"{stat['high_growth_pct']:.1f}%", 
                                   style={'color': COLORS['warning'] if stat['high_growth_pct'] > 40 else COLORS['success']})
                        ], className="text-center")
                    ])
                ])
            ], className="h-100")
        ], md=12 // len(stats_data))
        for stat in stats_data
    ])
    
    # Create comparison chart
    combined_df = pd.concat(comparison_data, ignore_index=True)
    
    # Bar chart comparing key metrics
    fig = go.Figure()
    
    # Add bars for each scenario
    for stat in stats_data:
        fig.add_trace(go.Bar(
            name=stat['scenario'],
            x=['Segments', 'Avg Growth', 'High Growth %'],
            y=[stat['segments'], stat['avg_growth'] * 1000, stat['high_growth_pct']],
            text=[f"{stat['segments']:,}", f"{stat['avg_growth']:.3f}x", f"{stat['high_growth_pct']:.1f}%"],
            textposition='auto'
        ))
    
    fig.update_layout(
        barmode='group',
        template='plotly_white',
        title='Scenario Comparison',
        xaxis_title='Metric',
        yaxis_title='Value',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return stats_cards, fig


@callback(
    Output("download-csv", "data"),
    Input("btn-download", "n_clicks"),
    State("scenario-dropdown", "value"),
    State("growth-slider", "value"),
    State("route-search", "value"),
    prevent_initial_call=True
)
def download_data(n_clicks, scenario, threshold, route_search):
    """Download filtered scenario data as CSV."""
    df = SCENARIOS_DATA.get(scenario, pd.DataFrame())
    filtered = df[df['predicted_car_growth_nbr'] >= threshold]
    
    # Apply route filter if present
    if route_search and route_search.strip():
        filtered = filtered[
            filtered['route_nbr'].astype(str).str.contains(route_search.strip(), case=False, na=False)
        ]
    
    filename = f"columbus_traffic_{scenario}_{threshold}x"
    if route_search:
        filename += f"_route{route_search.strip()}"
    filename += ".csv"
    
    return dcc.send_data_frame(filtered.to_csv, filename, index=False)


@callback(
    Output("map-markers", "children"),
    [Input("scenario-dropdown", "value"),
     Input("growth-slider", "value")]
)

def update_leaflet_map(scenario, threshold):
    """Update map markers based on scenario and threshold."""
    df = SCENARIOS_DATA.get(scenario, pd.DataFrame())
    
    if df.empty:
        # Just return district center marker if no data
        return [
            dl.Marker(position=[39.9612, -82.9988], children=[
                dl.Popup("Columbus District 6")
            ]),
        ]
    
    # Filter for high-growth segments
    high_growth = df[df['predicted_car_growth_nbr'] >= threshold].copy()
    
    markers = []
    
    # Add high-growth segment markers if location data exists
    if 'latitude' in high_growth.columns and 'longitude' in high_growth.columns:
        high_growth = high_growth.dropna(subset=['latitude', 'longitude'])
        
        for idx, row in high_growth.head(100).iterrows():  # Limit to 100 for performance
            color = 'red' if row['predicted_car_growth_nbr'] > 1.0 else 'orange'
            markers.append(
                dl.Marker(
                    position=[row['latitude'], row['longitude']],
                    children=[
                        dl.Popup(
                            html.Div([
                                html.Strong(f"Route {row['route_nbr']}"),
                                html.Br(),
                                f"Growth: {row['predicted_car_growth_nbr']:.3f}x",
                                html.Br(),
                                f"Volume: {row.get('total_volume_nbr', 'N/A'):,}"
                            ])
                        )
                    ]
                )
            )
    
    # Add district center marker
    markers.append(
        dl.Marker(position=[39.9612, -82.9988], children=[
            dl.Popup("Columbus District 6 Center")
        ])
    )
    
    return markers


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
