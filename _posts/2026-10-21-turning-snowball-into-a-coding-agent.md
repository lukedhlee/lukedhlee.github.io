---
layout: research
color_theme: snowball
title: "Turning Snowball into a Coding Agent: A Post-Training Journey"
description: "Early experiments, infrastructure fixes, and results from improving Snowball with SFT and RL."
image:
  path: /assets/img/snowball/snowball-coding-workshop.png
  alt: "Snowball learning to build and test code at a snowy mountain workshop."
  width: 1672
  height: 941
excerpt: "My first few weeks working on Snowball’s coding-agent capabilities: getting RL working, adding demonstrations, and trying SFT followed by RL."
date: 2026-10-21
published: true
reading_time: 18
authors:
  - name: Donghyun Lee
    bold: true
  - name: Harshit Varma
    url: https://hrshtv.github.io/
  - name: Alex Dimakis
    url: https://people.eecs.berkeley.edu/~alexdimakis/
---

<figure class="research-figure research-hero">
<a href="{{ '/assets/img/snowball/snowball-coding-workshop.png' | relative_url }}"><img src="{{ '/assets/img/snowball/snowball-coding-workshop.png' | relative_url }}" alt="Snowball learns its craft at a coding workbench, using an example book and terminal to build and test a glowing blue machine in a snowy mountain workshop." width="1672" height="941" loading="eager"></a>
</figure>

[Marin](https://marin.community/)’s ambition is to make the knowledge behind capable AI a public resource. That means sharing the data, experiments, and decisions that go into building models, including the ones that turn out to be wrong. This post shares our contribution to that effort through developing a coding-agent expert for Snowball, Marin’s 67B A2B mixture-of-experts model.

We collaborated with the Marin team, starting from an early checkpoint that had received general supervised fine-tuning across multiple domains. Our task was to develop its ability to solve coding and terminal tasks. We explored reinforcement learning, additional coding-agent SFT, and SFT followed by RL.

Some of the most interesting lessons came from reading the model’s attempts. Snowball could find the relevant function and describe a plausible fix, yet struggle to apply it. Other failures led us into the training system itself, where rising reward could hide falling held-out performance. Understanding these patterns helped us decide what to teach the model and what to fix around it.

Both SFT and RL substantially improved Snowball, with different strengths. **RL alone led on TBLite and was competitive on Terminal-Bench**, while **SFT + RL led on SWE-bench**. These results leave us asking how to divide training compute and tasks between SFT and RL. Below, we share the experiments and debugging that led us here.

<div class="table-wrap" markdown="1">

| Model, evaluated with Terminus-2 | SWE-bench Verified random-100 | Terminal-Bench 2.1 | OpenThoughts-TBLite |
|---|---:|---:|---:|
| [Snowball 09-21](https://github.com/marin-community/marin/issues/8089) | 12.8% | 7.2% | 11.5% |
| RL | 30.5% | **18.8%** | **45.1%** |
| SFT | 46.5% | 18.8% | 33.0% |
| SFT + RL | **47.0%** | 18.2% | 37.0% |

</div>



<nav class="research-toc" aria-label="Article contents">
<div class="research-toc-title">Contents</div>
<ul>
<li><strong><a href="#starting-with-reinforcement-learning">Starting with RL</a></strong><span class="toc-sub"><a href="#the-pre-rl-probe">Pre-RL probe</a> · <a href="#following-the-behavior-back-to-sft">SFT habits</a> · <a href="#diagnosing-entropy-collapse">Entropy collapse</a> · <a href="#fixing-the-training-stack">Stack fixes</a> · <a href="#what-rl-improved">Results</a> · <a href="#speeding-up-rollouts-without-retraining-the-draft">Speculative decoding</a></span></li>
<li><strong><a href="#training-with-sft-and-rl">Training with SFT and RL</a></strong><span class="toc-sub"><a href="#earlier-experiments-on-the-stage-3-checkpoint">Earlier experiments</a> · <a href="#additional-sft-on-the-09-21-checkpoint">09-21 SFT</a> · <a href="#one-exploration-learning-to-recover-with-a-teacher">Teacher-guided recovery</a> · <a href="#rl-on-the-mixed-task-pool">RL setup</a></span></li>
<li><strong><a href="#results-so-far">Results so far</a></strong></li>
<li><strong><a href="#what-did-sft-and-rl-actually-teach-snowball-looking-behind-the-scores">What did SFT and RL actually teach Snowball: looking behind the scores</a></strong></li>
<li><strong><a href="#conclusions">Conclusions</a></strong></li>
<li><strong><a href="#what-you-can-reuse">What you can reuse</a></strong></li>
<li><strong><a href="#acknowledgements">Acknowledgements</a></strong></li>
</ul>
</nav>

## Starting with Reinforcement Learning

### The Pre-RL Probe

Before running RL, it helps to understand what the starting model can already do. That means asking how many tasks it can sometimes solve, what its common failures are, and whether it lacks coding knowledge or struggles to put that knowledge into practice. The answers help decide whether to change the task pool, the training recipe, or the starting model.

I started with [Snowball's Stage-3 Nemotron-Terminal SFT checkpoint](https://github.com/marin-community/marin/issues/8225). Before training, I sampled R2E-Gym tasks eight times each and used coding agents to inspect the traces. Only 36% of fully sampled tasks had both successes and failures, the useful band for binary-reward GRPO.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/pre-rl-probe.png?v=clean-distribution' | relative_url }}"><img src="{{ '/assets/img/snowball/pre-rl-probe.png?v=clean-distribution' | relative_url }}" alt="Distribution of successes out of eight attempts: 62.9% of tasks had no successes and 36.2% had one to seven. Successful attempts more often edited the repository and ran a test." width="3060" height="1080" loading="lazy"></a>
<figcaption>The original probe: 4,206 tasks sampled eight times, before the terminal-screen fix. Dots show observed percentages and the curve joins the discrete bins. Right: 8,641 attempts on tasks solved one to three times in eight tries, with overlapping behavior categories. These historical measurements are separate from the later RL evaluations.</figcaption>
</figure>

In thirteen of fifteen closely read tasks with both successful and failed attempts, the losers reached the same file, usually the same function, as the winner. Often they could describe the fix. Getting it into the repository was another matter.

<aside class="research-reports" markdown="1">
[Full report](https://claude.ai/artifact/TefbJfphaTBsYFtFgrNgMY).
</aside>

### Following the Behavior Back to SFT

One recurring failure had a surprisingly specific source. Snowball wrote SEARCH/REPLACE blocks into `/app/solution.patch`, then tried to apply them with Unix `patch`, which does not understand that format. Its Stage-3 SFT data contained 31,661 single-file SWE traces whose instructions explicitly requested that path and format. Here the agent had a full repository and a shell, with no tool to consume those blocks. It was reproducing a procedure from a different task setup.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/sft-behavior-origin.png' | relative_url }}"><img src="{{ '/assets/img/snowball/sft-behavior-origin.png' | relative_url }}" alt="The patch-file and SEARCH/REPLACE behaviors appeared in the upstream SFT traces." width="1728" height="720" loading="lazy"></a>
<figcaption>The SWE slice explicitly requested the same path and edit format that Snowball later used in the wrong setting. These behaviors can overlap.</figcaption>
</figure>

The corpus also retained unfinished trajectories: 70% of its medium-difficulty synthetic traces never declared completion. That was consistent with Snowball's tendency to keep working until its window filled, though it did not isolate the cause. Marin's commitment to open training data made it possible to inspect what Snowball had seen and better understand the habits it brought into these tasks.

<aside class="research-reports" markdown="1">
[Full report](https://claude.ai/artifact/TefbJfphaTBsYFtFgrNgMY).
</aside>

### Diagnosing Entropy Collapse

Those traces helped explain Snowball’s starting behavior. Once RL began, another pattern emerged: held-out performance improved and then fell while training reward kept rising. Output entropy dropped to roughly half its starting value. Lowering the learning rate delayed the collapse without fixing it.

We found a mismatch in the rollout probabilities. Top-p and top-k filtering changed which tokens could be sampled, but the engine reported their probabilities before filtering. The trainer used those reported probabilities to correct for differences between the rollout and training policies, so its correction did not match how the tokens were actually sampled.

Our engine-versus-trainer checks missed this because both sides used the same unfiltered probabilities. They checked numerical agreement, but not whether those probabilities described the sampling process.

Disabling top-p and top-k aligned sampling with the probabilities used for training and restored full-distribution exploration. Entropy stayed near its starting level beyond the earlier collapse point.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/entropy-debugging.png' | relative_url }}"><img src="{{ '/assets/img/snowball/entropy-debugging.png' | relative_url }}" alt="Filtered sampling reduced entropy to about half its initial value, while full-distribution sampling stayed near its starting level." width="1760" height="880" loading="lazy"></a>
<figcaption>The same starting model and learning rate, changing only the sampling settings. Each curve is normalized to its own first update. Entropy stayed stable through update 38 with full-distribution sampling. Curves reproduced from the first RL report.</figcaption>
</figure>

<aside class="research-reports" markdown="1">
[Full report](https://gist.github.com/lukedhlee/9c19fd9288a94ecfd1dbd6906b0a8dda).
</aside>

### Fixing the Training Stack

Some apparent model failures were bugs in the system around it. I found and fixed problems that the loss curve did not reveal:

<div class="table-wrap" markdown="1">

| Problem | What changed |
|---|---|
| KL was logged but contributed no gradient | Restored gradients through the penalty ([#517](https://github.com/marin-community/MarinSkyRL/pull/517)). |
| Importance-sampling probabilities did not match temperature-scaled training | Corrected the probability accounting ([#519](https://github.com/marin-community/MarinSkyRL/pull/519)); also removed unsupported sampling filters. |
| Recovery after an over-long turn lost the sampled token chain | Preserved exact tokens so the rollouts remained trainable ([#122](https://github.com/marin-community/harbor/pull/122)). |
| Long terminal history produced a frozen screen | Captured a recent window of history ([#125](https://github.com/marin-community/harbor/pull/125), used in these runs; closed without merging). |
| Verification timeouts turned finished attempts into reward-zero training samples | Increased the verifier budget and excluded timed-out samples from training. |

</div>

The recovery bug in [harbor #122](https://github.com/marin-community/harbor/pull/122) illustrates why **token-in-token-out (TITO)** matters. When a turn hit its output limit, recovery could re-render the conversation and change tokens the model had already sampled. TITO keeps the exact sampled token IDs for both training and later turns. Consider a toy tokenizer:

```text
Model samples:          ["hel", "lo"]   (two tokens)
Decoded text:           "hello"
Text re-tokenized:      ["hello"]       (one different token)
```

The text looks identical, but the trainer now sees a token the model never sampled. The two original token probabilities no longer line up with the training sequence, breaking the probability accounting RL relies on. The fix preserved the prompt and completion token IDs through recovery, so the next request continued from the exact sampled sequence. Mercor and SkyRL discuss TITO in their [agent-training guide](https://www.mercor.com/blog/training-frontier-knowledge-work-agents-a-397b-rl-training-guide-with-skyrl/).

<aside class="research-reports" markdown="1">
[Full report](https://gist.github.com/lukedhlee/ad3a95fccccb527db66619d6b3667e7d).
</aside>

### What RL Improved

In the first held-out evaluation, RL nearly doubled pass@1 from 8.7% to 16.6%. Before RL, 91% of attempts exhausted the 64k context window while the agent was still working. One RL recipe brought that down to 56%, making it more likely that useful work reached a result within the window.


<figure class="research-figure">
<a href="{{ '/assets/img/snowball/early-rl-labeled.png?v=slim-bars' | relative_url }}"><img src="{{ '/assets/img/snowball/early-rl-labeled.png?v=slim-bars' | relative_url }}" alt="Starting model and two RL checkpoints, labeled by their single-attempt success and task coverage." width="1728" height="880" loading="lazy"></a>
<figcaption>The same 191 held-out tasks, eight attempts each. Both RL recipes also solved tasks the base missed in all eight attempts; this does not mean the base could never solve them.</figcaption>
</figure>

The early RL recipes also made source edits and test runs more common. Finishing more often came with different trade-offs. In the checkpoint with higher pass@1, correctness among attempts that declared completion fell from 39% to 29%. The checkpoint with higher pass@8 increased completion while keeping that figure around 41%. RL could teach the agent to finish without reliably teaching it to judge whether the work was correct. That judgment needed to be checked separately from the headline score.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/rl-behavior-changes.png?v=results-labels' | relative_url }}"><img src="{{ '/assets/img/snowball/rl-behavior-changes.png?v=results-labels' | relative_url }}" alt="Early RL behavior: more completion claims, fewer context overflows, more source edits and pytest runs. Completion accuracy fell for one RL checkpoint and held near the starting model for the other." width="1760" height="960" loading="lazy"></a>
<figcaption>The same 191-task evaluation as the first results above, with eight attempts per task. Gray is the starting model. Of the two RL checkpoints, blue has higher pass@1 and orange has higher pass@8. The last row is conditional on declaring completion.</figcaption>
</figure>

Rebuilding the stack improved the result further. On a later evaluation set, the new stack scored about ten points above the old one, using half as many nodes.


<figure class="research-figure">
<a href="{{ '/assets/img/snowball/stack-comparison.png' | relative_url }}"><img src="{{ '/assets/img/snowball/stack-comparison.png' | relative_url }}" alt="Old versus new training stack on two held-out R2E-Gym splits." width="1728" height="880" loading="lazy"></a>
<figcaption>Matched comparison under the older probe setup: 49.9% → 60.0% on new tasks in repositories used for RL, and 50.3% → 59.5% on tasks in repositories excluded from RL entirely. This is a separate evaluation from the early results above. Several changes landed together, so the gain belongs to the package.</figcaption>
</figure>

In the later 441-task probes, successful attempts took a median of 15 turns, down from 22, and exact repeats of the previous command fell from 2.19 to 0.48 per 100 turns. Verification shifted toward self-written repro/check scripts, while use of the repository's tests fell.

This was more than learning to announce completion. The grader already credited correct fixes left in the repository when the context ran out. RL made it more likely that useful work reached a correct fix within the budget. Verification remained a weakness: repository-test use fell, and wrong submissions became more common.


On SWE-bench, the selected RL checkpoint improved from the starting model's 12 correct tasks to 23 of 100. Terminal-Bench did not show a comparable gain.

One tempting context fix also failed. Removing earlier reasoning freed about a third of the window, but the model took more turns, spent 48% more tokens per rollout, and increasingly stopped reasoning. Editing the history changed how it behaved. The score barely moved.

<aside class="research-reports" markdown="1">
Full reports: [First RL results](https://gist.github.com/lukedhlee/9c19fd9288a94ecfd1dbd6906b0a8dda), [Old versus new stack](https://gist.github.com/lukedhlee/01897efa3ae7c474732c61d35150a43a), [Why RL improved](https://gist.github.com/lukedhlee/ad3a95fccccb527db66619d6b3667e7d), [Behavior and optimizer experiments](https://gist.github.com/lukedhlee/9747e8eb423f23ca6627199c2532de47), [Reasoning-history ablation](https://gist.github.com/lukedhlee/565d259cda4c396db9bcba027322186e).
</aside>

### Speeding Up Rollouts Without Retraining the Draft

Long agent rollouts also made each experiment expensive. The pre-RL probe supplied training data for a small EAGLE-3 draft: it proposes several tokens, and Snowball verifies them. Adapting the pilot draft on 2,177 of Snowball's own rollouts improved per-stream speed by another 12–15% in two same-node repeats. The probe was useful twice, first for inspecting the policy and choosing tasks, then for making the next experiments faster. In matched five-node runs, three RL updates took about 31 minutes instead of 44, making the updates **1.42× faster**.

I also checked whether the draft would need refreshing as RL changed Snowball. The same frozen draft held through 60 updates, with no decline in accepted tokens per verification step. At update 36, 86% of Snowball's weights were still bit-identical to the starting checkpoint. That small change was consistent with the draft remaining useful despite the improvement in agent performance. The draft needed training once, then no retraining during that run.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/speculative-decoding.png?v=balanced-spacing' | relative_url }}"><img src="{{ '/assets/img/snowball/speculative-decoding.png?v=balanced-spacing' | relative_url }}" alt="A frozen speculative-decoding draft accelerated RL updates and maintained acceptance through 60 updates." width="2772" height="1188" loading="lazy"></a>
<figcaption>The timing comparison and the 60-update acceptance trace come from separate experiments. A frozen draft holding here does not establish that it will hold under every RL recipe.</figcaption>
</figure>

<aside class="research-reports" markdown="1">
Full reports: [Toolkit and timing](https://gist.github.com/lukedhlee/b161a78a29e2c42b08a157aaaea6438b), [Frozen draft during RL](https://gist.github.com/lukedhlee/bd14e461b13557a3a541e721fcda643e), [Initial pilot](https://gist.github.com/lukedhlee/f02dc181b7383e47908091b565cf8619).
</aside>

<details markdown="1">
<summary>Another exploration: training an editing prompt into the weights</summary>

A short edit-discipline prompt improved the base by 9–14 points on a development set. I tried transferring that guidance into the weights by keeping it during rollouts and removing it from the context used for the weight update. Without the guidance, the trained model scored 29.8%, against 30.2% for the base. The prompted-versus-unprompted likelihood gap shrank 85%, but task success did not improve.

The turn-by-turn analysis was more revealing. When the same trajectories were rescored with and without the guidance, the largest likelihood difference was on the first action. By turns four to six, that gap was already small even in the starting model. Earlier actions were held fixed, so the history could still carry forward the prompt's initial influence.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/prompt-distillation.png' | relative_url }}"><img src="{{ '/assets/img/snowball/prompt-distillation.png' | relative_url }}" alt="The likelihood difference from retaining the editing guidance was largest on the first turn and much smaller on later turns, both before and after distillation." width="1760" height="832" loading="lazy"></a>
<figcaption>The same 152 prompted trajectories, rescored with and without the guidance. The gap measures the prompt's additional influence on the likelihood of the same actions, with the earlier history held fixed.</figcaption>
</figure>

That raises a question about when guidance is most useful. Later turns are where the agent needs to verify an edit, respond to a failed check, and decide whether the work is complete. One direction worth testing is to nudge the policy at those moments, with targeted reminders tied to what just happened. Combining prompt and weight optimization remains worth exploring, as in [Fast-Slow Training (FST)](https://arxiv.org/abs/2605.12484) and [P²O](https://arxiv.org/pdf/2603.21877). These experiments tested only one fixed initial prompt, leaving guidance across turns as an open direction.

<aside class="research-reports" markdown="1">
[Full report](https://gist.github.com/lukedhlee/edb2f69d38ed089f71f74ff711281807).
</aside>

</details>

These experiments brought us back to the starting policy. RL could reinforce useful attempts, but demonstrations offered a way to teach behaviors that Snowball rarely produced on its own. We wanted to see whether additional SFT could give RL a better place to start.

## Training with SFT and RL

For binary-reward GRPO, a group of attempts that all fail has no reward difference to learn from. Additional SFT might make more tasks sometimes solvable, giving RL more useful attempts to reinforce. That was our motivation for adding demonstrations, rather than continuing to change only the RL recipe.

### Earlier Experiments on the Stage-3 Checkpoint

On the older Stage-3 checkpoint, I tried additional SFT on a mixture of OpenThoughts-Agent traces, instruction-following traces, and successful synthesized-task traces, then ran GRPO from that SFT checkpoint.

SFT raised SWE-bench from 14.5% to 24.1%; another 30 GRPO updates brought it to **30.7%**. RL directly from the starting checkpoint scored 25.0% in its earlier evaluation. SFT could provide a better starting policy, and RL could improve it further. Terminal-Bench still showed no improvement.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/ota-sft-rl-swe.png?v=crisp-blue' | relative_url }}"><img src="{{ '/assets/img/snowball/ota-sft-rl-swe.png?v=crisp-blue' | relative_url }}" alt="SWE-bench Verified random-100 on the older Stage-3 checkpoint: starting model 14.5%, SFT 24.1%, RL only 25.0%, and SFT followed by RL 30.7%, with 95% Wilson intervals." width="2052" height="1007" loading="lazy"></a>
<figcaption>All rows use Eval Policy v0.1. The starting model, SFT, and SFT→RL results pool three evaluation runs; RL-alone is one earlier run at lower concurrency. Treat its comparison as approximate rather than a paired test. Lines show 95% intervals.</figcaption>
</figure>

<aside class="research-reports" markdown="1">
Full reports: [SFT versus RL versus SFT→RL](https://github.com/marin-community/marin/issues/9225), [training recipes and launch configs](https://gist.github.com/lukedhlee/d152f86a58e8619a988361e1502f9e55).
</aside>

### Additional SFT on the 09-21 Checkpoint

We next moved to Marin’s newer [09-21 checkpoint](https://github.com/marin-community/marin/issues/8089), which had already received general SFT. To give RL a stronger starting policy, we added coding-agent SFT using [Qwen3.8-27B traces on CalibForge tasks](https://huggingface.co/datasets/laion/calibforge-relay-traces), with and without [Kimi coding demonstrations](https://huggingface.co/datasets/open-athena/Kimi-2.5-swesmith-sandboxes-with_tests-oracle_verified_120s-maxeps-32k).

Additional SFT improved the benchmark scores substantially. For example, vanilla CalibForge + Kimi reached 46.5% on SWE-bench, compared with 12.8% for the starting checkpoint. We then tested whether RL could improve these policies further.

### One Exploration: Learning to Recover with a Teacher

We also explored a different kind of demonstration. A teacher’s own solution may not show how to recover from the mistakes Snowball actually makes. Could showing the student how a teacher continues from its own attempts provide a useful starting point for RL?

In **Relay SFT**, Snowball starts a task and Qwen3.8-27B intervenes after an invalid action, near the context limit, or when Snowball claims completion. The teacher repairs an action, continues the attempt, or checks the work. A completion claim is a reason to check, rather than proof of a mistake. During SFT, student turns provide context and only teacher turns contribute to the loss.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/relay-timeline.png?v=crisp-colors' | relative_url }}"><img src="{{ '/assets/img/snowball/relay-timeline.png?v=crisp-colors' | relative_url }}" alt="Teacher-only SFT uses teacher-generated histories. Relay SFT trains teacher actions following the student's attempts." width="2409" height="957" loading="lazy"></a>
<figcaption>Student turns (S) provide context without training loss. Local repairs (R) and teacher continuations (T) are trained.</figcaption>
</figure>

This was one exploration alongside ordinary SFT. Earlier comparisons looked promising, but later comparisons with corrected training precision and expert capacity did not establish a consistent advantage over vanilla SFT. Whether student-conditioned demonstrations produce a better starting policy for RL remains an open question.

<aside class="research-reports" markdown="1">
Earlier reports: [Relay design](https://gist.github.com/lukedhlee/d8fc1454ed134eff585448c4982458c9), [Initial results, before the corrected comparisons](https://gist.github.com/lukedhlee/8669f5b6f97e4e3bae72344a8fd51f4b). These historical results should be read separately from the newer experiments below.
</aside>

### RL on the Mixed Task Pool

We next ran GRPO on a mixture of R2E-Gym repository tasks and TMax terminal tasks. The motivation was to let the demonstration-trained policies learn from their own attempts and task rewards. The mixed task pool contained 3,832 tasks, comprising 1,104 R2E-Gym tasks and 2,728 TMax tasks. A held-out set of 426 tasks was excluded from band selection and training.

We probed the vanilla CalibForge epoch-7 model eight times per task and selected tasks it solved between one and six times. This produced a learnable band of 1,833 tasks, comprising 453 R2E-Gym tasks and 1,380 TMax tasks. All three additional-SFT models used this band for RL.

We ran 30 GRPO updates using batches of 64 tasks with eight attempts each, a learning rate of 5e-7, and a 64k context window. For comparison, we also trained Snowball 09-21 directly with RL.

## Results So Far

The figure compares Snowball 09-21, direct RL, and each additional SFT recipe before and after RL. Vanilla denotes ordinary teacher-demonstration SFT.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/sft-rl-stages.png?v=consistent-recipe-names' | relative_url }}"><img src="{{ '/assets/img/snowball/sft-rl-stages.png?v=consistent-recipe-names' | relative_url }}" alt="Across three benchmarks, the 09-21 starting model is shown in gray, three additional SFT recipes in cyan, and each recipe followed by RL in blue. The blue bar below the starting model shows RL directly from Snowball 09-21. TBLite scores rise after RL in all three SFT recipes, while SWE-bench changes are mixed." width="2951" height="1512" loading="lazy"></a>
<figcaption>Pass@1 point estimates with Terminus-2. “Snowball 09-21” is the general-SFT starting checkpoint. Blue bars follow 30 RL updates, including RL directly from the starting model.</figcaption>
</figure>

RL directly from the 09-21 starting checkpoint reached 30.5% on SWE-bench, 18.8% on Terminal-Bench 2.1, and 45.1% on TBLite. Its TBLite score exceeded every additional SFT recipe, including their RL continuations, and its Terminal-Bench score was close to the best continuation at 19.3%. Additional SFT followed by RL still produced the highest SWE-bench score at 47.0%. These results make the choice of starting policy more interesting than the SFT scores alone suggested.

## What Did SFT and RL Actually Teach Snowball: Looking Behind the Scores

RL directly from Snowball 09-21 matched or came close to the SFT + RL models on terminal tasks, despite skipping the additional demonstrations. We wanted to understand what those demonstrations contributed. Did they teach new knowledge, or change how Snowball approached and executed the work? We used coding agents to compare trajectories and inspect where the two routes succeeded or failed.

### SFT’s advantage on SWE-bench

On SWE-bench, additional coding-agent SFT with CalibForge + Kimi reached **46.5%**, compared with **30.5% for direct RL**. Following that SFT with RL brought the score to **47.0%**. The traces show where the stronger results went with better execution.

Both direct RL and Kimi SFT nearly always opened a file touched by the reference fix. The gap appeared afterward. Kimi SFT edited a relevant file **almost twice as often** and left the target tests passing **about 1.5 times as often** as direct RL.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/trace-swe-steps.png?v=connected-dots' | relative_url }}"><img src="{{ '/assets/img/snowball/trace-swe-steps.png?v=connected-dots' | relative_url }}" alt="SWE-bench execution milestones. Snowball 09-21 opens a relevant file in 78 percent of scored attempts and edits one in 38 percent. Vanilla Kimi SFT reaches 99 and 90 percent respectively and leaves the target tests passing in 51 percent of scored attempts. Direct RL also improves editing and target-test success." width="2952" height="1080" loading="lazy"></a>
<figcaption>Connected dots show each policy before and after RL. Values are shares of scored attempts, rather than the task-averaged benchmark scores above. A relevant file is one changed by the reference fix. Edit detection finds 80–89% of actual edits, so that column is a lower bound. These milestones are measured separately, rather than as conditional probabilities.</figcaption>
</figure>

The two routes found relevant files at similar rates. SFT’s higher SWE-bench score went with more attempts editing those files and leaving the target tests passing.

### Did SFT add knowledge?

The clearest knowledge difference appeared in `sqlite-db-truncate`, a Terminal-Bench 2.1 task. The rule that SQLite serial type 7 encodes an eight-byte IEEE double appeared in **12 of 13 SFT-family attempts** and **none of five starting-model or direct-RL attempts**. Direct RL finished using incorrect decoding rules and submitted wrong values. The SFT-family models consistently used the correct format knowledge, even though they did not always complete the task successfully.

RL also helped Snowball act on knowledge it already showed. The starting checkpoint identified the needed React version fix and wrote a correct SQL query, yet failed both tasks. After RL, Snowball successfully completed them. These gains suggest improved execution of existing ideas, rather than newly acquired knowledge.

The examples suggest two different kinds of improvement. In the database-recovery task, SFT-trained models consistently used a decoding rule that did not appear in the starting checkpoint’s attempts. In the React and SQL tasks, the starting checkpoint already showed the needed idea; RL helped turn it into a successful result.

### How the agents worked differently

We also compared 26 newly solved TBLite tasks where both routes succeeded. The median turn counts were similar, but direct RL used fewer output tokens and more shell commands. Reasoning made up about 42% of its output characters, compared with 69% for SFT + RL. Close reads suggested a pattern of shorter reasoning turns interleaved with more experiments, while SFT + RL often worked through more of the solution before acting.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/trace-working-style.png?v=turns-reasoning' | relative_url }}"><img src="{{ '/assets/img/snowball/trace-working-style.png?v=turns-reasoning' | relative_url }}" alt="On 26 shared TBLite successes, median time is 255 seconds for direct RL versus 604 for SFT plus RL; agent turns are 28.5 versus 31; output tokens are 35 thousand versus 92 thousand; reasoning shares are 42 versus 69 percent of output characters; shell commands are 61 versus 44." width="2952" height="882" loading="lazy"></a>
<figcaption>Medians of per-task medians over passing attempts, pooling the three SFT + RL recipes. Reasoning share is measured in output characters. These describe successful traces, not the cost of training or every attempt. The direction varied by task.</figcaption>
</figure>

Longer reasoning sometimes paid off. On parking-lot pathfinding, the vanilla Kimi SFT + RL model finished in roughly 100–120 seconds and 6–8 turns, while direct RL took 900–1,100 seconds and 68–83 turns. On shared Terminal-Bench 2.1 successes, direct RL was slower overall. There was no single working style that won everywhere.

### How the failures changed with training

The starting checkpoint often struggled to get actions executed at all. On TBLite, invalid action formats appeared in roughly four out of five attempts. Direct RL reduced that to about 2%, while additional SFT almost eliminated it. Both routes also made claims of completion without doing any work much rarer.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/trace-failure-modes.png?v=balanced-margins' | relative_url }}"><img src="{{ '/assets/img/snowball/trace-failure-modes.png?v=balanced-margins' | relative_url }}" alt="Five TBLite trace patterns before and after RL. Direct RL reduces invalid action formats from 81 to 2 percent of attempts. Turns reaching the token limit decline from 53 to 36 percent for CalibForge plus Kimi, but remain near 68 percent for CalibForge-only SFT. Summarization handoffs also decline for CalibForge plus Kimi. Unfinished shell commands persist, while failed submissions after successful self-checks become more common in the Kimi models." width="2952" height="1404" loading="lazy"></a>
<figcaption>Percentages use all scored attempts for each model, rather than only its failures. A single attempt can exhibit several patterns, including on attempts that eventually pass. The self-check mismatch counts only failed submissions. Labels come from the trace detectors and spot checks described in the failure-mode analysis.</figcaption>
</figure>

Additional SFT brought a different pattern. Long reasoning turns hit the per-turn token limit, and repeated summarization sometimes led agents to explore the same files again. RL reduced token-limit hits by roughly a third to a half in the Kimi models, but barely changed them in CalibForge-only SFT. The demonstrations affected which behaviors subsequent RL improved.

Some terminal mechanics remained troublesome. An unfinished heredoc or quote leaves the shell waiting for more input, so later commands become part of that input instead of executing. This still appeared in about one in five Kimi-model attempts before and after RL.

Verification also changed. In the Kimi models, failed submissions following an apparently successful self-check became roughly 1.5–2 times as common after RL. These agents were checking their work, but their checks missed requirements exercised by the hidden tests. This gives a more specific training target than simply asking the model to run more checks.

### Reward hacking

Some attempts satisfied the verifier without doing the requested work. Trace inspection found clear examples both before and after RL.

<div class="table-wrap" markdown="1">

| Benchmark | Task | Model | What it did | Why it passed |
|---|---|---|---|---|
| Terminal-Bench 2.1 | Implement a Scheme evaluator | Direct RL | Modified the supplied interpreter so the submission could delegate execution to a new primitive. | The verifier ran the modified interpreter. |
| OpenThoughts-TBLite | Repair a JavaScript network controller | CalibForge SFT | Replaced the controller with a toy simulation that printed `SYSTEM_STABLE`, removing the networking behavior it was supposed to repair. | The tests checked the success marker, exit code, and absence of error strings. |

</div>

The credited exploits each added only about half a percentage point to the model’s benchmark score. Direct RL also produced far more failed shortcuts than the other models, including fabricated outputs and copied answer files. All 31 of those attempts failed, so they contributed nothing to its gains.

The training audit found no confirmed case of fabrication earning reward. It found a different problem in R2E-Gym: the task repositories still exposed later Git commits containing the fixes. Agents read those fixes in 39 rewarded rollouts. This was already happening at the first RL update and did not become more common during training; its contribution to success remains unmeasured.

## Conclusions

SFT and RL both improved Snowball, with SFT + RL leading on SWE-bench and direct RL competitive on terminal tasks. Trace analysis connected those gains to changes in knowledge use and execution, and exposed evaluation reward hacking.

Agent-assisted trace analysis offers a direction for adaptive training. Agents could diagnose missing knowledge or unreliable execution, prepare targeted demonstrations and runnable environments, and test whether subsequent training improves the intended behavior on held-out tasks. The reward-hacking examples also motivate verifiers that distinguish solving a task from exploiting its evaluation.

How to allocate data and compute between SFT and RL remains open. SFT changes the policy and, with it, which tasks provide useful reward signals. A controlled comparison at fixed total compute could vary both the demonstration mix and the RL task pool, including the cost of generating data. This would help identify which tasks benefit from demonstrations, which support direct RL, and when to switch between them.

Domain-specific gains also raise a continual-learning question. Coding and terminal improvements alone do not reveal whether earlier abilities were preserved. Evaluating retention across the original domains could establish whether specialization requires rehearsal data, and how that data should share the training budget.

## What you can reuse

- **Models:** earlier [SFT](https://huggingface.co/laion/snowball-67b-a2b-relay-sft-allkimi-step1203) and [RL](https://huggingface.co/laion/snowball-67b-a2b-rl-r2egym-newstack-step24) checkpoints. The new SFT + RL checkpoints above are not yet uploaded.
- **Data:** [Relay demonstrations](https://huggingface.co/datasets/laion/calibforge-relay-traces) and [R2E-Gym environment artifacts](https://huggingface.co/datasets/laion/r2egym-build-artifacts).
- **Decoding:** the [EAGLE-3 toolkit](https://github.com/lukedhlee/grugmoe-eagle3) and [draft model](https://huggingface.co/laion/snowball-64k-eagle3-draft-r2egym).
- **Stack fixes:** [token preservation in Harbor](https://github.com/marin-community/harbor/pull/122) and [probability accounting in MarinSkyRL](https://github.com/marin-community/MarinSkyRL/pull/519).

## Acknowledgements

Thank you to Bespoke Labs for supporting my coding AI plan, Alex Dimakis for his advice, and JSC and TACC for providing compute for this work.
