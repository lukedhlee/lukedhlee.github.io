---
layout: research
color_theme: snowball
title: "Post-Training Marin’s Snowball into a Coding Agent: What Worked and What Didn’t"
description: "Taking Marin’s pretrained 67B A2B MoE from 12.8% to 50.5% on SWE-bench and 7.2% to 23.9% on Terminal-Bench. The SFT, RL, and training-stack debugging behind the gains—and what agent traces revealed beyond the scores."
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

[Marin](https://marin.community/)’s ambition is to make the knowledge behind capable AI a public resource. That means sharing the data, experiments, and decisions that go into building models, including the ones that turn out to be wrong.

We worked with the Marin team to improve coding and terminal performance in Snowball, Marin’s own 67B A2B MoE model, pretrained from scratch. Our starting checkpoint had received early general supervised fine-tuning across multiple domains. We explored reinforcement learning, additional coding-agent SFT, and SFT followed by RL.

Both SFT and RL substantially improved Snowball, with different strengths. SFT + RL reached the strongest SWE-bench and Terminal-Bench results, while direct RL was competitive on TBLite without additional coding demonstrations.

This post follows our part in Marin’s first post-training effort, including the failed experiments and debugging behind the results. We also explore how looking into the traces can help us understand the effects of training beyond the final scores.

We hope sharing these details helps others with their own post-training efforts and advances the open development of foundation models.

<!--
<figure class="research-figure">
<a href="{{ '/assets/img/snowball/intro-total-parameters.png' | relative_url }}"><img src="{{ '/assets/img/snowball/intro-total-parameters.png' | relative_url }}" alt="Benchmark scores against total model parameters" width="2880" height="1098" loading="lazy"></a>
</figure>
-->

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/intro-ranked-bars.png?v=padded' | relative_url }}"><img src="{{ '/assets/img/snowball/intro-ranked-bars.png?v=padded' | relative_url }}" alt="Snowball and Qwen3.5 benchmark comparison" width="6546" height="2299" loading="lazy"></a>
</figure>

<div class="table-wrap" markdown="1">

| Model, evaluated with Terminus-2 | SWE-bench Verified random-100 | Terminal-Bench 2.1 | OpenThoughts-TBLite |
|---|---:|---:|---:|
| Snowball 09-21 | 12.8% | 7.2% | 11.5% |
| RL | 30.5% | 18.8% | **45.1%** |
| SFT | 46.5% | 18.8% | 33.0% |
| SFT + RL | **50.5%** | **23.9%** | 41.8% |

</div>

<nav class="research-toc" aria-label="Article contents">
<div class="research-toc-title">Contents</div>
<ul>
<li><strong><a href="#starting-with-reinforcement-learning">Starting with RL</a></strong><span class="toc-sub"><a href="#the-pre-rl-probe">Pre-RL probe</a> · <a href="#early-rl-gains">Early gains</a> · <a href="#diagnosing-entropy-collapse">Entropy collapse</a> · <a href="#fixing-the-training-stack">Stack fixes and results</a> · <a href="#speeding-up-rollouts-with-speculative-decoding">Speculative decoding</a></span></li>
<li><strong><a href="#training-with-sft-and-rl">Training with SFT and RL</a></strong><span class="toc-sub"><a href="#earlier-experiments-on-the-stage-3-checkpoint">Earlier experiments</a> · <a href="#additional-sft-on-the-09-21-checkpoint">09-21 SFT</a> · <a href="#one-exploration-learning-to-recover-with-a-teacher">Teacher-guided recovery</a> · <a href="#rl-on-the-mixed-task-pool">RL setup</a></span></li>
<li><strong><a href="#results-so-far">Results so far</a></strong></li>
<li><strong><a href="#what-did-sft-and-rl-actually-teach-snowball-looking-behind-the-scores">What did SFT and RL actually teach Snowball: looking behind the scores</a></strong></li>
<li><strong><a href="#conclusions">Conclusions</a></strong></li>
<li><strong><a href="#what-you-can-reuse">What you can reuse</a></strong></li>
<li><strong><a href="#acknowledgements">Acknowledgements</a></strong></li>
</ul>
</nav>

## Starting with Reinforcement Learning

These early experiments used the older Stage-3 checkpoint to study Snowball’s behavior and get RL working reliably. The main comparison of SFT and RL later in the post uses the relatively newer [Snowball 09-21](https://huggingface.co/open-athena/Grug-67B-A2B-Datakit-SFT-262K-2026.09.21) checkpoint.

### The Pre-RL Probe

Before running RL, it helps to understand what the starting model can already do. That means asking how many tasks it can sometimes solve, what its common failures are, and whether it lacks coding knowledge or struggles to put that knowledge into practice. The answers help decide whether to change the task pool or the training recipe itself.

We first started with [Snowball's Stage-3 Nemotron-Terminal SFT checkpoint](https://github.com/marin-community/marin/issues/8225). It is now a much weaker model than later checkpoints, but was a decent starting point we had at the time. Before training, we sampled [R2E-Gym](https://arxiv.org/pdf/2504.07164) tasks eight times each and used coding agents to inspect the traces. Only 36% of fully sampled tasks had both successes and failures, the useful band for binary-reward GRPO.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/pre-rl-probe.png?v=clean-distribution' | relative_url }}"><img src="{{ '/assets/img/snowball/pre-rl-probe.png?v=clean-distribution' | relative_url }}" alt="Distribution of successes out of eight attempts: 62.9% of tasks had no successes and 36.2% had one to seven. Successful attempts more often edited the repository and ran a test." width="3060" height="1080" loading="lazy"></a>
</figure>

In thirteen of fifteen closely read tasks with both successful and failed attempts, the losers reached the same file, usually the same function, as the winner. Often they could describe the fix. This suggested that Snowball already had the knowledge required to solve certain tasks, but didn't know how to reliably use it to deliver the fix. This kind of behavioral failure is what RL can target.

Another recurring failure had a surprisingly specific source. Snowball wrote SEARCH/REPLACE blocks into `/app/solution.patch`, then tried to apply them with Unix `patch`, which does not understand that format. The figure below shows the scan over 31,661 SWE traces within the full Stage-3 corpus. Their instructions explicitly requested the path and edit format Snowball later used in the wrong setting.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/sft-behavior-origin.png?v=clean-type' | relative_url }}"><img src="{{ '/assets/img/snowball/sft-behavior-origin.png?v=clean-type' | relative_url }}" alt="Shares of all Stage-3 SFT traces containing editing routines: solution.patch and SEARCH/REPLACE blocks each 8.6 percent, patch commands 4.6 percent, and Python rewriters 3.5 percent." width="2088" height="810" loading="lazy"></a>
</figure>

Without access to a model’s training data, we can only guess why it gives wrong answers or behaves unexpectedly. Marin’s open data policy lets us investigate those failures by tracing them back to the examples the model learned from.

<aside class="research-reports" markdown="1">
[Full report](https://claude.ai/artifact/TefbJfphaTBsYFtFgrNgMY).
</aside>

### Early RL Gains

In the first held-out evaluation, RL nearly doubled pass@1 from 8.7% to 16.6%. Before RL, 91% of attempts exhausted the 64k context window while the agent was still working. One RL recipe brought that down to 56%, making it more likely that useful work reached a result within the window.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/early-rl-labeled.png?v=left-legend' | relative_url }}"><img src="{{ '/assets/img/snowball/early-rl-labeled.png?v=left-legend' | relative_url }}" alt="Starting model and two RL checkpoints, labeled by their single-attempt success and task coverage." width="1728" height="880" loading="lazy"></a>
</figure>

The early RL recipes also made source edits and test runs more common. But finishing more often came with trade-offs. In the checkpoint with higher pass@1, correctness among attempts that declared completion fell from 39% to 29%. RL taught the agent to submit its best-effort solutions rather than submit nothing and exhaust all the context budget. Another checkpoint with higher pass@8 also increased completion while keeping that figure around 41%. Overall, RL taught both checkpoints to take more actions (e.g. editing a repository file and running more tests) instead of spending too much budgets exploring the codebase.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/rl-behavior-changes.png?v=spacing-refined' | relative_url }}"><img src="{{ '/assets/img/snowball/rl-behavior-changes.png?v=spacing-refined' | relative_url }}" alt="Early RL behavior: more completion claims, fewer context overflows, more source edits and pytest runs. Completion accuracy fell for one RL checkpoint and held near the starting model for the other." width="1980" height="1080" loading="lazy"></a>
</figure>

### Diagnosing Entropy Collapse

Those early gains did not always last. In some runs, held-out performance improved and then fell while training reward kept rising. Output entropy dropped to roughly half its starting value. Lowering the learning rate delayed the collapse without fixing it.

Eventually, we found a hidden mismatch in the rollout probabilities. Top-p and top-k filtering changed which tokens could be sampled, but the inference engine reported their probabilities before filtering. The trainer used those reported probabilities to correct for differences between the rollout and training policies, so its correction did not match how the tokens were actually sampled.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/entropy-debugging.png?v=spacing-refined' | relative_url }}"><img src="{{ '/assets/img/snowball/entropy-debugging.png?v=spacing-refined' | relative_url }}" alt="Filtered sampling reduced entropy to about half its initial value, while full-distribution sampling stayed near its starting level." width="1980" height="990" loading="lazy"></a>
</figure>

Our engine-versus-trainer checks missed this because both sides used the same unfiltered probabilities. They checked numerical agreement, but couldn't tell whether those probabilities matched the actual sampling process.  We then simply switched to full-distribution sampling to resolve the mismatch, and entropy stayed near its starting level beyond the earlier collapse point.

<aside class="research-reports" markdown="1">
[Full report](https://gist.github.com/lukedhlee/9c19fd9288a94ecfd1dbd6906b0a8dda).
</aside>

### Fixing the Training Stack

The sampling mismatch was one of several problems in the training stack. Some apparent model failures came from bugs in the system around it:

<div class="table-wrap" markdown="1">

| Problem | What changed |
|---|---|
| KL was logged but contributed no gradient | Restored gradients through the penalty ([#517](https://github.com/marin-community/MarinSkyRL/pull/517)). |
| Importance-sampling probabilities did not match temperature-scaled training | Corrected the probability accounting ([#519](https://github.com/marin-community/MarinSkyRL/pull/519)); also removed unsupported sampling filters. |
| Recovery after an over-long turn lost the sampled token chain | Preserved exact tokens (TITO) so the rollouts remained trainable ([#122](https://github.com/marin-community/harbor/pull/122)). |
| Long terminal history produced a frozen screen | Captured a recent window of history ([#125](https://github.com/marin-community/harbor/pull/125), used in these runs; closed without merging). |
| Verification timeouts turned finished attempts into reward-zero training samples | Increased the verifier budget and excluded timed-out samples from training. |

</div>

Another interesting bug we fixed involved Harbor losing token-level information when it coverted tokens into text ([harbor #122](https://github.com/marin-community/harbor/pull/122)), breaking token-in-token-out (TITO). When a turn hit its output limit, recovery could re-render the conversation and change tokens the model had already sampled. TITO keeps the exact sampled token IDs for both training and later turns. Consider a toy tokenizer:

```text
Model samples:          ["hel", "lo"]   (two tokens)
Decoded text:           "hello"
Text re-tokenized:      ["hello"]       (one different token)
```

The text looks identical, but the trainer now sees a token the model never sampled. The two original token probabilities no longer line up with the training sequence, breaking the probability accounting RL relies on. Our new fix preserved the prompt and completion token IDs through recovery, so the next request continued from the exact sampled sequence. Mercor and SkyRL discuss TITO in their [agent-training guide](https://www.mercor.com/blog/training-frontier-knowledge-work-agents-a-397b-rl-training-guide-with-skyrl/).

<aside class="research-reports" markdown="1">
[Full report](https://gist.github.com/lukedhlee/ad3a95fccccb527db66619d6b3667e7d).
</aside>

With these repairs in place, held-out performance improved further. On a later evaluation set, the new stack was already ahead at update 12 and reached about ten points above the old stack by update 24.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/stack-comparison.png?v=clean-type' | relative_url }}"><img src="{{ '/assets/img/snowball/stack-comparison.png?v=clean-type' | relative_url }}" alt="Held-out R2E-Gym pass@1 across RL updates. The new stack improves from the shared starting policy through updates 12 and 24; the old stack is evaluated through update 36. Both held-out splits favor the new stack." width="2232" height="954" loading="lazy"></a>
</figure>

The traces showed how the rebuilt stack helped. On the 441-task probe, successful attempts took a median of 15 turns instead of 22, and the rate of repeated commands fell by more than fourfold. More attempts reached a working fix within the context budget.

<aside class="research-reports" markdown="1">
Full reports: [First RL results](https://gist.github.com/lukedhlee/9c19fd9288a94ecfd1dbd6906b0a8dda), [Old versus new stack](https://gist.github.com/lukedhlee/01897efa3ae7c474732c61d35150a43a), [Why RL improved](https://gist.github.com/lukedhlee/ad3a95fccccb527db66619d6b3667e7d), [Behavior and optimizer experiments](https://gist.github.com/lukedhlee/9747e8eb423f23ca6627199c2532de47).
</aside>

### Speeding Up Rollouts With Speculative Decoding

As long agent rollouts made each experiment expensive, we spent a few days to accelerate the RL infra. One of the biggest gains came from speculative decoding: a small draft model proposes several tokens, and Snowball verifies them. The pre-RL probe supplied training data for a small EAGLE-3 draft. So, the probe was useful twice, first for inspecting the policy and choosing tasks, then for making the next experiments faster. In matched five-node runs, decoding was **nearly 2× faster**, making RL steps **1.42× faster end to end**.

The same frozen draft remained effective through 60 RL updates, with no decline in accepted tokens per verification step. At update 36, 86% of Snowball's weights were still bit-identical to the starting checkpoint. This limited weight movement offers one explanation for the stable acceptance. [NeMo RL's experiments](https://arxiv.org/html/2604.26779#S3.SS3) likewise found little benefit from online draft updates when the draft was already trained on the policy's in-domain outputs. We note that RL runs with longer steps on other domains with higher unpredictability could observe the decline in draft acceptance.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/speculative-decoding.png?v=descriptive-title' | relative_url }}"><img src="{{ '/assets/img/snowball/speculative-decoding.png?v=descriptive-title' | relative_url }}" alt="A frozen speculative-decoding draft accelerated RL updates and maintained acceptance through 60 updates." width="2772" height="1188" loading="lazy"></a>
</figure>

<aside class="research-reports" markdown="1">
Full reports: [Toolkit and timing](https://gist.github.com/lukedhlee/b161a78a29e2c42b08a157aaaea6438b), [Frozen draft during RL](https://gist.github.com/lukedhlee/bd14e461b13557a3a541e721fcda643e), [Initial pilot](https://gist.github.com/lukedhlee/f02dc181b7383e47908091b565cf8619).
</aside>

After two weeks of improving the RL infra, we came back to strengthening the starting model before running more RL runs. RL could reinforce useful attempts, but a strong teacher's demonstrations would teach behaviors that Snowball rarely produced on its own. We wanted to see whether additional SFT could give RL a better place to start.

## Training with SFT and RL

For binary-reward GRPO, a group of attempts that all fail has no reward difference to learn from. Additional SFT might make more tasks sometimes solvable, giving RL more useful attempts to reinforce. In this section, we discuss the approaches we explored to train Snowball, including SFT, RL, prompt optimization, and mixing student and teacher rollouts for each task.

### Earlier Experiments on the Stage-3 Checkpoint

On the older Stage-3 checkpoint, we tried additional SFT on a mixture of OpenThoughts-Agent traces, instruction-following traces, and successful synthesized-task traces, then ran GRPO from that SFT checkpoint.

SFT raised SWE-bench from 14.5% to 24.1%; another 30 GRPO updates brought it to 30.7%. RL directly from the starting checkpoint scored 25.0% in its earlier evaluation. SFT could provide a better starting policy, and RL could improve it further.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/ota-sft-rl-swe.png?v=spacing-refined' | relative_url }}"><img src="{{ '/assets/img/snowball/ota-sft-rl-swe.png?v=spacing-refined' | relative_url }}" alt="SWE-bench Verified random-100 on the older Stage-3 checkpoint: starting model 14.5%, SFT 24.1%, RL only 25.0%, and SFT followed by RL 30.7%, with 95% Wilson intervals." width="2052" height="1007" loading="lazy"></a>
</figure>

<aside class="research-reports" markdown="1">
Full reports: [SFT versus RL versus SFT→RL](https://github.com/marin-community/marin/issues/9225), [training recipes and launch configs](https://gist.github.com/lukedhlee/d152f86a58e8619a988361e1502f9e55).
</aside>

### Additional SFT on the 09-21 Checkpoint

We next moved to Marin’s newer [09-21 checkpoint](https://huggingface.co/open-athena/Grug-67B-A2B-Datakit-SFT-262K-2026.09.21), which had already received general SFT. To give RL a stronger starting policy, we added coding-agent SFT using [Qwen3.8-27B traces on CalibForge tasks](https://huggingface.co/datasets/laion/calibforge-relay-traces), with and without [Kimi coding demonstrations](https://huggingface.co/datasets/open-athena/Kimi-2.5-swesmith-sandboxes-with_tests-oracle_verified_120s-maxeps-32k).

Additional SFT improved the benchmark scores substantially. For example, vanilla CalibForge + Kimi reached 46.5% on SWE-bench, compared with 12.8% for the starting checkpoint. We then tested whether RL could improve these policies further, which we describe further later in this blog.

### One Exploration: Learning to Recover with a Teacher

We also explored demonstrations designed to address **exposure bias**. During SFT, Snowball learns from teacher-generated histories; during deployment, it must act on histories shaped by its own mistakes. We designed **Relay SFT** to narrow that gap, using teacher continuations of Snowball’s attempts as demonstrations for further SFT before RL.

In our Relay SFT, Snowball starts the task. Qwen3.8-27B takes over after an invalid action, near the context limit, or when Snowball declares it is done. The teacher fixes the action, continues the solution, or verifies the result. We then train on the teacher’s turns, keeping Snowball’s turns as context.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/relay-timeline.png?v=plain-annotation' | relative_url }}"><img src="{{ '/assets/img/snowball/relay-timeline.png?v=plain-annotation' | relative_url }}" alt="Teacher-only SFT uses teacher-generated histories. Relay SFT trains teacher actions following the student's attempts." width="2409" height="957" loading="lazy"></a>
<figcaption>Student turns (S) provide context without training loss. Local repairs (R) and teacher continuations (T) are trained.</figcaption>
</figure>

This was one exploration alongside ordinary SFT. Earlier comparisons looked promising, but later comparisons with corrected training precision and expert capacity did not establish a consistent advantage over vanilla SFT. Whether student-conditioned demonstrations produce a better starting policy for RL remains an open question.

<aside class="research-reports" markdown="1">
Earlier reports: [Relay design](https://gist.github.com/lukedhlee/d8fc1454ed134eff585448c4982458c9), [Initial results, before the corrected comparisons](https://gist.github.com/lukedhlee/8669f5b6f97e4e3bae72344a8fd51f4b). These historical results should be read separately from the newer experiments below.
</aside>

### RL on the Mixed Task Pool

We next ran GRPO on a mixture of R2E-Gym repository tasks and TMax terminal tasks. The motivation was to let the demonstration-trained policies learn from their own attempts and task rewards. The mixed task pool contained 3,832 tasks, comprising 1,104 R2E-Gym tasks and 2,728 TMax tasks. A held-out set of 426 tasks was excluded from band selection and training.

We probed the vanilla CalibForge epoch-7 model eight times per task and selected tasks it solved between one and six times. This produced a learnable band of 1,833 tasks, comprising 453 R2E-Gym tasks and 1,380 TMax tasks. All three additional-SFT models used this band for RL.

We ran 30 GRPO updates using batches of 64 tasks with eight attempts each, a learning rate of 5e-7, and a 64k context window. For comparison, we also trained [Snowball 09-21](https://huggingface.co/open-athena/Grug-67B-A2B-Datakit-SFT-262K-2026.09.21) directly with RL. We extended the CalibForge and vanilla CalibForge + Kimi runs to 60 updates.

<details markdown="1">
<summary>Another exploration: prompt optimization followed by RL</summary>

The idea was to find instructions that improved Snowball's behavior, then use RL to make the improvement persist without those instructions. In this pilot, we compared five hand-written prompts and selected the best on development tasks. It asked Snowball to make precise source changes, check syntax, and inspect the diff. Adding that prompt improved the starting policy by **9–14 percentage points**.

This pilot selected a fixed prompt; it did not run an automated prompt-evolution loop.

During RL, the prompt stayed in the rollout context but was removed from the context used for weight updates. The goal was to reinforce useful actions given only the task. After 24 updates, the policy tested without the prompt scored **29.8%, against 30.2% for the starting policy**. Ordinary RL on the same task pool reached 47.4%.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/prompt-rl-outcome.png?v=prompt-optimization' | relative_url }}"><img src="{{ '/assets/img/snowball/prompt-rl-outcome.png?v=prompt-optimization' | relative_url }}" alt="Development-set pass@1: starting policy 30.2 percent, starting policy with the selected prompt 44.6 percent, prompt-guided RL evaluated without the prompt 29.8 percent, and ordinary RL 47.4 percent." width="2088" height="792" loading="lazy"></a>
<figcaption>The older Stage-3 checkpoint, evaluated on the same 120 development tasks with four attempts each. Both RL results are at update 24 and tested without the selected prompt.</figcaption>
</figure>

The prompted-versus-unprompted likelihood gap shrank 85%, yet task success did not improve. The prompt's additional influence was largest on the first action and much smaller by turns four to six, even before training. Once the history contained the model's own actions, the initial guidance added little to the likelihood of those same actions.

The older checkpoint also had low instruction-following evaluation scores. Even with the prompt, only **15% of attempts followed its full procedure**. Weak instruction following may have limited how much it could benefit from prompt optimization. A useful next test is to improve instruction following first, then repeat the prompt-plus-RL experiment. Guidance delivered after a failed check or before a completion claim could also help at moments the initial prompt no longer reaches. Joint prompt and policy optimization remains worth exploring, as in [Fast-Slow Training (FST)](https://arxiv.org/abs/2605.12484) and [P²O](https://arxiv.org/pdf/2603.21877).

<aside class="research-reports" markdown="1">
[Full report](https://gist.github.com/lukedhlee/edb2f69d38ed089f71f74ff711281807).
</aside>
</details>

## Results So Far

The results and trace comparisons from here onward use **[Snowball 09-21](https://huggingface.co/open-athena/Grug-67B-A2B-Datakit-SFT-262K-2026.09.21)**. The figure compares this starting checkpoint, direct RL, and each additional SFT recipe before and after RL. The highlighted run is vanilla CalibForge + Kimi after 60 RL updates, which also supplies the last row of the opening table. Vanilla denotes ordinary teacher-demonstration SFT.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/sft-rl-stages.png?v=tighter-panel-titles' | relative_url }}"><img src="{{ '/assets/img/snowball/sft-rl-stages.png?v=tighter-panel-titles' | relative_url }}" alt="Across three benchmarks, the 09-21 starting model is shown in gray, three additional SFT recipes in cyan, and each recipe followed by RL in blue. Lighter blue bars show RL step 30 and darker blue bars show step 60. Direct RL and Relay have step-30 results only. Vanilla CalibForge plus Kimi reaches 23.9 percent on Terminal-Bench, 50.5 on SWE-bench, and 41.8 on TBLite." width="2951" height="1512" loading="lazy"></a>
<figcaption>Pass@1 point estimates with Terminus-2. “Snowball 09-21” is the general-SFT starting checkpoint. Lighter blue is RL step 30; darker blue is step 60. No step-60 result is available for direct RL or Relay. Starting-policy scores are unchanged.</figcaption>
</figure>

Vanilla CalibForge + Kimi continued improving through 60 RL updates, reaching **50.5% on SWE-bench**, **23.9% on Terminal-Bench 2.1**, and **41.8% on TBLite**. It now leads the recipes shown on SWE-bench and Terminal-Bench. Direct RL still has the highest TBLite score at 45.1%, without the additional coding-agent demonstrations.

More updates did not help every recipe equally. CalibForge-only SFT gained on SWE-bench but lost ground on Terminal-Bench by step 60. The checkpoint progression below shows why the starting policy and training duration need to be considered together.

<details markdown="1">
<summary>Results at 30 and 60 RL updates</summary>

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/rl-checkpoint-progress.png?v=steps30-60' | relative_url }}"><img src="{{ '/assets/img/snowball/rl-checkpoint-progress.png?v=steps30-60' | relative_url }}" alt="Checkpoint scores for the three SFT recipes at 30 and 60 RL updates. Vanilla CalibForge plus Kimi reaches its highest score on every benchmark at step 60. CalibForge-only Terminal-Bench scores decline. Relay has results through step 30." width="2952" height="954" loading="lazy"></a>
<figcaption>Pass@1 with Terminus-2. The step-60 evaluation for direct RL is running. Lines connect the evaluated checkpoints.</figcaption>
</figure>

</details>

## What Did SFT and RL Actually Teach Snowball: Looking Behind the Scores

Direct RL from [Snowball 09-21](https://huggingface.co/open-athena/Grug-67B-A2B-Datakit-SFT-262K-2026.09.21) matched or came close to the SFT + RL models on terminal tasks, despite skipping the additional demonstrations. The trace inspections below compare these RL checkpoints with their starting policies. We wanted to understand what those demonstrations contributed. Did they teach new knowledge, or change how Snowball approached and executed the work? We used coding agents to compare trajectories and inspect where the two routes succeeded or failed.

### SFT’s advantage on SWE-bench

On SWE-bench, additional coding-agent SFT with CalibForge + Kimi reached **46.5%**, compared with **30.5% for direct RL**. Following that SFT with RL brought the score to 47.0% at update 30 and **50.5% at update 60**.

Both direct RL and Kimi SFT nearly always opened a correct target file to fix. But Kimi SFT edited a relevant file **almost twice as often** and left the target tests passing **about 1.5 times as often** as direct RL.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/trace-swe-steps.png?v=step30-only' | relative_url }}"><img src="{{ '/assets/img/snowball/trace-swe-steps.png?v=step30-only' | relative_url }}" alt="SWE-bench execution milestones. Snowball 09-21 opens a relevant file in 78 percent of scored attempts and edits one in 38 percent. Vanilla Kimi SFT reaches 99 and 90 percent respectively and leaves the target tests passing in 51 percent of scored attempts." width="2952" height="1080" loading="lazy"></a>
</figure>

The two routes found relevant files at similar rates. SFT’s higher SWE-bench score went with more attempts editing those files and leaving the target tests passing.

### Did SFT add knowledge?

The clearest knowledge difference appeared in `sqlite-db-truncate`, a Terminal-Bench 2.1 task. The rule that SQLite serial type 7 encodes an eight-byte IEEE double appeared in **12 of 13 SFT-family attempts** and **none of five starting-model or direct-RL attempts**. Direct RL finished using incorrect decoding rules and submitted wrong values.

On the other hand, RL helped Snowball act on knowledge it already showed. The starting checkpoint already identified the needed React version fix and wrote a correct SQL query, yet failed both tasks. After RL, Snowball successfully completed them by learning to make use of the existing knoweldge to solve a problem.

### How the agents worked differently

We also compared 26 newly solved TBLite tasks where both routes succeeded. The median turn counts were similar, but direct RL used fewer output tokens and more shell commands. Direct RL's reasoning made up about 42% of its output characters, compared with 69% for SFT + RL. It had a pattern of shorter reasoning turns interleaved with more experiments, while SFT + RL often worked through more of the solution before acting.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/trace-working-style.png?v=aligned-type' | relative_url }}"><img src="{{ '/assets/img/snowball/trace-working-style.png?v=aligned-type' | relative_url }}" alt="On 26 shared TBLite successes, median time is 255 seconds for direct RL versus 604 for SFT plus RL; agent turns are 28.5 versus 31; output tokens are 35 thousand versus 92 thousand; reasoning shares are 42 versus 69 percent of output characters; shell commands are 61 versus 44." width="2952" height="882" loading="lazy"></a>
</figure>

Longer reasoning of SFT sometimes paid off. On parking-lot pathfinding, the vanilla Kimi SFT + RL model finished in roughly 100–120 seconds and 6–8 turns, while direct RL took 900–1,100 seconds and 68–83 turns.

### How the failures changed with training

The starting checkpoint often struggled to get actions executed at all. On TBLite, invalid action formats appeared in roughly four out of five attempts. Direct RL reduced that to about 2%, while additional SFT almost eliminated it. Both runs also decreased the tendency of claiming done without doing any work.

<figure class="research-figure">
<a href="{{ '/assets/img/snowball/trace-failure-modes.png?v=spacing-refined' | relative_url }}"><img src="{{ '/assets/img/snowball/trace-failure-modes.png?v=spacing-refined' | relative_url }}" alt="Five TBLite trace patterns before and after RL. Direct RL reduces invalid action formats from 81 to 2 percent of attempts. Turns reaching the token limit decline from 53 to 36 percent for CalibForge plus Kimi, but remain near 68 percent for CalibForge-only SFT. Summarization handoffs also decline for CalibForge plus Kimi. Unfinished shell commands persist, while failed submissions after successful self-checks become more common in the Kimi models." width="2952" height="1404" loading="lazy"></a>
</figure>

### Reward hacking

Some attempts satisfied the verifier without doing the requested work. Trace inspection found clear examples both before and after RL.

<div class="table-wrap" markdown="1">

| Benchmark | Task | Model | What it did | Why it passed |
|---|---|---|---|---|
| Terminal-Bench 2.1 | Implement a Scheme evaluator | Direct RL | Modified the supplied interpreter so the submission could delegate execution to a new primitive. | The verifier ran the modified interpreter. |
| OpenThoughts-TBLite | Repair a JavaScript network controller | CalibForge SFT | Replaced the controller with a toy simulation that printed `SYSTEM_STABLE`, removing the networking behavior it was supposed to repair. | The tests checked the success marker, exit code, and absence of error strings. |

</div>

These exploits each added only about half a percentage point to the model’s benchmark score. Interestingly, direct RL also produced far more failed shortcuts than the other models, including fabricated outputs and copied answer files. All 31 of those attempts failed, so they contributed nothing to its gains.

During RL, we have found a few reward hackings. In R2E-Gym, some task repositories exposed later Git commits containing the fixes. Agents read those fixes in 39 rewarded rollouts. This was already happening at the first RL update and did not become more common during training.

## Conclusions

SFT and RL both improved Snowball. With RL, vanilla CalibForge + Kimi SFT led on SWE-bench and Terminal-Bench, while direct RL retained the highest TBLite score. Trace analysis connected those gains to changes in knowledge use and execution.

Using agents to inspect traces helped us understand each model’s strengths and failure modes. Those diagnoses could also guide targeted environments or demonstrations for more surgical improvements.

Our attempt to combine prompt optimization with RL did not improve the policy when tested without the prompt. Weak instruction following may have been one bottleneck. Improving that capability and exploring methods such as [GEPA](https://arxiv.org/abs/2507.19457) and [Fast-Slow Training (FST)](https://arxiv.org/abs/2605.12484) are worth pursuing to make better use of dense feedback from agent runs.

How to allocate data and compute between SFT and RL remains open. SFT changes the policy and, with it, which tasks provide useful reward signals. A controlled comparison at fixed total compute could vary both the demonstration mix and the RL task pool, including the cost of generating data. This would help identify which tasks benefit from demonstrations, which support direct RL, and when to switch between them.

A strong teacher sharing Snowball’s tokenizer was not available for these experiments, limiting straightforward token-level on-policy distillation (OPD). Cross-tokenizer OPD could make it possible to learn from stronger teachers on Snowball’s own trajectories.

Domain-specific gains also raise a continual-learning question. Coding and terminal improvements alone do not reveal whether earlier abilities were preserved. Evaluating retention across the original domains could establish whether specialization requires rehearsal data, and how that data should share the training budget.

## What you can reuse

- **Models:** earlier [SFT](https://huggingface.co/laion/snowball-67b-a2b-relay-sft-allkimi-step1203) and [RL](https://huggingface.co/laion/snowball-67b-a2b-rl-r2egym-newstack-step24) checkpoints. The new SFT + RL checkpoints above are not yet uploaded.
- **Data:** [Relay demonstrations](https://huggingface.co/datasets/laion/calibforge-relay-traces) and [R2E-Gym environment artifacts](https://huggingface.co/datasets/laion/r2egym-build-artifacts).
- **Decoding:** the [EAGLE-3 toolkit](https://github.com/lukedhlee/grugmoe-eagle3) and [draft model](https://huggingface.co/laion/snowball-64k-eagle3-draft-r2egym).
- **Stack fixes:** [token preservation in Harbor](https://github.com/marin-community/harbor/pull/122) and [probability accounting in MarinSkyRL](https://github.com/marin-community/MarinSkyRL/pull/519).

## Acknowledgements

Thank you to Bespoke Labs for supporting my coding AI plan, Alex Dimakis for his advice, and JSC and TACC for providing compute for this work.
