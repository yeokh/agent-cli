import pandas as pd
import plotext as plt
import asciichartpy
import tplot
import numpy as np

def main():
    # Load data
    df = pd.read_csv('titanic.csv')
    
    print("\n--- Titanic Data Analysis ---")
    print(f"Total Passengers: {len(df)}")
    print(f"Overall Survival Rate: {df['Survived'].mean():.2%}\n")

    # 1. Plotext: Survival Count by Class
    print("Chart 1: Survival Count by Class (using Plotext)")
    pclass_survived = df[df['Survived'] == 1]['Pclass'].value_counts().sort_index()
    pclass_total = df['Pclass'].value_counts().sort_index()
    
    classes = [str(c) for c in pclass_survived.index]
    counts = pclass_survived.values.tolist()
    
    plt.clear_data()
    plt.bar(classes, counts)
    plt.title("Survived count by Pclass")
    plt.xlabel("Pclass")
    plt.ylabel("Count")
    plt.show()
    print("\n" + "="*50 + "\n")

    # 2. Tplot: Survival by Sex
    print("Chart 2: Survival Count by Sex (using Tplot)")
    sex_survived = df[df['Survived'] == 1]['Sex'].value_counts()
    
    labels_sex = sex_survived.index.tolist()
    values_sex = sex_survived.values.tolist()
    
    print("Sex Distribution of Survivors:")
    fig = tplot.Figure()
    fig.bar(labels_sex, values_sex)
    fig.show()
    print("\n" + "="*50 + "\n")

    # 3. Asciichartpy: Survival Rate by Age Group
    print("Chart 3: Survival Rate by Age Group (using Asciichartpy)")
    # Drop rows with missing Age
    df_age = df.dropna(subset=['Age']).copy()
    df_age['AgeGroup'] = (df_age['Age'] // 10) * 10
    age_survival = df_age.groupby('AgeGroup')['Survived'].mean().sort_index()
    
    # Fill gaps in age groups if any
    full_age_groups = range(0, int(df_age['AgeGroup'].max()) + 10, 10)
    survival_rates = [age_survival.get(g, 0) for g in full_age_groups]
    
    print("Age Groups (0, 10, 20, ... 80)")
    # asciichartpy expects a list of numbers
    print(asciichartpy.plot(survival_rates, {'height': 10}))
    print("Survival rate (0.0 to 1.0) across age groups.")
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()
