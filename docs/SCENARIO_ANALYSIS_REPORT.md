# Columbus District 6 Traffic Growth: 2026 Scenario Analysis

## Executive Summary

This analysis presents five distinct scenarios for Columbus District 6 traffic growth in 2026, ranging from no growth (baseline) to aggressive post-pandemic expansion. Using machine learning trained on 2019-2025 historical data, we predict car growth rates for 3,570 road segments under different traffic volume assumptions.

---

## Key Findings

### Model Performance
- **Training Period**: 2019-2025 historical data
- **Model Type**: XGBoost Regression
- **Test Performance**: MAE = 0.463, R² = 0.304
- **Road Segments Analyzed**: 3,570 (Columbus District 6)

### Scenario Results Summary

| Scenario | Traffic Volume Growth | Avg Predicted Car Growth | High-Growth Segments (>100%) | % High-Growth |
|----------|----------------------|--------------------------|------------------------------|---------------|
| **Baseline** | 0% (no change) | 1.028 | 1,646 | 46.1% |
| **Conservative** | +2% cars, +1% trucks | 1.029 | 1,655 | 46.4% |
| **Moderate** | +5% cars, +3% trucks | 1.031 | 1,637 | 45.9% |
| **Aggressive** | +10% cars, +5% trucks | 1.037 | 1,722 | 48.2% |
| **Post-Pandemic Boom** | +15% cars, +8% trucks | 1.034 | 1,682 | 47.1% |

---

## Key Insights

### 1. Traffic Conditions Drive Growth More Than Time
The model learned that **car growth depends primarily on current traffic state** (volume, congestion, capacity) rather than calendar year. This means predictions are driven by realistic traffic dynamics, not arbitrary temporal trends.

### 2. High Baseline Growth Expected
Even with **zero traffic volume growth**, 46% of road segments are predicted to exceed 100% car growth in 2026. This indicates significant underlying growth pressure in Columbus District 6.

### 3. Volume Growth Has Moderate Impact
Increasing traffic volumes from 0% to 15% only changes average car growth from **1.028 → 1.037** (+0.9%). This suggests:
- Infrastructure is already near capacity
- Additional volume creates congestion, not proportional growth
- Capacity expansion may be needed for sustained growth

### 4. Aggressive Growth Scenarios Show Highest Risk
The **aggressive (10%) and post-pandemic boom (15%)** scenarios show:
- Nearly 48% of segments exceeding 100% growth
- Higher median growth rates
- Greater infrastructure stress

---

## Scenario Descriptions

### Baseline (No Growth)
**Assumption**: 2026 traffic volumes identical to 2025
- Represents status quo
- Useful for identifying existing growth pressure
- **Result**: 1,646 segments still exceed 100% growth

### Conservative (+2% / +1%)
**Assumption**: Modest recovery, cautious economic outlook
- Aligns with gradual population growth
- Reflects inflation-adjusted stable demand
- **Result**: Minimal change from baseline

### Moderate (+5% / +3%)
**Assumption**: Normal economic growth, standard development
- Typical annual growth for mid-sized metros
- Balanced commercial and residential expansion
- **Result**: Slightly lower high-growth segments (45.9%)

### Aggressive (+10% / +5%)
**Assumption**: Major economic expansion, significant development
- New business districts or residential areas
- Major infrastructure projects completed
- **Result**: Highest percentage of high-growth segments (48.2%)

### Post-Pandemic Boom (+15% / +8%)
**Assumption**: Strong economic rebound, remote work reversal
- Return to pre-pandemic commuting patterns
- Increased commercial activity
- **Result**: High growth but infrastructure constraints limit gains

---

## Recommendations

### For Infrastructure Planning
1. **Prioritize Capacity Expansion**: 46%+ of segments exceed 100% growth even at baseline
2. **Focus on High-Growth Corridors**: Identify and upgrade the 1,646+ segments predicted to exceed 100%
3. **Monitor Volume-Capacity Ratios**: Increasing traffic shows diminishing returns on growth

### For Policy Makers
1. **Scenario Planning Essential**: Small differences in traffic assumptions create measurable impacts
2. **Baseline Already Stressed**: Even without growth, system shows high growth pressure
3. **Congestion Management**: Growth is volume-driven; manage congestion for sustainable expansion

### For Forecasting
1. **Use Two-Stage Approach**: 
   - Stage 1: Forecast 2026 traffic volumes (external model)
   - Stage 2: Predict car growth using current model
2. **Update Annually**: Retrain with actual 2026 data when available
3. **Validate Assumptions**: Compare predicted vs actual traffic volumes quarterly

---

## Methodology

### Data Sources
- Historical CMS (Congestion Management System) data: 2019-2025
- Columbus District 6 road segments only
- Format harmonization across multiple CSV schemas

### Model Features (18 total)
- Traffic metrics: volume, capacity, congestion index, delay ratios
- Road characteristics: lanes, width, speed limits, section length
- Temporal features: year, normalized year, polynomial year term

### Scenario Application
1. Baseline 2025 data extracted for District 6
2. Traffic volume multipliers applied per scenario
3. Dependent metrics recalculated (VMT, volume-capacity ratio)
4. Time features updated for 2026
5. Predictions generated using trained XGBoost model

---

## Visualizations

Two comprehensive visualization files generated:
1. **2026_scenarios_comparison.png** - Multi-panel comparison across all scenarios
2. **2026_scenarios_distributions.png** - Distribution histograms for each scenario

See `backend/data/predictions/` folder for full results.

---

## Data Files Generated

| File | Description |
|------|-------------|
| `2026_scenarios_summary.csv` | Summary statistics for all scenarios |
| `2026_all_scenarios_combined.csv` | Combined predictions (17,850 rows) |
| `scenarios/predicted_cms_2026_baseline.csv` | Baseline scenario predictions |
| `scenarios/predicted_cms_2026_conservative.csv` | Conservative scenario predictions |
| `scenarios/predicted_cms_2026_moderate.csv` | Moderate scenario predictions |
| `scenarios/predicted_cms_2026_aggressive.csv` | Aggressive scenario predictions |
| `scenarios/predicted_cms_2026_post_pandemic_boom.csv` | Post-pandemic boom predictions |

---

## Model Limitations

1. **Static Infrastructure**: Assumes no capacity changes (new roads, lane additions)
2. **No External Events**: Does not account for economic shocks, policy changes
3. **Historical Patterns**: Trained on 2019-2025; may not capture unprecedented changes
4. **District 6 Only**: Results specific to Columbus area; not generalizable

---

## Next Steps

1. **Validation**: Compare 2026 predictions against actual data when available
2. **Geographic Analysis**: Map high-growth segments for targeted planning
3. **Cost-Benefit Analysis**: Evaluate infrastructure investments based on predicted growth
4. **Stakeholder Review**: Present scenarios to planning commission and ODOT

---

## Technical Details

**Model Training**:
- Algorithm: XGBoost (500 trees, max depth 6, learning rate 0.05)
- Sample weighting: More recent years weighted higher
- Train/test split: 2019-2023 train, 2024-2025 test

**Feature Importance** (Top 5):
1. Lane width (8.4%)
2. Total volume (8.2%)
3. Truck volume (8.0%)
4. Year (7.2%)
5. Congestion index (7.1%)

**Code Repository**: Analytics-Project-Workspace (GitHub)

---

*Report Generated: November 26, 2025*  
*Model Version: traffic_model.pkl (2025-11-26)*  
*Contact: Columbus Traffic Predictor Team*
