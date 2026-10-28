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
    def endpoints(metric):
        return [data["runs"][name][metric][data["steps"].index(data["selected_steps"][name])] for name in order]
    fig, axes = plt.subplots(1, 3, figsize=(16.4, 8.4), sharey=True)
    fig.subplots_adjust(left=.205, right=.98, bottom=.15, top=.80, wspace=.18)
    fig.text(.205, .94, "Coding-agent SFT and RL continuations",
             fontsize=21, weight="semibold")
    fig.legend(handles=[Patch(color=BASE, label="Snowball 09-21"),
                        Patch(color=LIGHT, label="Additional SFT"),
                        Patch(color=BLUE, label="After RL")],
               loc="upper left", bbox_to_anchor=(.205, .91), ncol=3,
               frameon=False, fontsize=12, handlelength=1.8, columnspacing=1.8)
    labels = ["Snowball 09-21\nRL step 30", "CalibForge SFT\nRL step 60",
              "CalibForge + Kimi SFT\nRL step 60", "CalibForge + Kimi Relay SFT\nRL step 30"]
    panels = [
        ("Terminal-Bench 2.1", 7.2, [17.4, 18.8, 17.4], endpoints("tb")),
        ("SWE-bench Verified r100", 12.8, [34.9, 46.5, 47.0], endpoints("swe")),
        ("OpenThoughts-TBLite", 11.5, [24.4, 33.0, 36.8], endpoints("tblite")),
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
    axes[0].get_yticklabels()[2].set_weight("bold")
    save(fig, "sft-rl-stages")


def checkpoint_progress():
    data = json.loads((Path(__file__).parent / "data/snowball_rl_checkpoints.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(16.4, 5.3))
    fig.subplots_adjust(left=.065, right=.98, bottom=.16, top=.67, wspace=.25)
    fig.text(.045, .92, "More RL updates helped some recipes more than others", fontsize=22, weight="semibold")
    styles = [
        ("CalibForge SFT", BASE, "o", "CalibForge"),
        (data["hero"], BLUE, "o", "CalibForge + Kimi (vanilla)"),
        ("CalibForge + Kimi Relay SFT", LIGHT, "s", "CalibForge + Kimi (Relay)"),
    ]
    for ax, metric, title in zip(axes, ["tb", "swe", "tblite"], data["metrics"]):
        ax.set_title(title, loc="left", fontsize=14, weight="semibold", pad=16)
        for name, color, marker, label in styles:
            xy = [(step, value) for step, value in zip(data["steps"], data["runs"][name][metric]) if value is not None]
            xs, ys = zip(*xy)
            ax.plot(xs, ys, color=color, marker=marker, markersize=6,
                    lw=2.7 if name == data["hero"] else 1.8, label=label)
            ax.annotate(f"{ys[-1]:.1f}", xy=xy[-1], xytext=(7, 0), textcoords="offset points",
                        va="center", color=color, fontsize=12, weight="semibold")
        ax.set_xlim(8, 72)
        ax.set_xticks([12, 30, 60])
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
    early_rl()
    sft_rl()
    checkpoint_progress()
