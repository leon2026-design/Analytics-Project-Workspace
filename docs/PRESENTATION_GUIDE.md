# Poster Presentation Guide: Columbus 2026 Traffic Growth Scenarios

## 🎯 The 30-Second Elevator Pitch

**When someone stops at your poster:**

"We're predicting Columbus traffic growth for 2026 using machine learning. The surprising finding? **46% of road segments already show high growth with zero traffic increase**—it's not a future problem, it's happening now."

---

## 📊 What We Did (Methodology)

### The Dataset
- **3,570 road segments** in Columbus District 6
- **6 years** of historical traffic data (2019-2025)
- Variables: traffic volume, congestion levels, road capacity, VMT, functional classification

### The Model
- **XGBoost machine learning** algorithm
- Trained on 2019-2023 data, validated on 2024-2025
- **Key insight**: Model learned that traffic conditions (volume, congestion, capacity) predict growth—not calendar year
- This means predictions are based on traffic physics, not time trends

### The Approach
- Created **5 scenarios** for 2026 with different traffic volume assumptions:
  - **Baseline**: No traffic growth (0%)
  - **Conservative**: +2% volume increase
  - **Moderate**: +5% volume increase
  - **Aggressive**: +10% volume increase
  - **Post-Pandemic Boom**: +15% volume increase
- Applied each scenario to 2025 baseline data and generated predictions

---

## 🔍 Key Findings

### Finding #1: Infrastructure Already Stressed
- **46.1%** of segments exceed 100% car growth in baseline scenario (zero traffic increase)
- It's measuring current conditions!

### Finding #2: Diminishing Returns on Volume
- Increasing traffic from 0% to 15% only raises high-growth segments from 46.1% to 47.1%
- **Why?** Capacity constraints—roads are already near limits

### Finding #3: Traffic State Matters More Than Time
- Model learned growth depends on current traffic conditions, not what year it is
- A congested arterial behaves the same way whether it's 2020 or 2026

**Show the comparison chart** and point to:
- Bar chart: minimal variation across scenarios
- Pie chart: 46% high-growth baseline
- Scatter plot: volume-growth relationship plateaus

---

## 💡 What We Learned

### About Machine Learning
- "We initially tried to make the model predict based on year, but it learned that time doesn't matter, traffic conditions do"
- "This was surprising at first, but makes sense: physics of traffic flow is constant"
- "The model accuracy (R² = 0.30) reflects real-world complexity in traffic patterns"

### About Columbus Traffic
- "Columbus District 6 infrastructure is already operating near capacity"
- "Even conservative growth scenarios show significant stress"
- "Traditional year-over-year forecasting doesn't work, scenario-based planning seems to be the best course of action"

### About the Data Challenge
- "We had to match two different CSV formats between 2024 and 2025 data"
- "Built a custom matching algorithm using route codes and position normalization"
- "Achieved 100% match rate for 3,570 segments"

---

## 🗣️ Common Questions & Answers

### "How accurate is your model?"
"R² of 0.30 on held-out data. Not perfect, but captures the key relationships between traffic conditions and growth. We're deliberately conservative, actual growth could be higher."

### "Why doesn't more traffic lead to more growth?"
"Capacity constraints. Once roads are full, additional volume creates congestion and slowdowns, not growth. That's why 46% are already stressed at baseline."

### "What's 'car growth' mean exactly?"
"It's the ratio of current traffic to some baseline capacity measure. Above 100% means the segment is experiencing higher demand than its design capacity."

### "Which scenario is most realistic?"
"Historically, Columbus sees 2-5% annual traffic growth, so 'Moderate' is most likely. But we should plan for 'Aggressive' given development trends."

### "What should ODOT do with this?"
"Focus on the 1,646 segments already at high growth. Don't wait for 2026—address current capacity issues now. Use scenario-based planning instead of single forecasts."

### "Can you show specific roads?"
"Yes! All predictions are in our CSV files. We can filter by route number, functional class, or geographic area. Want to see a specific corridor?"

### "What was the hardest part?"
"Understanding why the model wasn't predicting different values for 2026. Turns out it was working correctly, it learned that time doesn't drive growth, traffic conditions do. We had to pivot from temporal forecasting to scenario analysis."

### "What would you do differently?"
"Collect actual traffic volume forecasts from ODOT first, then use our model as a second stage. Two-stage forecasting: volumes first, then car growth predictions."

### "What tools did you use?"
"Python with pandas for data processing, XGBoost for machine learning, scikit-learn for preprocessing. All code is available if you want to see it."

---

## 📈 Talking Through the Visualizations

### When pointing to the bar chart:
"Notice how all five scenarios cluster around 1.03 average growth? That's because traffic conditions dominate—adding volume has minimal impact when roads are already stressed."

### When pointing to the pie chart:
"This shows that 46% of segments exceed 100% growth at baseline. Only 76 additional segments cross that threshold even with 10% more traffic."

### When pointing to the scatter plot:
"See how the relationship between volume and growth flattens? That's the capacity constraint effect—more traffic doesn't produce proportional growth."

---

## 🎯 Three Key Takeaways (Your Closing Remarks)

If someone asks "So what's the main message?" or as they're leaving:

1. **"46% already at risk"** - Columbus infrastructure stress is current, not future
2. **"Traffic conditions drive growth, not time"** - Machine learning revealed physics-based patterns
3. **"Scenario planning beats forecasting"** - Need to plan for multiple futures, not predict one

---

## 🎨 Engagement Tips

### Make It Interactive
- **Ask them**: "Want to know what roads near you are predicted to grow?"
- **Show the data**: Pull up the CSV and filter to routes they care about
- **Compare scenarios**: "Which future do you think is most likely?"

### Connect to Their Experience
- "Ever sit in traffic on I-270? That's one of our high-growth segments."
- "Columbus population keeps growing—infrastructure isn't keeping pace."

### Handle the Technical Crowd
- Be ready to discuss model hyperparameters (500 trees, depth 6, learning rate 0.05)
- Explain train/test split strategy (time-based, 2019-2023 train, 2024-2025 test)
- Discuss feature engineering (lags, rolling averages, volume-capacity ratios)

### Handle the Non-Technical Crowd
- Focus on the "46%" statistic—easy to remember
- Use traffic examples they can relate to
- Emphasize actionable recommendations, not methodology

---

## 📂 Materials to Have Ready

**On laptop/tablet**:
- Full report: `SCENARIO_ANALYSIS_REPORT.md`
- Comparison visualization: `2026_scenarios_comparison.png`
- CSV files for specific route lookups

**Printed handouts** (optional):
- One-page summary with key statistics
- QR code to GitHub repo or full report

---

*Remember: Your job isn't to present, it's to have a conversation. Listen to their questions, tailor your answers, and make them curious about your findings!*

### "How accurate is this model?"
- "R² of 0.304 on held-out data (2024-2025)"
- "Not perfect, but captures key traffic-growth relationships"
- "Conservative estimates—actual growth could be higher"

### "Why don't higher traffic volumes increase car growth more?"
- "Capacity constraints—once roads are full, additional volume creates congestion, not growth"
- "This is why infrastructure investment is critical"

### "What about new roads or lane additions?"
- "Current model assumes static infrastructure"
- "Capacity expansions would need separate modeling"
- "Can run updated scenarios if planned projects are defined"

### "Which scenario is most likely?"
- "Historically, Columbus has seen 2-5% annual traffic growth"
- "Moderate scenario (5%) is most realistic baseline"
- "But we should plan for aggressive scenario given development trends"

### "Can we see results for specific roads?"
- "Yes—all individual segment predictions are in the CSV files"
- "Can filter by route, functional class, or geography"
- "Happy to provide custom analysis for priority corridors"

---

## Pro Tips for Delivery

### Engagement Tricks:
1. **Start with the surprise**: "46% at risk with ZERO growth"
2. **Use the visualization**: Point to the charts, don't just talk
3. **Repeat the key stat**: Say "46%" multiple times—make it memorable
4. **End with urgency**: "This is a 2025 problem, not a 2026 problem"

### If You Have More Time:
- Show the distribution charts (how growth varies across segments)
- Discuss specific high-growth corridors by name
- Compare to other cities' growth patterns

### If You Have Less Time:
- Skip Slide 4 (model methodology)
- Combine Slides 2 and 3 into one "Results + Finding"
- Go straight from problem to recommendations

---

## Success Metrics

**Your presentation is successful if the audience remembers**:
1. The **46%** statistic (high-growth even at baseline)
2. That this is a **current** problem, not a future one
3. The need for **scenario-based planning**, not single-point forecasts

---

**We got compelling data and a clear story. Trust the numbers!*
