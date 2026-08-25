from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "analysis_outputs"
OUT = ROOT / "dashboard" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

metrics = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))
weekly = pd.read_csv(DATA / "weekly_conversion.csv", parse_dates=["acquisition_week"])
funnel = pd.read_csv(DATA / "funnel_summary.csv")
cart = pd.read_csv(DATA / "checkout_cart_band.csv")
retention = pd.read_csv(DATA / "retention_summary.csv")
experiment = pd.read_csv(DATA / "experiment_summary.csv")

plt.style.use("seaborn-v0_8-whitegrid")
fig = plt.figure(figsize=(16, 10), facecolor="#f5f7fb")
grid = fig.add_gridspec(3, 4, height_ratios=[0.75, 2.2, 2.2], hspace=0.45, wspace=0.36)
fig.suptitle("SwiftBasket Product Analytics — Executive Overview", x=0.06, ha="left", fontsize=20, fontweight="bold", color="#172033")
fig.text(0.06, 0.942, "Synthetic data | 1 Jan–7 Aug 2026 | Conversion diagnosis and experiment readout", fontsize=10, color="#62708a")

cards = [
    ("Users", f"{metrics['users']:,}", "Simulated acquisition base"),
    ("7-day conversion", f"{metrics['post_conversion_7d']*100:.2f}%", f"{metrics['relative_conversion_change']*100:.1f}% relative vs pre-change"),
    ("Delivered GMV", f"₹{metrics['gmv']/1_000_000:.2f}M", f"AOV ₹{metrics['aov']:.0f}"),
    ("Experiment", f"{metrics['experiment_absolute_lift_pp']:+.2f} pp", f"p={metrics['experiment_p_value']:.3f} — inconclusive"),
]
for i, (title, value, subtitle) in enumerate(cards):
    ax = fig.add_subplot(grid[0, i])
    ax.set_facecolor("white")
    ax.text(0.05, 0.78, title, transform=ax.transAxes, fontsize=10, color="#62708a")
    ax.text(0.05, 0.40, value, transform=ax.transAxes, fontsize=20, fontweight="bold", color="#172033")
    ax.text(0.05, 0.12, subtitle, transform=ax.transAxes, fontsize=8.5, color="#7a869c")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_visible(False)

ax1 = fig.add_subplot(grid[1, :2])
ax1.plot(weekly["acquisition_week"], weekly["conversion_7d"] * 100, color="#3867d6", linewidth=2.2)
ax1.axvline(pd.Timestamp("2026-04-15"), color="#eb3b5a", linestyle="--", linewidth=1.5, label="Fee change")
ax1.set_title("Weekly 7-day first-order conversion", loc="left", fontweight="bold")
ax1.set_ylabel("Conversion (%)")
ax1.legend(frameon=False)

ax2 = fig.add_subplot(grid[1, 2:])
labels = [x.replace("_", " ").title() for x in funnel["stage"]]
values = funnel["overall_conversion"] * 100
ax2.barh(labels[::-1], values[::-1], color="#20bf6b")
ax2.set_title("New-user funnel reach", loc="left", fontweight="bold")
ax2.set_xlabel("Eligible users reaching stage (%)")
for y, v in enumerate(values[::-1]): ax2.text(v + 0.6, y, f"{v:.1f}%", va="center", fontsize=8)

ax3 = fig.add_subplot(grid[2, :2])
pivot = cart.pivot(index="cart_band", columns="period", values="payment_attempt_rate").reindex(["<₹199", "₹199–398", "₹399+"])
x = np.arange(len(pivot)); width = 0.36
ax3.bar(x - width/2, pivot["pre_change"] * 100, width, label="Pre-change", color="#45aaf2")
ax3.bar(x + width/2, pivot["post_change"] * 100, width, label="Post-change", color="#eb3b5a")
ax3.set_xticks(x, pivot.index)
ax3.set_ylabel("Checkout → payment attempt (%)")
ax3.set_title("Fee friction concentrates in lower-value carts", loc="left", fontweight="bold")
ax3.legend(frameon=False)

ax4 = fig.add_subplot(grid[2, 2])
ax4.bar(retention["day"], retention["retention_rate"] * 100, color="#8854d0")
ax4.set_title("Exact-day retention", loc="left", fontweight="bold")
ax4.set_ylabel("Retention (%)")
for i, v in enumerate(retention["retention_rate"] * 100): ax4.text(i, v + 0.25, f"{v:.1f}%", ha="center", fontsize=8)

ax5 = fig.add_subplot(grid[2, 3])
ax5.bar(experiment["variant"].str.title(), experiment["conversion_rate"] * 100, color=["#778ca3", "#20bf6b"])
ax5.set_ylim(0, max(experiment["conversion_rate"] * 100) * 1.28)
ax5.set_title("ITT experiment result", loc="left", fontweight="bold")
ax5.set_ylabel("7-day conversion (%)")
for i, v in enumerate(experiment["conversion_rate"] * 100): ax5.text(i, v + 0.2, f"{v:.2f}%", ha="center", fontsize=8)
ax5.text(0.5, 0.92, f"p={metrics['experiment_p_value']:.3f}", transform=ax5.transAxes, ha="center", fontsize=9, color="#62708a")

fig.text(0.06, 0.018, "Decision: traffic mix and within-segment checkout deterioration both contributed; early fee transparency alone did not produce conclusive lift.", fontsize=9, color="#48566f")
fig.savefig(OUT / "swiftbasket_executive_dashboard.png", dpi=180, bbox_inches="tight")
print(OUT / "swiftbasket_executive_dashboard.png")
