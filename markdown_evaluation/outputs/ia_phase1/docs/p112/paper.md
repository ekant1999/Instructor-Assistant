---
title: "MemDLM: Memory-Enhanced DLM Training"
paper_id: 112
source_pdf: "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA/Instructor-Assistant/markdown_evaluation/pdfs/ResearchPapers/987e7ff453578105.pdf"
generated_at: "2026-04-05T20:56:31.687875+00:00"
num_figures: 11
num_tables: 3
num_equations: 18
---

Zehua Pei 1, Hui-Ling Zhen 2, Weizhe Lin 2, Sinno Jialin Pan 1, Yunhe Wang 2, Mingxuan Yuan 2, Bei Yu 1

1 The Chinese University of Hong Kong 2 Huawei Technologies Co., Ltd

## Abstract

Diffusion Language Models (DLMs) offer attractive advantages over Auto- Regressive (AR) models, such as full-attention parallel decoding and flexible generation. However, they suffer from a notable train-inference mismatch: DLMs are trained with a static, single-step masked prediction objective, but deployed through a multi-step progressive denoising trajectory. We propose MemDLM (Memory-Enhanced DLM), which narrows this gap by embedding a simulated denoising process into training via Bi-level Optimization. An inner loop updates a set of fast weights, forming a Parametric Memory that captures the local trajectory experience of each sample, while an outer loop updates the base model conditioned on this memory. By offloading memorization pressure from token representations to parameters, MemDLM yields faster convergence and lower training loss. Moreover, the inner loop can be re-enabled at inference time as an adaptation step, yielding additional gains on long-context understanding. We find that, when activated at inference time, this Parametric Memory acts as an emergent in-weight retrieval mechanism, helping MemDLM further reduce token-level attention bottlenecks on challenging Needle-in-a-Haystack retrieval tasks. Code: https://github.com/JarvisPei/MemDLM.

![Figure 1](assets/figures/page_001_vec_001.png)

_Figure 1: Needle-in-a-Haystack results overview. Gray bars denote Standard MDLM and blue bars denote MemDLM. Left: detailed results on RULER-MV, RULER-VT, RULER-CWE, and BABILong for the LLaDA-MoE-7B-A1B-Base and LLaDA2.1-mini backbones. Right: mean absolute improvement of MemDLM over Standard MDLM for each task, averaged across the evaluated context lengths within each backbone._

## Introduction

Diffusion Language Models (DLMs) have emerged as a promising alternative to traditional Auto- Regressive (AR) models, offering parallel generation, bidirectional context awareness, and flexible text manipulation capabilities [1, 2, 3, 4, 5, 6, 7, 8, 9]. Despite these architectural advantages, DLMs face an optimization challenge stemming from a train-inference mismatch. During training, DLMs optimize a static Masked Diffusion Language Modeling (MDLM) objective: they receive heavily masked text and must predict the clean sequence in a single, isolated step. In contrast, during inference, DLMs generate text through an iterative, progressive denoising trajectory, conditioning predictions on their own intermediate, noisy outputs. Because the base model is never trained on these progressive, sequential trajectories, errors can compound during generation, and the optimization landscape during training is not well aligned with the model’s actual deployment [10, 11, 12, 13].

To bridge this gap, we propose MemDLM (Memory-Enhanced DLM), a framework that mitigates exposure bias by internalizing local trajectory experiences into the model’s parameters. Our core insight is that exposure bias is exacerbated because standard DLMs must rely entirely on their noisy, intermediate token representations to maintain context across the generative trajectory; if prediction errors corrupt these tokens, the context can be significantly degraded. To address this, we introduce an inner optimization loop into the training graph that steps through a simulated progressive denoising trajectory. During this sequential simulation, we dynamically update a set of parameter-efficient fast weights. These fast weights act as a Parametric Memory that explicitly captures the local trajectory experience of the current sample [14, 15, 16, 17].

Figure 2 summarizes how MemDLM bridges the gap between static masked training and iterative
denoising inference by internalizing local trajectory information into transient fast weights. Because
this localized experience is internalized within the parameter space, it provides a stable anchor that is
more robust to the compounding, token-level noise inherent to iterative denoising. The base model
is then updated in an outer loop, conditioned on this Parametric Memory. By offloading part of
the local memorization burden to these fast weights during training, the base model is no longer
forced to preserve context solely through vulnerable token-space representations. This memory
internalization improves optimization and yields stronger zero-shot robustness to sequential noise,
while also enabling an optional inference-time adaptation pathway when the inner loop is re-enabled.
Empirically, on LLaDA-MoE [18], MemDLM improves RULER Variable Tracking [19] at 8K from
78.8% to 95.8%, and on LLaDA2.1 [20], it improves BABILong [21] at 8K from 47.4% to 57.0%.

In summary, our contributions are threefold. First, we identify and empirically demonstrate the traininference mismatch and the resulting context memorization difficulty in standard DLMs. Second, we introduce MemDLM, a Bi-level Optimization framework that simulates progressive denoising during training, naturally inducing a Parametric Memory mechanism. We demonstrate that this memoryaware training improves optimization and long-context performance even when the fast weights are discarded at inference time. Finally, we show that re-enabling the inner loop at inference time provides an additional prompt-specific adaptation pathway by explicitly internalizing the extended prompt into fast weights. We interpret this inference-time effect as an emergent in-weight retrieval mechanism, which further improves challenging Needle-in-a-Haystack tasks on top of the gains already obtained from training.

## Preliminaries and Motivation

Before formalizing our method, we first review the standard training and inference paradigms of Masked Diffusion Language Models (MDLMs) [2, 4]. We then conduct an empirical analysis to quantify a structural optimization gap inherent in this paradigm: the train-inference mismatch.

### Preliminaries: Masked Diffusion Language Models

Consider a sequence of clean text comprising L tokens, denoted as x 0 = (x 1 0, . . . , x L 0), where each token belongs to a discrete vocabulary V. Discrete diffusion models operate by defining a forward corruption process that gradually introduces noise over a continuous time variable t ∈ [0, 1]. At t = 0, the sequence is completely clean (x 0), and at t = 1, the sequence reaches a state of pure noise (x 1). The model is then trained to approximate the reverse generative process, learning to map a noisy state x t back to the original text x 0.

$$
ω 1 →L(1)
\tag{1}
$$
> Equation 1 JSON: `assets/equations/equation_0003.json`
> Equation 1 image: `assets/equations/equation_0003.png`

![Figure 2](assets/figures/page_003_vec_001.png)

_Figure 2: Overview of MemDLM. Left: standard MDLM training uses a static single-step denoising objective from xt to x0. Right: MemDLM uses Bi-level Optimization in which an inner loop updates fast weights ϕ along an anchor-consistent local trajectory (xtpre →xt →x0), and the outer loop updates the base model θ on the anchor state xt conditioned on this parametric memory. Legend: dark tokens denote mask tokens, light tokens denote observed tokens, straight arrows den_

Absorbing-State Masking. In the specific framework of MDLMs, the forward corruption q(x t|x 0) is instantiated as an absorbing-state process. Rather than transitioning tokens to random vocabulary items, tokens are replaced by a dedicated absorbing token, m / ∈V (often denoted as [MASK]). Under a linear noise schedule, the probability that the i-th token is masked at time t is simply t:

> Equation 1 JSON: `assets/equations/equation_0005.json`
> Equation 1 image: `assets/equations/equation_0005.png`

q(x i
t|x i
0) = (1 − t)I(x i
t = x i
0) + t I(x i
t = m),
(1)

where I(·) denotes the indicator function.

Standard MDLM training minimizes the expected negative log-likelihood of these masked tokens over uniformly sampled timesteps, yielding the following objective:

$$
L MDLM(\\theta) = E t∼U(0,1),x 0
$$
> Equation 7 JSON: `assets/equations/equation_0007.json`
> Equation 7 image: `assets/equations/equation_0007.png`

L MDLM(θ) = E t∼U(0,1),x 0

where ω(t) serves as a time-dependent weighting factor (e.g., ω(t) = 1/t) to balance the loss across varying noise levels. Critically, Equation (2) represents a single-step, static masking objective: the model receives a masked text based purely on ground-truth data and is optimized to predict the clean sequence in one isolated step.

Inference via Iterative Denoising. In contrast, DLMs generate text during inference through a multi-step, progressive denoising trajectory. Starting from a fully masked sequence at t = 1.0, the model predicts the clean tokens. A subset of the highest-confidence predictions is then unmasked to form a partially noisy intermediate sequence x t−∆t. This process repeats iteratively until t = 0, where all tokens are decoded. Crucially, at each step, the model’s input is conditioned on its own noisy predictions from previous steps, rather than pristine ground-truth context.

### Motivation: Quantifying Denoising Exposure Bias

Because the standard base model is never exposed to these sequential trajectories during training, the intermediate noisy sequences generated during inference inherently shift away from the true data distribution q(x t|x 0). Instead, they are drawn from the model’s own imperfect generative distribution

p θ(x t). As early-step prediction errors compound, the model faces inputs it was not optimized for, resulting in severe exposure bias.

To empirically quantify this discrepancy, we evaluate models on a validation set of prompt-response pairs. For a given mask ratio corresponding to timestep t, we measure the negative log-likelihood on the response tokens under two fundamental trajectories:

Static Condition: The model predicts masked tokens from a pristine context where the ground-truth response is artificially masked according to the true forward process. This represents the idealized state optimized during training:

$$
L static = E x 0,x t∼q(·|x 0) [− log p \\theta(x 0|x t)] .
\tag{3}
$$
> Equation 3 JSON: `assets/equations/equation_0008.json`
> Equation 3 image: `assets/equations/equation_0008.png`

L static = E x 0,x t∼q(·|x 0) [− log p θ(x 0|x t)] . (3)

Sequential Condition: Starting from a 100% masked response, the model iteratively predicts and unmasks tokens using its own predictions until reaching timestep t. This represents the actual conditions encountered during generation, where the noisy state ˆ x t is sampled from the model’s own iterative trajectory rather than the true forward process:

> Equation 9 JSON: `assets/equations/equation_0009.json`
> Equation 9 image: `assets/equations/equation_0009.png`

L seq = E x 0,ˆ x t∼p θ [− log p θ(x 0|ˆ x t)] . (4)

We define the Exposure Bias Ratio as R EB = L seq/L static. Because sequential generation inevitably introduces compounding errors (ˆ x t diverges from x t), this ratio is expected to be strictly greater than 1.0. A higher R EB indicates a more severe exposure bias, meaning the model struggles to denoise its own intermediate representations.

As illustrated in Figure 3, a Standard MDLM exhibits a steep, rapidly climbing exposure-bias curve. By the end of the generation process, the sequential loss is substantially higher than the static loss, confirming that standard training leaves the model highly vulnerable to its own sequential noise.

Figure 3 also clarifies an important aspect of our
empirical analysis. Even when evaluated zero-shot
(MemDLM Train-Only, where the inner loop is dis-
abled at inference), the model exhibits a substantially
flatter degradation curve than the baseline. This sug-
gests that the main benefit is already induced during
training: exposing the model to simulated denoising
trajectories and fast-weight adaptation improves the
robustness of the learned base model itself. When the
inner loop is reactivated at inference time (MemDLM
Train & Inference), the curve is smoothed further,
indicating an additional prompt-specific adaptation
effect on top of the training-time gains.

![Figure 3](assets/figures/page_004_vec_001.png)

_Figure 3: Exposure Bias Ratio (REB) across denoising steps. Standard MDLM degrades rapidly, while MemDLM remains substan- tially flatter._

These observations motivate our method along two key lines. First, mitigating train-inference mismatch requires reducing the model’s reliance on fragile token-space context during training. Second, if local trajectory information is internalized in parameter space, the learned model may acquire more stable long-context representations even without inference-time adaptation. This bridge between denoising robustness and long-context performance is the central motivation behind MemDLM.

## Methodology

Motivated by the empirical observations of exposure bias in Section 2, we aim to bridge the traininference gap while simultaneously easing the optimization pressure of context memorization on the base model. We achieve this by proposing MemDLM, which embeds a simulated denoising trajectory into the training process via a Bi-level Optimization framework.

### Bi-level Optimization for Denoising Simulation

To align the training objective with the iterative nature of inference, we partition the model parameters into the base weights θ and a set of parameter-efficient fast weights ϕ (e.g., low-rank adapters). We formulate the training process as a Bi-level Optimization problem:

$$
\begin{aligned}
ϕ k = ϕ k−1 − η∇ϕ L(k) \\
inner(\\theta, ϕ k−1) \\
for k = 1, . . . , K.
\end{aligned}
\tag{6}
$$
> Equation 6 JSON: `assets/equations/equation_0010.json`
> Equation 6 image: `assets/equations/equation_0010.png`

subject to ϕ k = ϕ k−1 − η∇ϕ L(k) inner(θ, ϕ k−1) for k = 1, . . . , K. (6)

Here, Equation (6) represents the inner loop, which simulates an unrolled K-step denoising trajectory for a specific batch. Starting from initial zero weights ϕ 0 = 0, the fast weights dynamically accumulate sample-specific contextual details through gradient descent, resulting in a final state ϕ K that acts as a Parametric Memory of the local trajectory experience. Equation (5) represents the outer loop, where the base model θ is updated conditioned on this internalized memory.

### The Inner Loop: Anchor-Consistent Trajectories

Rather than applying an arbitrary sequence of masks, we design the inner loop to simulate an Anchor- Consistent Local Trajectory. Because the outer objective is computed exactly at the noisy state x t, the inner loop’s parametric memory is most effective when it explicitly targets and processes this exact anchor state. This kind of masked inner-loop refinement is especially natural for DLMs: bidirectional denoising lets the model aggregate information from all visible tokens while updating multiple masked positions in a single step, whereas comparable hole-filling supervision is less direct under standard left-to-right auto-regressive factorization.

We formulate the inner loop as a two-stage gradient update (K = 2), initializing the fast weights to zero (ϕ 0 = 0). In the first stage (Pre-Anchor Alignment), we construct a noisier local state x t pre (where t pre > t) by further masking the anchor state x t. The model then denoises x t pre toward the anchor state x t. In the second stage (Anchor-to-Target), the model takes the exact anchor state x t and predicts the final clean state x 0.

Formally, the fast weights accumulate the trajectory dynamics through the following sequence of updates:

$$
L(1)
\tag{1}
$$
> Equation 1 JSON: `assets/equations/equation_0011.json`
> Equation 1 image: `assets/equations/equation_0011.png`

$$
ϕ 1 = ϕ 0 − η∇ϕ L(1)
\tag{1}
$$
> Equation 1 JSON: `assets/equations/equation_0012.json`
> Equation 1 image: `assets/equations/equation_0012.png`

$$
L(2)
\tag{2}
$$
> Equation 2 JSON: `assets/equations/equation_0015.json`
> Equation 2 image: `assets/equations/equation_0015.png`

$$
ϕ 2 = ϕ 1 − η∇ϕ L(2)
\tag{2}
$$
> Equation 2 JSON: `assets/equations/equation_0014.json`
> Equation 2 image: `assets/equations/equation_0014.png`

where η is the inner learning rate. Together, these two stages encourage the fast weights to capture how a noisier local state transitions through the anchor state x t toward the clean target x 0. In this way, the inner loop accumulates an anchor-centered local trajectory in the final parametric state ϕ 2.

### The Outer Loop: Conditioned Denoising

After the inner loop accumulates the adapted parameters ϕ 2 for a given batch, the outer objective is computed on the exact same anchor timestep t and masked state x t. The full outer objective mirrors standard MDLM training, but conditions the prediction on the Parametric Memory ϕ 2:

$$
L MemDLM(\\theta) = E t∼U(0,1),x 0
$$
> Equation 17 JSON: `assets/equations/equation_0017.json`
> Equation 17 image: `assets/equations/equation_0017.png`

L MemDLM(θ) = E t∼U(0,1),x 0

To update the base parameters θ, we employ a First-Order approximation. This avoids the computationally prohibitive calculation of second-order Hessian matrices by treating the inner gradients ∇ϕ L inner as independent of θ during the outer backward pass. For a given training batch, the update rule for the base model is computed using the per-sample loss:

!

where β is the outer learning rate. Because the fast weights ϕ 2 can absorb part of the batch-specific trajectory information, the gradients ∇θ generated by Equation (10) may place less pressure on the base model to memorize local context purely in token space. This interpretation is consistent with the faster convergence and stronger downstream performance observed in our experiments.

## Experiments

To validate the effectiveness of Parametric Memory in diffusion language models, our experiments are organized around four questions. First, does MemDLM improve long-context retrieval and generalization? Second, what aspects of the training-stage design make memory-aware training effective? Third, how should the inference-stage adaptation be used in practice? Finally, which components of the overall algorithm are essential rather than optional? We answer these questions through main-result comparisons, targeted training- and inference-stage analyses, and core ablations.

### Experimental Setup

Implementation and Baselines. We implement our framework in PyTorch [22], building upon the open-source dllm [23] training library, and utilize the lm-evaluation-harness [24] for all downstream evaluations. We study two backbones in the main experiments: LLaDA-MoE-7B-A1B-Base [18] and LLaDA2.1-mini [20]. For brevity, we refer to them as LLaDA- MoE and LLaDA2.1, respectively, throughout the paper. Unless otherwise noted, the targeted training-stage analyses and core ablations are conducted on the LLaDA-MoE backbone, while the main retrieval and optimization comparisons are reported on both backbones. The baseline in our experiments is the Standard MDLM [2], which represents the conventional diffusion language model training approach. This baseline optimizes only the standard denoising objective (equivalent to our outer loop) and employs a time-dependent reweighting schedule to balance loss contributions across different noise levels.

Training Data and Processing. We conduct instruction tuning using the LongAlpaca dataset [25], which is specifically designed to elicit long-context understanding and generation capabilities. To maintain computational efficiency, we filter the dataset to include only sequences with a maximum length of 4, 096 tokens. During training, we apply an asymmetric masking strategy: prompt tokens are left strictly unmasked (and excluded from the loss computation), while the noise and masking processes are applied exclusively to the response tokens.

Hyperparameters and Optimization. To ensure parameter efficiency, we load the base model in 4-bit quantization and apply Low-Rank Adaptation (LoRA) [26] for the outer loop updates, setting the rank r = 32 and α = 64. The outer loop is optimized using AdamW [27] with a learning rate of 2 × 10−5 and a cosine learning rate scheduler featuring a 0.1 warmup ratio.

For the Parametric Memory mechanism (the inner loop), we utilize a separate, transient set of LoRA adapters with an identical configuration (r = 32, α = 64). To minimize overhead, the inner loop only targets the Feed-Forward Network (FFN) modules in the final fraction of the transformer layers (controlled via a configurable hyperparameter). The inner loop adaptation consists of a single epoch of SGD optimization with a learning rate of 0.1 and gradient clipping set to 1.0.

Evaluation Benchmarks. We evaluate long-context capabilities in two stages. First, we perform rigorous information retrieval testing using the RULER (Needle-in-a-Haystack) [19] and BABI- Long [21] benchmarks to isolate the model’s ability to precisely locate and extract information from extensive contexts. Second, we assess generalized long-context reasoning using the LongBench [28] dataset suite, encompassing tasks like Multi-Document QA, Summarization, and Code Completion. All models are evaluated under identical generation configurations to ensure fair comparisons.

### Main Results: Long-Context Information Retrieval

Information retrieval in extended contexts, commonly evaluated as "Needle-in-a-Haystack" (NIAH), poses a significant challenge for DLMs. In standard models, retrieving a specific "needle" relies entirely on token-level attention over thousands of irrelevant "haystack" tokens. As the context length grows, the attention mechanism becomes increasingly diluted. During the sequential generation of

> Table JSON: `assets/tables/table_0001.json`
> Table 1: Performance on challenging Needle-in-a-Haystack (NIAH) tasks from RULER and BABI- Long across increasing context lengths. We report results for two backbones under three settings: Standard MDLM, MemDLM (Train-Only), and MemDLM (Train & Inference). RULER columns correspond to the Multi-Value (MV), Variable Tracking (VT), and Common Words Extraction (CWE) sub-tasks. Bold indicates the best result within each backbone block.

> Table JSON: `assets/tables/table_0002.json`
> Table 2: Length extrapolation on Needle-in-a-Haystack tasks using the LLaDA-MoE backbone, evaluated beyond its native 8K context setting. MemDLM continues to outperform Standard MDLM at 16K and 32K across RULER and BABILong.

These results provide strong evidence for the efficacy of Parametric Memory. The strong Train-Only results suggest that memory-aware training already teaches the base model to form more robust long-context representations. When the inner loop is additionally applied over the prompt at inference time, MemDLM gains a more explicit prompt-conditioned memory pathway. We interpret this extra inference-time effect as an in-weight retrieval mechanism, which further helps the model mitigate the token-level attention bottleneck during generation.

Length extrapolation via Parametric Memory. To further probe the robustness of this mechanism, we evaluate the LLaDA-MoE backbone beyond its native 8K context setting and test NIAH retrieval at 16K and 32K context lengths. As shown in Table 2, absolute performance drops for all methods as the context becomes substantially longer, but MemDLM continues to improve over the baseline even in this extrapolation regime. This suggests that Parametric Memory does not merely fit the training context range; it also helps preserve useful long-context representations when the model is pushed beyond the lengths emphasized during training.

### Long-Context Generalization

Building on the retrieval results, we evaluate our method on diverse real-world tasks from the LongBench dataset. Here, we compare Standard MDLM against our MemDLM model under two

> Table JSON: `assets/tables/table_0003.json`
> Table 3: Performance on LongBench datasets. Standard MDLM is the baseline. MemDLM (Train-Only) uses Parametric Memory during training but disables it at inference. MemDLM (Train & Inference) reactivates the inner loop at inference time.

![Figure 4](assets/figures/page_008_vec_001.png)

_Figure 4: Training dynamics on the LLaDA-MoE and LLaDA2.1 backbones. We compare Standard MDLM and MemDLM using train loss and evaluation loss. For the train-loss panels, faint curves show the raw logged values and bold curves show a smoothed trend. Across both backbones, MemDLM converges faster and reaches consistently lower train and evaluation loss, supporting the view that memory-aware training improves optimization by reducing the burden of preserving local traj_

As shown in Table 3, integrating Parametric Memory during training significantly improves the base model’s ability to handle long-context tasks, even when evaluated zero-shot (Train-Only). This mirrors the NIAH results and suggests that the training-time benefit already transfers to downstream longcontext reasoning. When the inner loop is reactivated during inference, we observe consistent further improvements across almost all tasks, indicating that prompt-specific adaptation is complementary to the gains already obtained during training.

Figure 4 examines the optimization behavior of
MemDLM more directly. Across both backbones,
MemDLM descends more rapidly in training loss and
also maintains lower evaluation loss throughout train-
ing. This pattern is consistent with our interpretation
that Bi-level Optimization with fast weights improves
the learned base model rather than merely providing
an inference-time mechanism. In particular, the gains
appear during training itself, supporting the claim that
Parametric Memory reduces optimization pressure by
allowing part of the local trajectory information to be
absorbed in parameter space.

![Figure 5](assets/figures/page_008_vec_002.png)

_Figure 5: Comparison with the untuned pre- trained LLaDA-MoE-7B-A1B-Base model across context lengths._

We further compare against the untuned LLaDA-MoE-7B-A1B-Base model to understand how training changes pretrained long-context behavior. Figure 5 shows that Standard MDLM fine-tuning does not uniformly preserve this capability: it drops below the base model at 1K and 2K, even though it improves at longer contexts. In contrast, MemDLM improves consistently over both the pretrained base and the Standard MDLM-trained model across the full 1K–32K range. This suggests that memory-aware training better preserves and refines the pretrained model’s long-context representations than standard MDLM fine-tuning.

![Figure 6](assets/figures/page_009_vec_001.png)

_Figure 6: Inner-loop supervision analysis on the LLaDA-MoE, evaluated on BABILong-1K._

![Figure 7](assets/figures/page_009_vec_002.png)

_Figure 7: Adaptation scope analysis on the LLaDA-MoE, evaluated on BABILong-1K._

Inner-loop supervision. An important training-stage question is what kind of supervision most effectively encodes useful trajectory information in the fast weights. Beyond the default cross-entropy objective, we explore several alternatives, including logit distillation with Kullback-Leibler (KL) [29] or reverse-KL divergence and hidden-state distillation with cosine or MSE losses. These variants are a form of self-distillation: the teacher and student are not different models, but different views of the same model under different information states. Specifically, both branches use the same underlying model with the current fast-weight state, but the teacher branch is evaluated under no_grad while the student branch carries gradients through the inner loop. In the progressive setting, the teacher is evaluated on the next denoising state and therefore sees strictly more revealed context than the student on the current state. This makes the supervision a form of privileged-information self-distillation rather than a standard same-input teacher-student setup. This formulation is conceptually related to recent self-adaptation methods [30] that distill from a stronger information state of the same model, as well as recent self-distillation and reinforcement-learning formulations [31, 32, 33]. Figure 6 summarizes a controlled comparison on the LLaDA-MoE backbone, evaluated on BABILong-1K. A notable result is that MemDLM remains trainable under several quite different inner-loop supervision choices, including multiple self-distillation objectives. This suggests that the overall memory-writing mechanism is not tightly coupled to a single particular loss design. Among the tested variants, the plain token-level cross-entropy objective still achieves the best final score (0.684), outperforming logit distillation with KL (0.660), logit distillation with reverse-KL (0.624), hidden-state cosine (0.582), and hidden-state MSE (0.572). Cross-entropy therefore provides the most effective supervision, while the self-distillation variants still demonstrate that the method continues to work.

Adaptation scope. We also study where the inner-loop updates should be applied. Figure 7 compares several adaptation scopes on the LLaDA-MoE backbone, again evaluated on BABILong- 1K. A striking phenomenon is that stronger inner-loop optimization does not necessarily imply better downstream adaptation: full-parameter updates achieve the lowest train loss, yet they underperform a much more restricted FFN-only update. Restricting the inner loop to FFN modules in the last 10% of layers yields the best downstream score (0.684), outperforming both shallower adaptation (0.616 at 5%) and broader adaptation (0.626 at 25%, 0.574 at 50%). Updating both FFN and attention modules at the same 10% scope also reduces performance (0.648), and using full-parameter adaptation instead of LoRA-style fast weights performs worse as well (0.602). This suggests that effective Parametric Memory depends not only on adaptation capacity, but also on constraining where the update is written: a moderate, targeted update space appears to preserve more task-useful structure than the most flexible one.

Gradient normalization in the inner loop. Because the inner loop performs rapid task-local adaptation, its update quality can be sensitive to how gradients are normalized across parameters. On the same LLaDA-MoE / BABILong-1K setting used above, local per-parameter gradient normalization with gradient clip 1.0 achieves the best score (0.684), whereas replacing it with global gradient normalization degrades performance to 0.632. Varying the clipping threshold under local normalization shows a weaker effect: clipping at 0.5 or 2.0 yields 0.630 and 0.640, respectively, while removing clipping entirely still remains competitive at 0.682. These results suggest that the important design choice is the local normalization itself, while the exact clipping threshold mainly plays a secondary role.

Pre-anchor design. Finally, we investigate the choice of the pre-anchor state x t pre used by the inner loop. In the anchor-consistent setting, the pre-anchor mask ratio is controlled by a pre-anchor scale hyperparameter s pre, which sets the starting ratio as min(1, max(s pre · t, t)) for anchor mask ratio t. Varying this scale shows that the design is meaningful but not overly fragile: a scale of 1.5 performs best (0.684), while nearby values of 1.75 and 2.0 remain competitive (0.674 and 0.678). In contrast, a smaller scale of 1.25 performs noticeably worse (0.624). This pattern suggests that the inner loop benefits from a sufficiently noisier pre-anchor state to expose informative local trajectory structure, but that the method is relatively robust once this noisier regime is reached.

### Understanding MemDLM During Inference

Although the largest conceptual effect of MemDLM appears during training, the inference stage still introduces several meaningful design choices. In this section, we study how the inner loop should be used at inference time and how sensitive the adaptation procedure is to the synthetic anchor construction. Our current inference procedure applies the inner loop to the prompt before generation, which empirically provides the most reliable way to improve context internalization and long-context understanding. An alternative design would adapt during the decoding process itself, but we treat this as future work because it introduces a substantially different optimization loop during generation.

At inference time, the anchor state is not prescribed by training data and must therefore be chosen by design. We parameterize this choice by the target mask ratio of the adapted prompt state. Figure 8 shows that the method is relatively insensitive to this hyperparameter: the tested ratios from 0.2 to 0.8 all exhibit the same qualitative degradation pattern as context length increases, and their scores remain close throughout the full 1K–16K range. Even at 16K, the results stay tightly grouped between 0.212 and 0.232. We therefore use 0.2 as the default not because it is uniquely optimal, but because it is a simple and robust operating point within a fairly flat design space.

### Ablation of Core Design Choices

Beyond exploratory analyses, we also perform ablations that test which components of MemDLM are necessary for the method to work. These experiments focus on removing or reversing core design choices rather than tuning them.

Consistency of the trajectory design. One central hypothesis of MemDLM is that the inner loop should remain consistent with the anchor-centered outer objective. To test this, we compare our default consistent design against an inconsistent progressive-memory variant. Figure 9 shows a clear optimization gap: the consistent trajectory converges to substantially lower training loss, while the inconsistent variant plateaus much earlier. This gap also carries over to downstream

![Figure 8](assets/figures/page_010_vec_001.png)

_Figure 8: Sensitivity to the inference an- chor ratio. We vary the target mask ratio of the adapted prompt state on the LLaDA- MoE backbone and evaluate from 1K to 16K. All settings follow a similar trend across con- text lengths._

One possible reason for this low sensitivity is the bidirectional nature of DLM denoising. When the inner loss is computed, the model can attend to all tokens in the corrupted prompt, so changing whether a token is treated as observed input or as a supervised prediction target does not fully remove its information from the local computation. In this view, varying the anchor ratio mainly changes how the prompt information is partitioned within the denoising objective, rather than whether that information is accessible at all, which may explain why a broad range of ratios behaves similarly in practice.

![Figure 9](assets/figures/page_010_vec_002.png)

_Figure 9: Consistency of the trajectory design. Training loss for an inconsistent progressive-memory variant and our consis- tent design._

![Figure 10](assets/figures/page_011_vec_001.png)

_Figure 10: Role of the two inner-loop stages. Training loss for pre-anchor-only, anchor-to- target-only, and two-stage variants on the LLaDA- MoE, evaluated on BABILong-1K._

![Figure 11](assets/figures/page_011_vec_002.png)

_Figure 11: Multiple pre-anchor steps. Training loss for 2-step, 3-step, and 4-step variants on the LLaDA-MoE, evaluated on BABILong-1K._

retrieval, improving BABILong-1K from 0.604 to 0.684. These results suggest that trajectory consistency is not merely an implementation detail; it is a core ingredient that allows the fast-weight updates to support, rather than conflict with, the anchor-centered outer objective.

Role of the two inner-loop stages. We ablate the two-stage inner loop by using only the pre-anchor stage or only the anchor-to-target stage. Figure 10 shows that neither stage alone is sufficient: using only the anchor-to-target stage reaches 0.646, while using only the pre-anchor stage with anchortoken-only supervision reaches 0.620. Combining the two stages is clearly better, but the exact pre-stage target also matters. If we keep both stages but restrict the pre-anchor loss to anchor-tokenonly supervision, the score improves to 0.668; however, our default design, which uses a broader clean-target supervision in the pre-anchor stage and then follows it with the anchor-to-target stage, performs best at 0.684.

This comparison reveals an important interaction effect. In isolation, anchor-token-only pre-anchor supervision is stronger than the broader clean-target pre-anchor supervision (0.620 vs. 0.604), but once the anchor-to-target stage is added, the broader clean-target supervision becomes more complementary and yields the strongest final result. Operationally, the default pre-anchor objective does not stop at predicting only the subset of tokens that will become visible at the anchor state; instead it predicts a broader clean target from the pre-anchor state. This is slightly richer than the idealized stagewise factorization described in Section 3, but empirically it provides a better first-stage update for the subsequent anchor-to-target refinement.

Multiple pre-anchor steps. Finally, we explore whether using multiple pre-anchor steps further improves performance. Figure 11 shows a clear divergence between inner-loop optimization and downstream utility. Increasing the number of pre-anchor steps from the default 2-step design to 3-step and 4-step variants steadily lowers the training loss, but the final BABILong-1K score drops from 0.684 to 0.644 and then to 0.590. In other words, deeper trajectory unrolling makes the inner objective easier to optimize, yet produces worse parametric memory for the downstream retrieval.

This result suggests that the current two-stage design is already sufficient for capturing the local trajectory information that matters. Adding more pre-anchor steps may encourage the fast weights to specialize too strongly to the auxiliary denoising path, rather than preserving the anchor-centered information that the outer objective ultimately needs. This observation is consistent with the other ablations in this section: lower inner-loop loss alone is not a reliable proxy for better adaptation.

## Related Work

MemDLM lies at the intersection of diffusion language modeling, fast-weight memory, bi-level adaptation, and inference-time adaptation.

Diffusion language models and the training-inference gap. Recent diffusion-based language models have shown that masked denoising can support high-quality text generation and flexible infilling, making DLMs a compelling alternative to standard auto-regressive decoding [1, 2, 3, 4, 5,

34, 6, 7, 8, 9, 35, 36]. At the same time, several recent works explicitly target the training-inference discrepancy in diffusion decoding. MDPO addresses the gap by training over progressive, inferencealigned remasking schedules [10]; trajectory-aware reinforcement learning (RL) frameworks instead optimize the denoising path as a sequential decision process rather than only token-level crossentropy [11, 12]; and planner-alignment methods use the model’s own confidence or self-planning signal to reweight training along generation paths [13]. MemDLM is motivated by the same mismatch, but differs from these approaches by addressing it through an explicit inner-loop simulation that writes local denoising trajectory information into fast weights during training, rather than primarily modifying the denoising policy or directly optimizing trajectory-level decisions.

Fast weights and parametric memory. The idea that neural networks can store short-lived, samplespecific information in parameters rather than only in activations has a long history in the fast-weights literature [14, 15, 16, 37]. Related memory-based adaptation methods, many of them developed in auto-regressive or modern LLM settings, further show that test-time or local weight updates can act as a form of parametric memory stored in the weights, enabling rapid adaptation from local context [17, 38, 39, 40, 41, 42, 43]. MemDLM is closely connected to this perspective: its fast weights act as a transient parametric memory of a local denoising trajectory. Unlike generic memoryaugmented models, however, our memory is not an external module or cache; it is formed directly through inner-loop gradient updates aligned with diffusion denoising states.

Meta-learning and Bi-level Optimization. MemDLM also relates to meta-learning methods that use inner-loop adaptation together with an outer-loop objective [44, 45, 46, 47, 48, 49, 50, 51]. As in these approaches, our method optimizes base parameters so that a small number of fast updates becomes useful at deployment time. The difference is that our inner loop is not intended to adapt across task episodes in the usual few-shot sense. Instead, it internalizes the local denoising trajectory of each training sample, making the bi-level structure serve as a mechanism for memory formation under diffusion corruption rather than as a generic meta-learner.

Test-time training. Finally, MemDLM is related to test-time training methods that update model behavior on the fly using unlabeled or self-supervised signals [52, 53, 54, 55, 56, 57, 58, 30]. Recent language-model variants push this idea further. TTT-E2E frames long-context modeling as continual test-time learning, using the same next-token objective at training and deployment time so that incoming context can be compressed into the model weights during inference [58]. SEAL instead studies self-adapting language models that generate their own update directives or synthetic supervision and then perform persistent weight updates under a reward-driven adaptation loop [30]. This connection is most visible when we re-enable the inner loop at inference time, allowing the model to internalize the prompt into fast weights before generation. However, our empirical results show that the main gains already emerge from memory-aware training, while inference-time adaptation provides an additional prompt-specific refinement on top of this training-induced robustness. In this sense, MemDLM connects test-time training to diffusion denoising, but is not reducible to a purely inference-time tuning method.

## Conclusion

We introduced MemDLM, a memory-aware training framework for diffusion language models built on Bi-level Optimization and fast weights acting as Parametric Memory. Our central finding is that simulating denoising trajectories during training does more than mimic inference: it changes what the base model learns. By allowing fast weights to absorb batch-specific trajectory information, MemDLM reduces the burden of preserving context purely in token space, leading to improved optimization, lower exposure bias, and stronger long-context performance even in the Train-Only setting. We further showed that re-enabling the inner loop at inference time provides an additional prompt-specific adaptation pathway. We interpret this extra effect as an emergent in-weight retrieval mechanism, which complements rather than replaces the gains already obtained from training. Taken together, our results suggest that reducing train-inference mismatch through parameter-space memory is a promising direction for improving the robustness and long-context capabilities of diffusion language models.

## References

[1] Jacob Austin, Daniel D Johnson, Jonathan Ho, Daniel Tarlow, and Rianne Van Den Berg. Structured denoising diffusion models in discrete state-spaces. Advances in neural information processing systems, 34:17981–17993, 2021.

[2] Subham S Sahoo, Marianne Arriola, Yair Schiff, Aaron Gokaslan, Edgar Marroquin, Justin T Chiu, Alexander Rush, and Volodymyr Kuleshov. Simple and effective masked diffusion language models. Advances in Neural Information Processing Systems, 37:130136–130184, 2024.

[4] Jiaxin Shi, Kehang Han, Zhe Wang, Arnaud Doucet, and Michalis Titsias. Simplified and generalized masked diffusion for discrete data. Advances in neural information processing systems, 37:103131–103167, 2024.

[7] Andrew Campbell, Joe Benton, Valentin De Bortoli, Thomas Rainforth, George Deligiannidis, and Arnaud Doucet. A continuous time framework for discrete denoising models. Advances in Neural Information Processing Systems, 35:28266–28279, 2022.

[9] Chenlin Meng, Kristy Choi, Jiaming Song, and Stefano Ermon. Concrete score matching: Generalized score matching for discrete data. Advances in Neural Information Processing Systems, 35:34532–34545, 2022.

[14] Tijmen Tieleman and Geoffrey Hinton. Using fast weights to improve persistent contrastive divergence. In Proceedings of the 26th annual international conference on machine learning, pages 1033–1040, 2009.

[15] Jimmy Ba, Geoffrey E Hinton, Volodymyr Mnih, Joel Z Leibo, and Catalin Ionescu. Using fast weights to attend to the recent past. Advances in neural information processing systems, 29, 2016.

[16] Geoffrey E Hinton and David C Plaut. Using fast weights to deblur old memories. In Proceedings of the ninth annual conference of the Cognitive Science Society, pages 177–186, 1987.

[21] Yuri Kuratov, Aydar Bulatov, Petr Anokhin, Ivan Rodkin, Dmitry Sorokin, Artyom Sorokin, and Mikhail Burtsev. Babilong: Testing the limits of llms with long context reasoning-in-a-haystack. Advances in Neural Information Processing Systems, 37:106519–106554, 2024.

[22] Adam Paszke, Sam Gross, Francisco Massa, Adam Lerer, James Bradbury, Gregory Chanan, Trevor Killeen, Zeming Lin, Natalia Gimelshein, Luca Antiga, et al. Pytorch: An imperative style, high-performance deep learning library. Advances in neural information processing systems, 32, 2019.

[23] Zhanhui Zhou, Lingjie Chen, Hanghang Tong, and Dawn Song. dllm: Simple diffusion language modeling, 2026.

[24] Leo Gao, Jonathan Tow, Baber Abbasi, Stella Biderman, Sid Black, Anthony DiPofi, Charles Foster, Laurence Golding, Jeffrey Hsu, Alain Le Noac’h, Haonan Li, Kyle McDonell, Niklas Muennighoff, Chris Ociepa, Jason Phang, Laria Reynolds, Hailey Schoelkopf, Aviya Skowron, Lintang Sutawika, Eric Tang, Anish Thite, Ben Wang, Kevin Wang, and Andy Zou. The language model evaluation harness, 07 2024.

[25] Yukang Chen, Shaozuo Yu, Shengju Qian, Haotian Tang, Xin Lai, Zhijian Liu, Song Han, and Jiaya Jia. Long alpaca: Long-context instruction-following models. https://github.com/ dvlab-research/LongLoRA, 2023.

[28] Yushi Bai, Xin Lv, Jiajie Zhang, Hongchang Lyu, Jiankai Tang, Zhidian Huang, Zhengxiao Du, Xiao Liu, Aohan Zeng, Lei Hou, et al. Longbench: A bilingual, multitask benchmark for long context understanding. In Proceedings of the 62nd annual meeting of the association for computational linguistics (volume 1: Long papers), pages 3119–3137, 2024.

[38] Jihoon Tack, Jaehyung Kim, Eric Mitchell, Jinwoo Shin, Yee Whye Teh, and Jonathan Richard Schwarz. Online adaptation of language models with a memory of amortized contexts. Advances in Neural Information Processing Systems, 37:130109–130135, 2024.

[41] Yu Wang, Yifan Gao, Xiusi Chen, Haoming Jiang, Shiyang Li, Jingfeng Yang, Qingyu Yin, Zheng Li, Xian Li, Bing Yin, Jingbo Shang, and Julian J. McAuley. MEMORYLLM: towards self-updatable large language models. In Forty-first International Conference on Machine Learning, ICML 2024, Vienna, Austria, July 21-27, 2024. OpenReview.net, 2024.

[43] Shankar Padmanabhan, Yasumasa Onoe, Michael Zhang, Greg Durrett, and Eunsol Choi. Propagating knowledge updates to lms through distillation. Advances in Neural Information Processing Systems, 36:47124–47142, 2023.

[44] Sebastian Thrun and Lorien Pratt. Learning to learn: Introduction and overview. In Learning to learn, pages 3–17. Springer, 1998.

[45] Chelsea Finn, Pieter Abbeel, and Sergey Levine. Model-agnostic meta-learning for fast adaptation of deep networks. In International conference on machine learning, pages 1126–1135. PMLR, 2017.

[47] Oriol Vinyals, Charles Blundell, Timothy Lillicrap, Daan Wierstra, et al. Matching networks for one shot learning. Advances in neural information processing systems, 29, 2016.

[48] Jake Snell, Kevin Swersky, and Richard Zemel. Prototypical networks for few-shot learning. Advances in neural information processing systems, 30, 2017.

[49] Adam Santoro, Sergey Bartunov, Matthew Botvinick, Daan Wierstra, and Timothy Lillicrap. Meta-learning with memory-augmented neural networks. In International conference on machine learning, pages 1842–1850. PMLR, 2016.

[50] Aravind Rajeswaran, Chelsea Finn, Sham M Kakade, and Sergey Levine. Meta-learning with implicit gradients. Advances in neural information processing systems, 32, 2019.

[51] Shivam Garg, Dimitris Tsipras, Percy S Liang, and Gregory Valiant. What can transformers learn in-context? a case study of simple function classes. Advances in neural information processing systems, 35:30583–30598, 2022.

[52] Yu Sun, Xiaolong Wang, Zhuang Liu, John Miller, Alexei Efros, and Moritz Hardt. Test-time training with self-supervision for generalization under distribution shifts. In Hal Daumé III and Aarti Singh, editors, Proceedings of the 37th International Conference on Machine Learning, volume 119 of Proceedings of Machine Learning Research, pages 9229–9248. PMLR, 13–18 Jul 2020.

[55] Dequan Wang, Evan Shelhamer, Shaoteng Liu, Bruno Olshausen, and Trevor Darrell. Tent: Fully test-time adaptation by entropy minimization. In International Conference on Learning Representations, 2021.
