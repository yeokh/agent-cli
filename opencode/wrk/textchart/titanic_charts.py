import pandas as pd
import numpy as np
import plotext as plt
import asciichartpy
import plotille

# Download Titanic dataset
url = 'https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv'
df = pd.read_csv(url)

# Survival analysis
survival_rate = df['Survived'].value_counts(normalize=True) * 100

print("\n1. Survival Rate (ASCII Bar)")
for category, rate in survival_rate.items():
    category_name = 'Survived' if category == 1 else 'Did Not Survive'
    print(f"{category_name}: {'#' * int(rate/2)} {rate:.1f}%")

# Age distribution
print("\n2. Age Distribution (Asciichartpy)")
age_hist, age_bins = np.histogram(df['Age'].dropna(), bins=20)
print(asciichartpy.plot(age_hist, {'height': 10}))

# Survival by Gender
print("\n3. Survival by Gender")
gender_survival = df.groupby(['Sex', 'Survived']).size().unstack()
gender_survival_percentages = gender_survival.apply(lambda x: x / x.sum() * 100, axis=1)

print("Survival Percentages:")
for gender, row in gender_survival_percentages.iterrows():
    print(f"{gender.capitalize()}:")
    print(f"  Survived: {'#' * int(row[1]/2)} {row[1]:.1f}%")
    print(f"  Did Not Survive: {'#' * int(row[0]/2)} {row[0]:.1f}%")

# Passenger Class Distribution
print("\n4. Passenger Class Distribution")
class_counts = df['Pclass'].value_counts()
for pclass, count in class_counts.items():
    percentage = (count / len(df)) * 100
    print(f"Class {pclass}: {'#' * int(percentage/2)} {percentage:.1f}%")

# Basic data summary
print("\nData Summary:")
print(df[['Age', 'Fare', 'Survived']].describe())