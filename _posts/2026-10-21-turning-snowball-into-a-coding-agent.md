---
layout: research
color_theme: snowball
title: "Turning Snowball into a Coding Agent: A Post-Training Journey"
description: "Early experiments, infrastructure fixes, and results from improving Snowball with SFT and RL."
excerpt: "My first few weeks working on Snowball’s coding-agent capabilities: getting RL working, adding demonstrations, and trying SFT followed by RL."
date: 2026-10-21
published: true
reading_time: 14
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

Below, we share what those experiments taught us about developing a coding agent, from inspecting inherited habits and getting RL working reliably to testing what additional demonstrations could contribute. Additional SFT brought the largest overall gains on the newer Snowball checkpoint, while RL afterward showed encouraging improvements on TBLite and mixed results elsewhere. The table shows one of those recipes.

<div class="table-wrap" markdown="1">

| Model, evaluated with Terminus-2 | SWE-bench Verified random-100 | Terminal-Bench 2.1 | OpenThoughts-TBLite |
|---|---:|---:|---:|
| [Snowball 09-21](https://github.com/marin-community/marin/issues/8089), starting checkpoint | 12.8% | 7.2% | 11.5% |
| Base + RL | 30.5% | **18.8%** | **45.1%** |
| Additional coding-agent SFT | 46.5% | 18.8% | 33.0% |
| SFT + RL coding expert | **47.0%** | 18.2% | 37.0% |

</div>



<nav class="research-toc" aria-label="Article contents">
<div class="research-toc-title">Contents</div>
<ul>
<li><strong><a href="#starting-with-reinforcement-learning">Starting with RL</a></strong><span class="toc-sub"><a href="#the-pre-rl-probe">Pre-RL probe</a> · <a href="#following-the-behavior-back-to-sft">SFT habits</a> · <a href="#diagnosing-entropy-collapse">Entropy collapse</a> · <a href="#fixing-the-training-stack">Stack fixes</a> · <a href="#what-rl-improved">Results</a> · <a href="#speeding-up-rollouts-without-retraining-the-draft">Speculative decoding</a></span></li>
<li><strong><a href="#strengthening-the-starting-policy-with-sft">Adding SFT before RL</a></strong><span class="toc-sub"><a href="#earlier-experiments-on-the-stage-3-checkpoint">Earlier experiments</a> · <a href="#additional-sft-on-the-09-21-checkpoint">09-21 SFT</a> · <a href="#one-exploration-learning-to-recover-with-a-teacher">Teacher-guided recovery</a></span></li>
<li><strong><a href="#rl-from-the-sft-checkpoints">RL from the SFT checkpoints</a></strong></li>
<li><strong><a href="#reflections">Reflections</a></strong></li>
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

Early RL runs improved and then lost their held-out gains while training reward kept rising. In one run, output entropy fell to about half its starting value. Snowball's predictions were becoming increasingly concentrated. Lowering the learning rate delayed the failure without resolving it.

The problem was a disagreement between how we generated rollouts and how we trained on them. The rollout engine used top-p and top-k sampling, which removed lower-probability tokens and redistributed their probability among the remaining choices. But it reported probabilities from before that filtering. A token with 5% probability could, for example, be sampled 10% of the time after filtering while still being reported as 5%.

Those probabilities matter because the trainer uses them to correct for differences between the policy generating the data and the policy being updated. Here, that correction did not describe the actual sampling process. Tokens outside the retained set also had no chance of being explored. As predictions became more concentrated, filtering could narrow the available choices further.

Our engine-versus-trainer checks looked healthy because both used the same unfiltered probabilities. Those checks established numerical agreement, but did not check whether the probabilities matched the distribution that actually generated the tokens.

Disabling top-p and top-k removed the exploration restriction and made sampling agree with the full-distribution probabilities used by the trainer. The run continued past the earlier collapse point, with entropy staying near its starting level.

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

## Strengthening the Starting Policy with SFT

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

## RL from the SFT Checkpoints

We next ran GRPO on a mixture of R2E-Gym repository tasks and TMax terminal tasks. The motivation was to let the demonstration-trained policies learn from their own attempts and task rewards. The mixed task pool contained 3,832 tasks. A held-out set of 426 tasks was excluded from band selection and training.

We probed the vanilla CalibForge epoch-7 model eight times per task and selected tasks it solved between one and six times. This produced a training band of 1,833 tasks, which all three SFT arms used. A separate probe of the 09-21 starting checkpoint produced a smaller band of 1,082 tasks. That probe had incomplete task coverage, so the band sizes are descriptive rather than a controlled measurement of how much SFT expanded capability. Many tasks in the SFT band were tasks the starting model failed in all eight attempts.

The RL runs used the same core recipe: batches of 64 tasks with eight attempts each, a learning rate of 5e-7, and a 64k context window. The figure compares the 09-21 starting model with each additional SFT recipe and its RL continuation. Vanilla denotes ordinary teacher-demonstration SFT.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/sft-rl-stages.png?v=updated-rl-results' | relative_url }}"><img src="{{ '/assets/img/snowball/sft-rl-stages.png?v=updated-rl-results' | relative_url }}" alt="Across three benchmarks, the 09-21 starting model is shown in gray, three additional SFT recipes in cyan, and each recipe followed by RL in blue. The blue bar below the starting model shows Base + RL. TBLite scores rise after RL in all three SFT recipes, while SWE-bench changes are mixed." width="2951" height="1512" loading="lazy"></a>
<figcaption>Pass@1 point estimates with Terminus-2. “Starting model” is the 09-21 general-SFT checkpoint. Blue bars follow 30 RL updates, including RL directly from the starting model.</figcaption>
</figure>

TBLite scores rose after RL across all three additional SFT recipes. SWE-bench changes were mixed, while Terminal-Bench scores changed less. RL directly from the 09-21 starting checkpoint reached 30.5% on SWE-bench, 18.8% on Terminal-Bench 2.1, and 45.1% on TBLite.

Most of the selected training tasks were TMax terminal tasks, which may help explain why TBLite moved most, though we have not tested that explanation.

## Reflections

One result I keep coming back to is that our engine-versus-trainer checks passed while the sampling probabilities were still wrong. Both sides agreed on the same unfiltered distribution, so agreement never tested the assumption we actually needed. When a run loses held-out performance, I would now check what each diagnostic establishes before changing the learning rate again. A healthy-looking check can leave an important part of the training loop untested.

The behavioral results also changed what I would look for in a better checkpoint. RL helped Snowball finish more often, but in one early recipe, a completion claim became less trustworthy. Later runs used fewer repository tests even as task success improved. Those observations leave a specific weakness to investigate. Can we improve how the agent checks its work and responds to failed checks, while preserving the gains in solving tasks within budget?

Additional SFT gave us much stronger starting policies, but these experiments do not tell us which demonstrations were responsible. Relay SFT tried to teach recovery from states Snowball actually reached. That remains an interesting hypothesis, especially given the gap between locating a fix and carrying it through, but the corrected comparisons did not establish a consistent advantage over ordinary demonstrations. A useful follow-up would compare demonstrations for a specific behavior, such as recovery after a failed edit, and check whether that behavior improves on held-out tasks.

Marin’s open data made this kind of investigation possible. We could follow an odd editing habit back to the instructions that taught it. That is the kind of connection I would like to make more often in future experiments. Reading traces already helped us form hypotheses; the next step is to test whether acting on those diagnoses produces improvements that carry beyond the examples we inspected.

## What you can reuse

- **Models:** earlier [SFT](https://huggingface.co/laion/snowball-67b-a2b-relay-sft-allkimi-step1203) and [RL](https://huggingface.co/laion/snowball-67b-a2b-rl-r2egym-newstack-step24) checkpoints. The new SFT + RL checkpoints above are not yet uploaded.
- **Data:** [Relay demonstrations](https://huggingface.co/datasets/laion/calibforge-relay-traces) and [R2E-Gym environment artifacts](https://huggingface.co/datasets/laion/r2egym-build-artifacts).
- **Decoding:** the [EAGLE-3 toolkit](https://github.com/lukedhlee/grugmoe-eagle3) and [draft model](https://huggingface.co/laion/snowball-64k-eagle3-draft-r2egym).
- **Stack fixes:** [token preservation in Harbor](https://github.com/marin-community/harbor/pull/122) and [probability accounting in MarinSkyRL](https://github.com/marin-community/MarinSkyRL/pull/519).

## Acknowledgements

Thank you to Bespoke Labs for supporting my coding AI plan, Alex Dimakis for his advice, and JSC and TACC for providing compute for this work.
