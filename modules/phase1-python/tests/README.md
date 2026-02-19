# Phase 1 Tests

This directory contains tests for reusable `ia_phase1` modules.

## Test groups

- Unit tests:
  - `test_parser.py`
  - `test_sectioning.py`
  - `test_chunking.py`
  - `test_tables.py`
  - `test_figures.py`
- Integration contract:
  - `test_contract_integration.py` (marked `integration`)

## Install test dependencies

```bash
cd modules/phase1-python
pip install -r requirements-test.txt
```

## Run tests

```bash
# Fast suite
pytest -m "not integration"

# Integration only
pytest -m integration
```
