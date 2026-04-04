---
title: "WRITEBACK-RAG: Training the Knowledge Base through Evidence Distillation and Write-Back Enrichment"
paper_id: 118
source_pdf: "/Users/siddhantraje/Documents/PersonalWork/ChatGPT Apps/NewCloneIA/Instructor-Assistant/markdown_evaluation/pdfs/ResearchPapers/699ede68aa0d6853.pdf"
generated_at: "2026-04-04T22:54:27.146474+00:00"
num_figures: 5
num_tables: 6
num_equations: 31
---

Yuxing Lu♠♡, Xukai Zhao♣, Wei Wu♠, Jinzhuo Wang *♠

♠Peking University ♡Georgia Institute of Technology ♣Tsinghua University

## Abstract

The knowledge base in a retrieval-augmented generation (RAG) system is typically assembled once and never revised, even though the facts a query requires are often fragmented across documents and buried in irrelevant content. We argue that the knowledge base should be treated as a trainable component and propose W RITE B ACK-RAG, a framework that uses labeled examples to identify where retrieval succeeds, isolate the relevant documents, and distill them into compact knowledge units that are indexed alongside the original corpus. Because the method modifies only the corpus, it can be applied once as an offline preprocessing step and combined with any RAG pipeline. Across four RAG methods, six benchmarks, and two LLM backbones, W RITE B ACK-RAG improves every evaluated setting, with gains averaging +2.14%. Cross-method transfer experiments further show that the distilled knowledge benefits RAG pipelines other than the one used to produce it, confirming that the improvement resides in the corpus itself.

## Introduction

Retrieval-augmented generation (RAG) systems consist of three core components: a retriever, a generator, and a knowledge base (KB) (Hu and Lu, 2024; Fan et al., 2024). Modern RAG research has devoted substantial effort to optimizing the first two: training better retrievers (Shi et al., 2024), teaching generators when and how to use retrieved evidence (Asai et al., 2023; Jiang et al., 2023b), and designing tighter retriever-generator integration (Izacard et al., 2023). The knowledge base, by contrast, is treated as a fixed input: assembled once from raw document collections like Wikipedia dumps, textbooks, or web crawls, and never updated in response to downstream task signals. Knowledge bases are composed of raw documents, so the granularity at which knowledge is

![Figure 1](assets/figures/page_001_vec_001.png)

_Figure 1: Standard RAG retrieves fragmented evidence from raw documents. WRITEBACK-RAG distills use- ful evidence into compact write-back documents that improve future retrieval and generation._

stored is dictated by document boundaries. However, the knowledge a query requires rarely aligns with these boundaries: the relevant facts are typically distributed across multiple documents (fragmentation), while each document contains substantial content irrelevant to the query (noise). As a result, the retriever surfaces partially relevant documents, but the context the generator receives is both incomplete and diluted. By observing how a RAG system interacts with the corpus on labeled data, which samples benefit from retrieval, and which documents contribute to the generation, we can identify where knowledge is fragmented and should be rewritten and fused. This provides a natural supervision signal for optimizing the KB. This observation motivates a new concept we call knowledge base training: optimizing the KB itself using supervision from labeled examples, analogous to how model parameters are updated through training data (Appendix A). We instantiate this idea in W RITE B ACK-RAG, a framework that learns from retrieval patterns on training data to improve the knowledge base. Concretely, a twostage gating mechanism analyzes retrieval behavior to identify which training samples benefit from retrieval and which retrieved documents contribute

to better generation. An LLM-based distiller then fuses and compresses the selected evidence into compact, self-contained knowledge units that are permanently indexed alongside the original corpus. Because W RITE B ACK-RAG augments only the KB, not the retriever or generator, it enhances any RAG pipeline as an orthogonal optimization step, with a one-time offline cost and no additional inference-time overhead. Our contributions are:

1. We propose treating the knowledge base as a
trainable component of RAG systems and in-
troduce W RITE B ACK-RAG, a framework that
learns from retrieval patterns on labeled data
to restructure and enrich the KB through gated
evidence distillation and persistent write-back.

2. We provide extensive empirical validation
across four RAG methods (Naive Retrieval, Re-
Plug, Self-RAG, Flare), six benchmarks (NQ,
BoolQ, FEVER, zsRE, HotpotQA, SQuAD),
and two LLM backbones (Llama-3.1-8B,
Gemma-3-12B), showing consistent improve-
ments in all settings.

3. We present detailed analyses of write-back
knowledge properties, including compression
statistics, retrieval dynamics, and generalization
behavior, providing insight into when and why
W RITE B ACK-RAG improves performance.

## Related Works

Retrieval and Generation Strategies. The standard RAG pipeline retrieves top-K documents and conditions generation on them (Lu et al., 2025; Guu et al., 2020; Borgeaud et al., 2022). A large body of work has improved this pipeline from both sides. On the retrieval side, R E P LUG (Shi et al., 2024) ensembles generation probabilities over documents for better passage weighting, and HyDE (Gao et al., 2023) generates hypothetical documents to improve query representations. On the generation side, S ELF-RAG (Asai et al., 2023) introduces reflection tokens for adaptive retrieval decisions, F LARE (Jiang et al., 2023b) triggers retrieval when generation confidence drops, and Atlas (Izacard et al., 2023) jointly trains the retriever and generator. These methods share a common assumption: the knowledge base is a fixed input. They optimize how to search it and how to consume its outputs, but the content and organization of the KB itself is never modified. W RITE B ACK-RAG addresses this independent dimension.

Improving Retrieved Context at Inference Time. A separate line of work aims to improve the quality of the context the generator sees, rather than the retrieval or generation mechanism. RE- COMP (Xu et al., 2023) trains extractive and abstractive compressors to shorten retrieved documents. FILCO (Wang et al., 2023) learns to select useful spans within documents. LLMLingua (Jiang et al., 2023a) uses perplexity-based token pruning to compress prompts. GenRead (Yu et al., 2022) bypasses retrieval entirely, prompting the LLM to generate its own context. RAGate (Wang et al., 2025) gates external retrieval according to whether the required knowledge is already available within the model. All of these operate per query at inference time: they produce ephemeral, compressed or generated context that is consumed once and discarded. This means the cost scales linearly with the number of test queries, and knowledge gained from one query never benefits another. W RITE B ACK- RAG inverts this paradigm: it distills and fuses evidence once during an offline phase, producing persistent knowledge units that benefit all future queries at zero inference-time cost.

Knowledge Base Optimization. The idea of directly modifying the knowledge source to improve downstream performance has been explored in two distinct settings, neither of which addresses the RAG corpus. In traditional NLP, knowledge base construction methods extract structured triples from text (Dong et al., 2015; Martinez-Rodriguez et al., 2018), but these produce symbolic KBs rather than retrieval-ready documents. In the model editing literature, methods like ROME (Meng et al., 2022a) and MEMIT (Meng et al., 2022b) update factual associations by modifying model parameters, effectively “editing the KB” that lives inside the network weights. However, these parametric edits are brittle at scale and entangled with the model’s other capabilities. W RITE B ACK-RAG pursues a non-parametric alternative: rather than editing model weights, it edits the external corpus that the model retrieves from. This is more modular (the enriched KB works with any retriever and generator), more interpretable (write-back units are readable text), and more scalable (adding documents does not risk degrading the model). To our knowledge, W RITE B ACK-RAG is the first framework to treat the RAG knowledge base as a trainable component that is systematically optimized using downstream task signals.

![Figure 2](assets/figures/page_003_vec_001.png)

_Figure 2: The WRITEBACK-RAG pipeline. During training (top), a two-stage gating mechanism identifies examples where retrieval helps and selects contributing documents. An LLM distiller fuses the selected evidence into a compact knowledge unit, which is indexed into a separate write-back corpus. During testing (bottom), the retriever searches combined knowledge source with no changes to the retriever or generator._

## Problem Formulation

and the generator produces an answer conditioned on both the query and retrieved documents:

$$
a = G(q, D q)
\tag{2}
$$
> Equation 2 JSON: `assets/equations/equation_0004.json`
> Equation 2 image: `assets/equations/equation_0004.png`

ˆ
a = G(q, D q)
(2)

$$
training examples D train = {(q i, a i)}N \\
i=1, the KB
$$
> Equation 5 JSON: `assets/equations/equation_0005.json`
> Equation 5 image: `assets/equations/equation_0005.png`

$$
wb = arg max
\tag{3}
$$
> Equation 3 JSON: `assets/equations/equation_0006.json`
> Equation 3 image: `assets/equations/equation_0006.png`

D test
M(q, a ∣ G, R(q, K ∪ K wb))
(3)

At test time, retrieval operates over the combined
index:

$$
q = R(q, K \\
') = Top-K(R(q, K) ∪ R(q, K wb))
\tag{4}
$$
> Equation 4 JSON: `assets/equations/equation_0002.json`
> Equation 4 image: `assets/equations/equation_0002.png`

D
′
q = R(q, K
′) = Top-K(R(q, K) ∪ R(q, K wb))
(4)

## Methods

### Overview

W RITE B ACK-RAG instantiates the KB training objective (Eq. 3) by learning from how a RAG system interacts with the corpus on labeled data. The key insight is that retrieval patterns on training examples reveal where the KB’s knowledge organization is deficient, where relevant facts are fragmented across documents or buried in noise, and this signal can be used to systematically restructure the KB. As shown in Figure 2, W RITE B ACK-RAG operates in two phases. During the training phase, a two-stage gating mechanism first selects training examples where retrieval genuinely helps (utility gate, §4.2) and then identifies which retrieved documents carry useful knowledge (document gate, §4.3). The selected evidence is fused and compressed into a single knowledge unit via LLMbased distillation (§4.4) and indexed into a separate write-back corpus (§4.5). During the test

$$
Ensure: Trained KB K' = K ∪ K wb
$$
> Equation 7 JSON: `assets/equations/equation_0007.json`
> Equation 7 image: `assets/equations/equation_0007.png`

phase, the retriever searches the combined knowledge source K′ = K ∪ K wb with no changes to the retriever or generator. The full pipeline is given in Algorithm 1. Both gating stages rely on two reference scores computed for each training example (q i, a i). The no-retrieval score measures what the generator can answer from parametric knowledge alone:

$$
i = M(q i, a i ∣ G)
\tag{5}
$$
> Equation 5 JSON: `assets/equations/equation_0010.json`
> Equation 5 image: `assets/equations/equation_0010.png`

s nr
i = M(q i, a i ∣ G)
(5)

The RAG score measures performance with retrieval from the original KB:

$$
= M(q i, a i ∣ G, R(q i, K))
\tag{6}
$$
> Equation 6 JSON: `assets/equations/equation_0012.json`
> Equation 6 image: `assets/equations/equation_0012.png`

s rag
= M(q i, a i ∣ G, R(q i, K))
(6)

The gap δ i = s rag i −s nr i quantifies the retrieval benefit for each example and drives all gating decisions. The backbone RAG method (e.g., Naive Retrieval, RePlug, Self-RAG, FLARE) is used consistently for computing these scores, for distillation, and for final evaluation. W RITE B ACK-RAG is an orthogonal optimization step that works on top of any backbone without modifying it.

$$
The gap δ i = s
$$
> Equation 13 JSON: `assets/equations/equation_0013.json`
> Equation 13 image: `assets/equations/equation_0013.png`

### Utility Gate

The utility gate operates at the sample level, selecting training examples where retrieved knowledge makes a genuine difference. If the generator can already answer correctly without retrieval, or if retrieval does not improve the answer, there is no useful signal for KB training.

W RITE B ACK-RAG retains a training example
(q i, a i) if and only if:

and
s rag
> τ s
(7)

The margin threshold τ δ ensures retrieval provides non-negligible improvement, and the quality threshold τ s ensures the retrieval-augmented answer is actually correct. Their conjunction guards against two failure modes: high gain but low absolute quality (retrieval improves a wrong answer to a slightly less wrong one), or high quality already achievable without retrieval. We denote the set of examples passing the utility gate as D util ⊆ D train.

### Document Gate

The document gate operates at the document level within each utility-approved example. Among the K retrieved documents, not all carry useful knowledge, some are noisy, tangential, or distracting. The document gate isolates the specific documents that contribute to the improved answer. For each retrieved document d j, W RITE B ACK- RAG measures its standalone contribution:

s doc
i,j = M(q i, a i ∣ G, d j)
(8)

A document passes if it provides information beyond the generator’s parametric knowledge:

> Equation 9 JSON: `assets/equations/equation_0009.json`
> Equation 9 image: `assets/equations/equation_0009.png`

> Equation 11 JSON: `assets/equations/equation_0011.json`
> Equation 11 image: `assets/equations/equation_0011.png`

If no documents pass (D∗ i = ∅), we retain the top-n min by retrieval rank as a fallback. Removing weak evidence before distillation ensures the resulting knowledge units are focused and more likely to generalize beyond the original training query.

### Distillation

Given a training query q i and its gated evidence D∗ i, an LLM-based distiller F synthesizes a single knowledge unit:

> Equation 10 JSON: `assets/equations/equation_0014.json`
> Equation 10 image: `assets/equations/equation_0014.png`

k i = F(q i, D
∗
(10)

The distiller takes multiple gated documents as input and produces a single compact passage as output. Its core operation is fusion: merging correlated knowledge that is scattered across separate documents, i.e., information that is related but separated by document boundaries in the original KB, into one coherent unit. At the same time, it compresses away redundant or tangential content within each source document, producing a denser passage. The

training query q i serves only as a locator that identifies which documents should be fused; the resulting knowledge unit is written in a topic-level, encyclopedic style so that it can be retrieved by diverse future queries, not just the original one (full prompt in Appendix G). The goal is that a single distilled unit is at least as useful as the full multi-document evidence it was derived from:

The distilled knowledge units are collected into a
separate write-back corpus:

$$
K wb = {k i ∣(q i, a i) \\in D util}
\tag{12}
$$
> Equation 12 JSON: `assets/equations/equation_0015.json`
> Equation 12 image: `assets/equations/equation_0015.png`

A retrieval index is built for K wb using the same retriever encoder. At inference time, the retriever searches K and K wb independently and merges the results into a single top-K set (Eq. 4). The trained knowledge base is K′ = K ∪ K wb. We store write-back knowledge in a separate index rather than merging it into the original KB for three reasons: (1) the original corpus is kept clean and unmodified, avoiding any risk of corrupting existing retrieval quality; (2) the write-back index can be updated, replaced, or rolled back independently without rebuilding the base index; and (3) it introduces no additional storage overhead beyond the distilled documents themselves. Because W RITE B ACK-RAG augments only the KB, not the retriever or generator, it enhances any RAG pipeline as an orthogonal optimization step (see Appendix C for a detailed discussion).

## Experiments

$$
knowledge base is K' = K ∪ K wb.
$$
> Equation 16 JSON: `assets/equations/equation_0016.json`
> Equation 16 image: `assets/equations/equation_0016.png`

### Datasets

We evaluate on six benchmarks from the FlashRAG collection (Jin et al., 2025): Natural Questions (NQ) (Kwiatkowski et al., 2019), BoolQ (Clark et al., 2019), FEVER (Thorne et al., 2018), zsRE (Levy et al., 2017), HotpotQA (Yang et al., 2018), and SQuAD (Rajpurkar et al., 2016). We use the preprocessed benchmark releases provided by FlashRAG (Jin et al., 2025) and adopt the FlashRAG-provided Wikipedia corpus as the external knowledge source for retrieval. These datasets cover a diverse set of knowledgeintensive tasks. NQ evaluates open-domain question answering over Wikipedia; BoolQ evaluates naturally occurring yes/no question answering;

> Table JSON: `assets/tables/table_0001.json`
> Table 1: Main evaluation datasets. Detailed descriptions and split statistics are given in Appendix Table 5.

FEVER evaluates evidence-based fact verification; zsRE evaluates slot filling / relation extraction formulated as question answering; HotpotQA evaluates multi-hop question answering that requires aggregating evidence across multiple documents; and SQuAD evaluates extractive question answering. Table 1 summarizes the datasets and evaluation metrics used in the main paper, while Appendix Table 5 provides detailed task descriptions and split statistics. Following our evaluation setup, we report Accuracy on NQ, BoolQ, zsRE, and HotpotQA; F1 on FEVER, and Exact Match (EM) on SQuAD.

### Implementation Details

We use E5-base-v2 (Wang et al., 2022) as the retriever with K=5 documents; the same encoder is used to index both K and K wb. The same LLM (Llama-3.1-8B (Grattafiori et al., 2024) and Gemma-3-12B (Team et al., 2024)) serves as both the generator G and the distiller F; the distiller operates only during the training phase with a taskspecific prompt (Appendix G). For gating, we set τ s = 0.1 and τ δ = 0.01 (any strict improvement suffices, i.e., δ i > 0). The document gate uses τ doc = 0.01 with n min = 2 fallback documents. Threshold sensitivity is analyzed in Section 6.5. Notably, the distiller does not receive the gold answer, so there is no direct answer leakage into the write-back corpus (Appendix B). K wb is stored as a separate FAISS index (Douze et al., 2025); at inference time, both indices are searched independently and results are merged into a single top-K set. Full hyperparameters are given in Appendix Table 6. The training phase has three cost components: baseline scoring (2 N generator calls), document gating (up to ∣D util∣ × K calls), and distillation (∣D util∣ calls). For NQ (N=79,168, ∣D util∣=12,295, K=5), this totals approximately 220 K generator calls, completing in 0.5 hours on two H200 GPUs. This is a one-time offline cost; at inference time, write-back adds zero overhead beyond a marginally

> Equation 19 JSON: `assets/equations/equation_0019.json`
> Equation 19 image: `assets/equations/equation_0019.png`

Table 2: Main results across six benchmarks, four RAG methods, and two LLMs. +WB denotes W RITE B ACK-RAG
using write-back RAG. Numbers in parentheses show absolute gains over the corresponding retrieval baseline.

> Table JSON: `assets/tables/table_0002.json`
> Table 2: Main results across six benchmarks, four RAG methods, and two LLMs. +WB denotes WRITEBACK-RAG using write-back RAG. Numbers in parentheses show absolute gains over the corresponding retrieval baseline.

larger retrieval index.

We organize the analysis around five research questions: whether KB training improves downstream accuracy (RQ1), what the write-back corpus looks like in practice (RQ2), where the retained evidence sits in the retrieval ranking (RQ3), whether writeback knowledge transfers across RAG methods (RQ4), and how sensitive the pipeline is to its main hyperparameters (RQ5).

### RQ1: Overall Performance

$$
Naive RAG gains +2.29%, RePlug +2.40%, Self- \\
RAG +1.90%, and FLARE +1.99%; averaged over \\
methods and datasets, Gemma-3-12B gains +1.92% \\
and Llama-3.1-8B gains +2.36%.
$$
> Equation 20 JSON: `assets/equations/equation_0020.json`
> Equation 20 image: `assets/equations/equation_0020.png`

Table 2 reports results for all 48 settings (4 RAG
methods × 6 datasets × 2 LLMs). W RITE B ACK-
RAG shows improvement on every single setting,
with an average gain of +2.14% (Prompts and Ex-
amples can be found in Appendix G and H). The
effect is not driven by any particular backbone or
model scale: averaged over datasets and LLMs,
Naive RAG gains +2.29%, RePlug +2.40%, Self-
RAG +1.90%, and FLARE +1.99%; averaged over
methods and datasets, Gemma-3-12B gains +1.92%
and Llama-3.1-8B gains +2.36%.
The size of the improvement varies across tasks
in a way that aligns with the nature of the knowl-
edge demand. FEVER (+4.79%) and NQ (+3.01%)
benefit most, as both require locating specific

factual evidence that is often scattered across Wikipedia passages, exactly the scenario where fusing and compressing evidence should help. BoolQ (+2.15%) also sees clear gains despite its shortanswer format. Improvements on zsRE (+0.56%), HotpotQA (+1.01%), and SQuAD (+1.33%) are smaller but uniformly positive. We note that even the smallest gains are achieved at zero inferencetime cost: the only change is a slightly larger retrieval index. Two observations deserve emphasis. First, the gains on Self-RAG and FLARE show that KB training is complementary to adaptive retrieval strategies, not redundant with them, these methods already decide when and whether to retrieve, yet still benefit from a better-organized corpus. Second, write-back helps even when retrieval itself hurts: on FEVER, Naive RAG (32.77%) underperforms the no-retrieval baseline (34.24%), yet adding writeback raises F1 to 37.89%, well above both. This suggests that distilled documents can partially compensate for noisy retrieval by placing more focused evidence within reach of the retriever.

### RQ2: Selection and Compression

Table 3 shows the write-back construction process
under Gemma-3-12B + Naive RAG (we use Naive
RAG as the reference setting throughout the analy-
sis to isolate the effect of write-back from retrieval

## Results

> Table JSON: `assets/tables/table_0003.json`
> Table 3: Training-time write-back construction statistics. Selected Rate is the fraction of training examples written back to the KB. Retained Docs is the average number of retained documents after document filtering. Source Tokens and Distilled Tokens denote the average source and distilled token counts for selected examples. Compression is computed as source tokens divided by distilled tokens. Fallback Rate is the fraction of selected examples for which no document passed the document gate and the top-nmin fallback was used.

strategy differences; see Appendix I). The utility gate selects vastly different fractions of training data depending on the task: only 6-14% for NQ, BoolQ, FEVER, and zsRE, but nearly half for HotpotQA (49.3%) and SQuAD (48.1%). The gap reflects how much each task depends on retrieval beyond the model’s parametric knowledge. HotpotQA, by design, requires cross-document reasoning that the generator cannot perform alone, so a large share of examples exhibit a positive retrieval benefit. SQuAD’s high selection rate has a different explanation: its fallback rate of 96.2% indicates that for extractive QA, where the answer typically resides in a single passage, individual documents rarely surpass the no-retrieval baseline on their own. In such cases the fallback mechanism ensures that distillation still receives a compact evidence bundle, and the downstream gains on SQuAD (+0.35% to +1.87% across settings) confirm that write-back remains effective even when the document gate defers to fallback. After document filtering, the evidence bundles are compact: roughly 2 documents on average for most tasks, and 4.76 for HotpotQA. The distiller compresses these bundles by 2.15-6.79×, producing write-back units of 72-93 tokens. The strongest compression occurs on HotpotQA, where multidocument bundles averaging 489 tokens are reduced to 80-token units. Appendix Figure 5 and Appendix F confirm this pattern: across all tasks, the majority of points fall below the identity line. The spread within each panel indicates that the distiller adapts its compression to the input length rather than producing fixed-length outputs.

### RQ3: Evidence Rank Distribution

To further understand how the document gate selects useful evidence, we analyze the retrieval-rank distribution of retained documents. Figure 3 shows,

![Figure 3](assets/figures/page_007_vec_001.png)

_Figure 3: Retrieval-rank distribution of retained docu- ments. Each panel shows the fraction of retained docu- ments among the retrieved documents._

for each dataset, the fraction of retained documents originating from each rank among the top-5 retrieved results. For NQ, BoolQ, FEVER, and zsRE, the distribution is clearly top-heavy: rank-1 and rank-2 documents account for the largest share, with a steady decline toward rank-5. This indicates that the retriever already places useful evidence near the top for these tasks; the document gate’s primary role is to filter out the lower-ranked noise rather than to rescue useful documents from deep in the list. HotpotQA and SQuAD illustrate two different non-standard patterns. HotpotQA is nearly flat across ranks 1 to 5, indicating that useful evidence is distributed broadly across the retrieved set rather than concentrated in the top few documents, which is consistent with its multi-hop nature, answering requires combining facts from multiple passages regardless of their retrieval score. SQuAD is almost entirely concentrated on ranks 1 and 2, which directly reflects its high fallback rate (96.2%, Table 3): the fallback mechanism defaults to the topn min documents, so the rank profile here illustrates fallback behavior rather than document-gate selectivity.

$$
=+0.44 \\
=+0.25 \\
+2.26 \\
+2.60 \\
+2.38 \\
+2.57 \\
=+0.12 \\
=-0.03
$$
> Equation 21 JSON: `assets/equations/equation_0021.json`
> Equation 21 image: `assets/equations/equation_0021.png`

> Table JSON: `assets/tables/table_0004.json`
> Table 4: Ablation study on the utility gate threshold τs, document gate threshold τdoc, and fallback size nmin. † marks the default configuration in the main experiments.

![Figure 4](assets/figures/page_008_vec_001.png)

_Figure 4: Cross-writeback robustness. Same-WB uses write-back knowledge from the same RAG method, while Cross-WB uses write-back knowledge from the other method. Numbers above the bars denote absolute gains over the No-WB baseline._

A key question is whether write-back knowledge is specific to the RAG method that produced it, or whether it behaves as a reusable improvement to the knowledge source itself. Figure 4 addresses this with a cross-writeback experiment between Naive RAG and RePlug. Same-WB evaluates a method using its own write-back corpus; Cross- WB evaluates it using the corpus distilled by the other method. Across all four evaluation settings, both Same- WB and Cross-WB outperform the corresponding no-write-back baseline. Same-WB yields gains of +2.26% to +3.38%, while Cross-WB yields +2.38% to +3.82%. The gap between the two never exceeds 0.44% in either direction, and in three of four cases Cross-WB is marginally better. If the distilled documents were encoding artifacts of a specific decoding policy rather than genuine improvements to the knowledge source, performance should degrade noticeably under cross-method reuse. Instead, the write-back corpus produced by one method is essentially interchangeable with that of another, indicating that W RITE B ACK-RAG improves the corpus itself rather than fitting to a particular pipeline.

### RQ5: Component Ablations

Table 4 ablates three controls of the write-back
pipeline on NQ (Naive RAG baseline: 31.44%
Acc). Every write-back configuration outperforms
this baseline, with gains ranging from +1.75 to
+3.45 points, so the method does not depend on
precise hyperparameter tuning.
The utility gate is the least sensitive: varying
τ s from 0 to 0.20 changes accuracy by only 0.16
points (34.66%-34.82%), indicating that its role is
simply to exclude clearly uninformative examples.

## Conclusion

$$
the default n min=2 (34.82%) and declines for both
$$
> Equation 23 JSON: `assets/equations/equation_0023.json`
> Equation 23 image: `assets/equations/equation_0023.png`

We proposed W RITE B ACK-RAG, a framework that treats the knowledge base as a trainable component of RAG systems. By observing which training examples benefit from retrieval and which documents contribute, W RITE B ACK-RAG distills scattered evidence into compact knowledge units that are indexed alongside the original corpus. The approach modifies only the KB and is therefore compatible with any retriever and generator. Experiments across four RAG methods, six benchmarks, and two LLM backbones show that write-back consistently improves downstream performance, with an average gain of +2.14%. Cross-method transfer experiments confirm that the distilled knowledge is a property of the corpus, not of the pipeline that produced it. These results establish W RITE B ACK- RAG as a viable method for improving RAG, complementary to advances in retrieval and generation.

W RITE B ACK-RAG has several limitations. It relies on labeled training examples, so its effectiveness in low-label or unsupervised settings remains unclear (though can be replaced by LLM-as-a- Judge). The quality of the auxiliary corpus also depends on the quality of the underlying LLM: unsupported abstractions or hallucinated details may be written back and later retrieved. In addition, our experiments are limited to public Wikipedia-based benchmarks, leaving domain transfer, multilingual settings, and continuously updated corpora for future work. Finally, W RITE B ACK-RAG introduces a nontrivial offline cost and currently studies only additive write-back, without deletion, deduplication, or contradiction resolution.

Because W RITE B ACK-RAG writes distilled knowledge back into a retrievable corpus, errors or biases in the distillation process may persist and affect future queries. We mitigate direct answer leakage by not exposing the gold answer during distillation, and we store write-back knowledge in a separate index to support inspection and rollback. However, the method still inherits biases from both the source corpus and the LLM used for distillation. Our experiments use public benchmark releases and a public Wikipedia corpus, but applying the method to proprietary or user-generated data would require additional safeguards for privacy, access control, and sensitive-content filtering. The method also incurs additional offline computation, which should be weighed against its downstream benefits.

## References

Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, and Hannaneh Hajishirzi. 2023. Self-rag: Learning to retrieve, generate, and critique through self-reflection. In The Twelfth International Conference on Learning Representations.

Sebastian Borgeaud, Arthur Mensch, Jordan Hoffmann, Trevor Cai, Eliza Rutherford, Katie Millican, George Bm Van Den Driessche, Jean-Baptiste Lespiau, Bogdan Damoc, Aidan Clark, and 1 others. 2022. Improving language models by retrieving from trillions of tokens. In International conference on machine learning, pages 2206–2240. PMLR.

Christopher Clark, Kenton Lee, Ming-Wei Chang,
Tom Kwiatkowski, Michael Collins, and Kristina

Toutanova. 2019. Boolq: Exploring the surprising difficulty of natural yes/no questions. In Proceedings of the 2019 conference of the north American chapter of the association for computational linguistics: Human language technologies, volume 1 (long and short papers), pages 2924–2936.

Matthijs Douze, Alexandr Guzhva, Chengqi Deng, Jeff Johnson, Gergely Szilvasy, Pierre-Emmanuel Mazaré, Maria Lomeli, Lucas Hosseini, and Hervé Jégou. 2025. The faiss library. IEEE Transactions on Big Data.

Wenqi Fan, Yujuan Ding, Liangbo Ning, Shijie Wang, Hengyun Li, Dawei Yin, Tat-Seng Chua, and Qing Li. 2024. A survey on rag meeting llms: Towards retrieval-augmented large language models. In Proceedings of the 30th ACM SIGKDD conference on knowledge discovery and data mining, pages 6491– 6501.

Luyu Gao, Xueguang Ma, Jimmy Lin, and Jamie Callan. 2023. Precise zero-shot dense retrieval without relevance labels. In Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pages 1762–1777.

Kelvin Guu, Kenton Lee, Zora Tung, Panupong Pasupat, and Mingwei Chang. 2020. Retrieval augmented language model pre-training. In International conference on machine learning, pages 3929–3938. PMLR.

Gautier Izacard, Patrick Lewis, Maria Lomeli, Lucas Hosseini, Fabio Petroni, Timo Schick, Jane Dwivedi- Yu, Armand Joulin, Sebastian Riedel, and Edouard Grave. 2023. Atlas: Few-shot learning with retrieval augmented language models. Journal of Machine Learning Research, 24(251):1–43.

Huiqiang Jiang, Qianhui Wu, Chin-Yew Lin, Yuqing Yang, and Lili Qiu. 2023a. Llmlingua: Compressing prompts for accelerated inference of large language models. In Proceedings of the 2023 conference on empirical methods in natural language processing, pages 13358–13376.

Zhengbao Jiang, Frank F Xu, Luyu Gao, Zhiqing Sun, Qian Liu, Jane Dwivedi-Yu, Yiming Yang, Jamie Callan, and Graham Neubig. 2023b. Active retrieval

augmented generation. In Proceedings of the 2023 conference on empirical methods in natural language processing, pages 7969–7992.

Jiajie Jin, Yutao Zhu, Zhicheng Dou, Guanting Dong, Xinyu Yang, Chenghao Zhang, Tong Zhao, Zhao Yang, and Ji-Rong Wen. 2025. Flashrag: A modular toolkit for efficient retrieval-augmented generation research. In Companion Proceedings of the ACM on Web Conference 2025, pages 737–740.

Tom Kwiatkowski, Jennimaria Palomaki, Olivia Redfield, Michael Collins, Ankur Parikh, Chris Alberti, Danielle Epstein, Illia Polosukhin, Jacob Devlin, Kenton Lee, and 1 others. 2019. Natural questions: a benchmark for question answering research. Transactions of the Association for Computational Linguistics, 7:453–466.

Omer Levy, Minjoon Seo, Eunsol Choi, and Luke Zettlemoyer. 2017. Zero-shot relation extraction via reading comprehension. In Proceedings of the 21st Conference on Computational Natural Language Learning (CoNLL 2017), pages 333–342.

Yuxing Lu, Gecheng Fu, Wei Wu, Xukai Zhao, Goi Sin Yee, and Jinzhuo Wang. 2025. Towards doctor-like reasoning: Medical rag fusing knowledge with patient analogy through textual gradients. In The Thirtyninth Annual Conference on Neural Information Processing Systems.

Jose L Martinez-Rodriguez, Ivan López-Arévalo, and Ana B Rios-Alvarado. 2018. Openie-based approach for knowledge graph construction from text. Expert Systems with Applications, 113:339–355.

Kevin Meng, David Bau, Alex Andonian, and Yonatan Belinkov. 2022a. Locating and editing factual associations in gpt. Advances in neural information processing systems, 35:17359–17372.

Pranav Rajpurkar, Jian Zhang, Konstantin Lopyrev, and Percy Liang. 2016. Squad: 100,000+ questions for machine comprehension of text. In Proceedings of the 2016 conference on empirical methods in natural language processing, pages 2383–2392.

Weijia Shi, Sewon Min, Michihiro Yasunaga, Minjoon Seo, Richard James, Mike Lewis, Luke Zettlemoyer, and Wen-tau Yih. 2024. Replug: Retrievalaugmented black-box language models. In Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers), pages 8371–8384.

Gemma Team, Thomas Mesnard, Cassidy Hardin, Robert Dadashi, Surya Bhupatiraju, Shreya Pathak, Laurent Sifre, Morgane Rivière, Mihir Sanjay Kale, Juliette Love, and 1 others. 2024. Gemma: Open

James Thorne, Andreas Vlachos, Christos Christodoulopoulos, and Arpit Mittal. 2018. Fever: a large-scale dataset for fact extraction and verification. In Proceedings of the 2018 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, Volume 1 (Long Papers), pages 809–819.

Xi Wang, Procheta Sen, Ruizhe Li, and Emine Yilmaz. 2025. Adaptive retrieval-augmented generation for conversational systems. In Findings of the Association for Computational Linguistics: NAACL 2025, pages 491–503.

Fangyuan Xu, Weijia Shi, and Eunsol Choi. 2023. Recomp: Improving retrieval-augmented lms with context compression and selective augmentation. In The Twelfth International Conference on Learning Representations.

Zhilin Yang, Peng Qi, Saizheng Zhang, Yoshua Bengio, William Cohen, Ruslan Salakhutdinov, and Christopher D Manning. 2018. Hotpotqa: A dataset for diverse, explainable multi-hop question answering. In Proceedings of the 2018 conference on empirical methods in natural language processing, pages 2369–2380.

## On the Use of “KB Training”

The implementation of W RITE B ACK-RAG is a corpus augmentation and distillation pipeline, not gradient-based optimization over KB parameters. We adopt the term “training” because the process is supervised (driven by labeled examples), taskinformed (guided by downstream retrieval performance signals), and persistent (the KB is modified once and benefits all future queries). In this sense the KB undergoes a transformation analogous to how model parameters are shaped by training data, even though the mechanism is distillation rather than gradient descent. More concretely, the analogy rests on three structural parallels. First, training data acts as supervision: just as labeled examples define a loss signal for model parameters, the labeled set D train provides the signal that drives the utility gate and document gate. Second, the process is iterative over data: the pipeline loops over training examples, accumulating write-back knowledge one unit at a time, analogous to how parameter updates accumulate over mini-batches. Third, the result is a persistent artifact: the enriched KB K′ is produced once and reused for all future inference, just as trained model weights are. We acknowledge that no gradient computation is involved, and the term “training” is used in this broader, process-level sense rather than in the narrow sense of stochastic optimization.

## W RITE B ACK-RAG Prevents Answer Leakage

Although the distiller never receives the gold answer a i, the utility gate selects examples where retrieval produces a correct answer, and the document gate retains documents that contributed to that answer. The distiller therefore receives an evidence bundle implicitly conditioned on correctness, raising the question of whether the method simply smuggles answers into the corpus. We argue that it does not. The selected documents D∗ i are passages already present in the original KB—the distiller has no access to information beyond what the retriever already surfaces, and its prompt instructs it to produce a general-purpose encyclopedic passage rather than to answer the question (Appendix G). Any answer-relevant content in a write-back document was already retrievable from the original corpus; the distiller merely reorganizes it into a more compact and retrieval-friendly format. More fundamentally, the improvement must gen-

eralize to unseen queries to affect test-time performance, because write-back documents compete with the entire original corpus and are ranked solely by embedding similarity to the test query. A document narrowly tailored to a single training question would not rank highly for semantically different test queries and would simply be ignored by the retriever. The cross-writeback experiment (RQ4, Figure 4) provides direct evidence of this generalization: write-back corpora produced by one RAG method transfer to another with negligible performance difference, ruling out pipeline-specific artifacts or memorized answer patterns. Together with the consistent gains across all 48 settings in Table 2, these results indicate that the benefit stems from improved knowledge organization rather than indirect answer leakage.

## W RITE B ACK-RAG as a General Method for RAG

A natural question is why W RITE B ACK-RAG can improve RAG methods with very different retrieval and generation strategies without any methodspecific modification. The four RAG backbones we evaluate differ substantially in how they use retrieved documents. Naive RAG concatenates the top-K passages into a single prompt. RePlug ensembles generation probabilities across documents, weighting each passage by its retrieval score. Self-RAG introduces reflection tokens that let the generator decide, per step, whether to retrieve and which passages to trust. FLARE monitors generation confidence token-bytoken and triggers retrieval only when uncertainty exceeds a threshold. Despite these differences, all four methods share a common dependency: the quality of the documents present in the retrieval index. A document that is more focused, less noisy, and better aligned with the knowledge a query requires will be ranked higher by the retriever and will be more useful to the generator, regardless of how the generator consumes it. W RITE B ACK-RAG operates entirely at this shared layer. It does not modify the retrieval algorithm, the generation prompt, or the decoding strategy. It adds distilled documents to the index, and the existing retriever decides whether to surface them. If a write-back document is more relevant than the original passages it was derived from, it will naturally rise in the ranking; if not, it will be ignored (Figure 1). This means the method can-

## Ethical Consideration

> Table JSON: `assets/tables/table_0005.json`
> Table 5: Detailed dataset statistics used in our experiments, following the FlashRAG benchmark release (Jin et al., 2025). All datasets use the FlashRAG-provided Wikipedia corpus (wiki18_100w) as external knowledge.

not degrade retrieval quality for queries unrelated to the training set, because irrelevant write-back documents simply remain unretrieved. The empirical results in Table 2 confirm this reasoning. The gains are positive across all four backbones, and the cross-writeback experiment (Figure 4) shows that write-back corpora are interchangeable across methods. Together, these observations support treating W RITE B ACK-RAG as a corpus-level preprocessing step that is independent of the choice of RAG pipeline: it can be applied once and reused with any downstream method.

## Datasets

We evaluate on six benchmarks from the FlashRAG collection (Jin et al., 2025) and use the FlashRAGprovided Wikipedia corpus (wiki18_100w) as the external knowledge source for retrieval in all experiments. These datasets span open-domain question answering, fact verification, slot filling, multihop reasoning, and extractive question answering. This breadth is important for our study because W RITE B ACK-RAG is designed to improve the knowledge base itself rather than a single taskspecific generation strategy. Table 5 reports the task type, a short description, the train and test split sizes, and the evaluation metric used in our experiments. We follow the FlashRAG benchmark release for preprocessing and split construction.

## Hyperparameters

Our implementation uses one shared retriever encoder for both the original corpus and the writeback corpus, and uses the same backbone LLM as both the generator and the distiller. The key design choices are therefore concentrated in retrieval

depth, gating thresholds, and distillation settings. Table 6 summarizes the full configuration used in the main experiments.

## Datasets

> Table JSON: `assets/tables/table_0006.json`
> Table 6: Full hyperparameter settings used in the main experiments.

The utility gate uses a minimum absolute retrieval score threshold τ s together with a positive improvement margin τ δ so that write-back is triggered only when retrieval is both useful and sufficiently correct. The document gate uses a small positive margin τ doc and a fallback mechanism with n min = 2 so that distillation still receives a compact evidence bundle even when no single retrieved document is individually strong enough under the standalone contribution test.

![Figure 5](assets/figures/page_013_vec_001.png)

_Figure 5: Source evidence length versus distilled write- back knowledge length for six benchmarks._

## Knowledge Distillation Analysis

Figure 5 visualizes the relationship between ex-
tracted source evidence length and distilled write-
back knowledge length across six datasets. Over-
all, most points fall below the identity line, show-
ing that the write-back module usually produces a
shorter distilled note than the source evidence from
which it is derived. This trend is consistent across
all datasets, confirming that the module generally
performs compression rather than direct copying.
The figure specifically reflects compression
from retrieved evidence into write-back knowledge,
rather than general prompt shortening. The broad
spread within each panel also indicates that the
rewrite module performs adaptive compression,
producing shorter or longer notes depending on
the amount and structure of the available evidence.

## Prompt Templates

We use task-specific prompts for retrieval-based inference. For no-retrieval baselines, we derive matched prompts by removing the document block from the corresponding retrieval prompt and removing evidence-dependent wording to preserve prompt parity as closely as possible. Below we show representative task prompts together with the extractive evidence prompt and the rewrite prompt used in the write-back pipeline.

BoolQ task prompt

Decide whether the answer to the question is true or false using the provided evidence. Output exactly one word: True or False. Do not output yes or no, labels, or any explanation. The following are given documents.

Answer the multi-hop question using the provided evidence. Output only the final answer. If the question is yes or no, output exactly yes or no in lowercase. Otherwise output only the shortest answer phrase. The following are given documents.

Representative no-retrieval task prompt

Answer the factoid question from your own knowledge. Output only the short final answer phrase or entity name. Do not output a sentence or explanation.

The next two prompts correspond to the writeback stage. The first extracts answer-relevant evidence sentences from retrieved passages, and the second rewrites the selected evidence into a compact retrieval-oriented document that is later indexed into the auxiliary write-back corpus. Because the distilled document must remain reusable for future queries, the rewrite stage is conditioned on the question and supporting evidence only and does not expose the gold answer.

Extractive evidence prompt

System: Extract only answer-relevant evidence sentences from retrieved passages. Do not paraphrase. Keep exact sentence text.

Rewrite prompt

System: You are writing a high-utility retrieval document for future QA. Use only facts supported by the provided knowledge.

Quality requirements: 1) Add concise supporting facts that improve retrieval recall: key entities, aliases, dates, numbers, and locations when supported. 2) Reuse important terms from the question and evidence; include alternative names only if supported. 3) Keep it factual and compact; do not add unsupported claims. Output format (exactly two parts, no labels): <title line> <knowledge paragraph(s)> Do not output prefixes like ‘Title:‘ or ‘ Knowledge:‘.

## Representative Write-Back Examples

We next present representative training instances that were rewritten and added to the write-back corpus. Each example includes the original question, the model outputs with and without retrieval, the utility signal used for selection, the extracted evidence sentences, and the final distilled document written back to the auxiliary corpus. For clarity, we report the reference answer in the qualitative examples below as part of analysis, but the distillation prompt itself does not receive the gold answer. To keep the appendix readable in ACL doublecolumn format, each example is displayed in a single breakable outer box, while the evidence and distilled text are shown as compact monospaced blocks inside the same box.

Binary verification example. This example shows a case where retrieval supplies historical and geopolitical context that is not reliably recovered in the no-retrieval setting.

Example 1: BoolQ

Question: do iran and afghanistan speak the same language Gold answer: ["True"] Original RAG prediction: True No-retrieval prediction: False Utility scores: s rag = 1.0, s nr = 0.0, ∆ = 1.0 Retained document indices: [3]

Extractive evidence.

[Doc 1] Afghanistan-Iran relations Afghanistan-Iran relations were established in 1935 during King Zahir Shah’s reign and the Pahlavi dynasty of Persia. [Doc 1] Mujahideen, Afghan refugees, and Taliban), as well as Iran’s water dispute , the growing influence of the United States in Afghanistan. [Doc 1] Afghanistan and Iran share the same underlying language, Persian, but speak different dialects.

[Doc 1] When the Safavid dynasty was founded in Persia, part of what is now Afghanistan was ruled by the Khanate of Bukhara and Babur from Kabulistan. [Doc 1] They have been negatively affected by the 1979 Iranian Revolution and issues related to the 1978-present Afghan conflicts.

Afghanistan-Iran relations Afghanistan-Iran relations were established in 1935 during King Zahir Shah’s reign and the Pahlavi dynasty of Persia. Afghanistan shares a relatively long history with Iran (called Persia in the West before 1935). When the Safavid dynasty was founded in Persia , part of what is now Afghanistan was ruled by the Khanate of Bukhara and Babur from Kabulistan. They have been negatively affected by the 1979 Iranian Revolution and issues related to the 1978-present Afghan conflicts (i.e. Mujahideen, Afghan refugees, ...

Multi-hop QA example. This case illustrates how the extracted evidence brings together lexical cues and supporting chemical context that help recover the correct answer.

Example 2: HotpotQA

Question: Cadmium Chloride is slightly soluble in this chemical, it is also called what? Gold answer: ["alcohol"] Original RAG prediction: alcohol No-retrieval prediction: water Utility scores: s rag = 1.0, s nr = 0.0, ∆ = 1.0 Retained document indices: [0, 1, 2, 3, 4]

Extractive evidence.

[Doc 2] It is a hygroscopic solid that is highly soluble in water and slightly soluble in alcohol. [Doc 1] Cadmium tetrafluoroborate may be prepared from the reaction between an aqueous solution of fluoroboric acid and cadmium carbonate or cadmium oxide: It is also possible to prepare Cadmium tetrafluoroborate through an oxidation reduction reaction implementing nitrosyl tetrafluoroborate: Cadmium tetrafluoroborate is an ionic compound formed from the two, ionic species Cd and BF. [Doc 3] Cadmium hydride Cadmium hydride ( systematically named cadmium dihydride) is an inorganic compound with the chemical formula. [Doc 5] It forms by treating cadmium oxide with acetic acid: Cadmium acetate is used for glazing ceramics and pottery; in electroplating baths, in dyeing and printing textiles; and as an analytic reagent for sulfur, selenium and tellurium. [Doc 1] At room temperature it forms colorless, odorless crystals which are

soluble in polar solvents such as water or ethanol. [Doc 2] Cadmium chloride Cadmium chloride is a white crystalline compound of cadmium and chlorine, with the formula CdCl. [Doc 2] The crystal structure of cadmium chloride (described below), composed of two dimensional layers of ions, is a reference for describing other crystal structures. [Doc 4] Operation LAC (Large Area Coverage) was a United States Army Chemical Corps operation in 1957 and 1958 which dispersed microscopic zinc cadmium sulfide (ZnCdS) particles over much of the United States.

Distilled knowledge.

Cadmium Chloride Cadmium chloride is a white crystalline compound of cadmium and chlorine, with the formula CdCl. It is a hygroscopic solid that is highly soluble in water and slightly soluble in alcohol. The crystal structure of cadmium chloride, composed of two dimensional layers of ions, is a reference for describing other crystal structures. At room temperature it forms colorless, odorless crystals which are soluble in polar solvents such as water or ethanol. Cadmium tetrafluoroborate may be prepared from the reaction between an aqueous solution of fluoroboric acid and cadmium carbonate or cadmium oxide. It is also possible to prepare Cadmium tetrafluoroborate ...

Short answer factoid QA example. This example shows a case where the rewritten document consolidates salient series-level facts into a compact document that is easy to retrieve later.

Example 3: NQ

Question: big little lies season 2 how many episodes Gold answer: ["seven"] Original RAG prediction: seven No-retrieval prediction: NAN Utility scores: s rag = 1.0, s nr = 0.0, ∆ = 1.0 Retained document indices: [0, 2]

Extractive evidence.

[Doc 1] All seven episodes are being written by Kelley [Doc 2] Kelley, the series’ seven episode first season was directed by Jean Marc Vallee. [Doc 2] Big Little Lies (TV series) Big Little Lies is an American drama television series, based on the novel of the same name by Liane Moriarty, that premiered on February 19, 2017, on HBO. [Doc 2] ""Big Little Lies"" stars Nicole Kidman, Reese Witherspoon and Shailene Woodley and tells the story of three emotionally

[Doc 1] Despite originally being billed as a miniseries, HBO renewed the series for a second season. [Doc 1] Production on the second season began in March 2018 and is set to premiere in 2019. [Doc 2] The first season was released on Blu ray and DVD on August 1, 2017.

Big Little Lies (TV series) Big Little Lies is an American drama television series, based on the novel of the same name by Liane Moriarty, that premiered on February 19, 2017, on HBO. ""Big Little Lies"" stars Nicole Kidman, Reese Witherspoon and Shailene Woodley and tells the story of three emotionally complex women. The first season, consisting of seven episodes, was directed by Jean Marc Vallee and released on Blu ray and DVD on August 1, 2017. Despite originally being billed as a miniseries, HBO renewed the series for a second ...

## Rationale for using Naive RAG for Analysis

We mainly adopt naive RAG as the reference baseline during analysis because it offers the most controlled setting for identifying the source of improvement. The central question of W RITE B ACK- RAG is not whether a more sophisticated retrieval pipeline can improve results, but whether our writeback mechanism can provide additional gains by distilling retrieved evidence into reusable knowledge. Using naive RAG as the primary comparison point reduces confounding factors and makes attribution clearer: performance differences can be interpreted more directly as arising from our method, rather than from auxiliary changes in retrieval, reranking, or prompt engineering. In contrast, if the main comparison were conducted only against stronger RAG variants, it would be difficult to disentangle whether the improvement came from the RAG system itself or from the proposed method layered on top of it. For this reason, naive RAG serves as the fairest baseline for measuring the incremental value of our approach.
