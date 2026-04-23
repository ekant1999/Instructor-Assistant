# SVR-OCR Header/Footer Implementation Plan

Status: implementation source of truth for the `headers_footers` weakness  
Last updated: 2026-04-22  
Owner: SVR-OCR research/code path

## 0. Implementation Status

P0 is implemented in the current SVR-OCR codebase:

- margin-aware page seeding is available through `make_margin_aware_page_bundle(...)`
- `PromptType.HEADER_FOOTER` and `PromptType.REPAIR_HEADER_FOOTER` are registered
- `header_footer.txt` and `repair_header_footer.txt` are present
- `HeaderFooterBlockVerifier` implements verifier-level drop semantics
- `MarkdownPageAssembler` respects `VerificationBreakdown.emit`
- `bench_runner.py` and `smoke_openai_compatible.py` expose `--page-seed-mode margin_aware`
- `SVR-OCR/tests/test_header_footer.py` covers the P0 behavior

P1/P2 remain open:

- repair-specific header/footer behavior beyond the P0 prompt file
- document-level recurrence cleanup
- automated benchmark ablation orchestration

## 1. Goal

Make `SVR-OCR` strong on `headers_footers.jsonl` without regressing the categories where it is already strong.

Current measured weakness:

| Slice | `StructuredPrompt+Post` | `Mistral OCR` | `SVR-OCR-Full` | `DeepSeek OCR` | `olmOCR-2` |
|---|---:|---:|---:|---:|---:|
| `headers_footers.jsonl` | 64.7% | 91.5% | 38.8% | 96.6% | 95.4% |

Related type-level weakness:

| Candidate | Absent |
|---|---:|
| `olmocr2` | 95.3% |
| `svr_ocr_full` | 42.3% |
| `qwen_structured_post` | 66.3% |

The target is not only better transcription. The target is better omission: SVR-OCR must learn when not to emit margin boilerplate.

## 2. Diagnosis

The current benchmarked path has these properties:

- `SVR-OCR/src/svr_ocr/io/page_inputs.py` creates one `whole_page` block.
- That block is seeded as `BlockType.PARAGRAPH`.
- `SVR-OCR/src/svr_ocr/crops/refinement_policy.py` turns high-density/difficult blocks into `PromptType.DENSE_PARAGRAPH`.
- `BlockType.HEADER_FOOTER` exists in `SVR-OCR/src/svr_ocr/contracts.py`, but it is not wired into prompt selection.
- There is no `PromptType.HEADER_FOOTER`.
- There is no header/footer prompt.
- There is no header/footer verifier.
- `SVR-OCR/src/svr_ocr/assemble/page_assembler.py` emits every selected non-empty block.
- `SVR-OCR/src/svr_ocr/assemble/document_reconciler.py` only joins pages and does not remove recurring margin boilerplate.

Therefore the system currently asks the VLM to solve header/footer suppression implicitly inside a full-page transcription prompt. That is the wrong control boundary.

## 3. Design Decision

Fix header/footer performance by changing the inference structure, not by adding one more full-page prompt.

The P0 implementation should:

1. Split rendered pages into three seed blocks: `top_margin`, `body`, and `bottom_margin`.
2. Run the main OCR pass on the `body` crop, not the full page.
3. Send the margin bands through a dedicated header/footer prompt.
4. Add verifier-supported drop semantics so intentional omission is scored as success internally, not treated as an empty failure.
5. Preserve a fallback path for the previous whole-page behavior for ablations.

The P1/P2 implementation should:

1. Add document-level recurrence cleanup when multi-page processing is available.
2. Add ablation tooling and metrics to prove which parts of the fix matter.

## 4. Non-Goals

- Do not train a detector.
- Do not add a large OCR dependency only for headers/footers.
- Do not make generic post-processing delete arbitrary repeated lines without provenance.
- Do not use a brittle global regex-only cleanup as the main solution.
- Do not regress `math`, `table_tests`, `multi_column`, or `long_tiny_text` by shrinking the body crop too aggressively.

## 5. Output Semantics

Introduce explicit emit/drop behavior.

The header/footer prompt should use a deterministic marker:

```text
<<SVR_DROP_HEADER_FOOTER>>
```

Meaning:

- The model saw visible text, but it is margin boilerplate and should not be emitted.
- The verifier should treat this as a successful omission for a `HEADER_FOOTER` block.
- The assembler should not include this block in final Markdown.

This is better than asking the model to return an empty response because empty text is currently interpreted as a failed transcription by `TextBlockVerifier`.

## 6. File-by-File Implementation Plan

### 6.1 `SVR-OCR/src/svr_ocr/config.py`

Add a new dataclass:

```python
@dataclass
class HeaderFooterPolicy:
    enabled: bool = True
    top_margin_ratio: float = 0.12
    bottom_margin_ratio: float = 0.12
    min_margin_px: int = 80
    max_margin_px: int = 260
    body_overlap_px: int = 16
    crop_scale: float = 1.25
    num_candidates: int = 2
    repair_budget: int = 0
    drop_marker: str = "<<SVR_DROP_HEADER_FOOTER>>"
    recurrence_min_pages: int = 3
    recurrence_similarity_threshold: float = 0.86
```

Extend `SVROCRConfig`:

```python
header_footer: HeaderFooterPolicy = field(default_factory=HeaderFooterPolicy)
```

Rationale:

- Keep all tunable thresholds out of prompts and verifiers.
- Make `headers_footers` ablations reproducible.
- Allow the benchmark runner to disable margin-aware behavior for baseline comparisons.

### 6.2 `SVR-OCR/src/svr_ocr/contracts.py`

Extend `PromptType`:

```python
HEADER_FOOTER = "header_footer"
REPAIR_HEADER_FOOTER = "repair_header_footer"
```

Extend `VerificationBreakdown` with backward-compatible defaults:

```python
emit: bool = True
drop_reason: str | None = None
```

Do not add a new `VerificationStatus` unless later code needs it. The current pipeline only needs to know whether a verified block should be emitted.

Expected metadata conventions for margin blocks:

```python
block.metadata["position_band"] = "top" | "bottom" | "body"
block.metadata["drop_candidate"] = True | False
block.metadata["seeded_margin_aware"] = True
block.metadata["page_num"] = int | None
```

### 6.3 `SVR-OCR/src/svr_ocr/io/page_inputs.py`

Keep `make_whole_page_bundle(...)` unchanged for reproducibility.

Add a new dataclass:

```python
@dataclass
class MarginAwareSeedOptions:
    top_margin_ratio: float = 0.12
    bottom_margin_ratio: float = 0.12
    min_margin_px: int = 80
    max_margin_px: int = 260
    body_overlap_px: int = 16
    body_difficulty: float = 0.7
    body_text_density: float = 1.0
    margin_difficulty: float = 0.5
    margin_text_density: float = 0.4
```

Add:

```python
def make_margin_aware_page_bundle(
    image_path: str | Path,
    *,
    page_id: str,
    seed: MarginAwareSeedOptions | None = None,
    extra_metadata: dict[str, object] | None = None,
) -> PageImageBundle:
    ...
```

This function should create exactly three blocks:

```text
top_margin     BlockType.HEADER_FOOTER  bbox=[0, 0, width, top_h]
body           BlockType.PARAGRAPH      bbox=[0, top_h - overlap, width, height - bottom_h + overlap]
bottom_margin  BlockType.HEADER_FOOTER  bbox=[0, height - bottom_h, width, height]
```

Each block must include:

```python
"order_index": 0 | 1 | 2
"layout_confidence": ...
"difficulty": ...
"signals": {"text_density": ...}
"metadata": {
    "seeded_margin_aware": True,
    "position_band": "top" | "body" | "bottom",
    "drop_candidate": True | False,
    "page_num": extra_metadata.get("page_num") if available,
}
```

Margin height calculation:

```python
raw_top = int(height * top_margin_ratio)
top_h = min(max(raw_top, min_margin_px), max_margin_px)
```

Use the same logic for bottom margin. Clamp body coordinates so the body block is always at least one pixel high.

### 6.4 `SVR-OCR/src/svr_ocr/io/__init__.py`

Export:

```python
MarginAwareSeedOptions
make_margin_aware_page_bundle
```

### 6.5 `SVR-OCR/src/svr_ocr/crops/refinement_policy.py`

Update `_prompt_type_for_block(...)`:

```python
if block.block_type == BlockType.HEADER_FOOTER:
    return PromptType.HEADER_FOOTER
```

Update `_plan_block(...)` so `HEADER_FOOTER` is handled before density/difficulty logic:

```python
if block.block_type == BlockType.HEADER_FOOTER:
    return RefinementDecision(
        block_id=block.block_id,
        prompt_type=PromptType.HEADER_FOOTER,
        crop_scale=self.config.header_footer.crop_scale,
        num_candidates=self.config.header_footer.num_candidates,
        repair_budget=self.config.header_footer.repair_budget,
        reasons=["header_footer_candidate", f"position_{block.metadata.get('position_band', 'unknown')}"],
    )
```

Important:

- Do not allow header/footer blocks to be converted to `DENSE_PARAGRAPH`.
- Do not apply generic high-density repair logic to header/footer blocks in P0.
- Body blocks should still use the existing dense paragraph path when appropriate.

### 6.6 `SVR-OCR/src/svr_ocr/prompts/library.py`

Register:

```python
PromptType.HEADER_FOOTER: "header_footer.txt"
PromptType.REPAIR_HEADER_FOOTER: "repair_header_footer.txt"
```

### 6.7 `SVR-OCR/src/svr_ocr/prompts/header_footer.txt`

Add a new prompt with a strict output protocol:

```text
You are inspecting a page margin region from a document.
The region is from the {position_band} of the page.

Decide whether the visible content should be emitted into the final Markdown.

Return exactly <<SVR_DROP_HEADER_FOOTER>> if the region is any of:
- page number
- running title
- running author name
- journal/conference name
- copyright line
- DOI/URL/arXiv identifier
- repeated document boilerplate
- decorative separator with no body content

Return faithful Markdown only if the margin contains real document content that should remain, such as:
- a first-page title that is visually in the top band
- an author/affiliation line that is part of the first-page content
- a section heading that was accidentally captured in the margin
- non-repeated body text

Do not summarize.
Do not invent missing text.
Do not include explanations.
Source hint: {source_text}
```

This requires `pipeline.py` to pass `position_band` into prompt rendering.

### 6.8 `SVR-OCR/src/svr_ocr/prompts/repair_header_footer.txt`

Add a repair prompt for P1. It can initially be unused because P0 sets `repair_budget=0`.

Protocol:

```text
You are repairing a header/footer classification.
Previous output:
{previous_output}

Verifier failure reasons:
{failure_reasons}

Return exactly <<SVR_DROP_HEADER_FOOTER>> for boilerplate.
Return faithful Markdown only for real body content.
Do not explain.
```

### 6.9 `SVR-OCR/src/svr_ocr/pipeline.py`

Update prompt rendering in `process_page(...)` to include block/page metadata:

```python
prompt_text = self.prompt_library.render(
    decision.prompt_type,
    block_type=block.block_type.value,
    source_text=block.source_text or "",
    position_band=block.metadata.get("position_band", ""),
    page_num=block.metadata.get("page_num", page.metadata.get("page_num", "")),
    drop_marker=self.config.header_footer.drop_marker,
)
```

Update `_seed_prompt_type(...)`:

```python
BlockType.HEADER_FOOTER: PromptType.HEADER_FOOTER
```

Update `_build_pipeline(...)` to create and pass a `HeaderFooterBlockVerifier`.

### 6.10 `SVR-OCR/src/svr_ocr/verify/header_footer_verifier.py`

Add a new verifier:

```python
class HeaderFooterBlockVerifier(BlockVerifier):
    ...
```

Verification behavior:

1. Normalize candidate content by trimming whitespace and stripping code fences.
2. If content equals `<<SVR_DROP_HEADER_FOOTER>>`, return:

```python
VerificationBreakdown(
    renderable=True,
    render_score=1.0,
    structure_score=1.0,
    type_consistency_score=1.0,
    syntax_validity_score=1.0,
    neighbor_consistency_score=1.0,
    final_score=0.95,
    emit=False,
    drop_reason="model_drop_marker",
)
```

3. If content is empty and the block is in a top/bottom margin, return `emit=False` with a good but lower score, e.g. `0.80`, and `drop_reason="empty_margin_candidate"`.
4. If content matches boilerplate patterns, return `emit=False` with high score:

Useful patterns:

```text
^\d+$
^page\s+\d+(\s+of\s+\d+)?$
^[ivxlcdm]+$
doi:
arxiv:
http://
https://
www\.
copyright
proceedings
conference
journal
preprint
submitted to
```

5. If content is non-empty and not confidently boilerplate, return `emit=True` with a moderate-to-high score.
6. Penalize long margin content only lightly because first-page titles or author blocks can be real content.
7. Use `block.metadata["position_band"]` and `graph.page_size` to confirm the region is actually near the page edge.

Do not call `TextBlockVerifier` for this path. The whole point is that intentional omissions should not be treated as failed text.

### 6.11 `SVR-OCR/src/svr_ocr/verify/base.py`

Extend `VerifierRouter.__init__(...)`:

```python
header_footer_verifier: BlockVerifier | None = None
```

Route:

```python
if block.block_type == BlockType.HEADER_FOOTER and self.header_footer_verifier is not None:
    return self.header_footer_verifier.verify(block, candidate, graph)
```

Fallback to `text_verifier` only if no header/footer verifier is provided.

### 6.12 `SVR-OCR/src/svr_ocr/verify/__init__.py`

Export:

```python
HeaderFooterBlockVerifier
```

### 6.13 `SVR-OCR/src/svr_ocr/assemble/page_assembler.py`

Update `MarkdownPageAssembler.assemble(...)`:

```python
should_emit = getattr(selected.verification, "emit", True)
if not should_emit:
    provenance[block.block_id] = ...
    continue
```

Also skip content equal to the configured drop marker. Because the assembler does not currently receive config, implement a local conservative check:

```python
if stripped == "<<SVR_DROP_HEADER_FOOTER>>":
    return ""
```

Extend provenance:

```python
"emitted": bool(should_emit and content)
"drop_reason": selected.verification.drop_reason
"position_band": block.metadata.get("position_band")
"content_preview": content[:200]
```

Rationale:

- The document reconciler needs enough provenance for later recurrence cleanup.
- Empty intentional drops should be auditable.

### 6.14 `SVR-OCR/src/svr_ocr/assemble/document_reconciler.py`

P0 can leave this unchanged.

P1 should add recurrence cleanup for multi-page document processing:

```python
class SimpleDocumentReconciler(DocumentReconciler):
    def reconcile(...):
        pages = self._drop_recurrent_margin_lines(pages)
        ...
```

Algorithm:

1. Read `content_preview`, `block_type`, `position_band`, and `emitted` from page provenance.
2. Normalize margin strings:

```python
lowercase
strip punctuation
replace digits with "#"
collapse whitespace
remove page/page-of prefixes
```

3. Count normalized strings across pages.
4. If a normalized string appears on at least `recurrence_min_pages` pages and comes from top/bottom margin blocks, remove it from final Markdown.
5. Add diagnostics:

```python
"recurrent_margin_lines_removed": int
"recurrent_margin_clusters": list[...]
```

Important:

- This helps real multi-page documents.
- It will not fully help `olmOCR-Bench` if the benchmark calls each page independently.
- Therefore P0 margin-aware seeding is still required.

### 6.15 `SVR-OCR/src/svr_ocr/transcribe/block_runner.py`

Update `_default_content_for_prompt(...)`:

```python
PromptType.HEADER_FOOTER: "<<SVR_DROP_HEADER_FOOTER>>"
PromptType.REPAIR_HEADER_FOOTER: "<<SVR_DROP_HEADER_FOOTER>>"
```

This keeps scaffold/smoke tests deterministic.

### 6.16 `SVR-OCR/src/svr_ocr/repair/repair_runner.py`

P0 can leave repair disabled for header/footer blocks.

P1 should map:

```python
PromptType.HEADER_FOOTER: PromptType.REPAIR_HEADER_FOOTER
```

Only enable this after verifier behavior is stable. Header/footer repair can easily overthink simple omissions.

### 6.17 `SVR-OCR/src/svr_ocr/eval/bench_runner.py`

Import:

```python
MarginAwareSeedOptions
make_margin_aware_page_bundle
```

Add runner option:

```python
page_seed_mode: Literal["whole_page", "margin_aware"] = "whole_page"
```

Add CLI:

```text
--page-seed-mode {whole_page,margin_aware}
--top-margin-ratio 0.12
--bottom-margin-ratio 0.12
--min-margin-px 80
--max-margin-px 260
--body-overlap-px 16
```

Update `_process_single_page(...)`:

```python
if self.page_seed_mode == "margin_aware":
    page = make_margin_aware_page_bundle(...)
else:
    page = make_whole_page_bundle(...)
```

For paper ablations, preserve both modes:

```text
svr_ocr_full_legacy_seed      -> whole_page
svr_ocr_full_margin_aware     -> margin_aware
```

Default recommendation:

- Keep CLI default as `whole_page` for backward-compatible reproduction.
- Use `--page-seed-mode margin_aware` for the new header/footer run.

### 6.18 `SVR-OCR/src/svr_ocr/eval/ablation_runner.py`

Replace the placeholder with a minimal orchestrator that can run these configurations:

| Name | Seed mode | Header/footer verifier | Recurrence cleanup |
|---|---|---:|---:|
| `legacy_whole_page` | `whole_page` | off | off |
| `margin_body_only` | `margin_aware` | off | off |
| `margin_hf_verifier` | `margin_aware` | on | off |
| `margin_hf_recurrence` | `margin_aware` | on | on |

The ablation runner can initially just print commands rather than executing them. The important part is preserving exact experimental conditions.

### 6.19 `SVR-OCR/scripts/smoke_openai_compatible.py`

Add:

```text
--page-seed-mode {whole_page,margin_aware}
```

Use `make_margin_aware_page_bundle(...)` when selected.

Smoke checks:

- A page image with only margin boilerplate should produce empty final Markdown.
- A page image with body content should still produce body Markdown.

### 6.20 `SVR-OCR/src/svr_ocr/__init__.py`

Export new contract symbols if the file currently exports `PromptType` and related public objects only indirectly.

Minimum:

- No required change if imports are enum-level only.
- Add exports only if tests or external callers need `HeaderFooterPolicy`, `MarginAwareSeedOptions`, or `make_margin_aware_page_bundle`.

### 6.21 `SVR-OCR/tests/test_header_footer.py`

Add a new SVR-OCR test directory if none exists.

Required unit tests:

1. `make_margin_aware_page_bundle(...)` creates exactly `top_margin`, `body`, `bottom_margin`.
2. Top and bottom blocks are `BlockType.HEADER_FOOTER`.
3. Body bbox excludes page margins and remains valid.
4. `TypedRefinementPlanner` maps header/footer blocks to `PromptType.HEADER_FOOTER`.
5. `HeaderFooterBlockVerifier` accepts `<<SVR_DROP_HEADER_FOOTER>>` with `emit=False`.
6. `MarkdownPageAssembler` omits non-emitted blocks.
7. Boilerplate patterns like `Page 3`, `https://...`, and `doi:` are dropped.
8. A first-page title-like margin string can still be emitted if it does not match boilerplate.

Optional integration test:

- Build a synthetic `PageImageBundle` with three seeded blocks and a `PassthroughBlockTranscriber`.
- Confirm final Markdown contains only the body block.

## 7. Rollout Order

### P0: Single-page benchmark fix

Implement these files first:

1. `config.py`
2. `contracts.py`
3. `io/page_inputs.py`
4. `io/__init__.py`
5. `crops/refinement_policy.py`
6. `prompts/library.py`
7. `prompts/header_footer.txt`
8. `pipeline.py`
9. `verify/header_footer_verifier.py`
10. `verify/base.py`
11. `verify/__init__.py`
12. `assemble/page_assembler.py`
13. `transcribe/block_runner.py`
14. `eval/bench_runner.py`
15. `tests/test_header_footer.py`

Expected effect:

- `headers_footers.jsonl` should improve because body OCR no longer sees most repeated margins.
- `Absent` should improve because intentional omissions become a first-class successful output.

### P1: Repair and smoke tooling

Implement:

1. `prompts/repair_header_footer.txt`
2. `repair/repair_runner.py`
3. `scripts/smoke_openai_compatible.py`
4. more tests around ambiguous margin content

Expected effect:

- Better handling of first-page author/title lines that fall into the top band.
- Safer debugging before long benchmark runs.

### P2: Multi-page recurrence cleanup

Implement:

1. `assemble/document_reconciler.py`
2. `eval/ablation_runner.py`
3. recurrence metrics in benchmark summaries if candidate provenance is available

Expected effect:

- Better production document behavior.
- Better explanation in the paper.
- Limited impact on `olmOCR-Bench` if pages are processed independently.

## 8. Evaluation Plan

Run these conditions:

| Candidate | Purpose |
|---|---|
| `svr_ocr_full_legacy_seed` | current behavior |
| `svr_ocr_full_margin_body_only` | isolates body crop benefit |
| `svr_ocr_full_margin_hf_verifier` | tests dedicated drop semantics |
| `svr_ocr_full_margin_hf_recurrence` | tests multi-page cleanup where applicable |

Primary metrics:

- `headers_footers.jsonl`
- type-level `Absent`
- type-level `Present`
- overall score

Regression guard metrics:

- `arxiv_math.jsonl`
- `old_scans_math.jsonl`
- `table_tests.jsonl`
- `multi_column.jsonl`
- `long_tiny_text.jsonl`
- `baseline`

Success criteria:

- `headers_footers.jsonl` improves materially over `38.8%`.
- `Absent` improves materially over `42.3%`.
- Overall score does not drop by more than 1 point.
- `math`, `table`, `multi_column`, and `long_tiny_text` do not regress by more than 2 points.

Strong target:

- `headers_footers.jsonl` reaches at least the `StructuredPrompt+Post` level first, then moves toward the specialized OCR range.
- A realistic near-term target is `70%+`.
- A strong target is `85%+`.

## 9. Key Risks

Risk: Top-band first-page titles get dropped.  
Mitigation: header/footer verifier should not drop long title-like text unless it matches boilerplate patterns; include first-page title test cases.

Risk: Body crop removes real content near page edges.  
Mitigation: use `body_overlap_px` and conservative margin ratios; evaluate on `baseline`, `long_tiny_text`, and `multi_column`.

Risk: VLM ignores the drop marker instruction.  
Mitigation: verifier also drops obvious boilerplate patterns and empty margin output.

Risk: Header/footer blocks add cost.  
Mitigation: margin crops are small; use 1-2 candidates and no repair in P0.

Risk: Regex rules over-delete.  
Mitigation: regex-only deletion should apply only to `HEADER_FOOTER` blocks, not body blocks.

## 10. Paper Interpretation

If the fix works, describe it as a method improvement:

> The initial SVR-OCR run showed strong gains on math, multi-column, tiny-text, and table-heavy regimes, but underperformed specialized OCR systems on header/footer omission. We addressed this by adding margin-aware seeding, dedicated header/footer classification, and verifier-level drop semantics, turning boilerplate suppression from an implicit prompting behavior into an explicit inference step.

Do not claim the model learned header/footer behavior. The system made omission explicit through routing, cropping, verification, and assembly.
