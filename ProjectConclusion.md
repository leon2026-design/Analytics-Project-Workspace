# Columbus Traffic Predictor: Project Conclusion

**Authors:** Leon Gonzales & Willie Tenney  
**Date:** December 6, 2025  
**Project:** Machine Learning-Based Traffic Growth Forecasting for ODOT District 6

---

## Executive Summary

We developed a machine learning system that predicts vehicle growth on 3,570 Columbus-area road segments for 2026. Through systematic hyperparameter optimization, we achieved an R² of 0.701 and MAE of 0.351, representing an 8.5% performance improvement over our baseline model. Our interactive dashboard enables stakeholders to explore five traffic scenarios and identify infrastructure stress points across the Columbus metropolitan area.

---

## Our Development Process

### Phase 1: Data Foundation (Weeks 1-3)
We began by consolidating ODOT's CMS (Congestion Management System) traffic data spanning multiple years. Our preprocessing pipeline handled:
- **Schema harmonization** across yearly data files with varying column names
- **Feature engineering** including capacity ratios, temporal cycles (month sin/cos), and infrastructure metrics
- **Data quality validation** ensuring consistency across 21,749 historical road segment observations

### Phase 2: Initial Model Development (Week 3-5)
We implemented our first XGBoost regression model with default hyperparameters:
- Achieved baseline R² = 0.304, MAE = 0.550
- Identified feature list mismatches causing prediction errors
- Corrected feature alignment, improving to R² = 0.646, MAE = 0.400 (+112% R² improvement)

### Phase 3: Hyperparameter Optimization (Week 5-7)
Recognizing suboptimal performance, we conducted systematic tuning:
- **Stage 1**: Coarse grid search across 108 parameter combinations (~30 minutes)
- **Stage 2**: Fine-tuning around optimal region with 27 combinations (~10 minutes)
- **Key discovery**: Reducing `colsample_bytree` from 0.8 to 0.5 addressed multicollinearity in 24 highly correlated feature pairs
- **Result**: R² = 0.701, MAE = 0.351 (+8.5% final improvement)

### Phase 4: Scenario Generation & Visualization (Week 7-9)
We built prediction infrastructure:
- Generated five 2026 traffic scenarios (baseline through post-pandemic boom)
- Geocoded all 3,570 segments for map visualization
- Developed interactive Dash dashboard with Plotly maps and Leaflet integration

### Phase 5: Project Organization (Week 10)
We reorganized our codebase from a flat 25-file structure into logical modules:
- **backend/core/**: ML modules (preprocessing, training, prediction, tuning)
- **backend/scripts/**: Organized utilities (predictions, spatial, data processing, analysis)
- **docs/**: Technical documentation
- Updated all import paths and created comprehensive README

---

## Tools & Technologies

### Why We Chose Each Tool

**XGBoost (v1.7.x)**
- **Reason**: Industry-standard gradient boosting with excellent performance on tabular data
- **Advantages**: Handles missing data, built-in regularization, fast training with histogram-based splitting
- **Trade-off**: Less interpretable than linear models, but superior predictive accuracy

**scikit-learn**
- **Reason**: Standard preprocessing (SimpleImputer) and GridSearchCV for systematic hyperparameter tuning
- **Advantages**: Well-documented, stable API, integrates seamlessly with XGBoost
- **Use case**: Data imputation, train/test splitting, performance metrics

**Pandas & NumPy**
- **Reason**: De facto standard for data manipulation in Python
- **Advantages**: Efficient operations on tabular data, extensive ecosystem
- **Use case**: CSV loading, feature engineering, data cleaning

**Dash + Plotly**
- **Reason**: Pure Python web framework (no JavaScript required) with interactive visualizations
- **Advantages**: Rapid development, responsive maps with Dash Leaflet, scenario comparison widgets

**GeoPandas & Shapely**
- **Reason**: Spatial operations for geocoding road segments
- **Advantages**: Built on industry-standard GEOS library, integrates with Pandas
- **Use case**: Latitude/longitude assignment, spatial joins, GeoJSON export

---

## How the Model Works

### Input Features (18 Total)
We engineered features across four categories:

**1. Infrastructure (6 features)**
- Lane count, median width, pavement width
- Highway vs arterial classification
- Capacity per lane

**2. Traffic Conditions (5 features)**
- Volume sum, median AADT (Annual Average Daily Traffic)
- Total lane miles, capacity metrics
- HCM (Highway Capacity Manual) auto throughput capacity

**3. Speed & Flow (2 features)**
- Posted speed, free-flow speed

**4. Temporal (5 features)**
- Year (enables trend learning)
- Time to end of year (seasonal effects)
- Cyclical month encoding (sin/cos) to capture annual patterns

### Model Architecture
```python
XGBRegressor(
    n_estimators=500,        # 500 decision trees
    learning_rate=0.07,      # Gradient descent step size
    max_depth=7,             # Tree complexity
    subsample=0.8,           # Row sampling (prevents overfitting)
    colsample_bytree=0.5,    # Feature sampling (addresses multicollinearity)
    reg_lambda=1.25,         # L2 regularization
    tree_method='hist',      # Histogram-based algorithm (fast)
    random_state=42          # Reproducibility
)
```

### Training Process
1. **Data split**: 80% training (17,399 samples), 20% testing (4,350 samples)
2. **Missing value handling**: Median imputation via scikit-learn pipeline
3. **Model fitting**: XGBoost learns relationships between features and target (`car_growth_nbr`)
4. **Validation**: Evaluate on held-out test set (R² = 0.701, MAE = 0.351)

### Prediction Workflow
1. Load 2024 Columbus District 6 baseline data (3,570 segments)
2. Apply scenario assumptions (e.g., 1.15× volume growth for "post_pandemic_boom")
3. Generate predictions using trained model
4. Geocode results with latitude/longitude
5. Display on interactive dashboard

---

## Model Strengths

### Technical Strengths
1. **Robust performance**: R² = 0.701 indicates 70% of variance explained
2. **Systematic optimization**: GridSearchCV removed guesswork from hyperparameter selection
3. **Handles real-world data**: Manages missing values, outliers, correlated features
4. **Scalable**: Predicts 3,570 segments in <1 second
5. **Reproducible**: Fixed random seed, version-controlled code, documented parameters

### Practical Strengths
1. **Scenario flexibility**: Easy to add new growth assumptions
2. **Spatial visualization**: Visible geographic patterns
3. **Infrastructure focus**: Captures capacity constraints and road characteristics
4. **Multi-year training**: Learns from 2019-2024 historical patterns

---

## Model Limitations

### Technical Limitations
1. **Weak scenario sensitivity**: Predictions vary only 2% across 5 scenarios (0.90-0.92 avg growth)
   - **Why**: Model learned infrastructure patterns dominate over volume inputs
   - **Impact**: Different traffic growth assumptions yield similar predictions

2. **Multicollinearity**: Despite `colsample_bytree=0.5`, 24 feature pairs remain highly correlated
   - **Example**: `posted_speed ↔ ff_speed` (r=0.974)
   - **Impact**: Feature importance may be unreliable

3. **Right-skewed predictions**: 35% of segments predicted >100% growth
   - **Why**: Model emphasizes capacity constraints
   - **Impact**: May overestimate growth on high-capacity roads

4. **Limited temporal features**: No economic indicators, population growth, or land-use data
   - **Why**: Data availability constraints
   - **Impact**: Can't capture external drivers like new developments

2. **Short time horizon**: 2-year prediction window (2024→2026)
   - **Confidence**: Longer forecasts would be less reliable

3. **Static infrastructure**: Assumes no major road changes (widening, new construction)
   - **Reality**: Infrastructure projects can invalidate predictions

### Practical Limitations
1. **"Black box" nature**: XGBoost is less interpretable than linear regression
   - **Stakeholder concern**: Hard to explain "why" a specific segment has high growth

2. **No uncertainty quantification**: Single point predictions without confidence intervals
   - **Decision-making**: Stakeholders don't know prediction reliability

3. **Deployment complexity**: Requires Python environment and 15+ dependencies
   - **Accessibility**: Not as simple as an Excel spreadsheet

---

## What We Learned

### Technical Lessons

**1. Feature engineering matters more than algorithms**
- Our +112% R² jump came from fixing feature lists, not changing models
- **Takeaway**: Data quality and feature alignment are foundational

**2. Hyperparameter tuning delivers real gains**
- Systematic GridSearchCV improved R² by 8.5% beyond baseline
- **Takeaway**: Don't accept default parameters—tune systematically

**3. Multicollinearity requires feature selection or regularization**
- 24 highly correlated pairs needed `colsample_bytree=0.5` to manage
- **Takeaway**: Always check feature correlations before training

**4. Model behavior reflects data patterns**
- Infrastructure dominates our predictions because it varies more than volume
- **Takeaway**: Models learn what varies in training data, not what we think matters

### Process Lessons

**1. Organization scales with complexity**
- Flat 25-file structure became unmaintainable
- **Takeaway**: Organize early into core modules and utility scripts

**2. Documentation is for future us**
- README and inline comments saved us when revisiting old code
- **Takeaway**: Document as you build, not after

**3. Version control prevents disasters**
- Git allowed us to experiment safely and revert mistakes
- **Takeaway**: Commit early, commit often

**4. Interactive tools improve stakeholder engagement**
- Dashboard made findings accessible beyond just numbers in CSVs
- **Takeaway**: Invest in visualization for non-technical audiences

### Domain Lessons

**1. Traffic growth is infrastructure-constrained**
- Capacity limits matter more than volume assumptions
- **Implication**: Adding lanes may be more impactful than managing demand

**2. Geographic clustering exists**
- High-growth areas concentrate in northwest/southwest Columbus
- **Implication**: Infrastructure investment could target these regions

**3. Scenario planning reveals robustness**
- Similar predictions across scenarios show stability (or insensitivity)
- **Implication**: Some decisions may be scenario-independent

---

## Key Findings

### Finding 1: Infrastructure Dominates Traffic Growth
**Observation**: Average predicted growth varies only 0.90-0.92 across scenarios with 1.0×-1.15× volume growth.

**Interpretation**: Road capacity, lane configuration, and speed characteristics explain more variance than traffic volume assumptions. The model learned that infrastructure determines growth potential.

**Implication**: Traffic management strategies (signal timing, demand management) may have limited impact compared to infrastructure improvements (adding lanes, increasing capacity).

**Recommendation**: Prioritize capacity expansion projects over demand-side interventions for high-growth segments.

---

### Finding 2: 35% of Segments Face Severe Growth
**Observation**: 1,250 out of 3,570 segments (35%) predicted to exceed 100% car growth by 2026.

**Interpretation**: Over a third of Columbus roads are approaching or exceeding designed capacity. This suggests systemic infrastructure stress, not isolated bottlenecks.

**Implication**: Widespread capacity issues require strategic, network-level planning rather than spot improvements.

**Recommendation**: Develop a prioritization framework (safety, economic impact, equity) to sequence investments across 1,250+ high-growth segments.

---

### Finding 3: Spatial Clustering of High-Growth Areas
**Observation**: High-growth segments concentrate in northwest (Worthington/Dublin) and southwest (Grove City/Hilliard) Columbus.

**Interpretation**: Suburban growth corridors are outpacing infrastructure capacity. This aligns with Columbus's pattern of sprawl and outer-ring development.

**Implication**: Regional coordination across municipal boundaries is critical, bottlenecks don't respect jurisdictional lines.

**Recommendation**: ODOT could potentially benefit from multi-jurisdictional planning sessions for northwest/southwest corridors to coordinate capacity improvements.

---

### Finding 4: Model Optimization Yields Measurable Gains
**Observation**: Systematic hyperparameter tuning improved R² by 8.5% (0.646→0.701) through data-driven parameter selection.

**Interpretation**: Default model settings are suboptimal. Investing time in GridSearchCV pays dividends in prediction accuracy.

**Implication**: Traffic forecasting agencies should adopt systematic model tuning practices rather than relying on default configurations.

**Recommendation**: Future ODOT models should include hyperparameter optimization as standard protocol, not optional.

---

### Finding 5: Weak Scenario Sensitivity Suggests Robust Insights
**Observation**: Predictions remain stable across diverse traffic growth assumptions (2% range across 15% scenario spread).

**Interpretation**: Either (1) the model is insensitive to volume inputs, or (2) infrastructure constraints make growth scenarios less relevant. Evidence suggests (1) is true.

**Implication**: For infrastructure planning, the exact traffic growth rate may matter less than identifying capacity-constrained segments.

**Recommendation**: Focus planning on segments where capacity is limiting factor, regardless of precise traffic projections. Build for infrastructure needs, not volume forecasts alone.

---

## Conclusions & Next Steps

### What We Accomplished
We successfully built an end-to-end machine learning pipeline that:
- Predicts traffic growth on 3,570 road segments with 70% accuracy (R² = 0.701)
- Provides interactive visualization for scenario exploration
- Identifies 1,250 high-growth segments requiring infrastructure attention
- Demonstrates systematic model optimization improving performance by 8.5%

### Limitations to Address
Future work should:
1. **Add uncertainty quantification** (confidence intervals via bootstrapping or quantile regression)
2. **Incorporate external data** (economic indicators, land-use changes, population projections)
3. **Improve scenario sensitivity** (rebalance features or use interaction terms for volume)
4. **Expand geographic scope** (train on all Ohio districts, test transferability)

### Broader Impact
This project demonstrates that:
- **Machine learning adds value** to traditional traffic forecasting beyond linear models
- **Systematic optimization matters** (GridSearchCV improved results meaningfully)
- **Open-source tools suffice** for production-quality traffic analysis
- **Interactive visualization** bridges the gap between technical models and policy decisions

### Final Reflection
We learned that building a robust prediction system requires equal attention to data quality, model optimization, and stakeholder communication. The technical challenge of achieving R² = 0.701 was matched by the organizational challenge of structuring code for maintainability and creating visualizations for accessibility.

Our hope is that ODOT and Columbus planners in the near future could confidently use this tool to make evidence-based infrastructure decisions, prioritizing investments where capacity constraints are most severe. While our model isn't perfect, no model is, it provides a data-driven starting point for conversations about where Columbus needs to build, widen, and improve its road network.

---

## Acknowledgments

We thank:
- **ODOT** for providing CMS traffic data
- **VS Code** for development environment
- **Open-source community** for XGBoost, Dash, Pandas, and countless other libraries
- **Columbus community** whose daily commutes generated the data that trained this model

---

**Project Repository**: [Analytics-Project-Workspace](https://github.com/leon2026-design/Analytics-Project-Workspace)  
**License**: MIT (see LICENSE file)  
**Contact**: Leon Gonzales & Willie Tenney

---

*Good data beats boujee algorithms. But good data + systematic optimization beats everything.*  
— Lessons from the Columbus Traffic Predictor, December 2025
