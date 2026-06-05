import os
import pandas as pd
import requests

CSV_URL = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"


def download_csv(url, filename):
    """Download the CSV file if it does not exist."""
    if not os.path.exists(filename):
        print("Downloading CSV file...")
        response = requests.get(url)
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"Downloaded {filename}")
    else:
        print(f"{filename} already exists. Skipping download.")


def ascii_bar_chart(title, data):
    """Prints a simple ASCII horizontal bar chart for given data.

    Args:
        title (str): Chart title
        data (dict): Dictionary with labels as keys and counts as values
    """
    print(f"\n{title}")
    max_value = max(data.values())
    # Determine scale factor to have bar of maximum 50 characters
    scale = max_value / 50 if max_value > 50 else 1
    for key, value in data.items():
        bar_length = int(value / scale)
        bar = '*' * bar_length
        print(f"{key}: {bar} ({value})")


def main():
    csv_file = "titanic.csv"
    download_csv(CSV_URL, csv_file)

    # Load the CSV file into a DataFrame
    df = pd.read_csv(csv_file)

    print("\nTitanic Data Analysis:\n")

    # 1. Survival Distribution
    if 'Survived' in df.columns:
        survival_counts = df['Survived'].value_counts().to_dict()
        print("Survival Distribution:")
        ascii_bar_chart("Survived (0=No, 1=Yes)", survival_counts)
    else:
        print("'Survived' column not found in data.")

    # 2. Passenger Class Distribution
    if 'Pclass' in df.columns:
        pclass_counts = df['Pclass'].value_counts().to_dict()
        print("\nPassenger Class Distribution:")
        ascii_bar_chart("Pclass", pclass_counts)
    else:
        print("'Pclass' column not found in data.")

    # 3. Gender Distribution
    if 'Sex' in df.columns:
        gender_counts = df['Sex'].value_counts().to_dict()
        print("\nGender Distribution:")
        ascii_bar_chart("Sex", gender_counts)
    else:
        print("'Sex' column not found in data.")

    # 4. Age Distribution Analysis using popular textual chart libraries
    if 'Age' in df.columns:
        age_series = df['Age'].dropna()
        print("\nAge Distribution Analysis:")

        # Using Plotext
        try:
            import plotext as plt
            plt.clp()  # clear previous plot
            plt.hist(age_series, bins=20)
            plt.title("Age Distribution (Plotext)")
            plt.show()
        except ImportError:
            print("Plotext library not installed. Skipping Plotext histogram.")

        # Using Asciichartpy
        try:
            import asciichartpy
            import numpy as np
            counts, bins = np.histogram(age_series, bins=20)
            print("\nHistogram using Asciichartpy:")
            chart = asciichartpy.plot(counts.tolist(), {'height': 10})
            print(chart)
        except ImportError:
            print("Asciichartpy library not installed. Skipping asciichartpy chart.")

        # Using Tplot
        try:
            import tplot
            print("\nHistogram using Tplot:")
            tplot.hist(age_series.tolist(), bins=20, title="Age Distribution (Tplot)")
        except ImportError:
            print("Tplot library not installed. Skipping Tplot chart.")
    else:
        print("'Age' column not found in data.")


if __name__ == "__main__":
    main()
