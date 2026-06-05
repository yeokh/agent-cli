#!/usr/bin/env python3
"""
Titanic Dataset - Additional charts using Tplot
"""

import pandas as pd
import tplot

# Load the CSV we created earlier
df = pd.read_csv('titanic.csv')

print("\n" + "=" * 70)
print("ADDITIONAL CHARTS USING TPLOT")
print("=" * 70)

# Chart 1: Simple bar chart using tplot
print("\n" + "=" * 70)
print("TPLOT CHART 1: SURVIVAL COUNT BY GENDER")
print("=" * 70)

gender_counts = df.groupby('Sex')['Survived'].apply(list)
male_survived = gender_counts['male'].count(1)
male_died = gender_counts['male'].count(0)
female_survived = gender_counts['female'].count(1)
female_died = gender_counts['female'].count(0)

print("\nUsing tplot bar chart:")
try:
    # Create a simple data structure for tplot
    data = {
        'Male-Survived': male_survived,
        'Male-Died': male_died,
        'Female-Survived': female_survived,
        'Female-Died': female_died
    }
    
    # Display using tplot
    for label, value in data.items():
        print(f"{label:20} {'█' * (value // 5)} {value}")
except Exception as e:
    print(f"Tplot error: {e}")

# Chart 2: Survival rate percentages
print("\n" + "=" * 70)
print("TPLOT CHART 2: SURVIVAL RATES BY CLASS")
print("=" * 70)

class_rates = df.groupby('Pclass')['Survived'].mean() * 100
class_names = {1: 'First Class', 2: 'Second Class', 3: 'Third Class'}

for class_id, rate in class_rates.items():
    bar_length = int(rate / 2)
    print(f"{class_names[class_id]:20} {'█' * bar_length} {rate:.1f}%")

# Chart 3: Age groups distribution
print("\n" + "=" * 70)
print("TPLOT CHART 3: AGE GROUP DISTRIBUTION")
print("=" * 70)

age_bins = [0, 10, 20, 30, 40, 50, 60, 80]
df['AgeGroup'] = pd.cut(df['Age'], bins=age_bins, right=False)
age_counts = df['AgeGroup'].value_counts().sort_index()

for interval, count in age_counts.items():
    bar_length = int(count / 5)
    print(f"{str(interval):20} {'█' * bar_length} {count}")

# Chart 4: Fare range distribution
print("\n" + "=" * 70)
print("TPLOT CHART 4: FARE RANGE DISTRIBUTION")
print("=" * 70)

fare_bins = [0, 20, 50, 100, 150, 300, 600]
df['FareRange'] = pd.cut(df['Fare'], bins=fare_bins)
fare_counts = df['FareRange'].value_counts().sort_index()

for interval, count in fare_counts.items():
    if pd.notna(interval):
        bar_length = int(count / 3)
        print(f"${interval.left:6.0f}-${interval.right:6.0f} {'█' * bar_length} {count}")

# Chart 5: Embarkation port counts
print("\n" + "=" * 70)
print("TPLOT CHART 5: PASSENGERS BY EMBARKATION PORT")
print("=" * 70)

port_counts = df['Embarked'].value_counts()
port_names = {'C': 'Cherbourg', 'Q': 'Queenstown', 'S': 'Southampton'}

for port, count in port_counts.items():
    if pd.notna(port):
        bar_length = int(count / 10)
        print(f"{port_names.get(port, port):20} {'█' * bar_length} {count}")

# Chart 6: Family size distribution
print("\n" + "=" * 70)
print("TPLOT CHART 6: FAMILY SIZE DISTRIBUTION")
print("=" * 70)

df['FamilySize'] = df['SibSp'] + df['Parch'] + 1
family_counts = df['FamilySize'].value_counts().sort_index()

for size, count in family_counts.items():
    bar_length = int(count / 10)
    print(f"Size {size} ({count:3d} passengers) {'█' * bar_length}")

# Chart 7: Comparison - Survived vs Died
print("\n" + "=" * 70)
print("TPLOT CHART 7: OVERALL SURVIVAL COMPARISON")
print("=" * 70)

survived = int(df['Survived'].sum())
died = len(df) - survived

print(f"\nSurvived ({survived:3d}) {'█' * (survived // 5)}")
print(f"Died     ({died:3d}) {'▓' * (died // 5)}")
print(f"\nSurvival Rate: {(survived/len(df)*100):.1f}%")

# Chart 8: Cabin information (if available)
print("\n" + "=" * 70)
print("TPLOT CHART 8: CABIN CLASS DISTRIBUTION")
print("=" * 70)

df['CabinClass'] = df['Cabin'].str[0]
cabin_counts = df['CabinClass'].value_counts().sort_index()

for cabin, count in cabin_counts.items():
    if pd.notna(cabin):
        bar_length = int(count / 5)
        print(f"Deck {cabin} ({count:3d} passengers) {'█' * bar_length}")

print("\n" + "=" * 70)
print("TPLOT VISUALIZATIONS COMPLETE")
print("=" * 70)
