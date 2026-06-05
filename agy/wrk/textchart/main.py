import pandas as pd
import asciichartpy
import plotext as plt
import tplot
import os

def main():
    # 1. Download Titanic CSV data
    url = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
    print(f"Downloading Titanic dataset from {url}...")
    df = pd.read_csv(url)
    
    print("\n--- Data Overview ---")
    print(df.head())
    
    # 2. Asciichartpy: Plotting Fare distribution for the first 50 passengers
    print("\n\n--- Asciichartpy: Fare of first 50 passengers ---")
    fares = df['Fare'].head(50).tolist()
    # asciichartpy expects a list of numbers
    chart = asciichartpy.plot(fares, {'height': 10})
    print(chart)

    # 3. Plotext: Bar chart of Survival by Class
    print("\n\n--- Plotext: Survival Rate by Passenger Class ---")
    survival_by_class = df.groupby('Pclass')['Survived'].mean() * 100
    classes = [f"Class {c}" for c in survival_by_class.index]
    rates = survival_by_class.values.tolist()

    plt.clf()
    plt.bar(classes, rates)
    plt.title("Survival Rate by Passenger Class (%)")
    plt.ylabel("Survival Rate (%)")
    plt.show()

    # 4. Tplot: Bar chart or similar for Survival count
    print("\n\n--- Tplot: Survived vs Perished Count ---")
    survival_counts = df['Survived'].value_counts().sort_index()
    labels = ["Perished", "Survived"]
    counts = survival_counts.values.tolist()
    
    try:
        # tplot has a simple bar chart function
        fig = tplot.Figure(xlabel="Status (0=Perished, 1=Survived)", ylabel="Count", title="Survival Count")
        fig.bar(counts)
        fig.show()
    except Exception as e:
        print(f"Error using tplot: {e}")
        print("Note: tplot usage can vary based on exact version/implementation.")

if __name__ == "__main__":
    main()
