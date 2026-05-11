# NVIDIA Nemotron Omni OCR Benchmark Report

## Run Summary

- Candidate: `nemotron_omni_nvidia_ocr`
- Model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Benchmark: `olmOCR-Bench`
- PDF pages evaluated: 1,403
- Candidate markdown files generated: 1,403
- Empty markdown files: 10
- Failed benchmark checks: 5,052
- HTML report: `results/nemotron_omni_nvidia_ocr_report.html`
- Failed checks: `results/nemotron_omni_nvidia_ocr_failed.jsonl`

## Overall Result

`nemotron_omni_nvidia_ocr` scored:

```text
Average Score: 37.1% ± 1.0%
95% CI: [36.2%, 38.3%]
Tests: 8,413
```

This is substantially below the workspace baselines:

```text
qwen_structured      50.0% ± 1.2%
qwen_structured_post 52.3% ± 1.2%
svr_ocr_full         72.8% ± 1.1%
olmocr2              74.7% ± 1.0%
```

## Score Breakdown

By test type:

```text
baseline: 91.6% over 1,403 tests
absent  : 54.4% over   823 tests
table   : 43.1% over 1,020 tests
order   : 32.1% over 1,061 tests
present : 23.0% over   721 tests
math    : 20.1% over 3,385 tests
```

By benchmark JSONL:

```text
baseline              91.6% (1277/1394)
headers_footers.jsonl 52.5% (399/760)
table_tests.jsonl     43.2% (441/1022)
multi_column.jsonl    35.7% (316/884)
old_scans.jsonl       29.7% (156/526)
arxiv_math.jsonl      23.2% (678/2927)
long_tiny_text.jsonl  20.6% (91/442)
old_scans_math.jsonl   0.7% (3/458)
```

## Failure Distribution

Failed checks by category:

```text
arxiv_math      2294
tables           592
multi_column     582
old_scans_math   463
old_scans        383
headers_footers  382
long_tiny_text   356
```

Failed checks by type:

```text
math     2704
order     720
table     580
present   555
absent    375
baseline  118
```

## Output Pathologies

The model produced all expected output files, but several outputs were invalid or clearly degraded:

```text
empty files:             10
non-empty files <50 chr: 138
files with no alnum:     57
files with repeat loops: 200
files with \\unknown:     14
```

Empty outputs occurred in these groups:

```text
arxiv_math       4
tables           2
multi_column     2
headers_footers  1
old_scans        1
```

The largest outputs were unusually long, up to 29,583 characters. Many of these were likely looped or repeated completions rather than faithful OCR.

## Qualitative Findings

The model can perform basic visual OCR on some clean text pages. Its `baseline` pass rate of 91.6% shows that many pages produced non-empty text with at least basic validity.

However, it performs poorly on the actual benchmark tasks:

- Math OCR is weak. The model often emits invalid LaTeX such as `\unknown`, malformed subscripts like `U_\tilde{q}`, or corrupted mathematical structure. This caused many KaTeX rendering errors and a low `math` pass rate of 20.1%.
- Old scanned math essentially fails. `old_scans_math.jsonl` scored only 0.7%.
- Long tiny text is weak. The `long_tiny_text` score was 20.6%, with many missed exact text snippets.
- Reading order is unreliable. `order` tests passed only 32.1%, especially on multi-column pages.
- Tables remain unstable. The table score was 43.1%; outputs sometimes malformed table structure, merged cells incorrectly, or repeated tokens.
- The model sometimes loops or emits near-empty outputs. The benchmark flagged many pages with repeating n-grams or no alphanumeric characters.
- Header/footer removal is inconsistent. `absent` tests passed only 54.4%, meaning the model often preserved text it was supposed to remove.

## Conclusion

The NVIDIA Nemotron Omni API is callable and can process document images, but this model is not competitive on `olmOCR-Bench` with the current OCR prompt and page rendering setup.

For OCR benchmark use, the result is below even the direct Qwen structured baseline:

```text
Nemotron Omni OCR: 37.1%
Qwen structured:   50.0%
SVR-OCR-Full:      72.8%
olmOCR-2:          74.7%
```

The main limitation is not API access; it is OCR reliability. The model struggles with exact transcription, math, tables, dense scans, and reading order. It also shows output-control problems such as looping and invalid math markup.

## Recommended Next Steps

1. Do not use this run as a strong OCR baseline in the paper except as a negative result.
2. If continuing with NVIDIA, test a table-specific/plain-text prompt that avoids HTML tables and asks for row-by-row transcription.
3. Test cropped page regions for multi-column and table pages.
4. Add post-processing to remove repeated n-grams, invalid `\unknown` LaTeX, and empty outputs before benchmarking a second run.
5. Consider lowering `max_tokens` or adding stricter stop controls to reduce looping, though this may also truncate valid pages.
