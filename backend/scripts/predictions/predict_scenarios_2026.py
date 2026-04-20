"""Generate multiple 2026 scenarios for Columbus District 6.

This script creates five different traffic growth scenarios and predicts
car growth for each, enabling scenario-based planning and decision making.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from backend.core.preprocessing import load_all_data, recompute_2026_time_features
from backend.core.predict import predict_from_dataframe


def apply_scenario(df, scenario_name, params):
    """Apply growth assumptions to base 2025 data.
    
    Args:
        df: Base 2025 DataFrame
        scenario_name: Name of the scenario
        params: Dict with volume_growth and truck_growth multipliers
        
    Returns:
        Modified DataFrame with scenario applied
    """
    df_scenario = df.copy()
    
    # Apply traffic growth multipliers
    df_scenario['total_volume_nbr'] *= params['volume_growth']
    df_scenario['truck_volume_nbr'] *= params['truck_growth']
    
    # Recalculate dependent traffic metrics
    if 'total_lanes_nbr' in df_scenario.columns:
        df_scenario['volume_per_lane_nbr'] = (
            df_scenario['total_volume_nbr'] / df_scenario['total_lanes_nbr'].replace(0, 1)
        )
    
    if 'capacity_nbr' in df_scenario.columns:
        df_scenario['volume_capacity_ratio_nbr'] = (
            df_scenario['total_volume_nbr'] / df_scenario['capacity_nbr'].replace(0, 1)
        )
    
    # Recalculate VMT (vehicle miles traveled)
    if 'section_length_nbr' in df_scenario.columns:
        df_scenario['vmt_nbr'] = df_scenario['total_volume_nbr'] * df_scenario['section_length_nbr']
        df_scenario['truck_vmt_nbr'] = df_scenario['truck_volume_nbr'] * df_scenario['section_length_nbr']
    
    # Add scenario metadata
    df_scenario['scenario'] = scenario_name
    df_scenario['volume_growth_pct'] = (params['volume_growth'] - 1) * 100
    df_scenario['truck_growth_pct'] = (params['truck_growth'] - 1) * 100
    
    return df_scenario


def main():
    print("="*70)
    print("Columbus Traffic Growth: 2026 Scenario Analysis")
    print("="*70)
    
    # Load 2025 baseline (most recent available year)
    print("\nLoading 2025 Columbus District 6 baseline data...")
    df_all = load_all_data("backend/data")
    
    # Filter to District 6, year 2025
    df_2025_d6 = df_all[
        (df_all.get('odot_district') == 6) & 
        (df_all.get('year') == 2025)
    ].copy()
    
    print(f"✓ Loaded {len(df_2025_d6)} road segments from District 6")
    
    # Define scenarios
    scenarios = {
        'baseline': {
            'volume_growth': 1.00,
            'truck_growth': 1.00,
            'description': 'No growth - 2026 traffic same as 2025'
        },
        'conservative': {
            'volume_growth': 1.02,
            'truck_growth': 1.01,
            'description': 'Conservative growth - 2% cars, 1% trucks'
        },
        'moderate': {
            'volume_growth': 1.05,
            'truck_growth': 1.03,
            'description': 'Moderate growth - 5% cars, 3% trucks'
        },
        'aggressive': {
            'volume_growth': 1.10,
            'truck_growth': 1.05,
            'description': 'Aggressive growth - 10% cars, 5% trucks'
        },
        'post_pandemic_boom': {
            'volume_growth': 1.15,
            'truck_growth': 1.08,
            'description': 'Post-pandemic boom - 15% cars, 8% trucks'
        }
    }
    
    # Generate predictions for each scenario
    results = []
    all_predictions = []
    
    for scenario_name, params in scenarios.items():
        print(f"\n{'-'*70}")
        print(f"Scenario: {scenario_name.upper()}")
        print(f"{params['description']}")
        print(f"{'-'*70}")
        
        # Apply scenario transformations
        df_scenario = apply_scenario(df_2025_d6, scenario_name, params)
        
        # Update year to 2026 and recompute time features
        df_scenario['year'] = 2026
        df_scenario = recompute_2026_time_features(df_all, df_scenario)
        
        # Generate predictions
        df_scenario = predict_from_dataframe(df_scenario)
        
        # Calculate summary statistics
        avg_growth = df_scenario['predicted_car_growth_nbr'].mean()
        median_growth = df_scenario['predicted_car_growth_nbr'].median()
        std_growth = df_scenario['predicted_car_growth_nbr'].std()
        high_growth_segments = (df_scenario['predicted_car_growth_nbr'] > 1.0).sum()
        very_high_growth = (df_scenario['predicted_car_growth_nbr'] > 1.5).sum()
        
        print(f"  Average predicted car growth:     {avg_growth:.3f}")
        print(f"  Median predicted car growth:      {median_growth:.3f}")
        print(f"  Std dev:                          {std_growth:.3f}")
        print(f"  Segments with >100% growth:       {high_growth_segments} ({high_growth_segments/len(df_scenario)*100:.1f}%)")
        print(f"  Segments with >150% growth:       {very_high_growth} ({very_high_growth/len(df_scenario)*100:.1f}%)")
        
        # Save individual scenario
        output_dir = Path("backend/data/predictions/scenarios")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"predicted_cms_2026_{scenario_name}.csv"
        df_scenario.to_csv(output_file, index=False)
        print(f"  ✓ Saved: {output_file}")
        
        # Store for combined output
        all_predictions.append(df_scenario)
        
        # Store summary
        results.append({
            'scenario': scenario_name,
            'description': params['description'],
            'volume_growth': params['volume_growth'],
            'truck_growth': params['truck_growth'],
            'avg_predicted_car_growth': avg_growth,
            'median_predicted_car_growth': median_growth,
            'std_predicted_car_growth': std_growth,
            'high_growth_segments': high_growth_segments,
            'very_high_growth_segments': very_high_growth,
            'total_segments': len(df_scenario),
            'pct_high_growth': high_growth_segments / len(df_scenario) * 100
        })
    
    # Create comparison summary
    df_summary = pd.DataFrame(results)
    summary_file = Path("backend/data/predictions/2026_scenarios_summary.csv")
    df_summary.to_csv(summary_file, index=False)
    
    # Save combined predictions
    df_combined = pd.concat(all_predictions, ignore_index=True)
    combined_file = Path("backend/data/predictions/2026_all_scenarios_combined.csv")
    df_combined.to_csv(combined_file, index=False)
    
    # Print final summary
    print(f"\n{'='*70}")
    print("SCENARIO COMPARISON SUMMARY")
    print(f"{'='*70}\n")
    
    summary_display = df_summary[[
        'scenario', 'volume_growth', 'avg_predicted_car_growth', 
        'high_growth_segments', 'pct_high_growth'
    ]].copy()
    summary_display.columns = [
        'Scenario', 'Volume Growth', 'Avg Car Growth', 
        'High-Growth Segs', '% High-Growth'
    ]
    print(summary_display.to_string(index=False))
    
    print(f"\n{'='*70}")
    print("✓ All scenario predictions complete!")
    print(f"✓ Summary saved: {summary_file}")
    print(f"✓ Combined data: {combined_file}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
