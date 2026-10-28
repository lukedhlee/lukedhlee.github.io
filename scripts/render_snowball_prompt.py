"""Prompt-selection pilot, from OpenThoughts-Agent/notes/artifacts/p2o-gist.

Source: prompt-distillation.md and make_figs.py. The five candidates were
hand-written; this was not an automated prompt-evolution experiment.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / "assets/img/snowball"
INK, MUTED, GRID = "#202e40", "#607084", "#e5edf5"
GRAY, CYAN, BLUE = "#a0a9b5", "#06a9df", "#2563eb"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                     "axes.labelcolor": INK, "svg.fonttype": "path"})


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=180, facecolor="white")
    path = OUT / f"{name}.svg"
    fig.savefig(path, facecolor="white")
    path.write_text("\n".join(x.rstrip() for x in path.read_text().splitlines()) + "\n")
    plt.close(fig)


def method():
    fig, ax = plt.subplots(figsize=(13, 2.7))
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.text(.04, .86, "Optimize the prompt, then train the policy", fontsize=19, weight="semibold")
    columns = [
        (.04, "1  Select the guidance", "Compare five written prompts\non development tasks."),
        (.37, "2  Generate attempts", "Keep the selected prompt\nin the rollout context."),
        (.70, "3  Update with RL", "Remove it from the training context.\nTest without it, too."),
    ]
    for x, title, description in columns:
        ax.plot([x, x + .26], [.65, .65], color=CYAN if x < .6 else BLUE, lw=2)
        ax.text(x, .52, title, fontsize=14, weight="semibold")
        ax.text(x, .26, description, fontsize=12, color=MUTED, linespacing=1.5)
    for x in [.325, .655]:
        ax.annotate("", xy=(x + .024, .48), xytext=(x - .018, .48),
                    arrowprops={"arrowstyle": "->", "color": MUTED, "lw": 1.4})
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    save(fig, "prompt-rl-method")


def outcome():
    fig, ax = plt.subplots(figsize=(11.6, 4.4))
    fig.subplots_adjust(left=.29, right=.91, top=.69, bottom=.15)
    fig.text(.04, .92, "The prompt helped; the benefit did not transfer through RL",
             fontsize=17, weight="semibold")
    fig.text(.04, .82, "R2E-Gym · Development-set pass@1 · 120 tasks, four attempts each",
             fontsize=11, color=MUTED)
    labels = ["Starting policy", "Starting policy + prompt", "Prompt-guided RL", "Ordinary RL"]
    values = [30.2, 44.6, 29.8, 47.4]
    colors = [GRAY, CYAN, BLUE, BLUE]
    for y, (value, color) in enumerate(zip(values, colors)):
        ax.barh(y, value, color=color, height=.35)
        ax.text(value + .9, y, f"{value:.1f}%", va="center", fontsize=13, color=INK)
    ax.set_yticks(range(4), labels, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlim(0, 55)
    ax.set_xticks([0, 20, 40], ["0%", "20%", "40%"], fontsize=11, color=MUTED)
    ax.tick_params(length=0, pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=GRID, linewidth=.8)
    save(fig, "prompt-rl-outcome")


if __name__ == "__main__":
    method()
    outcome()
