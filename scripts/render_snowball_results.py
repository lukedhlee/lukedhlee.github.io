"""Render the published Snowball point estimates with clear blue accents.

Values reproduce the existing figures, not a new evaluation or aggregation.
Run from any directory with matplotlib and numpy installed.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np


OUT = Path(__file__).resolve().parents[1] / "assets/img/snowball"
BASE, LIGHT, BLUE = "#a0a9b5", "#35a9e6", "#2563eb"
INK, MUTED, GRID = "#283747", "#728092", "#edf0f3"
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": "#d9e0e7",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.axisbelow": True,
    "svg.fonttype": "path",
})


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=180, facecolor="white")
    svg = OUT / f"{name}.svg"
    fig.savefig(svg, facecolor="white")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    plt.close(fig)


def early_rl():
    fig, ax = plt.subplots(figsize=(9.6, 4.89))
    fig.subplots_adjust(left=.09, right=.98, bottom=.24, top=.76)
    fig.text(.045, .94, "Early RL improved success and task coverage",
             fontsize=17, weight="semibold")
    x = np.arange(2)
    series = [
        ("Starting model", [8.7, 29.8], BASE),
        ("RL: higher pass@1", [16.6, 39.8], BLUE),
        ("RL: higher pass@8", [15.2, 42.9], LIGHT),
    ]
    width = .13
    spacing = .17
    for i, (label, values, color) in enumerate(series):
        bars = ax.bar(x + (i - 1) * spacing, values, width, color=color, label=label)
        ax.bar_label(bars, labels=[f"{v:.1f}%" for v in values],
                     padding=5, fontsize=11, color=INK)
    ax.set_ylim(0, 60)
    ax.set_yticks(range(0, 61, 10))
    ax.set_ylabel("Success rate (%)", fontsize=11, labelpad=10)
    ax.set_xticks(x, ["Single-attempt success\n(pass@1)",
                       "Solved at least once in eight\n(pass@8)"])
    ax.tick_params(axis="both", length=0, pad=8, labelsize=11)
    ax.grid(axis="y", color=GRID, linewidth=.7)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.04), ncol=3,
              frameon=False, fontsize=10, handlelength=1.5, columnspacing=1.6)
    fig.text(.045, .065, "Same 191 held-out R2E-Gym tasks, eight samples per task.\n"
             "Blue and cyan denote different experimental RL checkpoints.",
             fontsize=9, color=MUTED, linespacing=1.5)
    save(fig, "early-rl-labeled")


def sft_rl():
    fig, axes = plt.subplots(1, 3, figsize=(16.4, 8.4), sharey=True)
    fig.subplots_adjust(left=.205, right=.98, bottom=.15, top=.80, wspace=.18)
    fig.text(.205, .94, "Coding-agent SFT and RL continuations",
             fontsize=21, weight="semibold")
    fig.legend(handles=[Patch(color=BASE, label="09-21 starting model"),
                        Patch(color=LIGHT, label="SFT"),
                        Patch(color=BLUE, label="After RL")],
               loc="upper left", bbox_to_anchor=(.205, .91), ncol=3,
               frameon=False, fontsize=12, handlelength=1.8, columnspacing=1.8)
    labels = ["09-21 starting model", "CalibForge\nvanilla SFT",
              "CalibForge + Kimi\nvanilla SFT", "CalibForge + Kimi\nRelay SFT"]
    panels = [
        ("Terminal-Bench 2.1", 7.2, [17.4, 18.8, 17.4], [19.3, 18.2, 19.3]),
        ("SWE-bench Verified r100", 12.8, [34.9, 46.5, 47.0], [38.0, 47.0, 43.5]),
        ("OpenThoughts-TBLite", 11.5, [24.4, 33.0, 36.8], [30.8, 37.0, 44.0]),
    ]
    for ax, (title, base, sft, rl), base_rl in zip(axes, panels, [18.8, 30.5, 45.1]):
        ax.set_title(title, loc="left", fontsize=15, weight="semibold", pad=20)
        bars = ax.barh([-.16], [base], height=.25, color=BASE)
        ax.bar_label(bars, fmt="%.1f", padding=5, fontsize=12, color=MUTED)
        bars = ax.barh([.16], [base_rl], height=.25, color=BLUE)
        ax.bar_label(bars, fmt="%.1f", padding=5, fontsize=12, color=INK)
        for values, offset, color in [(sft, -.16, LIGHT), (rl, .16, BLUE)]:
            bars = ax.barh(np.arange(1, 4) + offset, values, height=.25, color=color)
            ax.bar_label(bars, fmt="%.1f", padding=5, fontsize=12, color=INK)
        ax.set_xlim(0, 63)
        ax.set_ylim(3.5, -.5)
        ax.set_yticks(range(4), labels)
        ax.set_xticks([0, 20, 40], ["0%", "20%", "40%"])
        ax.tick_params(axis="both", length=0, pad=10, labelsize=12)
        ax.grid(axis="x", color=GRID, linewidth=.7)
        ax.axhline(.5, color=GRID, linewidth=.8)
        ax.set_xlabel("Pass@1 (%)", fontsize=12, labelpad=12)
    axes[0].tick_params(axis="y", labelcolor=INK)
    save(fig, "sft-rl-stages")


if __name__ == "__main__":
    early_rl()
    sft_rl()
