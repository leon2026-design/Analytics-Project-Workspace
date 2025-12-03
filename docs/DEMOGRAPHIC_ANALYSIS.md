# External Data Integration - Results & Analysis

## Summary

**Date**: November 30, 2025  
**Experiments**:  
1. Franklin County-level demographics (5 features)  
2. ZIP-level housing occupancy (3 features, 39 ZIP codes)  
3. County-level employment (4 features, Census LODES 2019-2022)

**Result**: ❌ **No improvement in model performance**

### Performance Comparison

| Experiment | R² | MAE | Features | Outcome |
|-----------|----|----|----------|---------|
| **Baseline** | **0.304** | **0.463** | 18 | ✅ Best |
| County Demographics | 0.290 | 0.469 | 23 | ❌ Worse (-0.014 R²) |
| ZIP Occupancy | 0.289 | 0.467 | 21 | ❌ Worse (-0.015 R²) |
| County Employment | 0.298 | 0.465 | 22 | ❌ Worse (-0.006 R²) |

---

## What We Tried

### Experiment 1: County-Level Demographics
**Source**: ACS 1-Year Estimates (DP05 - Demographic and Housing Estimates)  
**Geographic Level**: Franklin County aggregate  
**Features Added**:
1. **Total Population**: 1,316,756 (2019) → 1,326,063 (2023)
2. **Population Growth Rate**: ~0.18% annual average
3. **Median Age**: 34.3 (2019) → 35.1 (2023)
4. **Total Housing Units**: 564,363 (2019) → 601,843 (2023)
5. **Cumulative Population Growth**: 0.71% over 5 years

### Experiment 2: ZIP-Level Housing Occupancy
**Source**: ACS Table B25002 - Occupancy Status  
**Geographic Level**: 39 ZIP codes (ZCTAs) in Franklin County  
**Features Added**:
1. **Occupancy Rate**: 90.2% average across ZIPs
2. **Vacancy Rate**: 9.8% average
3. **Total Housing Units**: Per-ZIP counts

**Route-to-ZIP Mapping**: Created comprehensive mapping of 33 major routes (I-70, I-71, I-270, US-23, US-33, SR-3, SR-161, etc.) to their traversed ZIP codes. Segments assigned based on route + position.

---

## Why Demographics Didn't Help

### 🎯 Feature Importance Analysis

**County-Level Demographics**:
| Feature | Importance | Rank |
|---------|-----------|------|
| `population_growth_rate` | 2.74% | 19th |
| `total_population` | 1.67% | 20th |
| `median_age` | **0.00%** | 21st ❌ |
| `total_housing_units` | **0.00%** | 22nd ❌ |
| `cumulative_population_growth` | **0.00%** | 23rd ❌ |

**ZIP-Level Occupancy**:
| Feature | Importance | Correlation with Car Growth |
|---------|-----------|----------------------------|
| `occupancy_rate` | **0.00%** ❌ | +0.037 (very weak) |
| `vacancy_rate` | **0.00%** ❌ | -0.037 (very weak) |
| `total_housing_units` | **0.00%** ❌ | +0.016 (negligible) |

### 🔍 Root Cause Analysis

#### 1. **No Spatial Variation**
- **Problem**: All 3,570 road segments in District 6 get **identical** demographic values
- **Why**: Franklin County is a single geographic unit—every road gets the same population, median age, etc.
- **Model perspective**: These features don't help the model distinguish between Route 33 downtown vs. I-270 in Gahanna

#### 2. **Multicollinearity with Year**
- **Problem**: Demographic changes are perfectly correlated with time
  - Population grows linearly: 2019 → 2020 → 2021 → ...
  - Year features already capture this trend
- **Why**: `year_norm` and `year_poly2` already encode temporal information

#### 3. **Insufficient Temporal Variation**
- **Problem**: Only 5 years of data (2019-2023)
- **Change magnitude**: 0.71% population growth over 5 years (tiny!)
- **Model perspective**: This signal is too weak to matter compared to 100% car growth variations

#### 4. **Wrong Geographic Scale**
- **Problem**: Traffic growth varies **within** Franklin County
  - Downtown Columbus ≠ Suburban Dublin ≠ Rural Hilliard
  - County-level averages wash out these differences
- **Model perspective**: Need census tract or ZIP code data, not county aggregates

---

## Correlation Analysis

### County-Level Demographics vs. Car Growth
```
population_growth_rate       -0.018  (near zero, slightly negative)
total_population            -0.136  (weak negative)
cumulative_population_growth -0.136  (weak negative)
median_age                  -0.139  (weak negative)
```

### ZIP-Level Occupancy vs. Car Growth
```
occupancy_rate              +0.037  (very weak positive)
vacancy_rate                -0.037  (very weak negative)
total_housing_units         +0.016  (negligible)
```

**Interpretation**: 
- All correlations are extremely weak (<0.04 for ZIP, <0.15 for county)
- ZIP-level data shows slightly positive relationship (higher occupancy → slightly higher growth)
- However, effect is too small to improve predictions
- **Key insight**: Static demographic snapshots don't capture growth dynamics

---

## Lessons Learned

### What Doesn't Work
1. **County-level demographics** for segment-level predictions
2. **Highly aggregated temporal data** (5 years, 4 data points + 1 interpolated)
3. **Features collinear with year**

### ✅ What Would Work Better

#### **Option 1: Census Tract-Level Demographics** (Recommended)
- **What**: Link each road segment to its census tract
- **Why**: Captures **spatial variation** (urban vs. suburban)
- **Data**: ACS 5-Year Estimates at tract level
- **Challenge**: Requires geocoding (lat/lon) to match segments to tracts
- **Expected R² gain**: +0.05 to +0.10

**Implementation**:
```python
# Geocode road segments (if lat/lon available)
segments_gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat))

# Spatial join to census tracts
tracts = gpd.read_file("census_tracts.geojson")
df_joined = gpd.sjoin(segments_gdf, tracts, how="left", predicate="within")

# Now each segment has tract-specific demographics
```

#### **Option 2: Development/Land Use Data** (High Impact)
- **What**: Building permits, new developments, business openings
- **Why**: Directly drives trip generation
- **Data**: Franklin County Auditor, MORPC, city planning departments
- **Expected R² gain**: +0.06 to +0.12

**Example**:
- New 500-unit apartment complex 0.5 miles from segment → Higher car growth
- Amazon distribution center opening nearby → Higher truck growth

#### **Option 3: Employment Density** (Moderate Impact)
- **What**: Jobs within 1-mile radius of each segment
- **Why**: Job centers = commute destinations = traffic
- **Data**: Census OnTheMap (LEHD), county GIS
- **Expected R² gain**: +0.05 to +0.10

**Example**:
- Route 33 near downtown (50,000 jobs/sq mi) vs. rural Route 161 (500 jobs/sq mi)

#### **Option 4: Point-of-Interest (POI) Data** (Lower Impact)
- **What**: Count of malls, schools, hospitals, stadiums near segment
- **Why**: Attractors generate trips
- **Data**: OpenStreetMap, Google Places API
- **Expected R² gain**: +0.02 to +0.05

---

## Recommendations

### For Research Gala Presentation

**What to say**:
> "We experimented with adding demographic data (population growth, median age) from the Census Bureau. Surprisingly, county-level demographics **didn't improve predictions** (R² decreased from 0.30 to 0.29). This taught us that **spatial resolution matters**—traffic growth varies within Columbus, so we need neighborhood-level data, not county averages. Future work will explore census tract demographics and development permits."

**Key takeaway**: 
- Shows scientific rigor (tried something, learned it didn't work)
- Demonstrates understanding of spatial scale
- Sets up future research directions

### For Model Improvement

**Priority 1**: Census Tract Demographics
- [ ] Download ACS 5-Year Estimates for all Franklin County census tracts
- [ ] Geocode road segments (or use begin/end lat/lon if available)
- [ ] Spatial join segments to tracts
- [ ] Retrain with tract-level population density, median income, working-age %

**Priority 2**: Development Data
- [ ] Scrape Franklin County building permit database (2019-2023)
- [ ] Aggregate permits within 1-mile radius of each segment
- [ ] Add as feature: `new_residential_units_nearby`, `new_commercial_sqft_nearby`

**Priority 3**: Employment Centers
- [ ] Download Census OnTheMap data for Franklin County
- [ ] Calculate job density around each segment
- [ ] Add as feature: `jobs_within_1mi`, `jobs_within_5mi`

---

## Technical Details

### Files Created
- `backend/integrate_acs_data.py` - Integration script
- `backend/data/processed/traffic_with_demographics.csv` - Enriched dataset (199,525 rows)
- `backend/data/processed/acs_demographics_summary.csv` - Demographics time series
- `backend/data/ACSDemographicHousing[year].csv` - Raw ACS files (2019, 2021-2023)

### Model Changes
- Added 5 demographic features to `FEATURES` list in `train_model.py`
- Modified `train_model()` to load demographics-enriched dataset
- Training now uses `use_demographics=True` by default

### To Disable Demographics
```python
# In backend/train_model.py
train_model(use_demographics=False)
```

Or delete/rename:
```powershell
mv backend/data/processed/traffic_with_demographics.csv traffic_with_demographics.csv.bak
```

---

## Appendix: ACS Data Structure

### Example: 2019 Demographics
```csv
Label (Grouping),Franklin County Ohio Estimate
Total population,1316756
Median age (years),34.3
Total housing units,564363
```

### Columns Extracted
- **Franklin County, Ohio!!Estimate** - Actual values
- **Franklin County, Ohio!!Margin of Error** - 90% confidence intervals (not used)

### Missing 2020 Data
**Reason**: COVID-19 pandemic disrupted census data collection  
**Solution**: Linear interpolation between 2019 and 2021  
**Formula**: `2020_value = (2019_value + 2021_value) / 2`

---

## Experiment 3: County-Level Employment (Census LODES)

**Date**: December 2025

### Data Source
**Source**: Census LEHD LODES (Longitudinal Employer-Household Dynamics)  
**Files**: Workplace Area Characteristics (WAC) 2019-2022  
**Geographic Level**: Franklin County aggregate (328 census tracts aggregated)  
**Coverage**: 4 years of employment data

### Employment Metrics (Franklin County)
| Year | Total Jobs | Job Growth Rate | High-Wage Share | Job Change |
|------|-----------|----------------|-----------------|------------|
| 2019 | 798,063 | — | 49.6% | — |
| 2020 | 766,264 | -4.0% | 50.9% | -31,799 |
| 2021 | 774,735 | +1.1% | 55.1% | +8,471 |
| 2022 | 798,714 | +3.1% | 57.9% | +23,979 |

**High-wage jobs**: Positions earning >$3,333/month (>$40k/year)

### Features Added
1. **total_jobs**: Total employment in Franklin County
2. **job_growth_rate**: Year-over-year percentage change
3. **job_growth_from_2019**: Cumulative growth from 2019 baseline
4. **high_wage_share**: Percentage of high-wage jobs

### Model Results
- **R² = 0.298** (baseline: 0.304) ❌ **-0.006 worse**
- **MAE = 0.465** (baseline: 0.463) ❌ Slightly higher error

### Feature Importance
| Feature | Importance | Rank |
|---------|-----------|------|
| high_wage_share | 4.4% | 12th |
| job_growth_rate | 3.8% | 13th |
| total_jobs | 2.9% | 19th |
| job_growth_from_2019 | 2.8% | 21st |

### Correlation with Traffic Growth
| Feature | Correlation |
|---------|------------|
| total_jobs | +0.015 |
| job_growth_from_2019 | +0.015 |
| job_growth_rate | -0.061 |
| high_wage_jobs | -0.112 |
| high_wage_share | -0.129 |

**Analysis**: Employment features show **weak or negative correlations** with traffic growth. This is surprising since employment should drive traffic, but county-level aggregation removes spatial patterns (e.g., downtown job centers vs suburban routes).

### Why Employment Data Didn't Help
1. **No spatial variation**: All 3,570 road segments in ODOT District 6 receive identical employment values
2. **Geographic mismatch**: Employment at census tract level (328 tracts) aggregated to county level loses 99.7% of spatial detail
3. **Weak temporal signal**: 4 years of data show pandemic dip/recovery but pattern is uniform across all segments
4. **Route-to-tract mapping failed**: Attempted to match road segments to census tracts using route numbers, but only 1.2% of segments matched to specific tracts, 98.8% defaulted to generic downtown tract

### Attempted Solutions
**Census Tract-Level Integration**: Created comprehensive route-to-tract mapping covering 70+ routes (I-70/71/270, US-23/33/40, SR-161/315/317, etc.), but traffic data lacks geographic identifiers (no lat/lon, no tract codes). Route-based matching proved insufficient.

**Key Challenge**: The traffic dataset (`CMS_D6_2024_2025_merged.csv`) contains `ROUTE_TYPE` and `ROUTE_NBR` columns but no geocoding. Without lat/lon or census tract IDs in the original data, spatial matching is impossible at scale.

---

## Conclusion

Three external data integration attempts all failed to improve model performance:
1. **County demographics**: R² decreased from 0.304 to 0.290
2. **ZIP occupancy**: R² decreased from 0.304 to 0.289  
3. **County employment**: R² decreased from 0.304 to 0.298

### Root Cause: Insufficient Spatial Granularity
All three approaches suffered from **spatial aggregation** that removes the variation needed for predictions:
- County-level data: 1 value for 3,570 segments (0% spatial variation)
- ZIP-level data: 39 values for 3,570 segments (~2% variation, 90% in few ZIPs)
- Employment tract-level: Failed to match segments to tracts without geocoding

### Key Learnings
1. **Spatial resolution is critical**: Need segment-level or at least census tract-level data with proper geographic matching
2. **Geographic identifiers required**: Traffic data needs lat/lon, census tract codes, or detailed route geometry to enable spatial joins
3. **Temporal variation alone insufficient**: Employment data showed clear pandemic trends (4% drop in 2020, 3% recovery by 2022) but without spatial differentiation, all segments see identical patterns
4. **Direct relevance matters less than spatial variation**: Employment should be highly relevant to traffic (job centers generate commutes), but county-level aggregation negates this relationship

### What Would Work
To improve the model with external data, we need:
1. **Geocoded road segments**: Lat/lon coordinates or census tract IDs for each segment
2. **Tract-level features**: Census tract demographics, employment density, development permits
3. **Local dynamic data**: Building permits, business openings/closings, land use changes
4. **Point-based matching**: Spatial join between segment midpoints and census geographies

---

## Critical Finding: Missing Geographic Coordinates

### The Fundamental Limitation

**The CMS traffic data lacks geographic coordinates**. Each segment has:
- ✅ `ROUTE_TYPE` (IR/SR/US) and `ROUTE_NBR` (route number)
- ✅ `CTL_BEGIN_NBR`, `CTL_END_NBR` (ODOT Control Section numbers - linear referencing)
- ✅ `STL_BEGIN_NBR`, `STL_END_NBR` (ODOT Section numbers - milepost positions)
- ❌ **No latitude/longitude coordinates**
- ❌ **No census tract IDs**
- ❌ **No ZIP codes or addresses**

**CTL/STL numbers** are ODOT's Linear Referencing System (LRS) - essentially mileposts along routes - but they **cannot be used for spatial matching** without a companion GIS dataset that maps these reference points to geographic coordinates.

### Impact on External Data Integration

Without geocoding, we **cannot**:
1. ❌ Match segments to census tracts (for tract-level employment/demographics)
2. ❌ Match segments to ZIP codes (for ZIP-level housing data)
3. ❌ Calculate distances to points of interest (airports, universities, job centers)
4. ❌ Perform spatial joins with any geographic dataset
5. ❌ Use spatial features like "employment density within 5 miles"

This explains why:
- County-level data: Same value for all segments → no spatial variation
- ZIP-level data: Route-based matching only covered 1.2% accurately
- Tract-level employment: Route-to-tract mapping failed for 98.8% of segments

### ODOT GIS Resources (Potential Solutions)

**Available from ODOT**:
1. **Straight Line Diagrams (SLDs)**: PDF diagrams showing CTL/STL positions along routes, but not in machine-readable format
2. **ODOT Location Finder App**: Mobile app that displays CTL/STL locations on maps, but no bulk data export
3. **Roadway Information GIS (RIGIS)**: ODOT maintains comprehensive GIS datasets, contact:
   - Vikki Hankus (RIGIS Manager): Vikki.Hankus@dot.ohio.gov, 614-752-5729
   - Ethan Pointer: Ethan.Pointer@dot.ohio.gov, 614-752-2970

**What to Request**:
1. **Road network shapefile** for District 6 with CTL/STL attributes
2. **CTL/STL to lat/lon crosswalk table** (route + CTL → coordinates)
3. **Census tract overlay** (which tracts does each route segment traverse)
4. **GIS data download portal** access if available to public/academic users

### Next Steps Options

**Option A: Obtain ODOT GIS Data** (Recommended if pursuing external data integration)
1. Contact ODOT RIGIS staff (see contacts above)
2. Request District 6 road network shapefile or CTL/STL geocoding crosswalk
3. Merge geographic coordinates with CMS traffic data on route + CTL/STL
4. Enable spatial joins with census tracts for tract-level employment/demographics
5. **Expected R² improvement**: +0.05 to +0.10 (if tract-level features add signal)

**Option B: Accept Current Model Limitations**
1. Baseline R²=0.304 may represent ceiling without geocoding
2. Focus on feature engineering with existing traffic/infrastructure metrics
3. Explore non-linear interactions, ensemble methods, time series approaches
4. Use model as-is for relative comparisons and trend analysis

**Option C: Alternative Data Sources**
1. Use publicly available GIS data (Ohio county road networks from USGS, OpenStreetMap)
2. Attempt probabilistic matching based on route + county + milepost ranges
3. Lower accuracy but may provide some spatial variation
4. **Risk**: High error rate in segment-to-tract assignments

### Recommendation

**Contact ODOT RIGIS** to determine if geocoded road network data is available for public/academic use. Without geographic coordinates, external spatial data integration is not feasible beyond county-level aggregates (which we've proven ineffective). The baseline model (R²=0.304, MAE=0.463) appears to capture most predictable signal from available non-spatial features.
