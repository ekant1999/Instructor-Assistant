# Gold Annotations

Store one JSON file per benchmark document under `gold/docs/`.

Recommended workflow:

1. run the benchmark systems you want to compare
2. normalize outputs
3. generate gold templates with `bootstrap_gold_templates.py`
4. manually curate headings, section anchors, and asset expectations
5. set `"validated": true` only after manual review
6. rerun scoring

The benchmark can run without gold files, but gold is required for real fidelity metrics.

Draft templates created by the bootstrap script are not scored as gold until they
are explicitly marked with `"validated": true`.

Notes:

- gold must be curated from the source PDF, not from any generated markdown
- bootstrapped templates are only a starting skeleton
- the current benchmark supports:
  - `ia_phase1`
  - `ocr_agent`
  - `improved_ocr_agent`
