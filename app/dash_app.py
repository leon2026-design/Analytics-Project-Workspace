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
    'primary': '#667eea',
    'success': '#48bb78',
    'warning': '#f6ad55',
    'danger': '#fc8181',
    'info': '#4299e1',
    'purple': '#764ba2'
}

# Functional Class mapping (FHWA Highway Functional Classification)
FUNCTIONAL_CLASS_LABELS = {
    1: 'Interstate',
    2: 'Principal Arterial',
    3: 'Minor Arterial',
    4: 'Major Collector',
    5: 'Minor Collector',
    6: 'Local Road',
    11: 'Interstate (Urban)',
    12: 'Principal Arterial (Urban)',
    13: 'Minor Arterial (Urban)',
    14: 'Collector (Urban)',
    15: 'Local (Urban)'
}

# ============================================================================
# DATA LOADING
# ============================================================================

def load_scenario_data(scenario_name):
    """Load prediction data for a specific scenario."""
    # Try enriched file first (has demographic data)
    enriched_file = DATA_DIR.parent / "predictions" / "enriched" / f"enriched_predicted_cms_2026_{scenario_name}.csv"
    if enriched_file.exists():
        print(f"✓ Loading enriched data from: {enriched_file}")
        return pd.read_csv(enriched_file, low_memory=False)
    
    # Fall back to geocoded file
    geocoded_file = SCENARIOS_DIR / f"geocoded_predicted_cms_2026_{scenario_name}.csv"
    if geocoded_file.exists():
        print(f"✓ Loading geocoded data from: {geocoded_file}")
        return pd.read_csv(geocoded_file, low_memory=False)
    
    # Fall back to original file
    file_path = SCENARIOS_DIR / f"predicted_cms_2026_{scenario_name}.csv"
    if file_path.exists():
        print(f"⚠ Loading original data from: {file_path}")
        return pd.read_csv(file_path)
    
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
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        dbc.icons.FONT_AWESOME,
        'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
    ],
    suppress_callback_exceptions=True,
    title="CTForecast - Columbus Traffic Predictor",
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}]
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
                        html.I(className="fas fa-traffic-light me-2", style={'color': 'indigo'}),
                        dbc.NavbarBrand("CTForecast", className="ms-2", style={'color': 'indigo'}),
                        html.Span(" | Columbus Traffic Predictor", className="ms-2", style={'fontSize': '0.9rem', 'color': 'rgba(75, 0, 130, 0.8)'})
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
                className="mt-2",
                style={'zIndex': 1000}
            )
        ], style={'overflow': 'visible'})
    ], style={'overflow': 'visible', 'zIndex': 100})

def create_stats_card(title, value, icon, color="primary"):
    """Create a statistics card."""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.I(className=f"fas {icon} fa-3x mb-2", style={'color': COLORS[color]}),
                ], style={'textAlign': 'center'}),
                html.Div([
                    html.H6(title, className="text-muted mb-1", style={'fontSize': '0.85rem', 'textAlign': 'center'}),
                    html.H2(value, className="mb-0", style={'fontWeight': '700', 'textAlign': 'center'})
                ])
            ])
        ], style={'padding': '1.5rem'})
    ], className="mb-3", style={'height': '100%'})

# ============================================================================
# MAIN LAYOUT
# ============================================================================

app.layout = html.Div([
    create_navbar(),
    
    dbc.Container([
        # Header Section
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2([
                        html.I(className="fas fa-chart-line me-3", style={'color': '#667eea'}),
                        "2026 Traffic Growth Scenarios"
                    ]),
                    html.P(
                        "Explore AI-powered predictions for 3,570 road segments across Columbus District 6. "
                        "Machine learning model trained on 5 years of ODOT data (2019-2024).",
                        className="text-muted",
                        style={'fontSize': '1.05rem'}
                    )
                ], style={'textAlign': 'center', 'padding': '2rem 0'})
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
                        html.Label("Growth Rate Threshold:", className="fw-bold"),
                        dcc.Slider(
                            id='growth-slider',
                            min=0,
                            max=3,
                            step=0.1,
                            value=1.0,
                            marks={i: f"{int(i*100)}%" for i in range(0, 4)},
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
                    dbc.CardHeader([
                        html.H5("Columbus District 6 Interactive Map", className="mb-0 d-inline"),
                        dbc.Checklist(
                            id="choropleth-toggle",
                            options=[{"label": " Show Employment Density", "value": "show"}],
                            value=[],
                            inline=True,
                            className="float-end",
                            switch=True
                        )
                    ]),
                    dbc.CardBody([
                        dl.Map(
                            id="columbus-leaflet-map",
                            style={'width': '100%', 'height': '500px'},
                            center=[39.9612, -82.9988],
                            zoom=12,
                            children=[
                                dl.TileLayer(),  # OpenStreetMap default
                                html.Div(id='employment-choropleth'),  # Choropleth layer
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
                html.Div([
                    html.P([
                        html.Strong("CTForecast"),
                        " - Powered by XGBoost ML (R²=0.701) | ",
                        html.I(className="fas fa-database me-1"),
                        "ODOT CMS 2019-2025 | ",
                        html.I(className="fas fa-map-marked-alt me-1"),
                        "3,570 Road Segments"
                    ], className="text-center text-muted small mb-2"),
                    html.P([
                        html.I(className="fas fa-code me-1"),
                        "Built with Python, Dash & Plotly | ",
                        html.I(className="fas fa-graduation-cap me-1"),
                        "BDAA Analytics & Visualization Project"
                    ], className="text-center text-muted small")
                ], style={'padding': '1rem 0'})
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
    
    # Add functional class labels for better visualization
    filtered['functional_class_label'] = filtered['functional_class_cd'].map(FUNCTIONAL_CLASS_LABELS)
    
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
            "Avg Growth Rate",
            f"{avg_growth*100:.1f}%",
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
    
    # Create scatter chart with categorical functional classes
    # Custom color palette with high contrast colors
    custom_colors = [
        '#667eea',  # Purple-blue (Interstate)
        '#48bb78',  # Green (Principal Arterial)
        '#f6ad55',  # Orange (Minor Arterial)
        '#fc8181',  # Red (Major Collector)
        '#4299e1',  # Light Blue (Minor Collector)
        '#9f7aea',  # Purple (Local Road)
        '#ed64a6',  # Pink (Interstate Urban)
        '#38b2ac',  # Teal (Principal Arterial Urban)
        '#ed8936',  # Dark Orange (Minor Arterial Urban - better contrast)
        '#e53e3e',  # Dark Red (Collector Urban)
        '#805ad5'   # Deep Purple (Local Urban)
    ]
    
    scatter_fig = px.scatter(
        filtered,
        x='total_volume_nbr',
        y='predicted_car_growth_nbr',
        color='functional_class_label',
        hover_data={
            'route_nbr': True,
            'section_length_nbr': ':.2f',
            'capacity_nbr': ':,',
            'functional_class_cd': True,
            'functional_class_label': False  # Already in color legend
        },
        labels={
            'total_volume_nbr': 'Traffic Volume',
            'predicted_car_growth_nbr': 'Predicted Growth Rate (%)',
            'functional_class_label': 'Highway Type'
        },
        title=f"{scenario.replace('_', ' ').title()} Scenario",
        color_discrete_sequence=custom_colors
    )
    scatter_fig.update_layout(
        hovermode='closest',
        template='plotly_white',
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            title_text='Highway Type',
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e2e8f0',
            borderwidth=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12),
        xaxis=dict(
            gridcolor='#f0f0f0',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            gridcolor='#f0f0f0',
            showgrid=True,
            zeroline=False
        )
    )
    
    # Create histogram with gradient color
    hist_fig = px.histogram(
        filtered,
        x='predicted_car_growth_nbr',
        nbins=40,
        labels={'predicted_car_growth_nbr': 'Growth Rate (%)'},
        color_discrete_sequence=['#667eea']
    )
    hist_fig.update_layout(
        yaxis_title='Number of Road Segments'
    )
    hist_fig.add_vline(
        x=1.0, 
        line_dash="dash", 
        line_color="#fc8181",
        line_width=3,
        annotation_text="100% Growth (Critical)",
        annotation_position="top",
        annotation=dict(
            font=dict(size=12, color='#fc8181', family='Inter, sans-serif'),
            bgcolor='rgba(252,129,129,0.1)',
            bordercolor='#fc8181',
            borderwidth=1
        )
    )
    hist_fig.update_layout(
        showlegend=False,
        template='plotly_white',
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12),
        xaxis=dict(
            gridcolor='#f0f0f0',
            showgrid=True
        ),
        yaxis=dict(
            gridcolor='#f0f0f0',
            showgrid=True
        )
    )
    hist_fig.update_traces(marker=dict(line=dict(color='#5568d3', width=1)))
    
    # Create aggregated data table by route (one row per route)
    table_df = filtered.groupby('route_nbr', as_index=False).agg({
        'predicted_car_growth_nbr': ['mean', 'max', 'min'],
        'total_volume_nbr': 'sum',
        'capacity_nbr': 'mean',
        'congestion_index_nbr': 'mean',
        'section_length_nbr': 'sum' if 'section_length_nbr' in filtered.columns else 'count'
    }).round(3)
    
    # Flatten multi-level columns
    table_df.columns = ['route_nbr', 'avg_growth', 'max_growth', 'min_growth', 
                        'total_volume', 'avg_capacity', 'avg_congestion', 'total_length']
    
    # Sort by max growth (highest risk routes first)
    table_df = table_df.sort_values('max_growth', ascending=False).head(50)
    
    column_labels = {
        'route_nbr': 'Route',
        'avg_growth': 'Avg Growth',
        'max_growth': 'Max Growth',
        'min_growth': 'Min Growth',
        'total_volume': 'Total Volume',
        'avg_capacity': 'Avg Capacity',
        'avg_congestion': 'Avg Congestion',
        'total_length': 'Total Length/Segments'
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
                'if': {'column_id': 'max_growth',
                       'filter_query': '{max_growth} > 1'},
                'backgroundColor': '#ffcccc',
                'color': 'darkred',
                'fontWeight': 'bold'
            },
            {
                'if': {'column_id': 'avg_growth',
                       'filter_query': '{avg_growth} > 1'},
                'backgroundColor': '#ffe6cc',
                'color': 'darkorange',
                'fontWeight': 'bold'
            }
        ],
        sort_action='native',
        filter_action='native',
        tooltip_header={
            'route_nbr': 'Road/Highway number (e.g., 70 = I-70)',
            'avg_growth': 'Average predicted growth rate across all segments of this route',
            'max_growth': 'Maximum growth rate among all segments (identifies worst bottleneck)',
            'min_growth': 'Minimum growth rate among all segments',
            'total_volume': 'Sum of traffic volume across all segments',
            'avg_capacity': 'Average capacity across all segments',
            'avg_congestion': 'Average congestion level (higher = more congested)',
            'total_length': 'Total route length or number of segments'
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
                            html.H5(f"{stat['avg_growth']*100:.1f}%")
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
            x=['Segments', 'Avg Growth %', 'High Growth %'],
            y=[stat['segments'], stat['avg_growth'] * 100, stat['high_growth_pct']],
            text=[f"{stat['segments']:,}", f"{stat['avg_growth']*100:.1f}%", f"{stat['high_growth_pct']:.1f}%"],
            textposition='auto'
        ))
    
    fig.update_layout(
        barmode='group',
        template='plotly_white',
        title='Scenario Comparison',
        xaxis_title='Metric',
        yaxis_title='Value',
        legend=dict(
            orientation='h', 
            yanchor='bottom', 
            y=1.02, 
            xanchor='right', 
            x=1,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e2e8f0',
            borderwidth=1
        ),
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', size=12),
        xaxis=dict(gridcolor='#f0f0f0'),
        yaxis=dict(gridcolor='#f0f0f0', showgrid=True)
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
    
    filename = f"columbus_traffic_{scenario}_{int(threshold*100)}pct"
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
            # Color code by growth intensity
            growth_pct = row['predicted_car_growth_nbr']
            if growth_pct > 1.0:
                color = 'red'
            elif growth_pct > 0.5:
                color = 'orange'
            elif growth_pct > 0.2:
                color = 'yellow'
            else:
                color = 'green'
            
            # Build popup with demographic info if available
            popup_elements = [
                html.Strong(f"Route {row['route_nbr']}"),
                html.Br(),
                f"Growth: {growth_pct*100:.1f}%",
                html.Br(),
                f"Volume: {row['total_volume_nbr']:,}" if pd.notna(row.get('total_volume_nbr')) else "Volume: N/A"
            ]
            
            # Add demographic data if available
            if 'jobs_within_2mi' in row and pd.notna(row['jobs_within_2mi']):
                popup_elements.extend([
                    html.Hr(style={'margin': '5px 0'}),
                    html.Strong("Employment:"),
                    html.Br(),
                    f"Jobs within 2mi: {int(row['jobs_within_2mi']):,}"
                ])
            
            if 'distance_to_downtown_mi' in row and pd.notna(row['distance_to_downtown_mi']):
                popup_elements.extend([
                    html.Br(),
                    f"Distance to downtown: {row['distance_to_downtown_mi']:.1f} mi"
                ])
            
            if 'area_type' in row and pd.notna(row['area_type']):
                popup_elements.extend([
                    html.Br(),
                    f"Area: {row['area_type']}"
                ])
            
            if 'C000' in row and pd.notna(row['C000']):
                popup_elements.extend([
                    html.Br(),
                    f"Tract jobs: {int(row['C000']):,}"
                ])
            
            markers.append(
                dl.Marker(
                    position=[row['latitude'], row['longitude']],
                    children=[dl.Popup(html.Div(popup_elements))]
                )
            )
    
    # Add district center marker
    markers.append(
        dl.Marker(position=[39.9612, -82.9988], children=[
            dl.Popup("Columbus District 6 Center")
        ])
    )
    
    return markers


@callback(
    Output("employment-choropleth", "children"),
    [Input("choropleth-toggle", "value")]
)
def update_choropleth_layer(toggle_value):
    """Show/hide employment density choropleth layer."""
    import json
    
    if not toggle_value or "show" not in toggle_value:
        return []  # Return empty if toggle is off
    
    # Load GeoJSON data
    geojson_path = Path(__file__).parent.parent / "backend" / "data" / "census_tracts" / "franklin_tracts_employment.geojson"
    
    try:
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)
        
        # Define color scale function for employment density
        def get_color(emp_density):
            """Return color based on employment density."""
            if emp_density is None or emp_density == 0:
                return '#f0f0f0'
            elif emp_density < 500:
                return '#deebf7'
            elif emp_density < 1000:
                return '#c6dbef'
            elif emp_density < 2000:
                return '#9ecae1'
            elif emp_density < 5000:
                return '#6baed6'
            elif emp_density < 10000:
                return '#3182bd'
            else:
                return '#08519c'
        
        # Create polygon layers for each census tract
        polygons = []
        for feature in geojson_data['features']:
            props = feature.get('properties', {})
            emp_density = props.get('emp_density', 0)
            total_jobs = props.get('C000', 0)
            tract_name = props.get('NAME', 'Unknown')
            
            # Get coordinates - handle both Polygon and MultiPolygon
            geom = feature['geometry']
            if geom['type'] == 'Polygon':
                coords_list = [geom['coordinates']]
            elif geom['type'] == 'MultiPolygon':
                coords_list = geom['coordinates']
            else:
                continue
            
            # Create polygon for each part
            for coords in coords_list:
                # Convert from [lon, lat] to [lat, lon] for Leaflet
                positions = [[[coord[1], coord[0]] for coord in ring] for ring in coords]
                
                polygon = dl.Polygon(
                    positions=positions,
                    color='white',
                    weight=1,
                    fillColor=get_color(emp_density),
                    fillOpacity=0.6,
                    children=[
                        dl.Tooltip(f"Tract {tract_name}: {int(total_jobs):,} jobs ({emp_density:.0f} jobs/sqmi)")
                    ]
                )
                polygons.append(polygon)
        
        # Create layer group with polygons and legend
        legend = html.Div([
            html.Div([
                html.Strong("Employment Density", style={'fontSize': '12px'}),
                html.Div("(jobs per sq mi)", style={'fontSize': '10px', 'fontStyle': 'italic'})
            ], style={'marginBottom': '5px'}),
            html.Div([
                html.Div(style={'backgroundColor': '#08519c', 'width': '20px', 'height': '15px', 'display': 'inline-block'}),
                html.Span(" 10,000+", style={'fontSize': '10px', 'marginLeft': '5px'})
            ]),
            html.Div([
                html.Div(style={'backgroundColor': '#3182bd', 'width': '20px', 'height': '15px', 'display': 'inline-block'}),
                html.Span(" 5,000-10,000", style={'fontSize': '10px', 'marginLeft': '5px'})
            ]),
            html.Div([
                html.Div(style={'backgroundColor': '#6baed6', 'width': '20px', 'height': '15px', 'display': 'inline-block'}),
                html.Span(" 2,000-5,000", style={'fontSize': '10px', 'marginLeft': '5px'})
            ]),
            html.Div([
                html.Div(style={'backgroundColor': '#9ecae1', 'width': '20px', 'height': '15px', 'display': 'inline-block'}),
                html.Span(" 1,000-2,000", style={'fontSize': '10px', 'marginLeft': '5px'})
            ]),
            html.Div([
                html.Div(style={'backgroundColor': '#c6dbef', 'width': '20px', 'height': '15px', 'display': 'inline-block'}),
                html.Span(" 500-1,000", style={'fontSize': '10px', 'marginLeft': '5px'})
            ]),
            html.Div([
                html.Div(style={'backgroundColor': '#deebf7', 'width': '20px', 'height': '15px', 'display': 'inline-block'}),
                html.Span(" 0-500", style={'fontSize': '10px', 'marginLeft': '5px'})
            ])
        ], style={
            'position': 'absolute',
            'bottom': '30px',
            'right': '10px',
            'backgroundColor': 'white',
            'padding': '10px',
            'border': '2px solid rgba(0,0,0,0.2)',
            'borderRadius': '5px',
            'zIndex': '1000',
            'fontSize': '11px'
        })
        
        return polygons + [legend]
        
    except Exception as e:
        print(f"Error loading choropleth: {e}")
        import traceback
        traceback.print_exc()
        return []


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
