"""Create visualizations for 2026 traffic growth scenarios.

Generates publication-ready charts comparing different growth scenarios
for Columbus District 6 traffic predictions.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'


def create_scenario_comparison_charts():
    """Generate comprehensive comparison charts for all scenarios."""
    
    # Load summary data
    summary_file = Path("backend/data/predictions/2026_scenarios_summary.csv")
    if not summary_file.exists():
        print("Error: Run predict_scenarios_2026.py first to generate data!")
        return
    
    df_summary = pd.read_csv(summary_file)
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    fig.suptitle('Columbus District 6: 2026 Traffic Growth Scenarios Analysis', 
                 fontsize=18, fontweight='bold', y=0.98)
    
    # Color palette
    colors = sns.color_palette("viridis", len(df_summary))
    
    # Plot 1: Average predicted car growth by scenario
    ax1 = fig.add_subplot(gs[0, :2])
    bars = ax1.bar(df_summary['scenario'], df_summary['avg_predicted_car_growth'], 
                   color=colors, edgecolor='black', linewidth=1.5)
    ax1.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='100% Growth Threshold', alpha=0.7)
    ax1.set_title('Average Predicted Car Growth Rate by Scenario', fontsize=14, fontweight='bold', pad=10)
    ax1.set_xlabel('Scenario', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Average Car Growth Rate', fontsize=11, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.3f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Plot 2: High-growth segments count
    ax2 = fig.add_subplot(gs[0, 2])
    wedges, texts, autotexts = ax2.pie(
        df_summary['high_growth_segments'], 
        labels=df_summary['scenario'],
        autopct='%1.0f%%',
        colors=colors,
        startangle=90
    )
    ax2.set_title('Distribution of\nHigh-Growth Segments', fontsize=12, fontweight='bold')
    plt.setp(autotexts, size=9, weight="bold")
    plt.setp(texts, size=8)
    
    # Plot 3: Input traffic growth vs predicted car growth
    ax3 = fig.add_subplot(gs[1, :2])
    scatter = ax3.scatter(
        (df_summary['volume_growth'] - 1) * 100,
        df_summary['avg_predicted_car_growth'],
        s=400,
        c=range(len(df_summary)),
        cmap='coolwarm',
        edgecolor='black',
        linewidth=2,
        alpha=0.8
    )
    
    # Add labels for each point
    for idx, row in df_summary.iterrows():
        ax3.annotate(
            row['scenario'],
            ((row['volume_growth'] - 1) * 100, row['avg_predicted_car_growth']),
            textcoords="offset points",
            xytext=(0, 10),
            ha='center',
            fontsize=9,
            fontweight='bold'
        )
    
    ax3.set_title('Traffic Volume Growth → Car Growth Relationship', fontsize=14, fontweight='bold', pad=10)
    ax3.set_xlabel('Input Traffic Volume Growth (%)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Predicted Average Car Growth Rate', fontsize=11, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Percentage of high-growth segments
    ax4 = fig.add_subplot(gs[1, 2])
    bars4 = ax4.barh(df_summary['scenario'], df_summary['pct_high_growth'], color=colors, edgecolor='black')
    ax4.set_title('% Segments with\n>100% Growth', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Percentage', fontsize=10, fontweight='bold')
    
    for bar in bars4:
        width = bar.get_width()
        ax4.text(width, bar.get_y() + bar.get_height()/2.,
                f'{width:.1f}%',
                ha='left', va='center', fontsize=9, fontweight='bold', 
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # Plot 5: Summary table
    ax5 = fig.add_subplot(gs[2, :])
    ax5.axis('tight')
    ax5.axis('off')
    
    table_data = []
    for _, row in df_summary.iterrows():
        table_data.append([
            row['scenario'].title(),
            f"{(row['volume_growth']-1)*100:.0f}%",
            f"{(row['truck_growth']-1)*100:.0f}%",
            f"{row['avg_predicted_car_growth']:.3f}",
            f"{row['median_predicted_car_growth']:.3f}",
            f"{row['high_growth_segments']:.0f}",
            f"{row['pct_high_growth']:.1f}%"
        ])
    
    table = ax5.table(
        cellText=table_data,
        colLabels=['Scenario', 'Volume\nGrowth', 'Truck\nGrowth', 
                  'Avg Car\nGrowth', 'Median Car\nGrowth', 
                  'High-Growth\nSegments', '% High-\nGrowth'],
        cellLoc='center',
        loc='center',
        bbox=[0, 0, 1, 1]
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    
    # Style header
    for i in range(7):
        table[(0, i)].set_facecolor('#4a90e2')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Alternate row colors
    for i in range(1, len(table_data) + 1):
        for j in range(7):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')
    
    # Save figure
    output_file = Path("backend/data/predictions/2026_scenarios_comparison.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✓ Saved: {output_file}")
    
    plt.show()


def create_distribution_charts():
    """Create distribution comparison across scenarios."""
    
    combined_file = Path("backend/data/predictions/2026_all_scenarios_combined.csv")
    if not combined_file.exists():
        print("Error: Combined data not found!")
        return
    
    df_combined = pd.read_csv(combined_file)
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Distribution of Predicted Car Growth by Scenario', 
                 fontsize=16, fontweight='bold')
    
    scenarios = df_combined['scenario'].unique()
    
    for idx, scenario in enumerate(scenarios):
        ax = axes[idx // 3, idx % 3]
        
        data = df_combined[df_combined['scenario'] == scenario]['predicted_car_growth_nbr']
        
        ax.hist(data, bins=30, color=sns.color_palette("viridis", len(scenarios))[idx],
               edgecolor='black', alpha=0.7)
        ax.axvline(data.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {data.mean():.3f}')
        ax.axvline(data.median(), color='orange', linestyle='--', linewidth=2, label=f'Median: {data.median():.3f}')
        
        ax.set_title(f'{scenario.title()}', fontsize=12, fontweight='bold')
        ax.set_xlabel('Predicted Car Growth', fontsize=10)
        ax.set_ylabel('Frequency', fontsize=10)
        ax.legend(fontsize=9)
        ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    output_file = Path("backend/data/predictions/2026_scenarios_distributions.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✓ Saved: {output_file}")
    
    plt.show()


if __name__ == "__main__":
    print("="*70)
    print("Generating 2026 Scenario Visualizations")
    print("="*70 + "\n")
    
    print("Creating comparison charts...")
    create_scenario_comparison_charts()
    
    print("\nCreating distribution charts...")
    create_distribution_charts()
    
    print("\n" + "="*70)
    print("✓ All visualizations complete!")
    print("="*70)
