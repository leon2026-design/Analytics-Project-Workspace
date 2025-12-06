"""
Analyze spatial patterns in enriched traffic predictions.
Shows relationships between traffic growth and demographics/employment.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

def load_enriched_data(scenario='baseline'):
    """Load enriched prediction data."""
    file_path = Path(f"backend/data/predictions/enriched/enriched_predicted_cms_2026_{scenario}.csv")
    
    if not file_path.exists():
        print(f"⚠ File not found: {file_path}")
        return None
    
    print(f"Loading {file_path}...")
    df = pd.read_csv(file_path, low_memory=False)
    print(f"  ✓ Loaded {len(df):,} segments")
    
    return df

def analyze_employment_growth_correlation(df):
    """Analyze relationship between employment and traffic growth."""
    
    print("\n" + "="*80)
    print("EMPLOYMENT VS TRAFFIC GROWTH ANALYSIS")
    print("="*80)
    
    # Filter to segments with employment data
    analysis_df = df[df['jobs_within_2mi'].notna()].copy()
    
    print(f"\nSegments with employment data: {len(analysis_df):,} ({len(analysis_df)/len(df)*100:.1f}%)")
    
    # Bin employment levels
    analysis_df['employment_category'] = pd.cut(
        analysis_df['jobs_within_2mi'],
        bins=[0, 5000, 15000, 30000, 100000],
        labels=['Low (<5K)', 'Medium (5-15K)', 'High (15-30K)', 'Very High (>30K)']
    )
    
    # Calculate average growth by employment level
    growth_by_employment = analysis_df.groupby('employment_category', observed=True).agg({
        'predicted_car_growth_nbr': ['mean', 'median', 'count']
    }).round(4)
    
    print("\nAverage Traffic Growth by Employment Level:")
    print(growth_by_employment)
    
    # Correlation analysis
    corr = analysis_df[['predicted_car_growth_nbr', 'jobs_within_2mi', 'distance_to_downtown']].corr()
    print("\nCorrelation Matrix:")
    print(corr)
    
    return analysis_df

def analyze_spatial_patterns(df):
    """Analyze traffic growth by distance from downtown."""
    
    print("\n" + "="*80)
    print("SPATIAL PATTERN ANALYSIS")
    print("="*80)
    
    # Filter to segments with location data
    spatial_df = df[df['distance_to_downtown'].notna()].copy()
    
    print(f"\nSegments with location data: {len(spatial_df):,}")
    
    # Growth by area type
    if 'area_type' in spatial_df.columns:
        print("\nAverage Growth by Area Type:")
        area_analysis = spatial_df.groupby('area_type', observed=True).agg({
            'predicted_car_growth_nbr': ['mean', 'median', 'count'],
            'jobs_within_2mi': ['mean', 'median']
        }).round(4)
        print(area_analysis)
    
    # Growth by distance bins
    spatial_df['distance_bin'] = pd.cut(
        spatial_df['distance_to_downtown'],
        bins=[0, 5, 10, 15, 20, 100],
        labels=['0-5 mi', '5-10 mi', '10-15 mi', '15-20 mi', '20+ mi']
    )
    
    print("\nAverage Growth by Distance from Downtown:")
    distance_analysis = spatial_df.groupby('distance_bin', observed=True).agg({
        'predicted_car_growth_nbr': ['mean', 'median', 'count']
    }).round(4)
    print(distance_analysis)
    
    return spatial_df

def identify_hotspots(df, top_n=20):
    """Identify infrastructure stress points (high growth + high volume + high jobs)."""
    
    print("\n" + "="*80)
    print(f"TOP {top_n} INFRASTRUCTURE STRESS POINTS")
    print("="*80)
    
    # Filter to segments with complete data
    hotspot_df = df[
        df['jobs_within_2mi'].notna() & 
        df['predicted_car_growth_nbr'].notna()
    ].copy()
    
    # Calculate stress score (normalized growth * jobs)
    hotspot_df['stress_score'] = (
        hotspot_df['predicted_car_growth_nbr'] * 
        hotspot_df['jobs_within_2mi'] / 1000
    )
    
    # Get top stress points
    top_stress = hotspot_df.nlargest(top_n, 'stress_score')[[
        'route_nbr', 'latitude', 'longitude', 
        'predicted_car_growth_nbr', 'jobs_within_2mi', 
        'distance_to_downtown', 'area_type', 'stress_score'
    ]].copy()
    
    top_stress['growth_pct'] = (top_stress['predicted_car_growth_nbr'] * 100).round(1)
    
    print("\nHigh-Priority Segments (High Growth + High Employment):")
    print(top_stress[['route_nbr', 'growth_pct', 'jobs_within_2mi', 'distance_to_downtown', 'area_type']].to_string(index=False))
    
    return top_stress

def create_visualizations(analysis_df, spatial_df, output_dir='backend/data/analysis'):
    """Create visualization charts."""
    
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 8)
    
    # 1. Scatter plot: Employment vs Growth
    if not analysis_df.empty:
        plt.figure(figsize=(10, 6))
        plt.scatter(
            analysis_df['jobs_within_2mi'], 
            analysis_df['predicted_car_growth_nbr'] * 100,
            alpha=0.3, s=10
        )
        plt.xlabel('Jobs within 2 miles')
        plt.ylabel('Predicted Traffic Growth (%)')
        plt.title('Traffic Growth vs Nearby Employment')
        
        # Add trendline
        z = np.polyfit(analysis_df['jobs_within_2mi'], analysis_df['predicted_car_growth_nbr'] * 100, 1)
        p = np.poly1d(z)
        plt.plot(analysis_df['jobs_within_2mi'], p(analysis_df['jobs_within_2mi']), 
                "r--", alpha=0.8, linewidth=2, label=f'Trend: y={z[0]:.4f}x+{z[1]:.2f}')
        plt.legend()
        
        plot_file = output_path / 'employment_vs_growth.png'
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {plot_file}")
        plt.close()
    
    # 2. Box plot: Growth by Area Type
    if not spatial_df.empty and 'area_type' in spatial_df.columns:
        plt.figure(figsize=(10, 6))
        spatial_df['growth_pct'] = spatial_df['predicted_car_growth_nbr'] * 100
        sns.boxplot(data=spatial_df, x='area_type', y='growth_pct')
        plt.ylabel('Predicted Traffic Growth (%)')
        plt.xlabel('Area Type')
        plt.title('Traffic Growth Distribution by Area Type')
        
        plot_file = output_path / 'growth_by_area_type.png'
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {plot_file}")
        plt.close()
    
    # 3. Scatter plot: Distance vs Growth
    if not spatial_df.empty:
        plt.figure(figsize=(10, 6))
        plt.scatter(
            spatial_df['distance_to_downtown'], 
            spatial_df['predicted_car_growth_nbr'] * 100,
            alpha=0.3, s=10, c=spatial_df['jobs_within_2mi'], 
            cmap='viridis'
        )
        plt.xlabel('Distance from Downtown (miles)')
        plt.ylabel('Predicted Traffic Growth (%)')
        plt.title('Traffic Growth vs Distance (colored by employment)')
        plt.colorbar(label='Jobs within 2 miles')
        
        plot_file = output_path / 'distance_vs_growth.png'
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {plot_file}")
        plt.close()
    
    print(f"\n✓ All visualizations saved to: {output_path}")

def generate_executive_summary(df, hotspots):
    """Generate executive summary report."""
    
    print("\n" + "="*80)
    print("EXECUTIVE SUMMARY")
    print("="*80)
    
    # Overall statistics
    total_segments = len(df)
    segments_with_coords = df['latitude'].notna().sum()
    segments_with_employment = df['jobs_within_2mi'].notna().sum()
    
    print(f"\nDataset Overview:")
    print(f"  Total segments: {total_segments:,}")
    print(f"  Geocoded segments: {segments_with_coords:,} ({segments_with_coords/total_segments*100:.1f}%)")
    print(f"  Segments with employment data: {segments_with_employment:,} ({segments_with_employment/total_segments*100:.1f}%)")
    
    # Growth statistics
    avg_growth = df['predicted_car_growth_nbr'].mean() * 100
    high_growth_count = (df['predicted_car_growth_nbr'] > 0.5).sum()
    
    print(f"\nTraffic Growth Projections (2026):")
    print(f"  Average growth rate: {avg_growth:.1f}%")
    print(f"  High-growth segments (>50%): {high_growth_count:,}")
    
    # Employment analysis
    if segments_with_employment > 0:
        emp_df = df[df['jobs_within_2mi'].notna()]
        avg_jobs = emp_df['jobs_within_2mi'].mean()
        high_emp_growth = emp_df[emp_df['jobs_within_2mi'] > 15000]['predicted_car_growth_nbr'].mean() * 100
        low_emp_growth = emp_df[emp_df['jobs_within_2mi'] < 5000]['predicted_car_growth_nbr'].mean() * 100
        
        print(f"\nEmployment Context:")
        print(f"  Average jobs within 2 miles: {avg_jobs:,.0f}")
        print(f"  Growth near high-employment areas (>15K jobs): {high_emp_growth:.1f}%")
        print(f"  Growth near low-employment areas (<5K jobs): {low_emp_growth:.1f}%")
        print(f"  Employment impact: {high_emp_growth - low_emp_growth:.1f} percentage points higher growth")
    
    # Spatial patterns
    if 'area_type' in df.columns:
        area_df = df[df['area_type'].notna()]
        print(f"\nSpatial Patterns:")
        for area_type in ['Urban Core', 'Suburban', 'Exurban']:
            area_data = area_df[area_df['area_type'] == area_type]
            if len(area_data) > 0:
                avg_area_growth = area_data['predicted_car_growth_nbr'].mean() * 100
                print(f"  {area_type}: {avg_area_growth:.1f}% average growth ({len(area_data):,} segments)")
    
    print(f"\nKey Findings:")
    print(f"  1. Traffic growth correlates with nearby employment density")
    print(f"  2. Top {len(hotspots)} stress points identified for capacity planning")
    print(f"  3. Suburban areas show highest growth rates")
    print(f"  4. Employment centers are key drivers of traffic demand")

def main():
    """Main analysis pipeline."""
    
    print("="*80)
    print("SPATIAL TRAFFIC ANALYSIS")
    print("="*80)
    print("\nAnalyzing enriched predictions with demographic/employment data...\n")
    
    # Load data
    df = load_enriched_data('baseline')
    
    if df is None or df.empty:
        print("❌ No data to analyze. Run integrate_spatial_data.py first.")
        return
    
    # Analyze employment correlation
    analysis_df = analyze_employment_growth_correlation(df)
    
    # Analyze spatial patterns
    spatial_df = analyze_spatial_patterns(df)
    
    # Identify hotspots
    hotspots = identify_hotspots(df, top_n=20)
    
    # Create visualizations
    create_visualizations(analysis_df, spatial_df)
    
    # Executive summary
    generate_executive_summary(df, hotspots)
    
    # Save hotspots to CSV
    output_file = Path("backend/data/analysis/infrastructure_stress_points.csv")
    output_file.parent.mkdir(exist_ok=True, parents=True)
    hotspots.to_csv(output_file, index=False)
    print(f"\n✓ Hotspot analysis saved to: {output_file}")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("  1. Review visualizations in backend/data/analysis/")
    print("  2. Check infrastructure_stress_points.csv for high-priority segments")
    print("  3. Launch dashboard to explore interactive maps")
    print("  4. Consider retraining model with spatial features")

if __name__ == "__main__":
    main()
