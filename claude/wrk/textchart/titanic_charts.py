import csv
from collections import defaultdict

# ── helpers ──────────────────────────────────────────────────────────────────

def load_titanic(path="titanic.csv"):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def hbar(label, value, max_val, width=40, fill="█", empty="░"):
    filled = round(value / max_val * width) if max_val else 0
    bar = fill * filled + empty * (width - filled)
    return f"  {label:<22} {bar} {value}"

def vbar_chart(title, data, height=12, bar_width=6, fill="█"):
    """Vertical bar chart with labels on x-axis."""
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    max_v = max(values) if values else 1

    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

    for row in range(height, 0, -1):
        threshold = max_v * row / height
        line = ""
        for v in values:
            cell = fill * bar_width if v >= threshold else " " * bar_width
            line += f" {cell}"
        # y-axis label every 3 rows
        if row % 3 == 0 or row == height:
            print(f"  {max_v*row/height:6.1f} |{line}")
        else:
            print(f"         |{line}")

    # x-axis
    print(f"         +{'─' * (len(values) * (bar_width + 1))}")
    label_line = "          "
    for lbl in labels:
        label_line += f"{lbl[:bar_width]:^{bar_width+1}}"
    print(label_line)

def separator(char="═", width=62):
    print(char * width)

# ── load & clean ─────────────────────────────────────────────────────────────

rows = load_titanic()
total = len(rows)

# parse numeric fields safely
def to_float(v):
    try: return float(v)
    except: return None

def to_int(v):
    try: return int(v)
    except: return None

survived_col  = [to_int(r["Survived"]) for r in rows]
pclass_col    = [to_int(r["Pclass"])   for r in rows]
sex_col       = [r["Sex"]              for r in rows]
age_col       = [to_float(r["Age"])    for r in rows]
fare_col      = [to_float(r["Fare"])   for r in rows]
embarked_col  = [r["Embarked"]         for r in rows]

survived_total = sum(s for s in survived_col if s is not None)

# ── HEADER ───────────────────────────────────────────────────────────────────

separator()
print("  TITANIC SURVIVAL ANALYSIS  —  Text-Based Charts (Python)")
print(f"  Dataset: {total} passengers  |  Survivors: {survived_total}  |  Lost: {total - survived_total}")
separator()

# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 · Overall Survival — Horizontal Bar
# ─────────────────────────────────────────────────────────────────────────────

print("\n  CHART 1 · Overall Survival Rate\n")
pct_surv = survived_total / total * 100
pct_lost = 100 - pct_surv
print(hbar(f"Survived ({survived_total})", round(pct_surv, 1), 100, fill="█"))
print(hbar(f"Did not survive ({total-survived_total})", round(pct_lost, 1), 100, fill="░"))
print(f"\n  Survival rate: {pct_surv:.1f}%")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 2 · Survival by Passenger Class — Grouped Bars
# ─────────────────────────────────────────────────────────────────────────────

print("\n")
separator("─")
print("\n  CHART 2 · Survival Rate by Passenger Class\n")

class_data = defaultdict(lambda: [0, 0])  # [survived, total]
for s, p in zip(survived_col, pclass_col):
    if s is not None and p is not None:
        class_data[p][0] += s
        class_data[p][1] += 1

class_labels = {1: "1st Class", 2: "2nd Class", 3: "3rd Class"}
for cls in [1, 2, 3]:
    surv, tot = class_data[cls]
    pct = surv / tot * 100 if tot else 0
    print(hbar(f"{class_labels[cls]} ({surv}/{tot})", round(pct, 1), 100))

# ─────────────────────────────────────────────────────────────────────────────
# CHART 3 · Survival by Sex — Horizontal Bars
# ─────────────────────────────────────────────────────────────────────────────

print("\n")
separator("─")
print("\n  CHART 3 · Survival Rate by Sex\n")

sex_data = defaultdict(lambda: [0, 0])
for s, g in zip(survived_col, sex_col):
    if s is not None and g:
        sex_data[g][0] += s
        sex_data[g][1] += 1

for gender in ["female", "male"]:
    surv, tot = sex_data[gender]
    pct = surv / tot * 100 if tot else 0
    print(hbar(f"{gender.title()} ({surv}/{tot})", round(pct, 1), 100))

# ─────────────────────────────────────────────────────────────────────────────
# CHART 4 · Age Distribution — ASCII Histogram
# ─────────────────────────────────────────────────────────────────────────────

print("\n")
separator("─")
print("\n  CHART 4 · Age Distribution (All Passengers)\n")

valid_ages = [a for a in age_col if a is not None]
buckets = [(0,10),(10,20),(20,30),(30,40),(40,50),(50,60),(60,70),(70,100)]
bucket_counts = []
for lo, hi in buckets:
    cnt = sum(1 for a in valid_ages if lo <= a < hi)
    bucket_counts.append((f"{lo}-{hi}", cnt))

max_cnt = max(c for _, c in bucket_counts)
for lbl, cnt in bucket_counts:
    bar = "█" * round(cnt / max_cnt * 40)
    print(f"  {lbl:>6}  {bar:<40}  {cnt}")

print(f"\n  Ages known for {len(valid_ages)}/{total} passengers")
print(f"  Mean age: {sum(valid_ages)/len(valid_ages):.1f}  |  "
      f"Min: {min(valid_ages):.0f}  |  Max: {max(valid_ages):.0f}")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 5 · Survival Rate by Age Group — Side-by-side bars
# ─────────────────────────────────────────────────────────────────────────────

print("\n")
separator("─")
print("\n  CHART 5 · Survival Rate by Age Group\n")
print(f"  {'Age':>6}  {'Survived %':^44}  {'N'}")

for lo, hi in buckets:
    grp_surv = [s for s, a in zip(survived_col, age_col)
                if a is not None and lo <= a < hi and s is not None]
    if not grp_surv:
        continue
    pct = sum(grp_surv) / len(grp_surv) * 100
    filled = round(pct / 100 * 40)
    bar = "█" * filled + "░" * (40 - filled)
    print(f"  {lo}-{hi:>3}   {bar}  {pct:5.1f}%  n={len(grp_surv)}")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 6 · Fare Distribution — Log-scaled buckets
# ─────────────────────────────────────────────────────────────────────────────

print("\n")
separator("─")
print("\n  CHART 6 · Fare Distribution & Survival Rate\n")

fare_buckets = [(0,10),(10,25),(25,50),(50,100),(100,200),(200,600)]
print(f"  {'Fare (£)':>12}  {'Count':^6}  {'Surv%':^7}  Chart")
for lo, hi in fare_buckets:
    grp = [(s, f) for s, f in zip(survived_col, fare_col)
           if f is not None and lo <= f < hi and s is not None]
    if not grp:
        continue
    cnt = len(grp)
    pct = sum(s for s, _ in grp) / cnt * 100
    bar = "█" * round(pct / 100 * 30)
    print(f"  £{lo:>4}–{hi:<5}  {cnt:>5}   {pct:5.1f}%  {bar}")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 7 · Embarkation Port — Horizontal bars
# ─────────────────────────────────────────────────────────────────────────────

print("\n")
separator("─")
print("\n  CHART 7 · Survival Rate by Port of Embarkation\n")

port_names = {"C": "Cherbourg (C)", "Q": "Queenstown (Q)", "S": "Southampton (S)"}
port_data = defaultdict(lambda: [0, 0])
for s, e in zip(survived_col, embarked_col):
    if s is not None and e in port_names:
        port_data[e][0] += s
        port_data[e][1] += 1

for code in ["C", "Q", "S"]:
    surv, tot = port_data[code]
    pct = surv / tot * 100 if tot else 0
    print(hbar(f"{port_names[code]} ({surv}/{tot})", round(pct, 1), 100))

# ─────────────────────────────────────────────────────────────────────────────
# CHART 8 · Vertical bar — Class × Sex survival count
# ─────────────────────────────────────────────────────────────────────────────

print("\n")
separator("─")
print("\n  CHART 8 · Survivors by Class & Sex (vertical bars)\n")

cs_data = defaultdict(int)
for s, p, g in zip(survived_col, pclass_col, sex_col):
    if s == 1 and p and g:
        cs_data[(p, g)] += 1

groups = [(f"F-{p}", cs_data[(p, "female")]) for p in [1,2,3]] + \
         [(f"M-{p}", cs_data[(p, "male")])   for p in [1,2,3]]

vbar_chart("Survivors  (F=Female, M=Male, 1/2/3=Class)", groups, height=10)

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

print("\n")
separator()
print("  KEY FINDINGS")
separator()
f_rate = sex_data["female"][0] / sex_data["female"][1] * 100
m_rate = sex_data["male"][0]   / sex_data["male"][1]   * 100
c1 = class_data[1][0] / class_data[1][1] * 100
c3 = class_data[3][0] / class_data[3][1] * 100
print(f"  • Women survived at {f_rate:.0f}% vs men at {m_rate:.0f}%  (\"women and children first\")")
print(f"  • 1st class: {c1:.0f}% survival  vs  3rd class: {c3:.0f}% survival")
ch_rate = port_data["C"][0] / port_data["C"][1] * 100
so_rate = port_data["S"][0] / port_data["S"][1] * 100
print(f"  • Cherbourg passengers: {ch_rate:.0f}% survived  vs  Southampton: {so_rate:.0f}%")
child_surv = [s for s, a in zip(survived_col, age_col) if a is not None and a < 10 and s is not None]
print(f"  • Children under 10: {sum(child_surv)/len(child_surv)*100:.0f}% survived  (n={len(child_surv)})")
separator()
