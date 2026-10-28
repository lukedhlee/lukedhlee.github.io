"""Render the published Snowball point estimates with clear blue accents.

Values reproduce the existing figures, not a new evaluation or aggregation.
Run from any directory with matplotlib and numpy installed.
"""

from pathlib import Path
import json

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


def stack_comparison():
    data = json.loads((Path(__file__).parent / "data/snowball_stack_progress.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.3), sharey=True)
    fig.subplots_adjust(left=.075, right=.965, bottom=.17, top=.66, wspace=.20)
    fig.text(.045, .94, "The rebuilt stack improved faster", fontsize=20, weight="semibold")
    fig.text(.045, .875, "R2E-Gym · Held-out pass@1 across RL updates", fontsize=12, color=MUTED)
    for ax, split in zip(axes, data["splits"]):
        for key, color, label in [("old", BASE, "Old stack"), ("new", BLUE, "New stack")]:
            xs, ys = split[f"{key}_steps"], split[f"{key}_scores"]
            ax.plot(xs, ys, color=color, label=label, lw=2.5, marker="o", ms=6)
            for x, y in zip(xs[1:], ys[1:]):
                ax.annotate(f"{y:.1f}%", (x, y), xytext=(0, 10 if key == "new" else -20),
                            textcoords="offset points", ha="center", fontsize=11,
                            color=BLUE if key == "new" else INK)
        ax.set_title(f'{split["title"]} · {split["tasks"]} tasks',
                     loc="left", fontsize=13, weight="semibold", pad=18)
        ax.set_xlim(-2, 40)
        ax.set_ylim(30, 66)
        ax.set_xticks([0, 12, 24, 36])
        ax.set_yticks([30, 40, 50, 60], ["30%", "40%", "50%", "60%"])
        ax.set_xlabel("RL update", fontsize=12, labelpad=12)
        ax.tick_params(length=0, pad=8, labelsize=11)
        ax.spines["bottom"].set_visible(False)
        ax.grid(axis="y", color=GRID, linewidth=.8)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(.04, .82),
               ncol=2, frameon=False, fontsize=12)
    save(fig, "stack-comparison")


def sft_behavior_origin():
    # Published scan: 31,661 SWE traces within 366,154 Stage-3 rows.
    # Preserve the original all-corpus denominator and rounded rates.
    fig, ax = plt.subplots(figsize=(11.6, 4.5))
    fig.subplots_adjust(left=.33, right=.91, bottom=.18, top=.70)
    fig.text(.045, .93, "SFT contained the same editing routines",
             fontsize=19, weight="semibold")
    fig.text(.045, .83, "Share of the full Stage-3 SFT corpus · 366,154 traces",
             fontsize=12, color=MUTED)
    labels = ["Write /app/solution.patch", "Write SEARCH/REPLACE blocks",
              "Run patch -pN", "Use a Python rewriter in /tmp"]
    values = [8.6, 8.6, 4.6, 3.5]
    for y, value in enumerate(values):
        ax.hlines(y, 0, 10, color=GRID, lw=1)
        ax.scatter(value, y, s=65, color=BLUE, zorder=3)
        ax.annotate(f"{value:.1f}%", (value, y), xytext=(11, 0),
                    textcoords="offset points", va="center", fontsize=13, color=INK)
    ax.set_yticks(range(4), labels, fontsize=12, color=INK)
    ax.set_ylim(3.5, -.5)
    ax.set_xlim(0, 10.5)
    ax.set_xticks([0, 2, 4, 6, 8, 10], ["0%", "2%", "4%", "6%", "8%", "10%"])
    ax.tick_params(length=0, pad=12, labelsize=12)
    ax.spines["bottom"].set_visible(False)
    save(fig, "sft-behavior-origin")


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
    data = json.loads((Path(__file__).parent / "data/snowball_rl_checkpoints.json").read_text())
    order = ["CalibForge SFT", data["hero"], "CalibForge + Kimi Relay SFT"]
    step30_color = "#5b8ff9"
    fig, axes = plt.subplots(1, 3, figsize=(16.4, 8.4), sharey=True)
    fig.subplots_adjust(left=.205, right=.98, bottom=.15, top=.80, wspace=.18)
    fig.text(.205, .94, "Coding-agent SFT and RL continuations", fontsize=21, weight="semibold")
    fig.legend(handles=[Patch(color=BASE, label="Snowball 09-21"),
                        Patch(color=LIGHT, label="Additional SFT"),
                        Patch(color=step30_color, label="RL step 30"),
                        Patch(color=BLUE, label="RL step 60")],
               loc="upper left", bbox_to_anchor=(.205, .91), ncol=4,
               frameon=False, fontsize=12, handlelength=1.8, columnspacing=1.6)
    labels = ["Snowball 09-21", "CalibForge SFT",
              "CalibForge + Kimi SFT", "CalibForge + Kimi Relay SFT"]
    panels = [
        ("Terminal-Bench 2.1", "tb", 7.2, [17.4, 18.8, 17.4], 18.8),
        ("SWE-bench Verified r100", "swe", 12.8, [34.9, 46.5, 47.0], 30.5),
        ("OpenThoughts-TBLite", "tblite", 11.5, [24.4, 33.0, 36.8], 45.1),
    ]
    for ax, (title, metric, base, sft, base_rl) in zip(axes, panels):
        ax.set_title(title, loc="left", fontsize=15, weight="semibold", pad=20)
        for y, value, color in [(-.12, base, BASE), (.12, base_rl, step30_color)]:
            bars = ax.barh([y], [value], height=.18, color=color)
            ax.bar_label(bars, fmt="%.1f", padding=5, fontsize=12, color=MUTED if color == BASE else INK)
        for row, (name, sft_value) in enumerate(zip(order, sft), start=1):
            values = [(row - .24, sft_value, LIGHT),
                      (row, data["runs"][name][metric][1], step30_color)]
            if data["runs"][name][metric][2] is not None:
                values.append((row + .24, data["runs"][name][metric][2], BLUE))
            for y, value, color in values:
                bars = ax.barh([y], [value], height=.18, color=color)
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
    axes[0].get_yticklabels()[2].set_weight("bold")
    save(fig, "sft-rl-stages")


def checkpoint_progress():
    data = json.loads((Path(__file__).parent / "data/snowball_rl_checkpoints.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(16.4, 5.3))
    fig.subplots_adjust(left=.065, right=.98, bottom=.16, top=.67, wspace=.25)
    fig.text(.045, .92, "From 30 to 60 RL updates", fontsize=22, weight="semibold")
    styles = [
        ("CalibForge SFT", BASE, "o", "CalibForge"),
        (data["hero"], BLUE, "o", "CalibForge + Kimi (vanilla)"),
        ("CalibForge + Kimi Relay SFT", LIGHT, "s", "CalibForge + Kimi (Relay)"),
    ]
    for ax, metric, title in zip(axes, ["tb", "swe", "tblite"], data["metrics"]):
        ax.set_title(title, loc="left", fontsize=14, weight="semibold", pad=16)
        for name, color, marker, label in styles:
            xy = [(step, value) for step, value in zip(data["steps"], data["runs"][name][metric]) if value is not None and step in (30, 60)]
            xs, ys = zip(*xy)
            ax.plot(xs, ys, color=color, marker=marker, markersize=6,
                    lw=2.7 if name == data["hero"] else 1.8, label=label)
            ax.annotate(f"{ys[-1]:.1f}", xy=xy[-1], xytext=(7, 0), textcoords="offset points",
                        va="center", color=color, fontsize=12, weight="semibold")
        ax.set_xlim(25, 72)
        ax.set_xticks([30, 60])
        ax.set_xlabel("RL update", fontsize=12, labelpad=10)
        ax.set_ylim({"tb":(10, 28), "swe":(32, 56), "tblite":(20, 50)}[metric])
        ax.set_ylabel("Pass@1 (%)", fontsize=12)
        ax.tick_params(length=0, pad=8, labelsize=12)
        ax.grid(axis="y", color=GRID, linewidth=.8)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(.04, .84),
               ncol=3, frameon=False, fontsize=12)
    save(fig, "rl-checkpoint-progress")


if __name__ == "__main__":
    stack_comparison()
    sft_behavior_origin()
    early_rl()
    sft_rl()
    checkpoint_progress()
