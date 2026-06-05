#!/usr/bin/env python3
"""
Quick comparison of different chart libraries with same data
"""

import pandas as pd
import asciichartpy
import plotext as plt

# Load data
df = pd.read_csv('titanic.csv')

print("\n" + "=" * 80)
print("COMPARISON: Same Data, Different Libraries")
print("=" * 80)

# Extract data for all charts
class_survival = df.groupby('Pclass')['Survived'].mean() * 100
class_names = ['First Class', 'Second Class', 'Third Class']
values = [class_survival[1], class_survival[2], class_survival[3]]

# LIBRARY 1: ASCIICHARTPY - Line Chart
print("\n" + "=" * 80)
print("ASCIICHARTPY: Line Chart (Survival Rate by Class)")
print("=" * 80)
print("\nCode: asciichartpy.plot(values, {'height': 10, 'width': 50})\n")
print(asciichartpy.plot(values, {'height': 10, 'width': 50}))

# LIBRARY 2: PLOTEXT - Bar Chart
print("\n" + "=" * 80)
print("PLOTEXT: Bar Chart (Survival Rate by Class)")
print("=" * 80)
print("\nCode: plt.simple_bar(['First', 'Second', 'Third'], values)\n")
plt.simple_bar(['First', 'Second', 'Third'], values, width=60)
plt.show()

# LIBRARY 3: TPLOT (Manual) - Simple Bar Chart
print("\n" + "=" * 80)
print("TPLOT: Simple Bar Chart (Survival Rate by Class)")
print("=" * 80)
print("\nCode: Simple loop with Unicode blocks\n")
for name, value in zip(['First Class', 'Second Class', 'Third Class'], values):
    bar_length = int(value / 2)
    print(f"{name:20} {'█' * bar_length} {value:.1f}%")

# Extended comparison with multiple metrics
print("\n" + "=" * 80)
print("COMPREHENSIVE COMPARISON: Multiple Metrics")
print("=" * 80)

metrics = {
    'Female Survival %': df[df['Sex'] == 'female']['Survived'].mean() * 100,
    'Male Survival %': df[df['Sex'] == 'male']['Survived'].mean() * 100,
    'Age 0-18 Survival %': df[df['Age'] <= 18]['Survived'].mean() * 100,
    'Age 18+ Survival %': df[df['Age'] > 18]['Survived'].mean() * 100,
}

print("\n1. ASCIICHARTPY (Line visualization):")
print(asciichartpy.plot(list(metrics.values()), {'height': 8, 'width': 50}))

print("\n2. TPLOT (Bar visualization):")
for metric, value in metrics.items():
    bar_length = int(value / 3)
    print(f"{metric:25} {'█' * bar_length} {value:.1f}%")

# Gender comparison in all three styles
print("\n" + "=" * 80)
print("DETAILED COMPARISON: Gender Survival Rates")
print("=" * 80)

female_surv = df[df['Sex'] == 'female']['Survived'].mean() * 100
male_surv = df[df['Sex'] == 'male']['Survived'].mean() * 100

print("\nUsing all three libraries to show same data:")

print("\n1. ASCIICHARTPY:")
print(asciichartpy.plot([female_surv, male_surv], {'height': 8, 'width': 40}))

print("\n2. PLOTEXT:")
plt.simple_bar(['Female', 'Male'], [female_surv, male_surv], width=50)
plt.show()

print("\n3. TPLOT (Text-based):")
print(f"Female  {'█' * int(female_surv / 2)} {female_surv:.1f}%")
print(f"Male    {'█' * int(male_surv / 2)} {male_surv:.1f}%")

print("\n" + "=" * 80)
print("LIBRARY COMPARISON SUMMARY")
print("=" * 80)

comparison = """
┌─────────────┬──────────────┬────────────────┬──────────────────────────┐
│ Feature     │ Asciichartpy │ Plotext        │ Tplot                    │
├─────────────┼──────────────┼────────────────┼──────────────────────────┤
│ Complexity  │ Low          │ Medium         │ Very Low                 │
│ Output      │ Line charts  │ Bar, Hist      │ Simple bars              │
│ Beauty      │ Medium       │ High           │ Low                      │
│ Colors      │ Limited      │ Full support   │ None                     │
│ Setup       │ pip install  │ pip install    │ Custom or lightweight    │
│ Best for    │ Trends       │ Dashboards     │ Quick viz                │
│ Performance │ Fast         │ Medium         │ Very Fast                │
│ Customizing │ Limited      │ Extensive      │ Minimal                  │
└─────────────┴──────────────┴────────────────┴──────────────────────────┘

RECOMMENDATION:
  • For dashboards and reports     → Use PLOTEXT
  • For quick exploration          → Use TPLOT
  • For trend visualization        → Use ASCIICHARTPY
  • For all features combined      → Use PLOTEXT (most versatile)
"""

print(comparison)

print("\n" + "=" * 80)
print("COMPARISON COMPLETE")
print("=" * 80)
