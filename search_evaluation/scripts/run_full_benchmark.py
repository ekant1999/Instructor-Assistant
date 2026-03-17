from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent


def _run_step(label: str, script_name: str, *args: str) -> None:
    cmd = [sys.executable, str(SCRIPT_DIR / script_name), *args]
    print(f"\n==> {label}")
    print(" ".join(shlex.quote(part) for part in cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full search-evaluation pipeline: build, benchmark, cleanup, and optional fetch."
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Refresh metadata/PDF selection before building the eval corpus. This changes the benchmark corpus.",
    )
    parser.add_argument(
        "--refresh-fetch",
        action="store_true",
        help="Force PDF re-download during the fetch step. Implies --fetch.",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Leave eval papers in pgvector after the run.",
    )
    args = parser.parse_args()

    failure: subprocess.CalledProcessError | None = None

    try:
        if args.fetch or args.refresh_fetch:
            fetch_args = ["--refresh"] if args.refresh_fetch else []
            _run_step("Fetch arXiv papers", "fetch_arxiv_papers.py", *fetch_args)
        _run_step("Build eval corpus", "build_eval_corpus.py")
        _run_step("Run benchmark", "run_benchmark.py")
    except subprocess.CalledProcessError as exc:
        failure = exc
    finally:
        if not args.skip_cleanup:
            try:
                _run_step("Cleanup eval pgvector rows", "cleanup_eval_pg.py")
            except subprocess.CalledProcessError as exc:
                if failure is None:
                    failure = exc
                else:
                    print(
                        f"cleanup also failed with exit code {exc.returncode}",
                        file=sys.stderr,
                    )

    if failure is not None:
        raise SystemExit(failure.returncode)

    print("\nDone.")
    print("Results:")
    print("- search_evaluation/reports/summary.json")
    print("- search_evaluation/reports/SEARCH_BASELINE_REPORT.md")
    print("- search_evaluation/runs/benchmark_results.jsonl")


if __name__ == "__main__":
    main()
