"""Figures for the paired trace reads, 2026-10-28.

Source: OpenThoughts-Agent/ai_memory/active/snowball-blog/results/2026-10-27/
trace_analysis/reports/tblite.md, section 9. Labels summarize traces; they are
not verbatim model quotations. Shared-success metrics are medians of per-task
medians over passing attempts, not a matched-compute training comparison.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "assets/img/snowball"
BLUE, CYAN = "#2563eb", "#06a9df"
INK, MUTED, LINE = "#202e40", "#607084", "#e5edf5"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                     "axes.labelcolor": INK, "svg.fonttype": "path"})


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
    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.9))
    fig.subplots_adjust(left=.15, right=.96, top=.65, bottom=.23, wspace=.42)
    fig.text(.045, .90, "On shared successes, the routes worked differently",
             fontsize=22, weight="bold")
    fig.text(.045, .82, "26 TBLite tasks unsolved in the starting-model attempts; both routes later passed",
             fontsize=11, color=MUTED)
    for ax, (title, vals, limit, fmt) in zip(axes, [
        ("Time to finish", [255, 604], 780, lambda n: f"{n:,} s"),
        ("Output tokens", [35000, 92000], 120000, lambda n: f"{n // 1000}k"),
        ("Shell commands", [61, 44], 82, lambda n: str(n)),
    ]):
        ax.set_title(title, fontsize=15, weight="bold", loc="left", pad=24)
        ax.barh([1, 0], vals, color=[BLUE, CYAN], height=.28)
        for y, n in zip([1, 0], vals):
            ax.text(n + limit * .025, y, fmt(n), va="center", fontsize=13)
        ax.set_xlim(0, limit)
        ax.set_ylim(-.65, 1.65)
        ax.set_yticks([1, 0], ["RL", "SFT + RL"])
        ax.tick_params(axis="y", length=0, labelsize=12, pad=10)
        ax.set_xticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.axvline(0, color=LINE, lw=1)
    fig.text(.045, .10, "Medians of per-task medians on passing attempts. SFT + RL pools the three recipes.\n"
             "These are successful-trace summaries, not estimates of training efficiency or causal effects.",
             fontsize=10, color=MUTED, linespacing=1.6)
    save(fig, "trace-working-style")


if __name__ == "__main__":
    cases()
    working_style()
