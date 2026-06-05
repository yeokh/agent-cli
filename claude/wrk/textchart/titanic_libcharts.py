import csv
from collections import defaultdict

# ── load data ─────────────────────────────────────────────────────────────────

def load(path="titanic.csv"):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def to_float(v):
    try: return float(v)
    except: return None

def to_int(v):
    try: return int(v)
    except: return None

rows = load()

survived = [to_int(r["Survived"]) for r in rows]
pclass   = [to_int(r["Pclass"])   for r in rows]
sex      = [r["Sex"]              for r in rows]
age      = [to_float(r["Age"])    for r in rows]
fare     = [to_float(r["Fare"])   for r in rows]

# precompute aggregates
class_surv = {}
for c in [1, 2, 3]:
    grp = [s for s, p in zip(survived, pclass) if p == c and s is not None]
    class_surv[c] = sum(grp) / len(grp) * 100

sex_surv = {}
for g in ["female", "male"]:
    grp = [s for s, gx in zip(survived, sex) if gx == g and s is not None]
    sex_surv[g] = sum(grp) / len(grp) * 100

age_buckets = [(0,10),(10,20),(20,30),(30,40),(40,50),(50,60),(60,70),(70,100)]
age_counts  = []
age_pcts    = []
age_labels  = []
for lo, hi in age_buckets:
    grp = [s for s, a in zip(survived, age) if a is not None and lo <= a < hi and s is not None]
    age_counts.append(len(grp))
    age_pcts.append(sum(grp) / len(grp) * 100 if grp else 0)
    age_labels.append(f"{lo}-{hi}")

valid_ages = [a for a in age if a is not None]
valid_fares = [f for f in fare if f is not None]

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — plotext
# ═══════════════════════════════════════════════════════════════════════════════

import plotext as plt
plt.theme("clear")

print("\n" + "═"*60)
print("  CHARTS USING  plotext")
print("═"*60)

# ── Chart 1: Overall survival — simple bar ─────────────────────────────────
plt.clf()
plt.bar(["Survived", "Did not survive"], [342, 549], color=["green", "red"])
plt.title("Chart 1 · Overall Survival Count")
plt.xlabel("Outcome")
plt.ylabel("Passengers")
plt.plotsize(60, 15)
plt.show()

# ── Chart 2: Survival rate by class ───────────────────────────────────────
plt.clf()
plt.bar(["1st Class", "2nd Class", "3rd Class"],
        [round(class_surv[1],1), round(class_surv[2],1), round(class_surv[3],1)],
        color=["cyan", "yellow", "magenta"])
plt.title("Chart 2 · Survival Rate (%) by Passenger Class")
plt.ylabel("Survival %")
plt.ylim(0, 100)
plt.plotsize(60, 15)
plt.show()

# ── Chart 3: Survival rate by sex ─────────────────────────────────────────
plt.clf()
plt.bar(["Female", "Male"],
        [round(sex_surv["female"],1), round(sex_surv["male"],1)],
        color=["pink", "blue"])
plt.title("Chart 3 · Survival Rate (%) by Sex")
plt.ylabel("Survival %")
plt.ylim(0, 100)
plt.plotsize(60, 15)
plt.show()

# ── Chart 4: Age distribution — histogram ─────────────────────────────────
plt.clf()
plt.hist(valid_ages, bins=16, color="cyan")
plt.title("Chart 4 · Age Distribution of All Passengers")
plt.xlabel("Age")
plt.ylabel("Count")
plt.plotsize(60, 15)
plt.show()

# ── Chart 5: Fare distribution — histogram ────────────────────────────────
plt.clf()
capped_fares = [min(f, 300) for f in valid_fares]
plt.hist(capped_fares, bins=20, color="yellow")
plt.title("Chart 5 · Fare Distribution (capped at £300)")
plt.xlabel("Fare (£)")
plt.ylabel("Count")
plt.plotsize(60, 15)
plt.show()

# ── Chart 6: Survival rate by age group — bar ─────────────────────────────
plt.clf()
plt.bar(age_labels, [round(p, 1) for p in age_pcts], color="green")
plt.title("Chart 6 · Survival Rate (%) by Age Group")
plt.ylabel("Survival %")
plt.ylim(0, 100)
plt.plotsize(60, 15)
plt.show()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — asciichartpy
# ═══════════════════════════════════════════════════════════════════════════════

import asciichartpy as acp

print("\n" + "═"*60)
print("  CHARTS USING  asciichartpy")
print("═"*60)

# ── Chart 7: Age distribution as line chart ───────────────────────────────
print("\n  Chart 7 · Age Distribution (line chart, bucket counts)\n")
print(acp.plot(age_counts, {"height": 12, "colors": [acp.cyan]}))
print("  Buckets (left→right): 0-10, 10-20, 20-30, 30-40, 40-50, 50-60, 60-70, 70+")

# ── Chart 8: Survival % by age group as line chart ────────────────────────
print("\n  Chart 8 · Survival Rate (%) by Age Group (line chart)\n")
print(acp.plot([round(p, 1) for p in age_pcts], {"height": 12, "colors": [acp.green]}))
print("  Buckets (left→right): 0-10, 10-20, 20-30, 30-40, 40-50, 50-60, 60-70, 70+")

# ── Chart 9: Fare distribution bucketed as line ───────────────────────────
fare_bkts = [0]*10
for f in valid_fares:
    idx = min(int(f / 30), 9)
    fare_bkts[idx] += 1
print("\n  Chart 9 · Fare Distribution (bucketed, £0-£300+)\n")
print(acp.plot(fare_bkts, {"height": 12, "colors": [acp.yellow]}))
print("  Buckets (left→right): £0-30, £30-60, £60-90 ... £270-300, £300+")

# ── Chart 10: Multi-series — survived vs died by class ────────────────────
class_survived_list = [sum(1 for s,p in zip(survived,pclass) if p==c and s==1) for c in [1,2,3]]
class_died_list     = [sum(1 for s,p in zip(survived,pclass) if p==c and s==0) for c in [1,2,3]]
print("\n  Chart 10 · Survivors (green) vs Deaths (red) by Class  [1st, 2nd, 3rd]\n")
print(acp.plot([class_survived_list, class_died_list],
               {"height": 10, "colors": [acp.green, acp.red]}))
print("  X-axis: 0=1st class, 1=2nd class, 2=3rd class")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — tplot
# ═══════════════════════════════════════════════════════════════════════════════

import tplot

print("\n" + "═"*60)
print("  CHARTS USING  tplot")
print("═"*60)

# ── Chart 11: Scatter — Age vs Fare coloured by survival ──────────────────
print("\n  Chart 11 · Age vs Fare (scatter, coloured by survival outcome)\n")
ages_s  = [a for a, s in zip(age, survived) if a is not None and s == 1]
fares_s = [f for a, f, s in zip(age, fare, survived) if a is not None and f is not None and s == 1]
ages_d  = [a for a, s in zip(age, survived) if a is not None and s == 0]
fares_d = [f for a, f, s in zip(age, fare, survived) if a is not None and f is not None and s == 0]

fig = tplot.Figure(
    title="Age vs Fare — Survived (o) vs Died (x)",
    xlabel="Age", ylabel="Fare (£)",
    width=60, height=20
)
fig.scatter(ages_d,  fares_d,  color="red",   label="Died",     marker="x")
fig.scatter(ages_s,  fares_s,  color="green", label="Survived", marker="o")
fig.show()

# ── Chart 12: Survival rate per class per sex — scatter points ────────────
print("\n  Chart 12 · Survival Rate by Class & Sex (scatter)\n")

xs_f, ys_f, xs_m, ys_m = [], [], [], []
for ci, c in enumerate([1, 2, 3]):
    for g, xlist, ylist in [("female", xs_f, ys_f), ("male", xs_m, ys_m)]:
        grp = [s for s,p,gx in zip(survived,pclass,sex) if p==c and gx==g and s is not None]
        pct = sum(grp)/len(grp)*100 if grp else 0
        xlist.append(ci * 2 + (0 if g == "female" else 1))
        ylist.append(round(pct, 1))

fig2 = tplot.Figure(
    title="Survival Rate (%) by Class & Sex",
    xlabel="Class group (0-1=1st, 2-3=2nd, 4-5=3rd)",
    ylabel="Survival %",
    width=60, height=15
)
fig2.scatter(xs_f, ys_f, color="magenta", label="Female", marker="o")
fig2.scatter(xs_m, ys_m, color="blue", label="Male",   marker="x")
fig2.show()

print("\n" + "═"*60)
print("  END OF CHARTS")
print("═"*60 + "\n")
