import pandas as pd
import plotext as plt
import asciichartpy as act
import tplot

def main():
    print("Loading data...")
    df = pd.read_csv('titanic.csv')
    
    print("\n" + "="*80)
    print("--- CHART 1: Plotext ---")
    print("Survival counts by Passenger Class")
    print("="*80)
    
    survived_by_class = df[df['Survived'] == 1]['Pclass'].value_counts().sort_index()
    died_by_class = df[df['Survived'] == 0]['Pclass'].value_counts().sort_index()
    classes = [str(c) for c in survived_by_class.index]
    
    plt.multiple_bar(
        classes,
        [survived_by_class.values.tolist(), died_by_class.values.tolist()],
        labels=["Survived", "Died"]
    )
    plt.title("Titanic Survival by Passenger Class")
    plt.xlabel("Passenger Class")
    plt.ylabel("Count")
    plt.show()

    print("\n" + "="*80)
    print("--- CHART 2: Tplot ---")
    print("Scatter plot: Age vs Fare")
    print("="*80)
    
    filtered_df = df.dropna(subset=['Age', 'Fare'])
    # Downsample for faster text plotting
    filtered_df = filtered_df.sample(min(200, len(filtered_df)), random_state=42)
    
    fig = tplot.Figure(
        xlabel="Age", 
        ylabel="Fare",
        title="Scatter plot of Age vs Fare"
    )
    fig.scatter(filtered_df['Age'].tolist(), filtered_df['Fare'].tolist(), color='cyan')
    fig.show()

    
    print("\n" + "="*80)
    print("--- CHART 3: Asciichartpy ---")
    print("Trend of Ascending Passenger Ages")
    print("="*80)
    
    sorted_ages = df['Age'].dropna().sort_values().tolist()
    # Downsample so it fits nicely
    sampled_ages = sorted_ages[::len(sorted_ages)//60]
    print(act.plot(sampled_ages, {'height': 15}))


if __name__ == "__main__":
    main()
