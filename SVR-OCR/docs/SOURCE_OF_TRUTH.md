# SVR-OCR Source of Truth

Status: active paper implementation target  
Last updated: 2026-04-12

## 1. Purpose

This document is the authoritative specification for **SVR-OCR**.

`SVR-OCR` stands for **Self-Verifying Region OCR**. It is the proposed next-stage method for improving the OCR behavior of a **general-purpose vision-language model (VLM)** so that it behaves more like a document-specialized OCR system.

This document is the source of truth for:

- the research motivation
- the core method
- the system architecture
- the data contracts between stages
- the verifier and repair logic
- the efficiency strategy
- the experiment plan
- the implementation roadmap
- the expected claims and limits

If later notes, code comments, or paper text disagree with this document, this document wins until it is explicitly revised.

Companion implementation source of truth:

- `HEADER_FOOTER_IMPLEMENTATION_PLAN.md` is the canonical plan for fixing the current `headers_footers` and `Absent` weaknesses through margin-aware seeding, dedicated header/footer prompts, verifier-level drop semantics, and targeted ablations.

### 1.1 Scope decision for the current paper

The current scope decision is explicit:

- **SVR-OCR is not only future work**
- **SVR-OCR is intended to be built and benchmarked in this paper**
- the target evaluated method is **`SVR-OCR-Full`**
- `SVR-OCR-Lite` remains a contingency path only if a full subsystem blocks the paper timeline

This means the paper target is no longer limited to:

- routing results
- specialized-vs-general backend comparison
- prompt plus post-processing ablation

The paper target now includes a fourth concrete result:

- a built and benchmarked `SVR-OCR` method on `olmOCR-Bench`, with comparison against `StructuredPrompt` and `StructuredPrompt+Post`

## 2. One-Sentence Thesis

A general-purpose VLM can be made substantially more document-competitive by replacing single-pass full-page transcription with a **layout-graph, region-specialized, render-verified OCR pipeline** that spends additional compute only on uncertain or structurally difficult regions.

## 3. Why SVR-OCR Exists

### 3.1 Immediate motivation from current results

The current project already established three things.

1. Category-aware routing improves end-to-end PDF extraction quality on heterogeneous documents.
2. Specialized OCR/document models still outperform the current Qwen-family general-purpose baseline by a large margin on `olmOCR-Bench`.
3. Structured prompting plus post-processing improves Qwen, but the improvement is narrow and does not close the gap.

Current benchmark evidence motivating SVR-OCR:

- `olmocr2`: `74.7% ± 1.0%`
- `qwen_structured`: `50.0% ± 1.2%`
- `qwen_structured_post`: `52.3% ± 1.2%`

The gap is especially large on:

- `math`
- `order`
- `table`
- `multi_column`
- `long_tiny_text`

This pattern matters. It implies that the main weakness of the current general-purpose VLM path is not only raw text recognition. The larger weakness is **document-specific inference structure**.

### 3.2 What current prompt engineering does not solve

The current `StructuredPrompt+Post` recipe helps mostly with:

- heading cleanup
- footer/header cleanup
- improved text-presence recovery on difficult pages

It does not materially solve:

- multi-column reading order
- table fidelity
- equation fidelity
- region typing
- selective high-resolution recovery for tiny text
- robust document reconstruction when some local outputs are uncertain

Therefore the next step should not be “one more prompt variant.” It should be a new inference-time architecture.

## 4. Core Idea

SVR-OCR treats OCR as a **structured inverse-rendering problem**, not as a single transcription call.

Instead of asking a general-purpose VLM to directly emit a complete page-level Markdown document in one pass, SVR-OCR does the following:

1. build a **layout graph** of the page
2. identify which regions are hard, uncertain, or structurally sensitive
3. re-transcribe only those regions with **typed prompts** and higher-resolution crops
4. **render** the candidate output back into synthetic content
5. compare the synthetic rendering against the original page crop
6. repair or rerank local candidates when the visual mismatch is too high
7. assemble the final page from verified block outputs and explicit reading-order edges

This makes the general-purpose VLM behave more like a document system:

- structure first
- transcription second
- verification third
- repair only where needed

## 5. Design Principles

SVR-OCR must obey the following principles.

### 5.1 Training-free first

The initial SVR-OCR system should be an **inference-time method**. It should not require model fine-tuning to show gains.

### 5.2 Selective compute

Additional compute should be spent only on:

- low-confidence blocks
- dense tiny-text regions
- tables
- equations
- ambiguous multi-column regions
- visually noisy historical scans

### 5.3 Typed processing

Different region types should be handled differently. A table block should not be transcribed with the same prompt and verification logic as a paragraph block.

### 5.4 Verifiable outputs

Whenever possible, generated output should be checked against the image, not trusted by default.

### 5.5 Provenance preservation

Every final block in the output should retain provenance:

- page id
- block id
- source crop
- prompt type
- verification score
- repair count

### 5.6 Document fidelity over fluency

The system must prefer conservative, faithful extraction over “nice-looking” but hallucinated output.

## 6. Targeted Failure Modes

SVR-OCR is designed specifically to reduce errors in the following categories.

### 6.1 Long tiny text

Problem:

- the VLM misses dense small text when processing the entire page at moderate resolution

SVR-OCR response:

- detect dense blocks
- crop them separately
- re-run transcription at higher effective resolution

### 6.2 Multi-column reading order

Problem:

- the VLM flattens columns incorrectly or interleaves content across columns

SVR-OCR response:

- infer a page graph with explicit reading-order edges
- transcribe block-wise rather than linearly from the full page
- assemble final output from the graph, not from a raw page string

### 6.3 Tables

Problem:

- the VLM paraphrases, linearizes, or partially drops table structure

SVR-OCR response:

- detect table blocks
- transcribe them with a table-specific prompt
- verify by rendering HTML and comparing visual alignment to the image crop

### 6.4 Equations and math-heavy regions

Problem:

- equation output is incomplete, malformed, or hard to render

SVR-OCR response:

- isolate equation blocks
- request LaTeX explicitly
- verify by rendering LaTeX to image and comparing against the source crop
- repair if the match is poor

### 6.5 Boilerplate contamination

Problem:

- headers, footers, page numbers, and running titles pollute output

SVR-OCR response:

- detect recurring boilerplate across pages
- mark such blocks as low-value or ignorable during assembly

### 6.6 Visual noise and old scans

Problem:

- background artifacts, skew, degradation, or low contrast reduce extraction quality

SVR-OCR response:

- preprocess with conservative denoising or contrast normalization
- use block-level retries rather than page-level reruns

## 7. System Overview

SVR-OCR has eight stages.

### Stage 0. Page preparation

Input:

- PDF page or page image

Operations:

- rasterize page if needed
- normalize orientation if obvious rotation is detected
- keep original page image as immutable source
- optionally create multiple cached versions:
  - original resolution
  - medium-resolution overview image
  - high-resolution image for crops

Output:

- `PageImageBundle`

### Stage 1. Layout graph pass

Goal:

- produce an explicit graph representation of the page before transcription

The model or layout subsystem predicts:

- block bounding boxes
- block type
- block confidence
- reading-order edges
- containment relationships when relevant
- estimated text density
- estimated difficulty score

Block types should include at least:

- `title`
- `heading`
- `paragraph`
- `list`
- `table`
- `equation`
- `figure`
- `caption`
- `footnote`
- `header_footer`
- `reference`
- `unknown`

Output:

- `LayoutGraph`

### Stage 2. Difficulty and confidence analysis

Goal:

- decide which blocks require extra work

Use a combination of:

- model-reported confidence if available
- OCR heuristics
- density heuristics
- block type priors
- visual complexity features
- page-pattern priors from neighboring pages

Blocks should be flagged for refinement when one or more of the following hold:

- low confidence
- high text density
- very small font estimate
- table block
- equation block
- ambiguous column order
- repeated verifier failures
- high uncertainty in block type

Output:

- `RefinementPlan`

### Stage 3. Region-specialized transcription

Goal:

- transcribe each block using a prompt specialized to that block type

Each selected block is transcribed from a crop, not from the full page.

Use typed prompts:

- paragraph prompt
- heading prompt
- table prompt
- equation prompt
- caption prompt
- footnote prompt
- reference prompt

Rules:

- do not use one generic prompt for all blocks
- pass surrounding context only when needed
- keep each block self-contained enough to avoid cross-block leakage

For example:

- heading blocks should forbid body text hallucination
- table blocks should require HTML table output
- equation blocks should require LaTeX and forbid prose explanation
- caption blocks should preserve figure/table numbering text exactly when readable

Output:

- one or more `BlockCandidate` objects per block

### Stage 4. Render-and-verify

Goal:

- test whether the candidate output is visually compatible with the original region

This is the key SVR-OCR step.

For each block candidate:

1. render the candidate output back into a synthetic image
2. compare the rendered image against the original crop
3. compute a verifier score
4. accept, rerank, or repair depending on that score

Different block types require different renderers.

- text blocks: render Markdown/plain text using a text renderer
- table blocks: render HTML table
- equation blocks: render LaTeX
- heading blocks: render as a single-line or multi-line title block

Possible verifier signals:

- image similarity score between crop and rendered candidate
- edge-map similarity
- text-line count agreement
- bounding-box occupancy overlap
- token count prior mismatch
- column alignment score
- table cell-grid consistency score
- equation renderability score

Output:

- `VerifiedBlockCandidate`

### Stage 5. Candidate reranking

Goal:

- choose the best candidate among multiple candidates for a block

This stage is used only for hard blocks.

Candidate generation can use:

- repeated samples with low temperature variation
- two prompt variants for the same block type
- one conservative candidate and one recall-oriented candidate

Reranking should be based on:

- verifier score
- type-consistency score
- syntax validity
- agreement with neighboring blocks
- cost budget

Output:

- `SelectedBlock`

### Stage 6. Repair loop

Goal:

- repair only blocks that fail verification

Repair should be local, not global.

Inputs to the repair prompt:

- original crop
- previous candidate output
- verifier failure reason
- structural constraints for the block type

Examples of repair instructions:

- “The previous HTML table does not match the visible row structure. Fix only the table.”
- “The previous LaTeX did not render into a visually matching equation. Keep the same equation and correct the syntax.”
- “The previous text appears to merge two columns. Extract only the left-column text in this crop.”

Repair loop budget:

- default max repairs per block: `2`
- after that, accept best verified candidate or mark block as degraded

Output:

- repaired `SelectedBlock` or degraded fallback block

### Stage 7. Page assembly

Goal:

- reconstruct faithful page Markdown from selected blocks and graph edges

Assembly should use:

- reading-order edges from the layout graph
- block type rules
- cross-block adjacency rules
- caption binding rules
- heading nesting rules

Assembly rules:

- preserve reading order without flattening columns incorrectly
- keep table and equation blocks in place
- bind captions to nearby figures/tables when graph evidence supports it
- omit boilerplate blocks when recurrence logic indicates header/footer content
- preserve footnotes and references as blocks, not as arbitrary paragraph spillover

Output:

- `PageMarkdownWithProvenance`

### Stage 8. Document-level reconciliation

Goal:

- enforce consistency across pages

Document-level cleanup can include:

- recurring header/footer detection
- heading style normalization
- numbering normalization
- duplicate section suppression when repeated by OCR noise
- caption numbering consistency checks
- cross-page reading continuity checks when blocks split across pages

Output:

- final document Markdown
- page/block provenance map
- summary diagnostics

## 8. Core Novelty

SVR-OCR is novel because it combines five ideas into one coherent inference-time system.

1. **Layout graph first**  
   Most general-purpose OCR prompting starts with page transcription. SVR-OCR starts with explicit structure.

2. **Self-specialization by block type**  
   The same general-purpose VLM is turned into a typed document processor through block-specific prompting.

3. **Selective high-resolution refinement**  
   Extra compute is spent only on hard blocks instead of repeatedly reprocessing the full page.

4. **Render-and-verify OCR**  
   Output is checked by rendering it back into image space and comparing it to the source crop.

5. **Local repair loops**  
   Failure triggers block-level repair, not full-page reruns.

The central claim is not “prompting helps.” The claim is that **document-specific inference structure** makes a general-purpose VLM significantly stronger as an OCR backend.

## 9. Data Contracts

The initial implementation should use explicit JSON-like internal contracts.

### 9.1 `LayoutGraph`

```json
{
  "page_id": "page_12",
  "page_size": {"width": 2480, "height": 3508},
  "blocks": [
    {
      "block_id": "b12",
      "bbox": [120, 340, 1820, 610],
      "block_type": "heading",
      "confidence": 0.88,
      "difficulty": 0.31,
      "text_density": 0.22,
      "column_id": 0,
      "neighbors": ["b13"],
      "metadata": {
        "font_scale_estimate": "large",
        "is_repeated_boilerplate": false
      }
    }
  ],
  "reading_order_edges": [["b12", "b13"], ["b13", "b14"]]
}
```

### 9.2 `RefinementPlan`

```json
{
  "page_id": "page_12",
  "refine_blocks": [
    {
      "block_id": "b25",
      "reason": ["low_confidence", "tiny_text"],
      "crop_scale": 2.0,
      "num_candidates": 2,
      "repair_budget": 2,
      "prompt_type": "paragraph_dense"
    }
  ]
}
```

### 9.3 `BlockCandidate`

```json
{
  "page_id": "page_12",
  "block_id": "b25",
  "candidate_id": "b25_c1",
  "block_type": "table",
  "prompt_type": "table_html",
  "content": "<table>...</table>",
  "raw_model_output": "<table>...</table>",
  "syntax_valid": true,
  "generation_metadata": {
    "model": "qwen-family-vlm",
    "temperature": 0.1,
    "max_tokens": 1200
  }
}
```

### 9.4 `VerifiedBlockCandidate`

```json
{
  "block_id": "b25",
  "candidate_id": "b25_c1",
  "verification": {
    "renderable": true,
    "render_score": 0.79,
    "structure_score": 0.91,
    "type_consistency_score": 0.95,
    "final_score": 0.84,
    "failure_reasons": []
  }
}
```

### 9.5 `SelectedBlock`

```json
{
  "page_id": "page_12",
  "block_id": "b25",
  "selected_candidate_id": "b25_c1",
  "content": "<table>...</table>",
  "verification_score": 0.84,
  "repair_count": 1,
  "degraded": false
}
```

### 9.6 `PageMarkdownWithProvenance`

```json
{
  "page_id": "page_12",
  "markdown": "## Results\n\n<table>...</table>",
  "ordered_blocks": ["b12", "b13", "b25"],
  "provenance": {
    "b25": {
      "source_crop": "page_12_b25.png",
      "block_type": "table",
      "verification_score": 0.84,
      "repair_count": 1
    }
  }
}
```

## 10. Verification Strategy in Detail

The verifier is the most important part of SVR-OCR.

### 10.1 Why a verifier is necessary

General-purpose VLM outputs can be:

- partially correct but structurally wrong
- fluent but visually mismatched
- plausible but hallucinated
- syntactically invalid for LaTeX or HTML

Therefore self-confidence or logprobs alone are insufficient.

### 10.2 Verifier components

The verifier should combine multiple signals.

#### A. Renderability

Binary or soft indicator that the candidate can be rendered at all.

Examples:

- valid LaTeX equation render
- valid HTML table render
- valid Markdown/text rendering without catastrophic parse failure

#### B. Visual match score

Compare rendered candidate to source crop using:

- structural similarity proxy
- binarized edge overlap
- line-profile overlap
- whitespace distribution similarity
- connected-component profile similarity

#### C. Structural consistency score

Block-type-specific checks:

- table grid alignment
- equation height/width profile match
- heading compactness
- paragraph line-count compatibility

#### D. Syntax validity score

Examples:

- HTML parse succeeds
- LaTeX render succeeds
- Markdown placeholder syntax matches expected contract

#### E. Neighbor consistency score

Examples:

- caption content consistent with nearby figure/table
- heading level consistent with surrounding headings
- reading order compatible with adjacent blocks

### 10.3 Final verifier score

A simple initial formulation:

```text
final_score =
  w_renderability * renderability
+ w_visual       * visual_match
+ w_structure    * structure_consistency
+ w_syntax       * syntax_validity
+ w_neighbor     * neighbor_consistency
```

Weights should be block-type-specific.

Examples:

- equations weight `renderability` and `visual_match` heavily
- tables weight `structure_consistency` heavily
- headings weight `neighbor_consistency` more than tables do

### 10.4 Accept / repair / reject policy

Suggested default thresholds:

- `>= 0.85`: accept
- `0.65 - 0.85`: eligible for reranking or single repair
- `< 0.65`: repair or degrade

### 10.5 Degraded fallback mode

If repeated repair fails:

- accept the best candidate with a degraded flag
- preserve provenance and the failure reason
- do not silently hallucinate a cleaner answer

## 11. Prompt Taxonomy

SVR-OCR should maintain a typed prompt library.

### 11.1 Heading prompt

Goal:

- extract only the heading text and level evidence

Rules:

- do not include body text
- preserve numbering if visible
- avoid inventing heading level

### 11.2 Paragraph prompt

Goal:

- faithful transcription of prose in reading order

Rules:

- preserve paragraph boundaries
- do not merge neighboring columns
- keep conservative unreadable markers when needed

### 11.3 Dense paragraph prompt

Use for long tiny text.

Rules:

- focus on visible text only
- no summarization
- preserve line breaks only when paragraph structure is ambiguous

### 11.4 Table prompt

Goal:

- produce HTML table

Rules:

- preserve row and column structure
- use empty cells only when visually justified
- do not linearize the table as prose
- include caption only if the crop includes it and it is part of the block

### 11.5 Equation prompt

Goal:

- output only LaTeX

Rules:

- no prose explanation
- preserve operators conservatively
- if a symbol is ambiguous, prefer a conservative placeholder strategy over hallucination

### 11.6 Caption prompt

Goal:

- preserve figure/table caption text exactly when readable

Rules:

- keep figure/table numbering
- do not fold body text into caption output

### 11.7 Footnote/reference prompt

Goal:

- preserve specialized bibliography or footnote formatting as faithfully as possible

## 12. Efficiency Strategy

SVR-OCR must remain cheaper than naive repeated full-page OCR.

### 12.1 Compute budget principle

The full page should be processed once for overview and graph construction. Additional expensive calls should happen only on selected blocks.

### 12.2 Block prioritization

By default, extra compute should be reserved for:

- tables
- equations
- dense small-text regions
- ambiguous multi-column regions
- blocks with poor verifier scores

### 12.3 Candidate count

Use `k > 1` only when needed.

Suggested defaults:

- easy block: `k = 1`
- hard block: `k = 2`
- very hard block: `k = 3` only if budget allows

### 12.4 Repair budget

Suggested defaults:

- easy block: `0` repairs
- hard block: `1` repair
- very hard block: `2` repairs max

### 12.5 Early exits

Skip further refinement when:

- verifier score already exceeds threshold
- block type is low-value boilerplate
- neighboring pages show stable recurring structure and current block is consistent

### 12.6 Required artifacts and logs

Every SVR-OCR run should persist enough artifacts for later debugging and paper analysis.

At minimum, retain:

- page overview image
- crop image per refined block
- raw layout graph
- refinement plan
- all block candidates for refined blocks
- verifier component scores
- selected block output
- repair prompts and repair outputs
- final page Markdown with provenance
- page-level cost and latency summary

## 13. Integration with the Current Project

SVR-OCR is intended to integrate into the current project in a staged way.

### 13.1 Initial deployment boundary

The first integration target is the **OCR branch only**.

That means:

- OCR-routed pages should use SVR-OCR instead of the current single-pass general-purpose VLM OCR path
- non-OCR scholarly pages should still go to `ia_phase1`
- non-OCR text-heavy pages should still go to the native `ocr_agent` path
- page outputs should still be merged in original page order by the current routed system

This boundary matters. The first goal is not to replace the whole routed system. The first goal is to make the OCR branch stronger.

### 13.2 Evaluation boundary

SVR-OCR should be evaluated in two modes, with a clear priority order.

1. **Primary paper target: backend-only mode**
   - use `olmOCR-Bench`
   - report `StructuredPrompt`, `StructuredPrompt+Post`, and `SVR-OCR-Full`
   - include `SVR-OCR-Lite` only as an intermediate ablation or fallback checkpoint

2. **Secondary paper target: routed-system mode**
   - plug `SVR-OCR-Full` into the OCR branch of `improved_ocr_agent`
   - evaluate on the internal benchmark, especially OCR-heavy and hybrid cases
   - if full routed integration is not finished in time, backend-only `olmOCR-Bench` evidence still remains mandatory for the paper

### 13.3 What counts as success in the routed system

SVR-OCR should be considered successful for the routed system if it improves OCR-heavy page fidelity without causing regressions in:

- page ordering
- figure/table placeholder handling
- section assignment downstream of OCR pages
- merge stability when OCR and non-OCR pages are combined

## 14. Expected Research Contributions

If successful, SVR-OCR supports the following research claims.

### 14.1 Main method claim

A general-purpose VLM can be made significantly more competitive for document OCR by adding explicit structure, verification, and targeted repair at inference time.

### 14.2 Efficiency claim

Most of the gains come from selective block refinement rather than repeated whole-page reruns.

### 14.3 Scientific claim

The main bottleneck for current general-purpose VLM OCR is not only text recognition capacity, but the lack of document-specific inference structure.

## 15. Success Criteria

SVR-OCR is successful if it meets at least some of the following.

### 15.1 On `olmOCR-Bench`

Relative to `StructuredPrompt+Post`, it should materially improve:

- `long_tiny_text`
- `multi_column`
- `table_tests`
- `math`
- `order`

### 15.2 On internal OCR-heavy pages

It should reduce:

- section drift
- header/footer leakage
- misplaced captions
- missing tables
- broken equation handling

### 15.3 On cost-quality tradeoff

It should deliver stronger quality than page-level structured prompting without multiplying cost by a large constant on every page.

## 16. Experiment Plan

SVR-OCR should be evaluated in a controlled ablation.

### 16.1 Conditions

Use the following sequence.

1. `Naive`
2. `StructuredPrompt`
3. `StructuredPrompt+Post`
4. `SVR-OCR-Lite`
5. `SVR-OCR-Full`

For the current paper, the required reported comparison is:

- `StructuredPrompt`
- `StructuredPrompt+Post`
- `SVR-OCR-Full`

`SVR-OCR-Lite` is useful as an implementation checkpoint and ablation, but it is not the intended final stopping point.

#### `SVR-OCR-Lite`

Minimum new method:

- layout graph
- selective high-resolution crop refinement
- typed prompts
- no full render-and-repair loop yet

#### `SVR-OCR-Full`

Complete method:

- layout graph
- refinement plan
- typed prompts
- render-and-verify
- local reranking
- repair loop
- document-level reconciliation

### 16.2 Datasets

Primary:

- `olmOCR-Bench`

Secondary:

- internal OCR-heavy subset from the project benchmark
- hard example set from:
  - `p118`
  - `p119`
  - `a001`
  - `a002`
  - `a004`
  - `t001`

### 16.3 Metrics

Track:

- official benchmark overall score
- category-level score deltas
- verifier acceptance rate
- repair frequency
- average candidates per refined block
- average cost or token usage per page
- average latency per page
- failure-type distribution

### 16.4 Slice-level expectations

SVR-OCR should show its strongest gains on:

- `long_tiny_text`
- `multi_column`
- `table_tests`
- `old_scans_math`
- `headers_footers`

### 16.5 Failure analysis

Every run should retain examples where:

- verifier falsely accepts a bad candidate
- verifier falsely rejects a good candidate
- repair loop causes regression
- graph ordering fails
- table or equation rendering fails despite correct transcription intent

## 17. Ablation Questions

The following ablations are important.

1. full-page structured prompting vs block-wise typed prompting
2. no verifier vs verifier
3. no repair vs repair loop
4. single-resolution crops vs adaptive crop scaling
5. generic prompt library vs block-type-specific prompt library
6. no document reconciliation vs document-level reconciliation

## 18. Risks and Mitigations

### 18.1 Risk: verifier becomes brittle

Problem:

- render comparison may reject semantically correct but visually different outputs

Mitigation:

- use multiple verifier signals
- keep human-readable failure reasons
- avoid one hard image-diff threshold

### 18.2 Risk: pipeline becomes too expensive

Problem:

- block-level refinement can explode cost if too many blocks are flagged

Mitigation:

- refine only uncertain or structurally important blocks
- cap candidate counts and repair loops
- collect page-level cost analytics from day one

### 18.3 Risk: layout graph is noisy

Problem:

- bad block segmentation poisons downstream steps

Mitigation:

- allow block merging and splitting in the repair stage
- keep `unknown` block type as safe fallback
- use neighbor consistency checks

### 18.4 Risk: block prompts lose context

Problem:

- local crops can omit context needed for disambiguation

Mitigation:

- allow limited surrounding context windows
- pass parent heading or nearby caption context when needed

### 18.5 Risk: system becomes too complex for the paper timeline

Problem:

- full SVR-OCR has multiple interacting subsystems and may be harder to stabilize than prompt-only baselines

Mitigation:

- implement in phases, but keep `SVR-OCR-Full` as the planned paper target
- use `SVR-OCR-Lite` only as a contingency checkpoint if one subsystem blocks evaluation
- prioritize the subsystems that matter most for the benchmark gap:
  - layout graph
  - typed refinement
  - verification
  - repair

## 19. Contingency Path if Full Build Blocks

The preferred paper outcome is a working and benchmarked `SVR-OCR-Full`.

If a full subsystem blocks the deadline, the contingency path is `SVR-OCR-Lite`, defined as:

1. page overview call to build rough block graph
2. refinement of tables, equations, and dense text blocks
3. typed prompts for those blocks
4. simple verifier based on renderability plus lightweight visual similarity
5. page assembly with explicit reading order

This contingency is not the default target. It exists only to protect the paper if full verification-guided repair is not ready in time.

## 20. Recommended Repository Structure

Suggested future structure under `SVR-OCR/`:

```text
SVR-OCR/
  docs/
    README.md
    SOURCE_OF_TRUTH.md
  src/
    layout/
      graph_builder.py
      block_types.py
    crops/
      crop_manager.py
      refinement_policy.py
    prompts/
      heading.txt
      paragraph.txt
      dense_paragraph.txt
      table.txt
      equation.txt
      caption.txt
    transcribe/
      block_runner.py
      candidate_store.py
    verify/
      text_verifier.py
      table_verifier.py
      equation_verifier.py
      score_fusion.py
    repair/
      repair_runner.py
    assemble/
      page_assembler.py
      document_reconciler.py
    eval/
      bench_runner.py
      ablation_runner.py
```

## 21. Implementation Roadmap

### 21.1 Milestone 1: Documentation and interfaces

Deliverables:

- this source-of-truth document
- typed data contracts
- initial prompt taxonomy
- experiment matrix
- explicit paper-scope commitment to `SVR-OCR-Full`

### 21.2 Milestone 2: Full-build foundation

Deliverables:

- rough layout graph pass
- typed crop selection
- dense text, table, and equation refinements
- block assembly

### 21.3 Milestone 3: verifier integration

Deliverables:

- block-specific renderers
- verifier scoring
- candidate reranking

### 21.4 Milestone 4: repair loop

Deliverables:

- failure reason generation
- local repair prompts
- capped repair retries

### 21.5 Milestone 5: document reconciliation and full evaluation

Deliverables:

- recurring boilerplate suppression
- document-level heading normalization
- benchmark and cost reporting
- `olmOCR-Bench` evaluation for `SVR-OCR-Full`
- paper-ready comparison against `StructuredPrompt` and `StructuredPrompt+Post`

## 22. Paper Positioning

SVR-OCR should be positioned as a **core method contribution of the current paper**, not only as follow-up work.

The paper message should now be:

- routing works on heterogeneous PDFs
- specialized OCR currently beats prompt-only general-purpose VLM OCR
- prompt/post-processing help but do not close the gap
- `SVR-OCR` tests whether document-specific inference structure can narrow that gap more substantially

If the benchmark results are positive, the method contribution becomes:

- a general-purpose VLM can be pushed materially closer to specialized OCR quality through layout-aware, verifier-guided inference

If the benchmark results are mixed, the contribution remains:

- SVR-OCR identifies which structural subsystems are necessary and which failure modes remain hardest even after explicit verification and local repair

## 23. Non-Goals

SVR-OCR is not initially trying to do the following.

- train a new OCR foundation model
- replace all specialized OCR systems immediately
- solve arbitrary document understanding tasks beyond OCR/linearization
- build a perfect universal verifier from day one

## 24. Decision Rules

Use these project rules going forward.

1. Do not add new generic prompt variants before implementing the core `SVR-OCR-Full` path.
2. Do not spend equal compute on every page region.
3. Do not trust page-level fluency as evidence of document fidelity.
4. Do not treat verifier score as a single source of truth; keep failure reasons and provenance.
5. When timing is tight, prioritize categories where current Qwen is weakest and where SVR-OCR is most likely to help.
6. Treat `SVR-OCR-Lite` as a contingency path, not as the intended paper endpoint.

## 25. Open Questions

These are open design questions, not unresolved goals.

1. Should the layout graph come from the same VLM, a specialized layout detector, or a hybrid of both?
2. What is the best cheap visual similarity metric for verifier scoring?
3. When should block splitting or merging be allowed after the initial graph pass?
4. How much neighboring context improves block prompts without reintroducing page-level confusion?
5. Which block types deserve multi-candidate reranking in the minimal prototype?

## 26. Immediate Next Steps

The next concrete actions after this document are:

1. implement the full `SVR-OCR` skeleton under `SVR-OCR/src`
2. define the exact `SVR-OCR-Full` benchmark experiment against:
   - `StructuredPrompt`
   - `StructuredPrompt+Post`
3. build the four core subsystems in this order:
   - layout graph
   - typed refinement
   - verification
   - repair
4. run `olmOCR-Bench` on `SVR-OCR-Full` and record paper-ready results
5. use `SVR-OCR-Lite` only if a full subsystem blocks the benchmark deadline

## 27. Summary

SVR-OCR is the method to be implemented and benchmarked in this paper for making a general-purpose VLM more competitive as an OCR backend by giving it three things it currently lacks:

- explicit document structure
- selective high-resolution specialization
- verifier-guided local repair

Its central bet is that a large part of the remaining gap to specialized OCR systems comes from **how inference is organized**, not only from the base model family itself.
