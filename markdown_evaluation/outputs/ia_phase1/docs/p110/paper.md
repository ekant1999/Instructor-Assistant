---
title: "Scaling DoRA: High-Rank Adaptation via Factored Norms and Fused Kernels"
paper_id: 110
source_pdf: "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA/Instructor-Assistant/markdown_evaluation/pdfs/ResearchPapers/c4a536b15a8624a5.pdf"
generated_at: "2026-04-05T20:56:23.323642+00:00"
num_figures: 12
num_tables: 16
num_equations: 32
---

Alexandra Zelenin∗ Alexandra Zhuravlyova

## Abstract

Abstract

Weight-Decomposed Low-Rank Adaptation (DoRA; Liu et al. [2024]) extends LoRA by decoupling weight magnitude from direction, but its forward pass requires the row-wise norm ∥W + s BA∥row, a computation that every major framework we surveyed implements by materializing the dense [d out, d in] product BA. At d in = 8192 and rank r = 384, a single module’s norm requires ∼512 MB of transient working memory in bf16, making high-rank DoRA costly and often infeasible on common single-GPU setups once hundreds of adapted modules and checkpointing are involved. We present two systems contributions: a factored norm that decomposes the squared norm into base, cross, and Gram terms computable through O(d out r + r 2) intermediates, eliminating the dense product. Fused Triton kernels collapse the four-kernel DoRA composition into a single pass, reducing memory traffic by ∼4× and using a numerically stable form that avoids catastrophic cancellation in the near-unity rescaling regime where magnitude scales concentrate in practice. Across six 8–32B vision-language models (VLMs) on three NVIDIA GPUs (RTX 6000 PRO, H200, B200) at r=384 in bf16, the fused implementation is 1.5–2.0× faster than HF PEFT’s DoRA implementation for inference, and 1.5–1.9× faster for gradient computation (optimizer step excluded), with up to 7 GB lower peak VRAM. Microbenchmarks on six GPUs spanning four architecture generations (L40S, A100, RTX 6000 PRO, H200, B200, B300) confirm 1.5–2.7× compose-kernel speedup. Final-logit cosine similarity exceeds 0.9999 across all model/GPU pairs, and multi-seed training curves match within 7.1 × 10−4 mean per-step loss delta over 2000 steps.

## Introduction

> Equation 1 JSON: `assets/equations/equation_0001.json`
> Equation 1 image: `assets/equations/equation_0001.png`

Low-Rank Adaptation (LoRA; Hu et al. 2022) is the dominant method for parameter-efficient finetuning. DoRA [Liu et al., 2024] extends LoRA by decomposing the adapted weight into magnitude and direction: W′ = m ⊙ W + s BA

where W ∈ R d out×d in is the frozen base weight, B ∈ R d out×r and A ∈ R r×d in are low-rank factors, s is a scaling coefficient (e.g., rsLoRA; Kalajdzievski 2023), and m ∈ R d out is a learnable magnitude vector. High-rank configurations narrow the gap to full fine-tuning on complex downstream tasks [Hu et al., 2022, Liu et al., 2024]. We treat weights as [d out, d in] and compute per-output-row norms (dim=1), consistent with PEFT and torchtune.

The bottleneck is the row-wise L 2 norm of the composed weight W + s BA. Hugging Face PEFT [Mangrulkar et al., 2022] (and five other major frameworks we surveyed: torchtune, Unsloth, SWIFT, LLaMA-Factory, Axolotl; see Appendix G) computes this by constructing a d in × d in identity matrix, thereby materializing the dense product BA:

This incurs O(d 2 in) memory for the identity matrix alone: 32 MB at d in = 4096, 128 MB at d in = 8192 in bf16. Including the dense BA product and composed-weight copy, a single module allocates 3–4 dense [d out, d in] temporaries: ∼512 MB at d in = 8192. With gradient checkpointing [Chen et al., 2016], these temporaries are allocated twice per step. Across hundreds of adapted modules in an 8–32B model, this cumulative pressure is a major contributor to both speed degradation and OOM failures at high rank. The most obvious fix (computing lora_B.weight @ lora_A.weight directly) eliminates the identity matrix but still materializes the full [d out, d in] product, which is the dominant cost. We show in §5.3 that this “dense (B@A)” path provides inconsistent speedups that depend on GPU bandwidth class and sometimes runs slower than the PEFT baseline. This paper does not propose a new adapter architecture, optimizer, or training recipe. Our contribution is systems-oriented: we execute the same DoRA computation with a smaller working set and lower memory traffic. Specifically:

1. A factored norm computation (§2) decomposes ∥W + s BA∥2
row into three terms, each
evaluable through O(d out r+r 2) intermediates without materializing BA. At d = 8192, r = 512
in fp32, the theoretical persistent-memory reduction is 15× (Table 1).

2. Fused Triton kernels (§3) collapse the DoRA composition (g−1)⊙base+g⊙s⊙lora from four
CUDA kernel launches to one pass. A numerically stable form avoids catastrophic cancellation
when g ≈ 1. Forward speedup: 1.5–2.7× (geometric mean); backward speedup: 1.06–1.23×.
A three-tier runtime dispatch (§4) selects the optimal path (fused backward for training,
fused forward for inference, eager fallback for CPU or sub-crossover shapes), compatible with
torch.compile [Ansel et al., 2024], gradient checkpointing, DeepSpeed ZeRO [Rajbhandari
et al., 2020], and FSDP1.

Both contributions are validated on six NVIDIA GPUs spanning four architecture generations (L40S, A100, RTX 6000 PRO, H200, B200, B300; 48–268 GB) with model-level benchmarks on three GPUs across six 8–32B VLMs (§5). Throughout this paper, four configurations are compared: PEFT (unmodified HF PEFT identity-matrix path), Dense (B@A) (direct product, still materializes the full matrix), Eager (our factored norm with PyTorch composition), and Fused (our factored norm with Triton kernels).

Factored Norm Computation

### Algebraic Decomposition

The row-wise squared norm of the composed weight expands into three terms:

> Equation 2 JSON: `assets/equations/equation_0002.json`
> Equation 2 image: `assets/equations/equation_0002.png`

where ⟨·, ·⟩row denotes the row-wise inner product. Each term is computable through low-rank intermediates:

Base norm. ∥W∥2 row accumulates via chunks along d in, producing a vector of size d out. Chunking limits working memory to a configurable budget (default: 256 MB).

Cross term. The row-wise inner product rewrites as:

> Equation 3 JSON: `assets/equations/equation_0003.json`
> Equation 3 image: `assets/equations/equation_0003.png`

BA norm. The row-wise squared norm factors through the Gram matrix:

> Equation 4 JSON: `assets/equations/equation_0004.json`
> Equation 4 image: `assets/equations/equation_0004.png`

where G = AA⊤ ∈ R r×r also accumulates chunk-wise. At r = 512 in fp32, G occupies 1 MB.

### Assembly and Precision

The three per-row scalars assemble into the weight norm:

r

> Equation 5 JSON: `assets/equations/equation_0005.json`
> Equation 5 image: `assets/equations/equation_0005.png`

The magnitude division is always computed in PyTorch after the kernel returns:

This ensures identical precision regardless of whether the Triton or PyTorch norm path produced w norm, eliminating a source of fidelity divergence we observed at large activation scales (see §5.8). All accumulation is performed in fp32 under torch.no_grad() with autocast disabled. Disabling autocast alone does not force fp32 when inputs are bf16, so each chunk of W, A, B, and the intermediate U c is explicitly cast to fp32 before accumulation. This is consistent with the DoRA paper’s instruction (Section 4.3) to treat the norm as a detached constant [Liu et al., 2024]. We use g consistently throughout to denote the post-division scale, distinct from the learnable magnitude m.

### Complexity

Table 1 compares asymptotic and concrete memory costs.

Why the measured reduction is smaller. The dominant transient is the base-norm computation (Term 1 of Equation 2): the chunked ∥W∥2 row accumulation creates a [d out, chunk_size] fp32 buffer that, at the default budget and d = 8192, approaches 256 MB, accounting for most of the 241 MB measured delta. This cost is rank-independent: identical at r = 16 and r = 768. The theoretical reduction, which counts only rank-dependent tensors (U and G), correctly predicts the asymptotic benefit as rank grows. Since W is frozen, ∥W∥2 row could be precomputed into a [d out] buffer (16 KB at d out = 4096), eliminating this transient entirely. We leave this caching for future work.

> Table JSON: `assets/tables/table_0001.json`
> Table 1: The factored norm reduces rank-dependent persistent memory by 15× at d=8192, r=512 in fp32. Measured reductions are smaller (3.2×) because allocator deltas include the rank-independent base-norm transient (§2.3).

Compute tradeoff. The factored norm is ∼4.8× slower than the dense reference when measured isolation (H200, fp32) because the reference performs a single contiguous torch.linalg.norm call, while the factored path uses multiple chunked matmuls. The system is faster end-to-end because the reference first materializes the full [d out, d in] product; it is this materialization, not the norm itself, that dominates time and memory. On lower-bandwidth hardware (RTX 6000 PRO, GDDR7), the factored norm matches or outperforms the reference at production ranks (r ≤ 384) for large weight matrices, so the 4.8× figure is a conservative bound.

All accumulation in fp32 under torch.no_grad(), autocast disabled. Cast W chunks, A, B to fp32 on the fly.

Notes: Chunk size aligns to 64 for Tensor Core MMA. U c is never stored for multiple chunks simultaneously. When s=0, cross and ba_sq are skipped; U c and G are not allocated. G is ≤ 2.4 MB at r = 768 in fp32.

Fused Triton Kernels

### Compose Kernel

The DoRA composition (g−1) ⊙ base + g ⊙ s ⊙ lora decomposes into four sequential element-wise operations in standard PyTorch, each launching a separate CUDA kernel: 3 reads + 1 write per op yields ∼12 memory passes total. The fused Triton [Tillet et al., 2019] kernel collapses these into a single pass: 3 reads (base, lora, g) + 1 write, a ∼4× reduction in memory traffic. The realized speedup of 2.0–2.7× (rather than 4×) reflects the fact that the eager path is partially latency-bound by kernel-launch gaps; the fused kernel achieves ∼50% of peak HBM bandwidth (Figure 7), vs. ∼20% for the eager path.

Numerical stability. The algebraically equivalent form g ⊙ (s · lora + base) − base suffers from catastrophic cancellation when g ≈ 1. This regime is not hypothetical. The stored magnitude parameters reflect the heterogeneous row norms of pretrained weights and naturally vary across layers and models, but DoRA initializes m = ∥W∥row and magnitudes track weight norms throughout training, so the composed scale g = m/w norm concentrates tightly around unity (mean ≈ 1.0, std ≈ 0.0015). Measurement on a Qwen2-VL-7B adapter (r =128, 326 modules, 1.77M elements) shows that 100% of g values fall in the bf16 collapse zone (|g − 1| < ε bf16/2) and 20% in the fp16 zone: if (g−1) ⊙ base were evaluated in bf16, the base correction would vanish for every element; in fp16, for one in five. The stable form (g−1) ⊙ base + g ⊙ s ⊙ lora keeps the small correction (g−1) explicit, but its precision advantage depends on fp32 intermediate computation to prevent (g−1) from rounding to zero. Both the Triton kernel and PyTorch fallback use this form with fp32 compute. Figure 1 shows 3.0× lower peak error near g ≈ 1 compared to the naive alternative. Beyond the algebraic form,

![Figure 1](assets/figures/page_006_vec_001.png)

_Figure 1: The stable compose form achieves 3.0× lower peak error near g ≈1 (bf16, dout = 8192, din = 2048). The naive form g ⊙(s · lora + base) −base exhibits catastrophic cancellation; the stable form and fused kernel both remain near the bf16 quantization floor. Reference: fp64._

Autotuning. Optimal kernel configurations vary substantially across GPUs (∼9% pairwise agreement across six GPUs), requiring per-device autotuning rather than a static table. First-run autotuning takes 10–30 s per kernel, and caches persist in Triton’s default directory. Details in Appendix B.

### Backward Kernel

The fused backward computes d lora = g · s · d out and d base = (g−1) · d out in a single Triton pass. Two design decisions merit note:

• d mag via PyTorch reduction: The magnitude gradient uses a separate .sum() rather than tl.atomic_add, avoiding contention at large num_rows and the non-deterministic ordering of floating-point atomics.

### Norm Assembly Kernel

A second Triton kernel fuses Equation 5, computing w norm from the three factored terms. Storereload barriers prevent FMA fusion, and an inline PTX sqrt.rn.f32 instruction replaces Triton’s default approximate sqrt, exactly reproducing PyTorch’s evaluation order. The kernel stops at

![Figure 2](assets/figures/page_007_vec_001.png)

_Figure 2: Three-tier dispatch: fused backward for training (Tier 1), fused forward for inference (Tier 2), eager fallback for CPU, no-Triton, or sub-crossover shapes (Tier 3)._

> Table JSON: `assets/tables/table_0002.json`
> Table 2: Dispatch tiers and their selection criteria.

w norm; the magnitude division (Equation 6) remains in PyTorch so both norm paths share the same precision context. Appendix C provides exact specifications for all three kernels.

The composition path is selected at runtime by _compose_with_dispatch (Figure 2, Table 2). Four environment variables control kernel availability and working-set budgets; defaults require no configuration.

Tier 1 (Fused Backward). A dual-output Triton kernel computes both the output and the saved tensor inner = s·lora+base in a single pass, eliminating the forward-pass VRAM spike from sequential PyTorch ops. When the magnitude is frozen (requires_grad=False), the inner allocation is skipped entirely. The default auto-mode crossover requires d out ≥ 2048 and (batch × seq) × d out ≥ 2048 × 6144; smaller activations use Tier 3 because launch latency dominates. In the six evaluated

Tier 2 (Fused Forward). A forward-only Triton kernel with no autograd graph nodes, dispatched when requires_grad is false.

Tier 3 (Eager Fallback). Pure PyTorch; handles CPU, no-Triton, and sub-crossover training. Uses out-of-place composition when autograd is active to avoid aliasing.

Precision. All PyTorch compose paths produce bitwise-identical forward outputs by enforcing a single evaluation order. The Triton kernels preserve the same algebra but not bitwise equality (FMA contraction and reduction trees can perturb last bits); we treat Triton–PyTorch agreement as an empirical envelope: fp32 outputs stay within 10−4 max-abs error, bf16/fp16 remain within dtype-appropriate tolerances (§5.8).

Compatibility. The fused compose is registered as a custom op (peft::fused_dora_compose) via torch.library, making the dispatch graph-break-free under torch.compile when dropout is inactive (p = 0). DeepSpeed ZeRO-2/3 and FSDP1 are supported; FSDP2/DTensor is not (§6). The forward contract, torch.compile details, and the chunked-dropout path are specified in Appendices A and B.

Magnitude division. Across all tiers, g = m/ max(w norm, ϵ) is computed in PyTorch outside the no_grad norm context, ensuring identical precision regardless of execution tier.

## Experiments

### Setup

Microbenchmarks use six GPUs spanning four architecture generations (Table 3); model-level benchmarks use three GPUs (RTX 6000 PRO, H200, B200) with sufficient VRAM for the tested models. All GPUs run identical software: PyTorch 2.10.0+cu130, Triton 3.6.0, Transformers 5.2.0, CUDA 13.1, driver 580.126.09. The PEFT baseline is upstream commit 20a9829 (v0.18.0.rc0).1

Model-level benchmarks exclude the optimizer step to isolate DoRA overhead and use a partialsequence loss (1024 loss tokens) to match production RLHF/GRPO memory profiles; full-sequence loss creates a 6–12 GB logit spike that masks adapter working-set differences. A sensitivity check at 4096 loss tokens confirms speedups are unchanged. Each microbenchmark reports the median of 200 CUDA-event-timed trials (10 warmup); model-level benchmarks use 20 repeats (3 warmup, CV < 1.7%). Memory measurement methodology and full reproducibility instructions are provided in Appendix D.

### Model-Level Performance

Table 4 summarizes the headline result: gradient-computation speedup across six 8–32B VLMs on
three GPUs. The fused implementation is 1.46–1.87× faster than HF PEFT’s DoRA implementation
and 1.18–1.24× faster than our own eager baseline, with 1.3–6.7 GB lower peak VRAM (Table 8).
These timings cover forward+backward only (excluding optimizer updates), so the end-to-end

> Table JSON: `assets/tables/table_0003.json`
> Table 3: Benchmark hardware. “Micro”: microbenchmark coverage. “Model”: full model-level gradient-computation and inference benchmarks.

> Table JSON: `assets/tables/table_0004.json`
> Table 4: Gradient-computation speedup on 8–32B VLMs (r = 384, bf16, seq=4096, bs=1, ga=8, loss_tokens=1024, 20 repeats). The HF PEFT DoRA baseline takes 46–87% longer per iteration than fused. 32B models OOM on RTX 6000 PRO (96 GB) under all configurations. See Table 5 for absolute times.

> Table JSON: `assets/tables/table_0005.json`
> Table 5: Absolute gradient-computation time (seconds). Each iteration covers 8 gradient- accumulation micro-steps; 32 768 tokens total. Standard deviations ≤0.13 s (CV < 1.7%).

wall-clock gain is smaller: in the 2000-step convergence run, the same optimization reduced total training time by 8.3% once optimizer, data loading, and framework overhead were included (§5.9). The 32B models exceed the 96 GB RTX 6000 PRO under all configurations; this is a capacity limit, not a method-specific regression.

Inference. Inference speedup is higher than gradient computation: 1.5–2.0× over PEFT, 1.14– 1.20× over eager (Figure 4), because the forward pass concentrates the compose savings without dilution from backward-pass work. RTX 6000 PRO runs inference on all six models including 32B (84–88 GB peak), which OOM during gradient computation.

Speedup (PEFT / Fused)

1.75

1.73x

1.67x

1.24x

1.56x

1.53x

1.50x

1.47x

1.46x

1.18x

0.75

1.05

0.50

1.00

0.25

### OOM

0.00

### Gemma3-27B

![Figure 3](assets/figures/page_010_vec_001.png)

_Figure 3: Gradient-computation speedup across six VLMs on three GPUs (bf16, r=384, seq=4096). (a) Fused vs. the HF PEFT DoRA baseline: 1.46–1.87×. (b) Fused vs. eager: 1.18–1.24×. 32B models OOM on RTX 6000 PRO under all configurations._

Figure 4: Inference speedup: 1.5–2.0× over the HF PEFT DoRA baseline. All six models run on all
three GPUs, including 32B on RTX 6000 PRO (96 GB) that OOM during gradient computation.

High-rank scaling. Table 6 validates the high-rank framing at r =384, 512, and 768. Speedup vs. PEFT DoRA increases with rank for the 32B model (1.66× → 1.74×) because PEFT’s materialization cost grows with r, while the factored norm’s rank-dependent overhead (U and G) remains small. Speedup vs. eager decreases modestly (1.18× → 1.14×) as larger LoRA matmuls dilute the compose kernel’s contribution.

> Table JSON: `assets/tables/table_0006.json`
> Table 6: Speedup vs. the HF PEFT DoRA baseline grows with rank; speedup vs. eager decreases modestly (H200, bf16, seq=4096, 20 repeats).

![Figure 5](assets/figures/page_011_vec_001.png)

_Figure 5: Dense (B@A) position in the eager-to-fused gap (0% = eager, 100% = fused). Negative values: dense (B@A) is slower than eager. The benefit is GPU-bandwidth-sensitive; the factored approach is robust._

### Why Dense (B@A) Is Not Enough

Computing lora_B.weight @ lora_A.weight directly (the most obvious fix) eliminates the identity matrix but still materializes the full [d out, d in] product. Figure 5 shows that dense (B@A) captures 0% of the eager-to-fused gap on some model/GPU combinations and is sometimes slower than the eager baseline. Dense (B@A) also uses 1–2 GB more peak VRAM than fused on all tested models. The full factored norm is necessary for consistent gains across GPU architectures.

### Compose Kernel Performance

Figure 6 shows compose speedup across activation sizes on six GPUs. Geometric mean forward
speedup (bf16, all 20 shapes): 2.70× B200, 2.62× B300, 2.00× H200, 1.92× RTX 6000 PRO, 1.73×
A100, 1.47× L40S. The consistency from GDDR6 (0.86 TB/s) to HBM3e (7.7 TB/s) confirms the
gains derive from reduced memory traffic rather than architecture-specific effects.

Compose Kernel Speedup (bf16)

![Figure 6](assets/figures/page_012_vec_001.png)

_Figure 6: Compose kernel speedup vs. eager (bf16) across six GPUs. (a) Forward: 1.5–4.5×. (b) Autograd: gains compound with activation size._

Figure 7: Bandwidth utilization (fp32, six GPUs). Fused approaches ∼50% of peak on all architec-
tures; eager values are approximate lower bounds.

Bandwidth utilization. The fused kernel achieves 3950–4070 GB/s on B200/B300 (∼53% of peak), 2490–2540 GB/s on H200 (∼53%), 1040–1050 GB/s on A100 (∼52%), 880–890 GB/s on RTX 6000 PRO (∼55%), and 460–470 GB/s on L40S (∼54%) at the largest shapes (Figure 7). On B200, the eager path reaches only 17% of peak, yielding the largest absolute bandwidth gap. Throughput scales nearly linearly with peak bandwidth across the full 0.86–7.7 TB/s range, confirming these kernels are memory-bandwidth-bound.

![Figure 8](assets/figures/page_013_vec_001.png)

_Figure 8: Backward speedup (bf16). Below ∼4096 × 4096, launch overhead dominates; above ∼8192 × 8192, fused wins on all GPUs._

> Table JSON: `assets/tables/table_0007.json`
> Table 7: Norm memory: measured allocation delta and theoretical reduction (fp32, H200). Measured reductions are smaller than theoretical because they include the rank-independent base-norm transient (§2.3).

The backward kernel shows a clear crossover: below ∼2048 × 6144 (rows × d out), launch overhead dominates and fused can trail eager (0.88–0.99×); above ∼8192 × 8192, fused wins on all six GPUs (Figure 8). Geometric mean speedup (bf16, all shapes): 1.23× B200, 1.22× B300/RTX 6000 PRO, 1.16× A100, 1.08× H200, 1.06× L40S. Gradient correctness: fp32 d lora and d base match the eager baseline at tolerance floor; d mag shows ≤ 2.14 × 10−4 difference due to the separate reduction path.

### Norm Memory Reduction

Figure 9 and Table 7 show both theoretical and measured memory reductions. The 8192 × 28672
MoE shape achieves 11× measured reduction. The factored norm’s latency tradeoff (Figure 10) is
hardware-dependent: on RTX 6000 PRO, factored matches or outperforms the reference at r ≤ 384
for 8192 × 8192 matrices.

42x

12.4x

71x

11.0x

16x

8.0x

30x

20x

3.6x

3.1x

26x

Allocation Delta (MB)

2.9x

2.8x

Working Set (MB)

7x

2.7x

2.6x

10 0

10−1

10 0

4k, r16

4k, r64

8k, r64

4k, r16

4k, r64

8k, r64

4k, r128

4k, r256

4k, r384

8k, r384

4k, r512

8k, r512

8k, r768

1k, r128

1k, r384

2k, r384

3k, r384

6k, r384

4k, r128

4k, r256

4k, r384

8k, r384

4k, r512

8k, r512

8k, r768

1k, r128

1k, r384

2k, r384

3k, r384

6k, r384

512, r64

512, r64

16k, r384

16k, r384

512, r384

512, r384

![Figure 9](assets/figures/page_014_vec_001.png)

_Figure 9: Norm memory reduction. (a) Theoretical persistent working set. (b) Measured allocator delta. The MoE shape 8192 × 28672 achieves 11× measured reduction._

Figure 10: Norm latency vs. rank (RTX 6000 PRO, fp32). The PEFT time is constant in r; factored
scales linearly. At r ≤ 128, factored matches the reference due to reduced memory traffic.

### Memory Profile

The fused backward path reduces forward peak VRAM by eliminating intermediate materialization while maintaining identical backward peak (Figure 11). At the model level (Table 8), fused uses 0.1–1.0 GB less peak VRAM than eager and 1.2–6.7 GB less than PEFT. Dense (B@A) uses more peak VRAM than fused on all models.

![Figure 11](assets/figures/page_015_vec_001.png)

_Figure 11: Memory profile (H200, bf16, d=4096, bs=4, seq=2048). (a) Fused reduces forward peak by 64 MB. (b) Savings grow with batch×seq; backward peak is unchanged._

> Table JSON: `assets/tables/table_0008.json`
> Table 8: Model-level peak VRAM (GB). Fused uses less than all baselines on every model. 32B models OOM on RTX 6000 PRO.

Table 9 summarizes microbenchmark speedups across all six GPUs. Model-level eager/fused speedups
range from 1.18× to 1.24× with cross-GPU CV < 2%, providing stronger statistical evidence than
additional repeats on a single GPU.

Fidelity. Cosine similarity between fused and eager final logits exceeds 0.9999 for all six models on all three GPUs (cos ≥ 0.999996 on HBM-class GPUs). An earlier code version showed reduced fidelity on Gemma-3-12B (cos = 0.991–0.999); the root cause was fusing the magnitude division into Triton, which allowed FMA contraction and approximate sqrt to perturb rounding at large

> Table JSON: `assets/tables/table_0009.json`
> Table 9: Geometric mean microbenchmark speedups (all shapes, 200 repeats). Norm memory 0.8× in bf16 means factored uses more memory for the isolated norm due to fp32 accumulation transients (§2.3).

> Table JSON: `assets/tables/table_0010.json`
> Table 10: Multi-seed convergence: eager vs. fused training loss (Qwen3.5-9B-Base, r =384, 2000 steps). Grand mean per-step delta 7.1 × 10−4; final eval losses agree to < 1.5 × 10−4.

activation scales. De-fusing the division (§4), adding store-reload barriers, and replacing the sqrt with inline PTX resolved the discrepancy, improving fidelity to cos > 0.9999 across all GPUs.

To verify that fused kernels do not affect training dynamics, we trained controlled SFT experiments on a length-filtered derivative of MMFineReason-SFT-123K [Lin et al., 2026] using Qwen3.5-9B-Base, DoRA r = 384, α = 192, rsLoRA, bf16, AdamW, ZeRO-2, gradient checkpointing, bs = 3, ga = 2, seq=5120, 2000 steps on a single RTX 6000 PRO, using the SWIFT framework [Zhao et al., 2024], with three seeds (× eager/fused = 6 runs). Table 10 and Figure 12 summarize the results. The worst-case single-step delta (1.1 × 10−2, seed 1, step 398) is a transient early-training divergence that does not propagate: by step 1000, all deltas fall below 3.3 × 10−3. Gradient norms track identically, confirming that the d mag reduction-ordering difference does not accumulate over 2000 steps.

Wall-clock. The fused path completed 2000 steps in 330 min compared with 360 min for the eager baseline (8.3% reduction), consistent with the 21% gradient-computation speedup diluted by optimizer steps, data loading, and framework overhead.

Cross-model and cross-optimizer check. An additional pair on Qwen3-VL-8B-Instruct with Muon+AdamW (r =256, single seed) showed consistent results: mean |∆loss| = 7.7 × 10−4, final eval |∆| = 3.9 × 10−5, 8.2% wall-clock reduction.

> Table JSON: `assets/tables/table_0011.json`
> Table 11 consolidates practitioner recommendations.

![Figure 12](assets/figures/page_017_vec_001.png)

_Figure 12: Convergence: eager vs. fused are visually indistinguishable (Qwen3.5-9B-Base, r=384, seed 3 of 3). (a) Training loss (25-step smoothing). (b) Eval loss (200-step intervals). (c) Gradient norms._

Where fusion offers no advantage. Below ∼2048 × 6144 activations, launch latency dominates; the dispatch encodes this crossover conservatively. On non-CUDA platforms, Triton kernels are unavailable.

Fused backward VRAM. The fused backward saves one activation-sized tensor (inner) per module, but the dual-output kernel also eliminates the forward-pass spike from sequential ops. Net effect: fused uses 0.1–1.0 GB less peak VRAM than eager at the model level. With frozen magnitude, inner is skipped entirely.

Numerical precision. All PyTorch compose paths are bitwise identical. Triton preserves the same algebra but not bitwise equality (§4). Residual drift concentrates in d mag reductions rather

## Discussion

> Table JSON: `assets/tables/table_0012.json`
> Table 11: Recommended configuration by scenario.

than pointwise compose. Convergence studies (§5.9) confirm these differences do not accumulate.

Distributed training. DeepSpeed ZeRO-2/3 and FSDP1 are supported. FSDP2/DTensor is not: the factored norm assumes access to the full base weight W. Extending to FSDP2 would require distributed accumulation of the chunk-wise partial sums followed by an all-reduce over the shard dimension; the per-row output ([d out]) is small enough to replicate. We leave this for future work.

Embedding formula correction. PEFT’s embedding path computes only g ⊙ lora · s, omitting (g−1) ⊙ base. Our implementation applies the full DoRA formula consistently across all layer types. No headline benchmarks include adapted embeddings; checkpoints fine-tuned with PEFT’s embedding path may require re-fine-tuning or a legacy composition fallback.

Ablation. Model-level speedups reflect both contributions (factored norm + fused kernels) jointly. Microbenchmarks (Tables 9 and 7) provide component-level measurements, and the model-level eager-vs.-fused comparison provides a partial ablation of the kernel-fusion contribution. A fuller factorial ablation across additional model families would strengthen the evidence.

## Related Work

Parameter-efficient fine-tuning. LoRA [Hu et al., 2022] introduced low-rank adapter decomposition; DoRA [Liu et al., 2024] adds magnitude-direction separation. rsLoRA [Kalajdzievski, 2023] provides rank-stabilized scaling that interacts with our factored norm (s appears in all three terms of Equation 2).

DoRA variants. EDoRA [Nasiri and Garraghan, 2025] reduces static parameter count via SVD; DoRAN [Diep et al., 2025] injects noise into the normalization denominator. Both address statistical efficiency rather than transient memory; our optimization is complementary. Chronicals [Nair, 2026] and LoRAFusion [Zhu et al., 2026] fuse LoRA-related operations but do not target the DoRA-specific norm or composition.

Framework implementations. Every major framework we checked (HF PEFT, torchtune, Unsloth, SWIFT, LLaMA-Factory, Axolotl) uses the same torch.eye materialization pattern. Unsloth explicitly disables its custom kernels when DoRA is active; orchestration frameworks delegate entirely to PEFT. As of February 2026, no existing framework avoids materializing the dense BA product (Appendix G).

Kernel fusion. FlashAttention [Dao et al., 2022, Dao, 2024] demonstrated that tiled, fused kernels improve both speed and memory for attention. Liger Kernel [Hsu et al., 2024] applies similar principles to cross-entropy, SwiGLU, and RMSNorm. Our work targets the DoRA composition, a simpler (element-wise with broadcasting) but equally memory-bound pattern. The algebraic identity underlying the factored norm (expanding a sum-of-squares into base, cross, and Gram terms) is standard in numerical linear algebra; our contribution is its application to the DoRA-specific computation with dtype discipline, chunking, and integration into the fused pipeline.

LLM-guided optimization. Meta’s KernelAgent [PyTorch, 2025] confirmed our compose kernel is near-roofline (89% memory bandwidth SOL, 1.5% improvement). For the backward, KernelAgent discovered a two-stage partial-reduction strategy that fuses the d mag reduction, achieving 3.58× over eager (88.5% SOL) vs. our 1.06–1.23×. Our release prioritizes drop-in compatibility and end-to-end wins across real models; integrating that pattern is a direct avenue for future work. KernelAgent’s generated listings are included in code/kernelagent_sols.

## Conclusion

We presented a systems implementation of DoRA: a factored norm that reduces working memory from O(d out × d in) to O(d out × r + r 2), and fused Triton kernels that collapse multi-step composition into single-pass GPU operations. On six 8–32B VLMs, the fused implementation is 1.5–2.0× faster than HF PEFT’s DoRA implementation for inference, and 1.5–1.9× faster for gradient computation (optimizer step excluded), with up to 7 GB lower peak VRAM. Microbenchmarks on six GPUs spanning four architecture generations confirm 1.5–2.7× compose-kernel speedup. Fidelity holds at three levels: operator tests within quantization-aware bounds, final-logit cos > 0.9999, and matched training curves across seeds.

Known limitations. FSDP2 is unsupported. Convergence validation covers two model families, two optimizers, and one dataset in the SFT regime; generalization to RL pipelines remains to be confirmed. Model-level benchmarks cover three of six GPUs; L40S, A100, and B300 have microbenchmark coverage only. The dispatch crossover is an empirical heuristic that may need retuning for future hardware.

Data Availability

All source code, benchmark scripts, raw JSON results, Triton autotune caches, and figure generation scripts are available at https://github.com/sockeye44/dorafactors (tag v1.0). The convergence validation uses a public dataset (MMFineReason-SFT-123K; Lin et al. 2026) for fully reproducible confirmation. The authors declare no competing interests.

Acknowledgements

This work was developed through extensive collaborative programming with Claude Opus 4.6 (Anthropic), which contributed to kernel implementation, test design, numerical analysis, and iterative debugging. The authors take full responsibility for the accuracy and integrity of the work.

## References

Jason Ansel, Edward Yang, Horace He, Natalia Gimelshein, Animesh Jain, Michael Voznesensky, Bin Bao, Peter Bell, David Berard, Evgeni Burovski, et al. PyTorch 2: Faster machine learning through dynamic Python bytecode transformation and graph compilation. In Proceedings of the 29th ACM International Conference on Architectural Support for Programming Languages and Operating Systems, volume 2 of ASPLOS ’24. ACM, 2024. doi: 10.1145/3620665.3640366.

Sourab Mangrulkar, Sylvain Gugger, Lysandre Debut, Younes Belkada, Sayak Paul, Benjamin Bossan, and Marian Tietz. PEFT: State-of-the-art parameter-efficient fine-tuning methods.

PyTorch. KernelAgent — multi-agent GPU kernel synthesis, 2025. URL https://github.com/ meta-pytorch/KernelAgent.

Philippe Tillet, H. T. Kung, and David Cox. Triton: An intermediate language and compiler for tiled neural network computations. In Proceedings of the 3rd ACM SIGPLAN International Workshop on Machine Learning and Programming Languages, MAPL 2019, pages 10–19. ACM, 2019. doi: 10.1145/3315508.3329973.

Yuze Zhao, Jintao Huang, Jinghan Hu, Xingjun Wang, Yunlin Mao, Daoze Zhang, Zeyinzi Jiang, Zhikai Wu, Baole Ai, Ang Wang, Wenmeng Zhou, and Yingda Chen. SWIFT: A scalable lightweight infrastructure for fine-tuning, 2024. URL https://arxiv.org/abs/2408.05517.

## Forward Contract and Execution Semantics

• Output: The module computes a delta ∆Y; the caller applies Y = Y base + ∆Y. • Compose Equation: ∆Y = g ⊙ (s XA⊤B⊤) + (g − 1) ⊙ Y base.

## Implementation Details

• Recomputed every forward pass; never cached across steps. • Detached (no gradient flow), per Liu et al. [2024] §4.3. • Accumulated in FP32 with autocast disabled. • ϵ = 10−12 (fp32/fp64) or 10−6 (bf16/fp16). • Bias subtracted before compose, re-added after.

Formal contract for clean-room replication.

Chunk alignment. The chunk size aligns to 64 elements on CUDA/XPU devices for Tensor Core MMA alignment on all NVIDIA architectures since Volta.

Environment variables. PEFT_DORA_FUSED (0 = force eager), PEFT_DORA_FUSED_BACKWARD (1 = force fused bwd, 0 = disable, unset = auto), PEFT_DORA_NORM_CHUNK_MB and PEFT_DORA_FWD_ CHUNK_MB (override 256 MB defaults).

Scale-is-zero fast path. When s = 0, cross and ba_sq are skipped; U and G are not allocated.

Dtype-aware epsilon. 10−12 for fp32/fp64; 10−6 for bf16/fp16. For fp16 (max ≈ 65504), ε = 10−6

limits the quotient to ∼10 6, reducing saturation risk.

Compose kernel autotuning. RPP=1 is selected in 95% of autotuned entries (1149/1206). Exact config agreement between GPUs is ∼9%, confirming per-device autotuning is essential.

Chunked dropout path. When dropout is active, _compose_with_base_chunks iterates over output-dimension slices with adaptive sizing, decorated with @dynamo_disable to avoid runaway recompilations.

Magnitude broadcast shape guard. A shape guard gates Triton kernel dispatch on whether the magnitude vector broadcasts exclusively along the last dimension of the activation tensor. The Triton compose kernel treats magnitude as a 1-D vector along the last dimension; Conv-style shapes like [1, C, 1, 1] applied to [N, C, H, W] activations would violate this assumption. The guard checks both element count and last-dimension alignment; failing shapes route to the PyTorch fallback.

Custom op for torch.compile. The registered backward uses PyTorch (not Triton) because AOTAutograd traces with FakeTensors. Eager training uses Triton for both forward and backward; compiled training uses Inductor to fuse the PyTorch backward graph.

## Kernel Specifications

This appendix provides exact specifications for the three Triton kernels and the PyTorch magnitude division stage, including casting points, fused operations, shape constraints, and reduction ordering, to support a clean-room reimplementation.

1. Compose Forward kernel.
Fuses (g − 1) ⊙ base + g ⊙ s ⊙ lora in one pass. Inputs: base
[bs, seq, d out], lora [bs, seq, d out], g [d out], s (scalar). Output: delta [bs, seq, d out]. All tensors in input
dtype (fp16/bf16/fp32); no intermediate dtype cast. g is broadcast along all but the last dimension.

2. Compose Backward kernel.
Fuses d lora = g·s·d out and d base = (g−1)·d out in a single Triton
pass. d mag is computed separately via a .sum() reduction over the batch/sequence dimensions on
the inner activation; this avoids non-deterministic tl.atomic_add ordering.

3. Norm Assembly kernel (norm-only).
Inputs: base_sq [d out], cross [d out], ba_sq [d out] (all
fp32), two_s (scalar, = 2 s, precomputed in fp64), s2 (scalar, = s 2, precomputed in fp64). Computes
w norm =
p

max(base_sq + two_s · cross + s2 · ba_sq, 0) in fp32 with store-reload barriers after each multiply-add to prevent FMA fusion, exactly reproducing PyTorch’s separate-kernel evaluation order. The clamp preserves NaN semantics (matching torch.clamp_min, which propagates NaNs per IEEE 754) rather than collapsing NaNs to zero. The square root uses inline PTX sqrt.rn.f32 for IEEE 754 correctly-rounded results (Triton’s tl.sqrt compiles to sqrt.approx.ftz.f32 on SM90). The kernel returns the result in the input dtype. In default mode, it uses a fixed block size of 256 (norm kernels are launch-latency bound; see Appendix B); comprehensive autotuning over 36 configurations (block sizes 32–2048) is available for new GPU architectures. If future Triton versions change the lowering of tl.sqrt to IEEE-compliant rounding, the inline PTX can be removed; the Tier-3 eager fallback provides a portable alternative on any platform.

4. Magnitude division (PyTorch).
The division g = m/ max(w norm, ε) is always computed
in PyTorch after the norm assembly kernel returns. This ensures identical precision regardless of
whether the Triton or PyTorch norm path was used, at the cost of one additional element-wise
kernel launch (negligible relative to surrounding matmuls).

Shape constraints. d out must be divisible by BLOCK_SIZE (128). The magnitude vector must broadcast only along the last dimension of the activation; other broadcast shapes (e.g., [1, C, 1, 1] applied to [N, C, H, W]) route to the Tier-3 eager fallback. Non-contiguous input tensors also fall back to Tier 3.

Tested compatibility matrix. Table 12 summarizes the integration points explicitly tested, with notes on scope and caveats. “Tested” indicates the feature was exercised in benchmarks or convergence runs reported in this paper; “CI only” indicates coverage via the test suite (1041 tests) but not in model-level experiments.

## Reproducibility

Code and data. All source code, benchmark scripts, raw JSON results, Triton autotune caches, and figure generation scripts are available at https://github.com/sockeye44/dorafactors (tag v1.0). The patched PEFT module is included as a git submodule (vendor/dorafactors-peft,

Table 12: Compatibility matrix. Scope: Bench = model-level benchmarks, Conv = convergence
runs, CI = operator-level test suite.

branch v1); cloning with --recurse-submodules fetches it automatically. Alternatively, the patch can be reconstructed via git apply hf.patch against upstream PEFT commit 20a9829 2. All commands below assume the repository root as working directory.

Software environment. All benchmarks were run under a single, pinned software stack: PyTorch 2.10.0+cu130 (built against CUDA 13.0 for compatibility), Triton 3.6.0, Transformers 5.2.0, CUDA toolkit 13.1 (ptxas V13.1.115), driver 580.126.09, Python 3.12.12 on Linux 6.8.0 (Ubuntu 22.04, glibc 2.35). The exact environment is published as a Docker image 3 for full-stack reproducibility; a code/requirements.txt is also included.

Memory measurement methodology. We report three complementary memory metrics, each appropriate to a different level of analysis:

• Allocator peak (torch.cuda.max_memory_allocated()): the maximum bytes actually allocated by PyTorch’s caching allocator. Used for microbenchmark memory deltas (Tables 1 and 7), measured after reset_peak_memory_stats() and empty_cache() to isolate a single operation’s footprint.

• Working-set delta (max_memory_allocated − baseline_allocated): the peak minus the model’s quiescent allocation, capturing the true transient overhead of DoRA’s forward/backward pass. Used for model-level gradient-computation analysis (§5.3, Table 4).

• Reserved VRAM (memory_reserved): the amount of memory the GPU physically withholds from other processes, including caching allocator fragmentation overhead. Used for peak VRAM comparison (Table 8) because it determines whether colocated workloads can share the device.

2 PEFT commit: 20a9829 (v0.18.0.rc0, 2025-09-16).
3 Docker image: https://hub.docker.com/r/alexazel/dorafactors-env. Tag: cu131-pt210-vllm-t52-base.

Every memory claim in this paper specifies both the metric and the dtype (fp32 vs. bf16) to avoid conflation. Microbenchmark reproduction.

\# 200 repeats , extended
shapes , bf16

Each run produces a self-contained JSON file with per-test timing distributions (200 samples), memory measurements, and pre-computed summary statistics. The –shapes extended flag generates the 20 unique activation shapes (60 entries across 3 ranks) used throughout this paper. Model identifiers. All model-level benchmarks use the following Hugging Face model IDs (weights downloaded March 2026; exact file hashes in the JSON artifacts):

--json -out models.json

Figure regeneration.
All figures can be regenerated from the included JSON artifacts:

This produces 13 PDF figures in paper/figures/ sourced from the code/bench_it6/ data directory (6 GPUs × 3 dtypes for microbenchmarks, 3 GPUs for model-level). The convergence figure (Figure 12) is generated separately from TensorBoard logs via python paper/generate_training_

figure.py.

Test suite. The full test suite (1041 tests) has been validated on SM 80 through SM 120 (Ampere– Blackwell); Triton kernel tests require SM ≥ 80:

cp code/scripts/dora. reference_hf_peft .py \

## Full Model-Level Memory Table

> Table JSON: `assets/tables/table_0014.json`
> Table 13: Model-level gradient-computation peak VRAM (GB) across three GPUs, all six models. Same setup as Table 8. Values from peak_vram_mb.

## Single-Layer E2E Decomposition

The following figures show single-layer end-to-end (E2E) speedup, which isolates the per-layer overhead but does not predict model-level speedup. Compose gains compound across ∼500 DoRA modules in a real model, while per-layer backward overhead is amortized, so single-layer E2E can understate the model-level benefit.

fp32 microbenchmark summary. Table 14 provides the fp32 rows omitted from the main-body summary (Table 9). Norm memory 3.2× in fp32 reflects the full theoretical benefit, since both paths accumulate in fp32 and the PEFT baseline also allocates fp32 temporaries.

> Table JSON: `assets/tables/table_0016.json`
> Table 14: Geometric mean microbenchmark speedups, fp32 (all shapes, 200 repeats). Complement to Table 9.

## Framework Survey

> Table JSON: `assets/tables/table_0015.json`
> Table 15: DoRA norm implementation in major fine-tuning frameworks (February 2026).

2.4

### Speedup (Eager / Fused)

### Step Time (ms)

1.200

1.175

1.150

1.9

1.125

1.8

1.100

1.7

1.075

Figure 13: Single-layer E2E overhead decomposition (B200, bf16, d = 4096, bs=4, seq=2048).
Single-layer E2E does not predict model-level speedup: compose gains compound across ∼500 DoRA
modules while per-layer backward overhead is amortized.

![Figure 13](assets/figures/page_028_vec_001.png)

_Figure 13: Single-layer E2E overhead decomposition (B200, bf16, d = 4096, bs=4, seq=2048). Single-layer E2E does not predict model-level speedup: compose gains compound across ∼500 DoRA modules while per-layer backward overhead is amortized._

![Figure 14](assets/figures/page_028_vec_002.png)

_Figure 14: Single-layer E2E speedup (eager/fused) across six GPUs and ranks (bf16, d = 4096, bs=4, seq=2048). All GPUs show consistent improvement._

![Figure 15](assets/figures/page_029_vec_001.png)

_Figure 15: Single-layer E2E speedup vs. hidden dimension (bf16, r = 384, six GPUs). The benefit peaks at h = 3072–4096, corresponding to common LLM sizes._
