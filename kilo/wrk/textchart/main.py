import pandas as pd
import plotext as plt
import asciichartpy as ascii
import tplot

def main():
    # Load the dataset
    df = pd.read_csv('titanic.csv')
    print("="*60)
    print("🛳️  TITANIC SURVIVAL DATASET ANALYSIS (TEXT CHARTS)")
    print("="*60)
    print("\nDataset Overview:")
    print(f"Total Passengers: {len(df)}")
    print(f"Overall Survival Rate: {(df['Survived'].mean() * 100):.1f}%")

    print("\n\n" + "="*60)
    print("1. PLOTEXT: Survival Rate by Passenger Class")
    print("="*60)
    class_survival = df.groupby('Pclass')['Survived'].mean() * 100
    
    # Configure plotext chart
    plt.clf()
    plt.bar(class_survival.index.astype(str), class_survival.values, color="blue")
    plt.title("Survival Rate (%) by Passenger Class")
    plt.xlabel("Passenger Class (1 = 1st, 2 = 2nd, 3 = 3rd)")
    plt.ylabel("Survival Rate %")
    plt.show()

    print("\n\n" + "="*60)
    print("2. ASCIICHARTPY: Fare Prices of First 60 Passengers")
    print("="*60)
    # Get fares of first 60 passengers
    fares = df['Fare'].head(60).fillna(0).tolist()
    
    # Configure asciichartpy chart
    config = {'height': 15, 'colors': [ascii.green]}
    print(ascii.plot(fares, config))
    print("\n(X-Axis: Passenger Index 0-60, Y-Axis: Fare Price in £)")


    print("\n\n" + "="*60)
    print("3. TPLOT: Scatter Plot of Passenger Age vs. Ticket Fare")
    print("="*60)
    # Drop N/A values for Age and Fare
    sample = df.dropna(subset=['Age', 'Fare'])
    
    # Configure tplot chart
    fig = tplot.Figure(xlabel="Age (years)", ylabel="Fare Price (£)")
    fig.scatter(sample['Age'].values, sample['Fare'].values, marker="•")
    fig.show()

if __name__ == "__main__":
    main()
