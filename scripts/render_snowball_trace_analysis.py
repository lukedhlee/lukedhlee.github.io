"""Figures for the paired trace reads, 2026-10-28.

Source: OpenThoughts-Agent/ai_memory/active/snowball-blog/results/2026-10-27/
trace_analysis/reports/tblite.md, section 9, and TRACE_ANALYSIS.md, table T5.
Labels summarize traces; they are
not verbatim model quotations. Shared-success metrics are medians of per-task
medians over passing attempts, not a matched-compute training comparison.
"""

from pathlib import Path
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.font_manager import FontProperties

TITLE_FONT = FontProperties(family=["Helvetica Neue", "Arial", "DejaVu Sans"], weight="medium")

OUT = Path(__file__).resolve().parents[1] / "assets/img/snowball"
BLUE, CYAN = "#2563eb", "#06a9df"
INK, MUTED, LINE = "#202e40", "#607084", "#e5edf5"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "svg.fonttype": "path"})


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=180, facecolor="white")
    path = OUT / f"{name}.svg"
    fig.savefig(path, facecolor="white")
    path.write_text("\n".join(x.rstrip() for x in path.read_text().splitlines()) + "\n")
    plt.close(fig)


def cases():
    fig = plt.figure(figsize=(13.4, 8.5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.text(.045, .945, "The useful idea was there. The outcome differed.",
            fontsize=23, weight="bold")
    ax.text(.045, .902, "Two TBLite tasks, compared across the same training routes",
            fontsize=12, color=MUTED)
    for x, label, color in [(.045, "RL", BLUE), (.515, "SFT + RL", CYAN)]:
        ax.text(x + .018, .84, label, fontsize=17, color=color, weight="bold")
        ax.plot([x, x + .44], [.822, .822], color=color, lw=3)

    rows = [
        (.765, "Reverse-engineer a stack VM", "reverse-engineer-stack-vm",
         [("Saw the candidate passphrase", "Tested it on the validator", "Passed 2 / 2 attempts"),
          ("Saw the same passphrase", "Never tested it on the validator", "Passed 0 / 6 attempts")]),
        (.405, "Fix a checkpoint / resume bug", "etl_checkpoint_resume_bug",
         [("Found the disabled guard", "Rewrote the fix or left a patch file", "Passed 0 / 2 attempts"),
          ("Found the same disabled guard", "Applied the minimal fix", "Passed 6 / 6 attempts")]),
    ]
    for top, title, task, columns in rows:
        ax.text(.045, top, title, fontsize=17, weight="bold")
        ax.text(.045, top - .031, task, fontsize=10, color=MUTED)
        for x, steps, color in zip([.045, .515], columns, [BLUE, CYAN]):
            bottom = top - .276
            ax.add_patch(FancyBboxPatch((x, bottom), .44, .222,
                         boxstyle="round,pad=0.009,rounding_size=0.012",
                         facecolor="#f7faff", edgecolor=LINE, linewidth=1))
            for k, step in enumerate(steps):
                y = top - .101 - k * .066
                ax.text(x + .018, y, str(k + 1) if k < 2 else "→", fontsize=12,
                        color=color, weight="bold", va="center")
                ax.text(x + .05, y, step, fontsize=12, va="center",
                        weight="bold" if k == 2 else "normal")
    ax.text(.045, .045, "RL: 2 attempts. SFT + RL: 2 per recipe × 3 recipes. Counts show these examples, not an aggregate ranking.",
            fontsize=10, color=MUTED)
    save(fig, "trace-paired-examples")


def working_style():
    fig, axes = plt.subplots(1, 5, figsize=(16.4, 4.9), sharey=True)
    fig.subplots_adjust(left=.10, right=.98, top=.59, bottom=.23, wspace=.38)
    fig.text(.045, .91, "On shared successes, the routes worked differently",
             fontsize=22, fontproperties=TITLE_FONT, va="top")
    fig.text(.045, .80, "26 TBLite tasks unsolved in the starting-model attempts; both routes later passed",
             fontsize=12, color=MUTED)
    for ax, (title, vals, limit, fmt) in zip(axes, [
        ("Time to finish", [255, 604], 800, lambda n: f"{n:,} s"),
        ("Agent turns", [28.5, 31], 43, lambda n: f"{n:g}"),
        ("Output tokens", [35000, 92000], 125000, lambda n: f"{n // 1000}k"),
        ("Reasoning share", [42, 69], 95, lambda n: f"{n}%"),
        ("Shell commands", [61, 44], 85, lambda n: str(n)),
    ]):
        ax.set_title(title, fontsize=14, fontproperties=TITLE_FONT, loc="left", pad=24)
        ax.barh([1, 0], vals, color=[BLUE, CYAN], height=.28)
        for y, n in zip([1, 0], vals):
            ax.text(n + limit * .025, y, fmt(n), va="center", fontsize=13)
        ax.set_xlim(0, limit)
        ax.set_ylim(-.65, 1.65)
        ax.set_yticks([1, 0], ["RL", "SFT + RL"])
        ax.tick_params(axis="y", length=0, labelsize=12, pad=10, labelleft=ax is axes[0])
        ax.set_xticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.axvline(0, color=LINE, lw=1)
    fig.text(.04, .10, "Medians of per-task medians on passing attempts. SFT + RL pools the three recipes.\n"
             "Reasoning share is measured in output characters.",
             fontsize=11, color=MUTED, linespacing=1.6)
    save(fig, "trace-working-style")


def swe_steps():
    """T5 milestones, with each starting policy paired with its RL continuation."""
    labels = ["Snowball 09-21", "CalibForge SFT",
              "CalibForge + Kimi SFT", "CalibForge + Kimi Relay SFT"]
    values = [
        ([77.7, 38.0, 14.7], [95.9, 50.5, 34.2]),
        ([97.6, 59.3, 42.8], [94.9, 64.0, 42.6]),
        ([99.5, 89.9, 51.0], [96.4, 87.8, 52.8]),
        ([98.0, 90.9, 54.5], [97.0, 87.3, 50.3]),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(16.4, 6.0), sharey=True)
    fig.subplots_adjust(left=.235, right=.955, bottom=.15, top=.59, wspace=.20)
    fig.text(.045, .91, "From finding the file to passing target tests", fontsize=23, fontproperties=TITLE_FONT, va="top")
    fig.text(.045, .80, "SWE-bench Verified r100 · Share of scored attempts reaching each milestone",
             fontsize=15, color=MUTED)
    from matplotlib.lines import Line2D
    fig.legend(handles=[
        Line2D([], [], marker="o", ls="", color="#a0a9b5", markerfacecolor="white", markersize=8, label="Snowball 09-21"),
        Line2D([], [], marker="o", ls="", color=CYAN, markerfacecolor="white", markersize=8, label="Additional SFT"),
        Line2D([], [], marker="o", ls="", color=BLUE, markersize=8, label="RL step 30"),
    ], loc="upper left", bbox_to_anchor=(.04, .75), ncol=3, frameon=False, fontsize=12)
    for col, (ax, title) in enumerate(zip(axes, [
        "Opened a relevant file", "Edited a relevant file", "Target tests passing",
    ])):
        ax.set_title(title, loc="left", fontsize=16, fontproperties=TITLE_FONT, pad=22)
        for row, (before, after) in enumerate(values):
            x1, x2 = before[col], after[col]
            color = "#a0a9b5" if row == 0 else CYAN
            ax.hlines(row, 0, 100, color=LINE, linewidth=.8, zorder=0)
            ax.plot([x1, x2], [row, row], color="#aebdd0", lw=2.5, zorder=1)
            ax.scatter(x1, row, s=100, facecolors="white", edgecolors=color, linewidths=2.1, zorder=3)
            ax.scatter(x2, row, s=48, facecolors=BLUE, edgecolors=BLUE, zorder=4)
            ax.text(111, row, f"{x1:.1f} → {x2:.1f}", va="center", fontsize=13, color=INK)
        ax.set_xlim(-3, 184)
        ax.set_ylim(3.55, -.55)
        ax.set_xticks([0, 50, 100], ["0%", "50%", "100%"])
        ax.set_yticks(range(4), labels)
        ax.tick_params(axis="both", length=0, labelsize=14, pad=9)
        ax.grid(axis="x", color=LINE, linewidth=.8)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)
    save(fig, "trace-swe-steps")


def failure_modes():
    """Compare pattern incidence with the same all-attempt denominator."""
    data = json.loads((Path(__file__).parent / "data/snowball_failure_modes.json").read_text())
    modes = data["modes"]
    routes = [
        ("Snowball 09-21", "base0921", "baserl30"),
        ("CalibForge SFT", "cv7", "v7rl30"),
        ("CalibForge + Kimi SFT", "vkimicf2", "vkrl30"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(16.4, 7.8), sharey=True)
    fig.subplots_adjust(left=.20, right=.95, top=.65, bottom=.16, wspace=.24)
    fig.text(.045, .91, "How failure patterns changed with RL", fontsize=23, fontproperties=TITLE_FONT, va="top")
    fig.text(.045, .82, "OpenThoughts-TBLite · Share of all scored attempts with each pattern",
             fontsize=14, color=MUTED)
    from matplotlib.lines import Line2D
    fig.legend(handles=[
        Line2D([], [], marker="o", ls="", color="#a0a9b5", markerfacecolor="white", markersize=8, label="Starting checkpoint"),
        Line2D([], [], marker="o", ls="", color=CYAN, markerfacecolor="white", markersize=8, label="Additional SFT"),
        Line2D([], [], marker="o", ls="", color=BLUE, markersize=8, label="After RL"),
    ], loc="upper left", bbox_to_anchor=(.04, .78), ncol=3, frameon=False, fontsize=13)
    for ax, (title, before, after) in zip(axes, routes):
        ax.set_title(title, fontsize=17, loc="left", fontfamily=TITLE_FONT.get_family(), fontweight="medium", pad=10)
        before_color = "#a0a9b5" if before == "base0921" else CYAN
        for y, mode in enumerate(modes):
            a = 100 * mode["counts"][before] / mode["n_trials"][before]
            b = 100 * mode["counts"][after] / mode["n_trials"][after]
            ax.hlines(y, 0, 85, color=LINE, linewidth=.8, zorder=0)
            ax.plot([a, b], [y, y], color="#aebdd0", lw=2.5, zorder=1)
            ax.scatter([a], [y], s=90, facecolors="white", edgecolors=before_color, linewidths=2.1, zorder=3)
            ax.scatter([b], [y], s=45, facecolors=BLUE, edgecolors=BLUE, zorder=4)
            ax.text(94, y, f"{a:.0f} → {b:.0f}", va="center", fontsize=12)
        ax.set_xlim(-4, 138)
        ax.set_ylim(4.65, -.6)
        ax.set_xticks([0, 40, 80], ["0%", "40%", "80%"])
        ax.set_yticks(range(len(modes)), [m["label"] for m in modes])
        ax.tick_params(axis="both", length=0, labelsize=13, pad=10)
        ax.grid(axis="x", color=LINE, lw=.8)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)
        n1, n2 = modes[0]["n_trials"][before], modes[0]["n_trials"][after]
        ax.set_xlabel(f"n = {n1} → {n2} attempts", fontsize=11, color=MUTED, labelpad=18)
    save(fig, "trace-failure-modes")


if __name__ == "__main__":
    cases()
    working_style()
    swe_steps()
    failure_modes()
