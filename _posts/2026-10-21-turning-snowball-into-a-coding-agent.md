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

[Marin](https://marin.community/)’s ambition is to make the knowledge behind capable AI a public resource. That means sharing how models are built: the data, the experiments, and the decisions along the way, including the ones that turn out to be wrong. Other researchers can then see what happened, question it, and contribute their own ideas.

Training a coding agent still leaves plenty of room for that kind of work. We can give a model a repository, a terminal, and a task, but getting it to reliably finish the job is another matter. It needs to make changes, test them, and recover when something goes wrong. How best to teach these abilities is still an open question.

Over the last two months, I worked with Marin’s post-training team to develop a coding-agent expert for Snowball, Marin’s 67B A2B MoE model. Snowball had already been through general supervised fine-tuning, and our plan was to use reinforcement learning to develop its coding-agent capabilities, with the aim of eventually distilling that expertise into the general model.

As we ran experiments, we encountered limits in both the training system and what the starting policy could learn through RL. That brought additional SFT back into the picture and raised questions about how to combine the two. Which demonstrations would give RL a better starting point? When should the model learn from its own attempts, and when would examples from a stronger model help more?

This post follows that process, from the initial RL experiments to strengthening the policy with SFT, combining SFT with RL, and eventually collecting teacher guidance from Snowball’s own attempts. Each step changed our understanding of what the model needed to learn next.

The final experiments improved all three agent benchmarks I was tracking:

<div class="table-wrap" markdown="1">

| Model, evaluated with Terminus-2 | SWE-bench Verified random-100 | Terminal-Bench 2.1 | OpenThoughts-TBLite |
|---|---:|---:|---:|
| [Snowball 09-21](https://github.com/marin-community/marin/issues/8089), starting checkpoint | 13.8% | 6.5% | 11.7% |
| Best recipe (Relay SFT + Kimi demonstrations) | **46.6%** | **18.8%** | **27.2%** |

</div>

*Pass@1, averaged over three evaluation runs. The recipe fine-tunes [Grug Datakit 09-21](https://github.com/marin-community/marin/issues/8089) on Relay SFT and Kimi coding demonstrations. These results are from an experimental checkpoint; the final Snowball launch checkpoint is not yet specified.*

That result took several changes of approach. Snowball itself also changed during the work, so this is an account of building the expert across successive starting checkpoints.

<nav class="research-toc" aria-label="Article contents">
<div class="research-toc-title">Contents</div>
<ul>
<li><strong><a href="#starting-with-reinforcement-learning">Starting with RL</a></strong><span class="toc-sub"><a href="#the-pre-rl-probe">Pre-RL probe</a> · <a href="#following-the-behavior-back-to-sft">SFT habits</a> · <a href="#diagnosing-entropy-collapse">Entropy collapse</a> · <a href="#fixing-the-training-stack">Stack fixes</a> · <a href="#what-rl-improved">Results</a> · <a href="#speeding-up-rollouts-without-retraining-the-draft">Speculative decoding</a> · <a href="#training-a-prompt-into-the-weights">Prompt distillation</a></span></li>
<li><strong><a href="#strengthening-the-starting-policy-with-sft">Strengthening the policy with SFT</a></strong><span class="toc-sub"><a href="#better-loss-worse-agent">The Kimi experiment</a> · <a href="#combining-sft-and-rl">SFT → RL</a></span></li>
<li><strong><a href="#relay-sft">Relay SFT</a></strong><span class="toc-sub"><a href="#bringing-in-the-teacher">Motivation and recipe</a> · <a href="#testing-the-idea">Testing the idea</a></span></li>
<li><strong><a href="#reflections">Reflections</a></strong></li>
<li><strong><a href="#what-you-can-reuse">What you can reuse</a></strong></li>
</ul>
</nav>

## Starting with Reinforcement Learning

### The Pre-RL Probe

Before running RL, it helps to understand what the starting model can already do. That means asking how many tasks it can sometimes solve, what its common failures are, and whether it lacks coding knowledge or struggles to put that knowledge into practice. The answers help decide whether to change the task pool, the training recipe, or the starting model.

I started with [Snowball's Stage-3 Nemotron-Terminal SFT checkpoint](https://github.com/marin-community/marin/issues/8225). Before training, I sampled R2E-Gym tasks eight times each and used coding agents to inspect the traces. Only 36% of fully sampled tasks had both successes and failures, the useful band for binary-reward GRPO.

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
<a href="{{ '/assets/img/snowball/early-rl-labeled.png' | relative_url }}"><img src="{{ '/assets/img/snowball/early-rl-labeled.png' | relative_url }}" alt="Starting model versus RL with truncated and full-distribution sampling, with all colors labeled." width="1728" height="880" loading="lazy"></a>
<figcaption>The same 191 held-out tasks, eight attempts each. Both RL recipes also solved tasks the base missed in all eight attempts; this does not mean the base could never solve them.</figcaption>
</figure>

Finishing more often came with different trade-offs. With truncated sampling, correctness among attempts that declared completion fell from 39% to 29%. Full-distribution sampling increased completion while keeping that figure around 41%. RL could teach the agent to finish without reliably teaching it to judge whether the work was correct. That judgment needed to be checked separately from the headline score.

Rebuilding the stack improved the result further. On a later evaluation set, the new stack scored about ten points above the old one, using half as many nodes.


<figure class="research-figure">
<a href="{{ '/assets/img/snowball/stack-comparison.png' | relative_url }}"><img src="{{ '/assets/img/snowball/stack-comparison.png' | relative_url }}" alt="Old versus new training stack on two held-out R2E-Gym splits." width="1728" height="880" loading="lazy"></a>
<figcaption>Matched comparison under the older probe setup: 49.9% → 60.0% on new tasks in repositories used for RL, and 50.3% → 59.5% on tasks in repositories excluded from RL entirely. This is a separate evaluation from the early results above. Several changes landed together, so the gain belongs to the package.</figcaption>
</figure>

The changes were visible in the traces. Successful attempts took a median of 15 turns, down from 22, and exact repeats of the previous command fell from 2.19 to 0.48 per 100 turns. Verification shifted toward self-written repro/check scripts, while use of the repository's tests fell.

This was more than learning to announce completion. The grader already credited correct fixes left in the repository when the context ran out. RL made it more likely that useful work reached a correct fix within the budget. Verification remained a weakness: repository-test use fell, and wrong submissions became more common.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/rl-behavior-changes.png' | relative_url }}"><img src="{{ '/assets/img/snowball/rl-behavior-changes.png' | relative_url }}" alt="Before and after RL: repeated-command attempts fell from 3.3% to 0.6%, self-written check use rose from 90.9% to 98.2%, repository-test use among passing attempts fell from 54.8% to 26.8%, and submission precision fell from 78.9% to 68.6%." width="1760" height="992" loading="lazy"></a>
<figcaption>Starting model versus new-stack update 24 on the same 441 R2E-Gym tasks, eight attempts each. Each row states its denominator. Submission precision uses the same 247 tasks, but the checkpoints chose different attempts to submit, so this does not isolate coding ability.</figcaption>
</figure>

On SWE-bench, the selected RL checkpoint improved from the starting model's 12 correct tasks to 23 of 100. Terminal-Bench did not show a comparable gain.

One tempting context fix also failed. Removing earlier reasoning freed about a third of the window, but the model took more turns, spent 48% more tokens per rollout, and increasingly stopped reasoning. Editing the history changed how it behaved. The score barely moved.

<aside class="research-reports" markdown="1">
Full reports: [First RL results](https://gist.github.com/lukedhlee/9c19fd9288a94ecfd1dbd6906b0a8dda), [Old versus new stack](https://gist.github.com/lukedhlee/01897efa3ae7c474732c61d35150a43a), [Why RL improved](https://gist.github.com/lukedhlee/ad3a95fccccb527db66619d6b3667e7d), [Behavior and optimizer experiments](https://gist.github.com/lukedhlee/9747e8eb423f23ca6627199c2532de47), [Reasoning-history ablation](https://gist.github.com/lukedhlee/565d259cda4c396db9bcba027322186e).
</aside>

### Speeding Up Rollouts Without Retraining the Draft

Long agent rollouts also made each experiment expensive. The pre-RL probe supplied training data for a small EAGLE-3 draft: it proposes several tokens, and Snowball verifies them. Adapting the pilot draft on 2,177 of Snowball's own rollouts improved per-stream speed by another 12–15% in two same-node repeats. The probe was useful twice, first for inspecting the policy and choosing tasks, then for making the next experiments faster. In matched five-node runs, three RL updates took about 31 minutes instead of 44, making the updates **1.42× faster**.

I also checked whether the draft would need refreshing as RL changed Snowball. The same frozen draft held through 60 updates, with no decline in accepted tokens per verification step. At update 36, 86% of Snowball's weights were still bit-identical to the starting checkpoint. That small change was consistent with the draft remaining useful despite the improvement in agent performance. The draft needed training once, then no retraining during that run.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/speculative-decoding.png' | relative_url }}"><img src="{{ '/assets/img/snowball/speculative-decoding.png' | relative_url }}" alt="A frozen speculative-decoding draft accelerated RL updates and maintained acceptance through 60 updates." width="1760" height="848" loading="lazy"></a>
<figcaption>The timing comparison and the 60-update acceptance trace come from separate experiments. A frozen draft holding here does not establish that it will hold under every RL recipe.</figcaption>
</figure>

<aside class="research-reports" markdown="1">
Full reports: [Toolkit and timing](https://gist.github.com/lukedhlee/b161a78a29e2c42b08a157aaaea6438b), [Frozen draft during RL](https://gist.github.com/lukedhlee/bd14e461b13557a3a541e721fcda643e), [Initial pilot](https://gist.github.com/lukedhlee/f02dc181b7383e47908091b565cf8619).
</aside>

### Training a Prompt into the Weights

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

The lesson was that the starting policy deserved as much attention as the RL recipe. SFT offered a way to build a stronger coding foundation by learning from demonstrations, including behaviors Snowball rarely discovered on its own. The next experiments focused on whether that foundation would give RL more useful behavior to reinforce.

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

The next experiments started from Marin's newer [Grug Datakit 09-21](https://github.com/marin-community/marin/issues/8089) checkpoint. Kimi demonstrations alone now reached 41.6% on SWE-bench, against 13.8% for that starting model under the three-run evaluation recipe. The earlier failure did not make the dataset universally unhelpful: the starting checkpoint and training recipe mattered.

### Bringing in the Teacher

Teacher-only SFT trains on histories generated by the teacher. At deployment, Snowball creates its own history: different commands, mistaken assumptions, invalid actions, and unfinished fixes. This mismatch is **exposure bias**. A demonstration of the teacher's clean solution may not show how to recover from the situations the student actually encounters.

Trace analysis identified three major failure modes that were cheap to detect programmatically during online trajectory generation: invalid actions, exhausting the context budget, and premature completion. The harness could flag a rejected action, track context use, or intercept a completion claim. These became the intervention points for **Relay SFT**. A completion claim triggered verification, since it could also be correct.

Snowball starts the task, and a stronger teacher intervenes at those points. The teacher repairs an invalid action, continues when the context-budget trigger fires, or checks the work when Snowball claims completion. For these experiments the teacher was Qwen3.8-27B. During SFT, Snowball's turns remain as context and only the teacher's turns contribute to the loss.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/relay-timeline.png' | relative_url }}"><img src="{{ '/assets/img/snowball/relay-timeline.png' | relative_url }}" alt="Teacher-only SFT trains on teacher-generated histories; Relay SFT includes student turns, local teacher repairs, and teacher continuations." width="2409" height="957" loading="lazy"></a>
<figcaption>Student turns (S) provide context without training loss. Local repairs (R) and teacher continuations (T) are trained. A completion claim prompts a check; it is not proof that the student made a mistake.</figcaption>
</figure>

<aside class="research-reports" markdown="1">
Full reports: [Initial relay design](https://gist.github.com/lukedhlee/d8fc1454ed134eff585448c4982458c9), [Behavior and knowledge evaluation](https://gist.github.com/lukedhlee/12f2e7293f332ce398655b4ec3e17b22), [Evaluation scheme](https://gist.github.com/lukedhlee/18b42f882bf099f6e89f901d6bd05e29).
</aside>

### Testing the Idea

On matched CalibForge tasks, trace counts, and pass/fail outcomes, Relay SFT beat teacher-only SFT on all three benchmarks. The advantage repeated on a separate task pool, TMax.

The best recipe then used the full set of 5,916 relay episodes plus 4,392 Kimi traces. It reached **46.6% on SWE-bench, 18.8% on Terminal-Bench 2.1, and 27.2% on OpenThoughts-TBLite**, the same checkpoint shown in the opening table. The smaller matched-data run is a separate comparison, labeled below.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/relay-matched-dots.png' | relative_url }}"><img src="{{ '/assets/img/snowball/relay-matched-dots.png' | relative_url }}" alt="Matched teacher-only and Relay SFT comparisons alongside the best full-data recipe from the opening table." width="2160" height="1056" loading="lazy"></a>
<figcaption>The green bars show the best recipe from the opening table. Blue and orange bars show the smaller matched-data comparisons, while the full-data recipe uses more relay episodes. Three-run means, with standard errors over tasks.</figcaption>
</figure>

Exposure bias motivated the recipe, but these experiments do not isolate it as the mechanism or show that the triggers beat random switching. The broader idea is related to [teacher continuations from student contexts](https://arxiv.org/abs/2607.04574v2) and [Relay-OPD](https://arxiv.org/abs/2607.26057).

<aside class="research-reports" markdown="1">
[Full report](https://gist.github.com/lukedhlee/8669f5b6f97e4e3bae72344a8fd51f4b).
</aside>

## Reflections

The starting policy mattered more than I appreciated at the beginning. GRPO needed tasks the current model could sometimes solve. SFT could change that starting point substantially, but a lower demonstration loss was not enough to tell whether it had helped.

Reading traces repeatedly changed the next experiment. It exposed inherited editing habits, broken probability accounting, and the difference between a model finishing an episode and producing a correct result. Having access to the upstream data and code made those investigations possible. Fixing the system and improving the policy were both part of building the expert.

A broader question is whether post-training can become a process of diagnosing a particular model and choosing targeted interventions. Four directions seem especially worth investigating.

**Can diagnosis scale beyond reading individual traces?** A failed attempt might reflect missing knowledge, poor planning, weak verification, or a broken environment. Can automated probes distinguish these explanations, map the model's strengths, and predict which intervention will help? A useful diagnosis should lead to improvements on new tasks while preserving existing strengths.

**What should change in the harness, and what should change in the weights?** A reminder, a different tool interface, or teacher intervention might address the same failure as additional training. Can cheap harness experiments identify useful behaviors before committing to weight updates? When should those behaviors stay in the harness, and when should they be distilled? This connects to [Yoonho Lee's discussion of learning across text and weights](https://yoonholee.com/blog/2026/we-should-take-text-optimization-more-seriously/).

**How should SFT and RL share tasks and compute?** Which failures call for demonstrations, and which can improve through the model's own attempts? That allocation should change as the policy improves. Relay SFT adds another option by collecting teacher continuations from the student's attempts. When can existing demonstrations be adapted to those situations, and when is collecting new ones worth the cost?

**Can AI help invent better post-training methods?** Beyond choosing datasets and running ablations, could an agent diagnose a recurring failure and propose a new objective, credit-assignment rule, or teacher-intervention strategy? What limits this today: reliable diagnosis, trustworthy evaluation, experiment cost, or the ability to distinguish an algorithmic improvement from a favorable experiment?

## What you can reuse

The expert checkpoints are public: the [model in the opening table](https://huggingface.co/laion/snowball-67b-a2b-relay-sft-allkimi-step1203), a [similarly performing continuation](https://huggingface.co/laion/snowball-67b-a2b-relay-sft-acont-step999), and the [earlier RL checkpoint](https://huggingface.co/laion/snowball-67b-a2b-rl-r2egym-newstack-step24). The opening model's training set is in [calibforge-relay-traces](https://huggingface.co/datasets/laion/calibforge-relay-traces), under `terminus2_relay_sft`.

I also released an [EAGLE-3 toolkit](https://github.com/lukedhlee/grugmoe-eagle3) and [draft model](https://huggingface.co/laion/snowball-64k-eagle3-draft-r2egym). The frozen draft made matched RL updates arrive 1.42× sooner and held through 60 updates in the tested run. The [R2E-Gym Daytona artifacts](https://huggingface.co/datasets/laion/r2egym-build-artifacts) make 3,020 tasks available from eleven shared images. That pool includes tasks recovered from previously omitted repositories; passing the build gate does not certify that every task is well specified.

Build checks did not catch every task defect. In a close read of 243 failed attempts across 39 tasks, 40 were attributed to task or sandbox defects. One issue requested a clear error message while its hidden test demanded exact wording. Another task's grader depended on a test helper changed by the reference patch. Two suspected misgrades lacked enough logs to confirm. **The 16% belongs to that audited sample, which over-represented difficult tasks.** [Audit details](https://gist.github.com/lukedhlee/9eafb59ad72f08957f2e7fd551c249cb).

Several fixes went upstream to harbor ([#117](https://github.com/marin-community/harbor/pull/117), [#122](https://github.com/marin-community/harbor/pull/122), [#124](https://github.com/marin-community/harbor/pull/124), [#126](https://github.com/marin-community/harbor/pull/126)) and MarinSkyRL ([#517](https://github.com/marin-community/MarinSkyRL/pull/517), [#519](https://github.com/marin-community/MarinSkyRL/pull/519), [#542](https://github.com/marin-community/MarinSkyRL/pull/542)). Ben Feuer also added an upstream [probability-parity guardrail](https://github.com/marin-community/MarinSkyRL/pull/525) that rejects unsupported sampling filters.

David Hall recently wrote about the missing [posttraining data commons](https://marin.community/blog/2026/10/15/there-is-no-posttraining-data-commons/). Working on this expert made that problem concrete for me. A task needs a working environment, a meaningful requirement, and a grader worth trusting. A demonstration needs to teach behavior the student can use. Sharing those pieces, including the experiments that failed, is part of what I wanted to contribute to Marin.

<aside class="research-reports" markdown="1">
Full reports: [R2E-Gym on Daytona](https://gist.github.com/lukedhlee/b84aab48a67861b94d10ebc9b1ef77b8), [Evaluation policy](https://gist.github.com/lukedhlee/d152f86a58e8619a988361e1502f9e55), [Earlier experiment index (historical)](https://gist.github.com/lukedhlee/b509ed9dca3adf98414a9c7f93e27b2c).
</aside>
