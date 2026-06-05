I want to show examples of text based charts that I can generate using python.
Please use Python environment.
Please download a CSV file of some statistical data such as the Titanic survival rate sample data.
Analyse the CSV data and then generate a few charts to showcase the findings.
Display the text charts on the terminal, using python libraries such as Asciichartpy, Plotext, and Tplot.



TEXT-BASED CHART EXAMPLES USING PYTHON
================================================================================

This project demonstrates how to create text-based charts in Python using three
popular libraries: Asciichartpy, Plotext, and Tplot.

PROJECT STRUCTURE
================================================================================

Files created:
  • titanic.csv              - Downloaded Titanic dataset (891 passengers)
  • analyze_titanic.py       - Main analysis script with Asciichartpy & Plotext
  • tplot_examples.py        - Additional visualizations using Tplot
  • README.md                - This documentation file

PYTHON LIBRARIES USED
================================================================================

1. ASCIICHARTPY
   - Purpose: Line and area charts rendered in ASCII
   - GitHub: https://github.com/pawamoy/python-asciichartpy
   - Key functions:
     • asciichartpy.plot()     - Line chart
     • asciichartpy.bar()      - Bar chart (not available in current version)
   
   Example output:
     468.00  ┤
     428.11  ┤╭
     388.22  ┤│
     ...
   
   Best for: Time series, trends, comparative line charts

2. PLOTEXT
   - Purpose: High-quality terminal plotting library
   - GitHub: https://github.com/piccolomo/plotext
   - Key functions:
     • plt.simple_bar()    - Simple bar charts
     • plt.hist()          - Histograms
     • plt.plot()          - Line plots
     • plt.scatter()       - Scatter plots
   
   Example output:
     ──────────── Survival Rate % by Passenger Class ────────────
     First  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 62.96
     Second ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 47.28
     Third  ▇▇▇▇▇▇▇▇▇ 24.24
   
   Best for: Professional-looking bar charts and histograms

3. TPLOT
   - Purpose: Simple text-based charting using Unicode blocks
   - Minimal library for quick bar visualizations
   - Key feature: Using Unicode block characters (█, ▓, ▒, ░)
   
   Example output:
     First Class          ███████████████████████████████ 63.0%
     Second Class         ███████████████████████ 47.3%
     Third Class          ████████████ 24.2%
   
   Best for: Quick, simple bar charts and simple distributions

INSTALLATION
================================================================================

Create a Python virtual environment and install dependencies:

  python3 -m venv venv
  source venv/bin/activate
  pip install pandas requests asciichartpy plotext tplot

RUNNING THE EXAMPLES
================================================================================

Activate the virtual environment:
  source venv/bin/activate

Run the main analysis:
  python3 analyze_titanic.py

Run the Tplot examples:
  python3 tplot_examples.py

DATASET: TITANIC SURVIVAL DATA
================================================================================

Dataset Details:
  • Total passengers: 891
  • Columns: PassengerId, Survived, Pclass, Name, Sex, Age, SibSp, Parch, 
             Ticket, Fare, Cabin, Embarked
  • Survival rate: 38.4% (342 survived, 549 perished)

Key Statistics:
  • Average age: 29.7 years
  • Average fare: $32.20
  • Gender split: 314 females, 577 males

ANALYSIS FINDINGS
================================================================================

1. SURVIVAL BY GENDER
   Female: 233/314 survived (74.2%) ✓ Much higher survival rate
   Male:   109/577 survived (18.9%) ✗ Much lower survival rate
   
   → Women had priority in lifeboat evacuation ("Women and children first")

2. SURVIVAL BY PASSENGER CLASS
   First Class:  136/216 survived (63.0%) ✓ Best chances
   Second Class:  87/184 survived (47.3%) ⚬ Medium chances
   Third Class:  119/491 survived (24.2%) ✗ Worst chances
   
   → Socioeconomic status strongly influenced survival odds

3. GENDER + CLASS COMBINED
   First Class Female:   96.8% ✓ Highest survival rate
   Second Class Female:  92.1% ✓ Very high survival rate
   Third Class Female:   50.0% ⚬ Moderate survival rate
   First Class Male:     36.9% ⚬ Moderate survival rate
   Second Class Male:    15.7% ✗ Low survival rate
   Third Class Male:     13.5% ✗ Lowest survival rate
   
   → Gender was a more significant factor than class

4. AGE DISTRIBUTION
   • Children (0-10): Higher survival rates
   • Young adults (20-30): Peak survival group
   • Seniors (60+): Lower survival rates

5. FARE DISTRIBUTION
   • Most passengers paid lower fares ($0-$20): 500 passengers
   • Higher fares correlated with first/second class (better survival)
   • Few passengers paid very high fares ($300+): Only 3

6. FAMILY SIZE IMPACT
   • Traveling alone: 30.4% survival
   • Families of 2-4: 55-72% survival (better)
   • Large families (5+): Dropped to 0-20% survival
   
   → Optimal family size was 2-4 for survival

7. EMBARKATION PORT
   • Cherbourg (C): 55.4% survival rate (mostly 1st class)
   • Queenstown (Q): 38.96% survival rate
   • Southampton (S): 33.7% survival rate (mostly 3rd class)
   
   → Port reflects passenger class distribution

CHART EXAMPLES IN OUTPUT
================================================================================

The scripts generate 9+ different chart types:

1. LINE CHARTS (Asciichartpy)
   ├─ Survival by Gender (line trends)
   ├─ Age Distribution comparisons
   └─ Family Size vs Survival Rate

2. BAR CHARTS (Plotext)
   ├─ Survival Rate by Passenger Class
   ├─ Survival Rate by Embarkation Port
   ├─ Class & Gender Survival Comparison
   └─ Distribution of Ticket Fares (Histogram)

3. ASCII BAR CHARTS (Tplot)
   ├─ Survival Count by Gender
   ├─ Survival Rates by Class
   ├─ Age Group Distribution
   ├─ Fare Range Distribution
   ├─ Passengers by Embarkation Port
   ├─ Family Size Distribution
   └─ Survival Comparison (Survived vs Died)

ADVANTAGES & DISADVANTAGES
================================================================================

ASCIICHARTPY:
  ✓ Smooth line rendering with Unicode characters
  ✓ Good for time series and trends
  ✗ Limited chart types
  ✗ Smaller output text

PLOTEXT:
  ✓ Professional-looking output
  ✓ Multiple chart types (bar, histogram, scatter, plot)
  ✓ Customizable colors and markers
  ✓ Good for terminal dashboards
  ✗ Requires more setup than simple tplot

TPLOT:
  ✓ Very simple to use
  ✓ Quick implementation
  ✓ Lightweight (minimal dependencies)
  ✗ Limited to simple bar charts
  ✗ Less customization

USE CASES
================================================================================

1. Server-side dashboards    → Use Plotext (professional output)
2. Real-time monitoring      → Use Tplot (simple and fast)
3. Data exploration scripts  → Use Asciichartpy (for trends)
4. Quick visualizations      → Use Tplot (least dependencies)
5. Production reports        → Use Plotext (best output quality)

TIPS FOR TEXT-BASED CHARTS
================================================================================

1. Terminal width: Charts adapt to terminal width, maximize your terminal
2. Colors: Plotext supports colors if your terminal supports ANSI colors
3. Resolution: Text-based charts have limited resolution (text granularity)
4. Data scaling: Always normalize/scale data appropriately for visibility
5. Bar length: Use proportional scaling (divide by constant factor)

FURTHER READING
================================================================================

Documentation:
  • Asciichartpy: https://github.com/pawamoy/python-asciichartpy
  • Plotext: https://github.com/piccolomo/plotext
  • Tplot: Simple custom implementation

Python Data Science:
  • Pandas: Data manipulation and analysis
  • NumPy: Numerical computing
  • Matplotlib: Full graphical charts (when terminal is not available)

Text-UI Libraries:
  • Rich: Terminal rich text and beautiful formatting
  • Curses: Terminal control for interactive dashboards
  • Blessed: Cross-platform terminal control

CONCLUSION
================================================================================

Text-based charts are excellent for:
  • SSH sessions where no GUI is available
  • Server monitoring and dashboards
  • Data science exploration in terminal environments
  • Quick data visualization without setting up Jupyter
  • Log analysis and streaming data visualization

Each library serves different purposes:
  • Asciichartpy: Best for trends and line charts
  • Plotext: Best for professional bar charts and histograms
  • Tplot: Best for quick, simple visualizations

The Titanic dataset demonstrates real-world insights that can be discovered
through text-based visualization, showing that socioeconomic status (class) and
gender were the primary predictors of survival.

================================================================================
