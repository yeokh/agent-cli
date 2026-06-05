from pathlib import Path

import asciichartpy
import pandas as pd
import plotext as plt
import requests
from tplot import Figure

DATA_URL = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
DATA_DIR = Path("data")
DATA_PATH = DATA_DIR / "titanic.csv"


def download_csv(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    destination.write_bytes(response.content)


def build_summary(df: pd.DataFrame) -> dict[str, object]:
    total_passengers = int(len(df))
    overall_survival_rate = float(df["Survived"].mean() * 100)
    survival_by_class = (
        df.groupby("Pclass", observed=False)["Survived"].mean().mul(100).round(2).sort_index()
    )
    survival_by_sex = (
        df.groupby("Sex", observed=False)["Survived"].mean().mul(100).round(2).sort_values()
    )
    age_bins = [0, 18, 35, 60, 100]
    age_labels = ["0-18", "19-35", "36-60", "61+"]
    age_groups = pd.cut(df["Age"], bins=age_bins, labels=age_labels, include_lowest=True)
    survival_by_age = (
        df.assign(AgeGroup=age_groups)
        .dropna(subset=["AgeGroup"])
        .groupby("AgeGroup", observed=False)["Survived"]
        .mean()
        .mul(100)
        .round(2)
    )
    return {
        "total_passengers": total_passengers,
        "overall_survival_rate": overall_survival_rate,
        "survival_by_class": survival_by_class,
        "survival_by_sex": survival_by_sex,
        "survival_by_age": survival_by_age,
    }


def print_findings(summary: dict[str, object]) -> None:
    print("\nTitanic CSV analysis")
    print("-" * 60)
    print(f"Total passengers: {summary['total_passengers']}")
    print(f"Overall survival rate: {summary['overall_survival_rate']:.2f}%")
    print("\nSurvival rate by class (%):")
    print(summary["survival_by_class"].to_string())
    print("\nSurvival rate by sex (%):")
    print(summary["survival_by_sex"].to_string())
    print("\nSurvival rate by age group (%):")
    print(summary["survival_by_age"].to_string())


def chart_with_asciichart(summary: dict[str, object]) -> None:
    series = summary["survival_by_class"]
    values = series.tolist()
    labels = [f"Class {idx}" for idx in series.index.tolist()]
    print("\n[Asciichartpy] Survival rate by passenger class")
    print("Labels:", ", ".join(labels))
    chart = asciichartpy.plot(
        values,
        {
            "height": 10,
            "format": "{:6.2f}%",
        },
    )
    print(chart)


def chart_with_plotext(summary: dict[str, object]) -> None:
    series = summary["survival_by_sex"]
    print("\n[Plotext] Survival rate by sex")
    plt.clear_figure()
    plt.bar(series.index.tolist(), series.tolist())
    plt.title("Titanic Survival Rate by Sex")
    plt.xlabel("Sex")
    plt.ylabel("Survival Rate (%)")
    plt.plotsize(90, 20)
    plt.show()


def chart_with_tplot(summary: dict[str, object]) -> None:
    series = summary["survival_by_age"]
    print("\n[Tplot] Survival rate by age group")
    fig = Figure(
        title="Titanic Survival Rate by Age Group",
        xlabel="Age Group",
        ylabel="Survival Rate (%)",
        width=90,
        height=20,
    )
    fig.bar(series.index.tolist(), series.tolist())
    fig.show()


def main() -> None:
    download_csv(DATA_URL, DATA_PATH)
    df = pd.read_csv(DATA_PATH)
    summary = build_summary(df)

    print(f"Downloaded CSV to: {DATA_PATH.resolve()}")
    print_findings(summary)
    chart_with_asciichart(summary)
    chart_with_plotext(summary)
    chart_with_tplot(summary)


if __name__ == "__main__":
    main()
