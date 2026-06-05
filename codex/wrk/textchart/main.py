from pathlib import Path
from urllib.request import urlretrieve

import asciichartpy
import pandas as pd
import plotext as plt
import tplot

DATA_URL = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
DATA_PATH = Path("data/titanic.csv")


def download_titanic_csv() -> Path:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DATA_PATH.exists():
        print(f"Using cached CSV: {DATA_PATH}")
        return DATA_PATH

    print(f"Downloading Titanic CSV from: {DATA_URL}")
    urlretrieve(DATA_URL, DATA_PATH)
    print(f"Saved CSV to: {DATA_PATH}")
    return DATA_PATH


def analyze(df: pd.DataFrame) -> dict:
    overall_survival = float(df["Survived"].mean() * 100)
    survival_by_sex = (df.groupby("Sex")["Survived"].mean() * 100).sort_values(ascending=False)
    survival_by_class = (df.groupby("Pclass")["Survived"].mean() * 100).sort_index()
    median_fare_by_class = df.groupby("Pclass")["Fare"].median().sort_index()

    age_bins = [0, 10, 20, 30, 40, 50, 60, 70, 80]
    age_labels = [f"{age_bins[i]}-{age_bins[i + 1]}" for i in range(len(age_bins) - 1)]
    age_frame = df[["Age", "Survived"]].dropna().copy()
    age_frame["AgeBand"] = pd.cut(
        age_frame["Age"], bins=age_bins, labels=age_labels, right=False
    )
    survival_by_age_band = (
        age_frame.groupby("AgeBand", observed=False)["Survived"].mean() * 100
    ).reindex(age_labels)

    return {
        "overall_survival": overall_survival,
        "survival_by_sex": survival_by_sex,
        "survival_by_class": survival_by_class,
        "median_fare_by_class": median_fare_by_class,
        "survival_by_age_band": survival_by_age_band,
    }


def chart_asciichartpy(metrics: dict) -> None:
    print("\n=== Asciichartpy: Survival Rate by Age Band (%) ===")
    series = metrics["survival_by_age_band"].fillna(0).round(2).tolist()
    chart = asciichartpy.plot(series, {"height": 12})
    print(chart)
    print("Age bands:", " | ".join(metrics["survival_by_age_band"].index.tolist()))


def chart_plotext(metrics: dict) -> None:
    print("\n=== Plotext: Survival Rate by Passenger Class (%) ===")
    plt.clear_figure()
    plt.clear_data()
    x = [str(x) for x in metrics["survival_by_class"].index.tolist()]
    y = metrics["survival_by_class"].round(2).tolist()
    plt.bar(x, y, color="green")
    plt.title("Titanic Survival % by Class")
    plt.xlabel("Passenger Class")
    plt.ylabel("Survival %")
    plt.ylim(0, 100)
    plt.plotsize(90, 20)
    plt.show()
    plt.clear_figure()
    plt.clear_data()


def chart_tplot(metrics: dict) -> None:
    print("\n=== Tplot: Median Fare by Passenger Class ===")
    fig = tplot.Figure(
        title="Titanic Median Fare by Class",
        xlabel="Passenger Class",
        ylabel="Median Fare",
        width=90,
        height=22,
    )
    x = [str(x) for x in metrics["median_fare_by_class"].index.tolist()]
    y = metrics["median_fare_by_class"].round(2).tolist()
    fig.bar(x=x, y=y, color="yellow", label="Median Fare")
    fig.show()


def print_key_findings(metrics: dict) -> None:
    by_sex = metrics["survival_by_sex"].round(2)
    by_class = metrics["survival_by_class"].round(2)
    print("\n=== Key Findings ===")
    print(f"Overall survival rate: {metrics['overall_survival']:.2f}%")
    print(
        "Survival by sex: "
        + ", ".join(f"{k} {v:.2f}%" for k, v in by_sex.items())
    )
    print(
        "Survival by class: "
        + ", ".join(f"Class {k} {v:.2f}%" for k, v in by_class.items())
    )


def main() -> None:
    csv_path = download_titanic_csv()
    df = pd.read_csv(csv_path)
    metrics = analyze(df)
    print_key_findings(metrics)
    chart_asciichartpy(metrics)
    chart_plotext(metrics)
    chart_tplot(metrics)


if __name__ == "__main__":
    main()
