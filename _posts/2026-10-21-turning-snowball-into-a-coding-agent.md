---
layout: research
title: "Turning Snowball into a Coding Agent: A Post-Training Journey"
description: "Experiments, fixes, and lessons from building a coding-agent expert with Marin."
excerpt: "Working with Marin’s post-training team to build Snowball’s coding expert, from RL debugging and SFT experiments to Relay SFT."
date: 2026-10-21
published: true
reading_time: 14
---

<figure class="research-figure research-hero">
<a href="{{ '/assets/img/snowball/snowball-opening.png' | relative_url }}"><img src="{{ '/assets/img/snowball/snowball-opening.png' | relative_url }}" alt="Snowball and a teacher untangle a winding blue and orange trail through a snowy landscape." width="1672" height="941" loading="eager"></a>
</figure>

I spent September and October working closely with Marin's post-training team on a coding-agent expert for Snowball. The Marin team handled mid-training and general SFT, producing the checkpoints I started from. My job was to get as much coding-agent performance as possible out of those models, with the aim of eventually distilling that expertise into the general model.

As the team produced new checkpoints, I tried different ways to build on them. I started with reinforcement learning, fixed problems in the training pipeline, inspected failed attempts and their training data, and tried additional SFT. That eventually led to collecting demonstrations with the student and teacher working on the same attempt.

The final experiments improved all three agent benchmarks I was tracking:

<div class="table-wrap" markdown="1">

| Model, evaluated with Terminus-2 | SWE-bench Verified random-100 | Terminal-Bench 2.1 | OpenThoughts-TBLite |
|---|---:|---:|---:|
| Snowball 09-21, starting checkpoint | 13.8% | 6.5% | 11.7% |
| Best recipe (Relay SFT + Kimi demonstrations) | **46.6%** | **18.8%** | **27.2%** |

</div>

*Pass@1, averaged over three evaluation runs. The recipe fine-tunes Grug Datakit 09-21 on Relay SFT and Kimi coding demonstrations. These results are from an experimental checkpoint; the final Snowball launch checkpoint is not yet specified.*

That result took several changes of approach. Snowball itself also changed during the work, so this is an account of building the expert across successive starting checkpoints.

<nav class="research-toc" aria-label="Article contents">
<div class="research-toc-title">Contents</div>
<ul>
<li><strong><a href="#starting-with-reinforcement-learning">Starting with RL</a></strong><span class="toc-sub"><a href="#the-pre-rl-probe">Pre-RL probe</a> · <a href="#following-the-behavior-back-to-sft">SFT habits</a> · <a href="#diagnosing-entropy-collapse">Entropy collapse</a> · <a href="#fixing-the-training-stack">Stack fixes</a> · <a href="#what-rl-improved">Results</a> · <a href="#speeding-up-rollouts-without-retraining-the-draft">Speculative decoding</a> · <a href="#finding-useful-training-tasks">Training tasks</a></span></li>
<li><strong><a href="#strengthening-the-starting-policy-with-sft">Strengthening the policy with SFT</a></strong><span class="toc-sub"><a href="#better-loss-worse-agent">The Kimi experiment</a> · <a href="#combining-sft-and-rl">SFT → RL</a></span></li>
<li><strong><a href="#relay-sft">Relay SFT</a></strong><span class="toc-sub"><a href="#bringing-in-the-teacher">Motivation and recipe</a> · <a href="#testing-the-idea">Testing the idea</a></span></li>
<li><strong><a href="#reflections">Reflections</a></strong></li>
<li><strong><a href="#what-you-can-reuse">What you can reuse</a></strong></li>
</ul>
</nav>

## Starting with Reinforcement Learning

### The Pre-RL Probe

I started with Snowball's Stage-3 Nemotron-Terminal SFT checkpoint. Before training, I sampled R2E-Gym tasks eight times each and used coding agents to inspect the traces. Only 36% of fully sampled tasks had both successes and failures—the useful band for binary-reward GRPO.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/pre-rl-probe.png' | relative_url }}"><img src="{{ '/assets/img/snowball/pre-rl-probe.png' | relative_url }}" alt="The pre-RL probe: 36% of tasks were sometimes solvable; successful attempts more often edited the repository and ran a test." width="2380" height="901" loading="lazy"></a>
<figcaption>The original probe, before the terminal-screen fix. The right panel compares attempts on tasks solved one to three times in eight tries. These historical measurements are not directly comparable with the later RL evaluations.</figcaption>
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

**Access to the SFT data made that behavior explainable.** The corpus also retained unfinished trajectories: 70% of its medium-difficulty synthetic traces never declared completion. That was consistent with Snowball's tendency to keep working until its window filled, though it did not isolate the cause. Later audits found task overlap too: held out from my RL run did not necessarily mean unseen in upstream SFT.

<aside class="research-reports" markdown="1">
[Full report](https://claude.ai/artifact/TefbJfphaTBsYFtFgrNgMY).
</aside>

### Diagnosing Entropy Collapse

Early runs could look promising and then lose their held-out gains. Training reward alone did not make the problem obvious. Output entropy—the spread of the model's next-token predictions—fell to about half its starting value in one run.

The rollout engine was filtering tokens with top-p and top-k, also called truncated sampling, but returning probabilities from the full distribution. The trainer's probability accounting did not describe how the tokens were sampled. Separately, the KL penalty was being logged without contributing a gradient.

Fixing KL alone did not rescue the run: entropy eventually rose to 1.75× its starting value instead, while held-out performance deteriorated. Removing the sampling filters produced runs whose entropy stayed near its starting level. Lowering the learning rate had delayed failure; checking the sampler and update code exposed what needed fixing.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/entropy-debugging.png' | relative_url }}"><img src="{{ '/assets/img/snowball/entropy-debugging.png' | relative_url }}" alt="Entropy fell under filtered sampling, rose when only KL was repaired, and stayed stable under full-distribution sampling." width="1760" height="880" loading="lazy"></a>
<figcaption>Solid lines omit a working KL penalty; dashed lines include one. Red uses filtered sampling; blue samples the full distribution. This comparison explains the two sampling recipes in the results below. Entropy was a diagnostic here, not a replacement for held-out evaluation.</figcaption>
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

**Token-in-token-out (TITO)** means keeping the exact token IDs the model sampled, both for training and for later turns. Consider a toy tokenizer:

```text
Model samples:          ["hel", "lo"]   (two tokens)
Decoded text:           "hello"
Text re-tokenized:      ["hello"]       (one different token)
```

The text looks identical, but the trainer now sees a token the model never sampled. The two original token probabilities no longer line up with the training sequence, breaking the probability accounting RL relies on. TITO preserves the original IDs instead of reconstructing them from text. Mercor and SkyRL discuss this in their [agent-training guide](https://www.mercor.com/blog/training-frontier-knowledge-work-agents-a-397b-rl-training-guide-with-skyrl/).

<aside class="research-reports" markdown="1">
[Full report](https://gist.github.com/lukedhlee/ad3a95fccccb527db66619d6b3667e7d).
</aside>

### What RL Improved

In the first corrected held-out evaluation, RL nearly doubled pass@1 from 8.7% to 16.6%. Much of the improvement came from completing useful work inside the context window.


<figure class="research-figure">
<a href="{{ '/assets/img/snowball/early-rl-labeled.png' | relative_url }}"><img src="{{ '/assets/img/snowball/early-rl-labeled.png' | relative_url }}" alt="Starting model versus RL with truncated and full-distribution sampling, with all colors labeled." width="1728" height="880" loading="lazy"></a>
<figcaption>The same 191 held-out tasks, eight attempts each. Both RL recipes also solved tasks the base missed in all eight attempts; this does not mean the base could never solve them.</figcaption>
</figure>

Rebuilding the stack improved the result further. On a later evaluation set, the new stack scored about ten points above the old one, using half as many nodes.


<figure class="research-figure">
<a href="{{ '/assets/img/snowball/stack-comparison.png' | relative_url }}"><img src="{{ '/assets/img/snowball/stack-comparison.png' | relative_url }}" alt="Old versus new training stack on two held-out R2E-Gym splits." width="1728" height="880" loading="lazy"></a>
<figcaption>Matched comparison under the older probe setup: 49.9% → 60.0% on new tasks in repositories used for RL, and 50.3% → 59.5% on tasks in repositories excluded from RL entirely. This is a separate evaluation from the early results above. Several changes landed together, so the gain belongs to the package.</figcaption>
</figure>

On SWE-bench, the selected RL checkpoint improved from the starting model's 12 correct tasks to 23 of 100. Terminal-Bench did not show a comparable gain.

One tempting context fix also failed. Removing earlier reasoning freed about a third of the window, but the model took more turns, spent 48% more tokens per rollout, and increasingly stopped reasoning. Editing the history changed how it behaved. The score barely moved.

<aside class="research-reports" markdown="1">
Full reports: [First RL results](https://gist.github.com/lukedhlee/9c19fd9288a94ecfd1dbd6906b0a8dda), [Old versus new stack](https://gist.github.com/lukedhlee/01897efa3ae7c474732c61d35150a43a), [Behavior and optimizer experiments](https://gist.github.com/lukedhlee/9747e8eb423f23ca6627199c2532de47), [Reasoning-history ablation](https://gist.github.com/lukedhlee/565d259cda4c396db9bcba027322186e).
</aside>

### Speeding Up Rollouts Without Retraining the Draft

Long agent rollouts also made each experiment expensive. I trained a small EAGLE-3 draft on Snowball's own rollouts: it proposes several tokens, and the main model verifies them. In matched five-node runs, three RL updates took about 31 minutes instead of 44—**1.42× faster**.

I also checked whether the draft would need refreshing as RL changed Snowball. The same frozen draft held through 60 updates. Its accepted tokens per verification step did not decline. The draft needed training once, then no retraining during that run. That made the speedup useful across the experiments rather than another model to maintain after each update.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/speculative-decoding.png' | relative_url }}"><img src="{{ '/assets/img/snowball/speculative-decoding.png' | relative_url }}" alt="A frozen speculative-decoding draft accelerated RL updates and maintained acceptance through 60 updates." width="1760" height="848" loading="lazy"></a>
<figcaption>The timing comparison and the 60-update acceptance trace come from separate experiments. A frozen draft holding here does not establish that it will hold under every RL recipe.</figcaption>
</figure>

<aside class="research-reports" markdown="1">
Full reports: [Toolkit and timing](https://gist.github.com/lukedhlee/b161a78a29e2c42b08a157aaaea6438b), [Frozen draft during RL](https://gist.github.com/lukedhlee/bd14e461b13557a3a541e721fcda643e), [Initial pilot](https://gist.github.com/lukedhlee/f02dc181b7383e47908091b565cf8619).
</aside>

### Finding Useful Training Tasks

For binary-reward GRPO, a group of attempts that all fail gives no relative reward signal. Neither does a group that all pass. I screened for tasks Snowball could solve sometimes, and later refreshed the curriculum as its capabilities changed.

The task pool grew from 1,003 to 1,247. Continuing the selected checkpoint for another 24 updates gave roughly three points on two held-out splits, but the uncertainty included no improvement. There was no matched continuation on the old pool, either, so this did not isolate the value of the new tasks.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/curriculum-refresh.png' | relative_url }}"><img src="{{ '/assets/img/snowball/curriculum-refresh.png' | relative_url }}" alt="A larger curriculum produced small gains whose confidence intervals included zero." width="1760" height="880" loading="lazy"></a>
<figcaption>Adding tasks and continuing training produced a positive but unresolved result. Both ranges include zero.</figcaption>
</figure>

Hard tasks were not always useful tasks. In a close read of 243 failed attempts across 39 tasks, 40 were attributed to task or sandbox defects. One issue requested a clear error message while its hidden test demanded exact wording. Another task's grader depended on a test helper changed by the reference patch. Two suspected misgrades lacked enough logs to confirm. **The 16% belongs to that audited sample, which over-represented difficult tasks.**

I also tried training a useful prompt into the weights. A short edit-discipline prompt improved the base by 9–14 points on a development set; 24 updates of context distillation left the unprompted model at base performance. The model made the prompted trajectories more likely without becoming more successful. That was an expensive distinction to learn.

The advice I was getting from experienced RL researchers became increasingly relevant: start with a stronger policy. My next experiments focused on SFT.

<aside class="research-reports" markdown="1">
Full reports: [Curriculum continuation](https://gist.github.com/lukedhlee/969b5bf852b9d1274ec980996232f7ba), [Unwinnable tasks](https://gist.github.com/lukedhlee/9eafb59ad72f08957f2e7fd551c249cb), [Prompt distillation](https://gist.github.com/lukedhlee/edb2f69d38ed089f71f74ff711281807), [Synthesized task-pool audit](https://gist.github.com/lukedhlee/6ad754b83d62536e1976777231c9754e).
</aside>

## Strengthening the Starting Policy with SFT

### Better Loss, Worse Agent

On the older starting checkpoint, Kimi SWE-smith demonstrations looked promising by loss: every one of 628 held-out trajectories became easier for the model to predict. SWE-bench went backwards, from 12 correct tasks to 7 of 100.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/kimi-fit-versus-agent.png' | relative_url }}"><img src="{{ '/assets/img/snowball/kimi-fit-versus-agent.png' | relative_url }}" alt="Held-out demonstration loss improved while SWE-bench task performance declined." width="1760" height="704" loading="lazy"></a>
</figure>

The transcripts were more informative than the loss. The model declared completion on 96 of 99 inspected trials; only 7% of those declarations were correct. A data audit found that 39% of the training traces were failed attempts that still ended by declaring completion. I had trained on those endings too. Subsequent RL recovered performance, but did not establish an advantage over starting RL from the original checkpoint.

<aside class="research-reports" markdown="1">
Full reports: [Kimi training and fit](https://gist.github.com/lukedhlee/5bbf6bdd183b7f9047790cbb61c55011), [Kimi SFT and subsequent RL](https://gist.github.com/lukedhlee/48185da748a200d44f7fe31431054e37), [Trace-level behavior](https://gist.github.com/lukedhlee/ec30c26faedd2a85baa3dd1d212d9efa).
</aside>

### Combining SFT and RL

The OpenThoughts experiments worked better. I fine-tuned the same older starting checkpoint on a mixture of OpenThoughts-Agent traces, instruction-following traces, and successful synthesized-task traces, then ran GRPO from that SFT checkpoint.

SFT raised SWE-bench from 14.5% to 24.1%; another 30 GRPO updates brought it to **30.7%**. RL directly from the starting checkpoint scored 25.0% in its earlier evaluation. SFT could provide a better starting policy, and RL could improve it further. Terminal-Bench still showed no improvement.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/ota-sft-rl-comparison.png' | relative_url }}"><img src="{{ '/assets/img/snowball/ota-sft-rl-comparison.png' | relative_url }}" alt="Starting model, OpenThoughts-mixture SFT, RL alone, and SFT followed by RL on SWE-bench and Terminal-Bench." width="1920" height="832" loading="lazy"></a>
<figcaption>All rows use Eval Policy v0.1. The starting model, SFT, and SFT→RL results pool three evaluation runs; RL-alone is one earlier run at lower concurrency. Treat its comparison as approximate rather than a paired test. Lines show 95% intervals.</figcaption>
</figure>

<aside class="research-reports" markdown="1">
Full reports: [SFT versus RL versus SFT→RL](https://github.com/marin-community/marin/issues/9225), [training recipes and launch configs](https://gist.github.com/lukedhlee/d152f86a58e8619a988361e1502f9e55).
</aside>

## Relay SFT

The next experiments started from Marin's newer Grug Datakit 09-21 checkpoint. Kimi demonstrations alone now reached 41.6% on SWE-bench, against 13.8% for that starting model under the three-run evaluation recipe. The earlier failure did not make the dataset universally unhelpful: the starting checkpoint and training recipe mattered.

### Bringing in the Teacher

Teacher-only SFT trains on histories generated by the teacher. At deployment, Snowball creates its own history: different commands, mistaken assumptions, invalid actions, and unfinished fixes. This mismatch is **exposure bias**. A demonstration of the teacher's clean solution may not show how to recover from the situations the student actually encounters.

That motivated **Relay SFT**. Snowball starts the task, and a stronger teacher responds to its attempt. The teacher repairs invalid actions, continues when the context-budget trigger fires, or checks the work when Snowball claims completion. For these experiments the teacher was Qwen3.8-27B. During SFT, Snowball's turns remain as context and only the teacher's turns contribute to the loss.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/relay-timeline.png' | relative_url }}"><img src="{{ '/assets/img/snowball/relay-timeline.png' | relative_url }}" alt="Teacher-only SFT trains on teacher-generated histories; Relay SFT includes student turns, local teacher repairs, and teacher continuations." width="2409" height="957" loading="lazy"></a>
<figcaption>Student turns (S) provide context without training loss. Local repairs (R) and teacher continuations (T) are trained. A completion claim prompts a check; it is not proof that the student made a mistake.</figcaption>
</figure>

<aside class="research-reports" markdown="1">
Full reports: [Initial relay design](https://gist.github.com/lukedhlee/d8fc1454ed134eff585448c4982458c9), [Behavior and knowledge evaluation](https://gist.github.com/lukedhlee/12f2e7293f332ce398655b4ec3e17b22), [Evaluation scheme](https://gist.github.com/lukedhlee/18b42f882bf099f6e89f901d6bd05e29).
</aside>

### Testing the Idea

The first small held-out CalibForge comparison did not establish a Relay SFT advantage. Later agent-benchmark experiments did. On matched CalibForge tasks, trace counts, and pass/fail outcomes, Relay SFT beat teacher-only SFT on all three benchmarks. The advantage repeated on a separate task pool, TMax.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/relay-matched-dots.png' | relative_url }}"><img src="{{ '/assets/img/snowball/relay-matched-dots.png' | relative_url }}" alt="Relay SFT and teacher-only demonstrations on matched CalibForge tasks, with and without the same Kimi coding data." width="2080" height="960" loading="lazy"></a>
<figcaption>Relay SFT helped where teacher-only traces taught much less. Kimi coding traces supplied additional software-repair gains; Relay SFT retained a substantial Terminal-Bench advantage with Kimi in both arms. Three-run means, with standard errors over tasks. Matching data did not make this an equal-compute comparison.</figcaption>
</figure>

Exposure bias motivated the recipe, but these experiments do not isolate it as the mechanism or show that the triggers beat random switching. The broader idea is related to [teacher continuations from student contexts](https://arxiv.org/abs/2607.04574v2) and [Relay-OPD](https://arxiv.org/abs/2607.26057).

<aside class="research-reports" markdown="1">
[Full report](https://gist.github.com/lukedhlee/8669f5b6f97e4e3bae72344a8fd51f4b).
</aside>

## Reflections

The starting policy mattered more than I appreciated at the beginning. GRPO needed tasks the current model could sometimes solve; SFT could change that starting point substantially, but a lower demonstration loss was not enough to tell whether it had helped.

Reading traces repeatedly changed the next experiment. It exposed inherited editing habits, broken probability accounting, and the difference between a model finishing an episode and producing a correct result. Having access to the upstream data and code made those investigations possible. Fixing the system and improving the policy were both part of building the expert.

Relay SFT grew out of that process. I wanted demonstrations that addressed what Snowball did after it had already started working. The resulting recipe improved all three evaluations, but the broader lesson I take from the work is to choose the next training intervention by inspecting the current model's attempts. As Marin supplied new checkpoints, I had to check those assumptions again.

## What you can reuse

The expert checkpoints are public: the [model in the opening table](https://huggingface.co/laion/snowball-67b-a2b-relay-sft-allkimi-step1203), a [similarly performing continuation](https://huggingface.co/laion/snowball-67b-a2b-relay-sft-acont-step999), and the [earlier RL checkpoint](https://huggingface.co/laion/snowball-67b-a2b-rl-r2egym-newstack-step24). The opening model's training set is in [calibforge-relay-traces](https://huggingface.co/datasets/laion/calibforge-relay-traces), under `terminus2_relay_sft`.

I also released an [EAGLE-3 toolkit](https://github.com/lukedhlee/grugmoe-eagle3) and [draft model](https://huggingface.co/laion/snowball-64k-eagle3-draft-r2egym). The frozen draft made matched RL updates arrive 1.42× sooner and held through 60 updates in the tested run. The [R2E-Gym Daytona artifacts](https://huggingface.co/datasets/laion/r2egym-build-artifacts) make 3,020 tasks available from eleven shared images. That pool includes tasks recovered from previously omitted repositories; passing the build gate does not certify that every task is well specified.

Several fixes went upstream to harbor ([#117](https://github.com/marin-community/harbor/pull/117), [#122](https://github.com/marin-community/harbor/pull/122), [#124](https://github.com/marin-community/harbor/pull/124), [#126](https://github.com/marin-community/harbor/pull/126)) and MarinSkyRL ([#517](https://github.com/marin-community/MarinSkyRL/pull/517), [#519](https://github.com/marin-community/MarinSkyRL/pull/519), [#542](https://github.com/marin-community/MarinSkyRL/pull/542)). Ben Feuer also added an upstream [probability-parity guardrail](https://github.com/marin-community/MarinSkyRL/pull/525) that rejects unsupported sampling filters.

David Hall recently wrote about the missing [posttraining data commons](https://marin.community/blog/2026/10/15/there-is-no-posttraining-data-commons/). Working on this expert made that problem concrete for me. A task needs a working environment, a meaningful requirement, and a grader worth trusting. A demonstration needs to teach behavior the student can use. Sharing those pieces, including the experiments that failed, is part of what I wanted to contribute to Marin.

<aside class="research-reports" markdown="1">
Full reports: [R2E-Gym on Daytona](https://gist.github.com/lukedhlee/b84aab48a67861b94d10ebc9b1ef77b8), [Evaluation policy](https://gist.github.com/lukedhlee/d152f86a58e8619a988361e1502f9e55), [Earlier experiment index (historical)](https://gist.github.com/lukedhlee/b509ed9dca3adf98414a9c7f93e27b2c).
</aside>
