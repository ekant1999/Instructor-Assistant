#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_ROOT = WORKSPACE_ROOT.parent


@dataclass
class WorkspaceConfig:
    repo_root: Path
    bench_data_dir: Path
    bench_pdf_dir: Path
    results_dir: Path
    qwen_structured_candidate: str
    qwen_structured_post_candidate: str
    svr_ocr_candidate: str
    olmocr2_candidate: str
    qwen_model: str
    olmocr_model: str
    env: dict[str, str]


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]
        values[key] = value
    return values


def resolve_config() -> WorkspaceConfig:
    file_env = load_env_file(WORKSPACE_ROOT / ".env")
    merged_env = dict(file_env)
    merged_env.update(os.environ)

    repo_root = Path(merged_env.get("REPO_ROOT") or DEFAULT_REPO_ROOT).expanduser().resolve()
    bench_data_dir = Path(
        merged_env.get("BENCH_DATA_DIR")
        or (WORKSPACE_ROOT / "data" / "olmOCR-bench" / "bench_data")
    ).expanduser()
    bench_pdf_dir = Path(
        merged_env.get("BENCH_PDF_DIR")
        or (bench_data_dir / "pdfs")
    ).expanduser()
    results_dir = Path(
        merged_env.get("RESULTS_DIR")
        or (WORKSPACE_ROOT / "results")
    ).expanduser()

    return WorkspaceConfig(
        repo_root=repo_root,
        bench_data_dir=bench_data_dir,
        bench_pdf_dir=bench_pdf_dir,
        results_dir=results_dir,
        qwen_structured_candidate=merged_env.get("QWEN_STRUCTURED_CANDIDATE", "qwen_structured"),
        qwen_structured_post_candidate=merged_env.get("QWEN_STRUCTURED_POST_CANDIDATE", "qwen_structured_post"),
        svr_ocr_candidate=merged_env.get("SVR_OCR_CANDIDATE", "svr_ocr_full"),
        olmocr2_candidate=merged_env.get("OLMOCR2_CANDIDATE", "olmocr2"),
        qwen_model=merged_env.get("QWEN_MODEL", "qwen3-vl-plus"),
        olmocr_model=merged_env.get("OLMOCR_MODEL", "allenai/olmOCR-2-7B-1025-FP8"),
        env=merged_env,
    )


def command_env(config: WorkspaceConfig) -> dict[str, str]:
    env = os.environ.copy()
    env.update(config.env)
    return env


def ensure_results_dir(config: WorkspaceConfig) -> None:
    config.results_dir.mkdir(parents=True, exist_ok=True)


def bench_candidate_dir(config: WorkspaceConfig, candidate: str) -> Path:
    return config.bench_data_dir / candidate


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    tee_path: Path | None = None,
) -> None:
    tee_file = None
    if tee_path is not None:
        tee_path.parent.mkdir(parents=True, exist_ok=True)
        tee_file = tee_path.open("w", encoding="utf-8")
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            if tee_file is not None:
                tee_file.write(line)
        return_code = process.wait()
        if return_code != 0:
            raise SystemExit(return_code)
    finally:
        if tee_file is not None:
            tee_file.close()


def count_empty_markdown_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for file in path.rglob("*.md") if file.is_file() and file.stat().st_size == 0)


def delete_empty_markdown_files(path: Path) -> int:
    deleted = 0
    for file in path.rglob("*.md"):
        if file.is_file() and file.stat().st_size == 0:
            file.unlink()
            deleted += 1
    return deleted


def check_binary(name: str) -> bool:
    return shutil.which(name) is not None


def validate_workspace(config: WorkspaceConfig) -> int:
    problems: list[str] = []

    if not (config.repo_root / "SVR-OCR" / "src").exists():
        problems.append(f"Missing SVR-OCR source tree under {config.repo_root / 'SVR-OCR' / 'src'}")
    if not check_binary("pdfinfo"):
        problems.append("Missing `pdfinfo` (install Poppler)")
    if not check_binary("pdftoppm"):
        problems.append("Missing `pdftoppm` (install Poppler)")
    if not config.bench_data_dir.exists():
        problems.append(f"Benchmark data directory not found: {config.bench_data_dir}")
    if not config.bench_pdf_dir.exists():
        problems.append(f"Benchmark PDF directory not found: {config.bench_pdf_dir}")

    try:
        subprocess.run(
            [sys.executable, "-c", "import olmocr"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        problems.append("`olmocr` is not importable in this Python environment. Run scripts/setup_workspace.sh.")

    print("Workspace configuration")
    print(f"  repo_root      : {config.repo_root}")
    print(f"  bench_data_dir : {config.bench_data_dir}")
    print(f"  bench_pdf_dir  : {config.bench_pdf_dir}")
    print(f"  results_dir    : {config.results_dir}")
    print(f"  python         : {sys.executable}")
    print(f"  qwen_model     : {config.qwen_model}")
    print(f"  olmocr_model   : {config.olmocr_model}")

    if problems:
        print("\nValidation failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nValidation passed.")
    return 0


def download_bench_data(args: argparse.Namespace, config: WorkspaceConfig) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("huggingface_hub is not installed. Run scripts/setup_workspace.sh first.") from exc

    target_root = WORKSPACE_ROOT / "data" / "olmOCR-bench"
    target_root.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        local_dir=str(target_root),
    )

    detected = None
    if (target_root / "bench_data" / "pdfs").exists():
        detected = target_root / "bench_data"
    elif (target_root / "pdfs").exists():
        detected = target_root

    print(f"Downloaded dataset snapshot to {target_root}")
    if detected is not None:
        print(f"Detected benchmark root: {detected}")
        print("If your .env uses default paths, no further change is needed.")
    else:
        print("Could not auto-detect bench_data root. Inspect the downloaded directory and set BENCH_DATA_DIR in .env.")


def run_olmocr_convert(
    config: WorkspaceConfig,
    *,
    candidate: str,
    model: str,
    endpoint_env: str,
    api_key_env: str,
    prompt_template: str,
    response_template: str,
    repeats: int,
    parallel: int,
    force: bool,
) -> None:
    env = command_env(config)
    server_spec = (
        f"server:name={candidate}:model={model}:endpoint_env={endpoint_env}:"
        f"api_key_env={api_key_env}:prompt_template={prompt_template}:response_template={response_template}"
    )
    command = [
        sys.executable,
        "-m",
        "olmocr.bench.convert",
        "--dir",
        str(config.bench_data_dir),
        "--repeats",
        str(repeats),
        "--parallel",
        str(parallel),
    ]
    if force:
        command.append("--force")
    command.append(server_spec)
    run_command(command, cwd=config.repo_root, env=env)


def run_svr_convert(
    config: WorkspaceConfig,
    *,
    candidate: str,
    repeats: int,
    parallel: int,
    force: bool,
    target_longest_image_dim: int,
    max_tokens: int,
    temperature: float,
    write_provenance: bool,
) -> None:
    env = command_env(config)
    existing_pythonpath = env.get("PYTHONPATH", "")
    svr_path = str(config.repo_root / "SVR-OCR" / "src")
    env["PYTHONPATH"] = f"{svr_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else svr_path
    output_dir = bench_candidate_dir(config, candidate)
    command = [
        sys.executable,
        "-m",
        "svr_ocr.eval.bench_runner",
        "--pdf-dir",
        str(config.bench_pdf_dir),
        "--output-dir",
        str(output_dir),
        "--repeats",
        str(repeats),
        "--parallel",
        str(parallel),
        "--max-tokens",
        str(max_tokens),
        "--temperature",
        str(temperature),
        "--target-longest-image-dim",
        str(target_longest_image_dim),
        "--base-url-env",
        "QWEN_SERVER",
        "--model-env",
        "QWEN_MODEL",
        "--api-key-env",
        "QWEN_API_KEY",
    ]
    if force:
        command.append("--force")
    if write_provenance:
        command.append("--write-provenance")
    run_command(command, cwd=config.repo_root, env=env)


def split_front_matter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    marker = "\n---\n"
    end = text.find(marker, 4)
    if end == -1:
        return "", text
    front = text[: end + len(marker)]
    body = text[end + len(marker) :]
    return front, body


HEADER_FOOTER_PATTERNS = [
    re.compile(r"^\s*Page\s+\d+(\s+of\s+\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*arXiv:\d{4}\.\d{4,5}(v\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*https?://\S+\s*$", re.IGNORECASE),
    re.compile(r"^\s*doi:\s*\S+\s*$", re.IGNORECASE),
]


def normalize_placeholder_syntax(text: str) -> str:
    text = re.sub(r"!\s*\[\s*(.*?)\s*\]\s*\(\s*(.*?)\s*\)", r"![\1](\2)", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def normalize_lines(lines: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    previous_non_empty: str | None = None
    for raw_line in lines:
        line = raw_line.rstrip()
        if any(pattern.match(line) for pattern in HEADER_FOOTER_PATTERNS):
            continue
        heading_match = re.match(r"^(#{1,6})\s*(.*?)\s*$", line)
        if heading_match:
            title = re.sub(r"\s+", " ", heading_match.group(2)).strip(" -:")
            if not title:
                continue
            line = f"{heading_match.group(1)} {title}"
        if line and previous_non_empty == line:
            continue
        normalized.append(line)
        if line:
            previous_non_empty = line
    return normalized


def remove_empty_headings(lines: list[str]) -> list[str]:
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^#{1,6}\s+\S", line):
            j = i + 1
            body_has_content = False
            while j < len(lines) and not re.match(r"^#{1,6}\s+\S", lines[j]):
                if lines[j].strip():
                    body_has_content = True
                    break
                j += 1
            if not body_has_content:
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                continue
        result.append(line)
        i += 1
    return result


def postprocess_markdown(text: str) -> str:
    front_matter, body = split_front_matter(text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff"))
    body = normalize_placeholder_syntax(body)
    lines = normalize_lines(body.splitlines())
    lines = remove_empty_headings(lines)
    cleaned = "\n".join(lines).strip() + "\n"
    if front_matter:
        return front_matter + cleaned
    return cleaned


def copy_and_postprocess_candidate(input_dir: Path, output_dir: Path, *, force: bool) -> None:
    if not input_dir.exists():
        raise SystemExit(f"Input candidate directory does not exist: {input_dir}")
    if output_dir.exists():
        if force:
            shutil.rmtree(output_dir)
        else:
            raise SystemExit(f"Output candidate directory already exists: {output_dir} (use --force)")
    shutil.copytree(input_dir, output_dir)
    for file in output_dir.rglob("*.md"):
        if file.is_file():
            file.write_text(postprocess_markdown(file.read_text()))


def benchmark_candidate(
    config: WorkspaceConfig,
    *,
    candidate: str,
    bootstrap_samples: int,
    max_reports: int,
) -> None:
    ensure_results_dir(config)
    report_path = config.results_dir / f"{candidate}_report.html"
    failed_path = config.results_dir / f"{candidate}_failed.jsonl"
    stdout_path = config.results_dir / f"{candidate}_stdout.txt"
    env = command_env(config)
    command = [
        sys.executable,
        "-m",
        "olmocr.bench.benchmark",
        "--dir",
        str(config.bench_data_dir),
        "--candidate",
        candidate,
        "--bootstrap_samples",
        str(bootstrap_samples),
        "--test_report",
        str(report_path),
        "--output_failed",
        str(failed_path),
        "--max_reports",
        str(max_reports),
    ]
    run_command(command, cwd=config.repo_root, env=env, tee_path=stdout_path)


SUMMARY_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9_\-]+)\s*:\s*Average Score:\s*(?P<score>[0-9.]+)% ± (?P<ci>[0-9.]+)%",
    re.MULTILINE,
)
CATEGORY_RE = re.compile(
    r"^\s+(?P<name>[a-z_]+)\s*:\s*(?P<score>[0-9.]+)% average pass rate over (?P<count>\d+) tests",
    re.MULTILINE,
)


def parse_benchmark_stdout(stdout_path: Path) -> dict[str, object]:
    text = stdout_path.read_text()
    summary_match = SUMMARY_RE.search(text)
    if not summary_match:
        raise SystemExit(f"Could not parse benchmark summary from {stdout_path}")
    categories = {
        match.group("name"): {
            "score_percent": float(match.group("score")),
            "tests": int(match.group("count")),
        }
        for match in CATEGORY_RE.finditer(text)
    }
    return {
        "candidate": summary_match.group("name"),
        "average_score_percent": float(summary_match.group("score")),
        "ci_half_width_percent": float(summary_match.group("ci")),
        "categories": categories,
    }


def summarize_candidate(config: WorkspaceConfig, candidate: str) -> dict[str, object]:
    stdout_path = config.results_dir / f"{candidate}_stdout.txt"
    failed_path = config.results_dir / f"{candidate}_failed.jsonl"
    candidate_dir = bench_candidate_dir(config, candidate)
    summary = parse_benchmark_stdout(stdout_path)
    summary["empty_markdown_files"] = count_empty_markdown_files(candidate_dir)
    summary["candidate_dir"] = str(candidate_dir)
    summary["stdout_path"] = str(stdout_path)
    summary["failed_test_count"] = 0
    if failed_path.exists():
        with failed_path.open() as fh:
            summary["failed_test_count"] = sum(1 for _ in fh)
    return summary


def print_summary(summary: dict[str, object]) -> None:
    print(
        f"{summary['candidate']}: {summary['average_score_percent']:.1f}% ± "
        f"{summary['ci_half_width_percent']:.1f}% | "
        f"failed tests={summary['failed_test_count']} | "
        f"empty markdown files={summary['empty_markdown_files']}"
    )
    categories = summary.get("categories", {})
    if categories:
        ordered = ", ".join(
            f"{name}={values['score_percent']:.1f}%"
            for name, values in sorted(categories.items())
            if name != "baseline"
        )
        print(f"  categories: {ordered}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Repro workspace for olmOCR-Bench experiments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate")
    subparsers.add_parser("show-config")

    download_parser = subparsers.add_parser("download-bench-data")
    download_parser.add_argument("--repo-id", default="allenai/olmOCR-bench")

    qwen_parser = subparsers.add_parser("convert-qwen-structured")
    qwen_parser.add_argument("--repeats", type=int, default=1)
    qwen_parser.add_argument("--parallel", type=int, default=1)
    qwen_parser.add_argument("--force", action="store_true")

    post_parser = subparsers.add_parser("postprocess-qwen")
    post_parser.add_argument("--input-candidate")
    post_parser.add_argument("--output-candidate")
    post_parser.add_argument("--force", action="store_true")

    olmocr_parser = subparsers.add_parser("convert-olmocr2")
    olmocr_parser.add_argument("--repeats", type=int, default=1)
    olmocr_parser.add_argument("--parallel", type=int, default=1)
    olmocr_parser.add_argument("--force", action="store_true")

    svr_parser = subparsers.add_parser("convert-svr")
    svr_parser.add_argument("--repeats", type=int, default=1)
    svr_parser.add_argument("--parallel", type=int, default=4)
    svr_parser.add_argument("--target-longest-image-dim", type=int, default=1024)
    svr_parser.add_argument("--max-tokens", type=int, default=2000)
    svr_parser.add_argument("--temperature", type=float, default=0.0)
    svr_parser.add_argument("--write-provenance", action="store_true")
    svr_parser.add_argument("--force", action="store_true")

    clean_parser = subparsers.add_parser("clean-empty")
    clean_parser.add_argument("--candidate", required=True)
    clean_parser.add_argument("--delete", action="store_true")

    benchmark_parser = subparsers.add_parser("benchmark")
    benchmark_parser.add_argument("--candidate", required=True)
    benchmark_parser.add_argument("--bootstrap-samples", type=int, default=200)
    benchmark_parser.add_argument("--max-reports", type=int, default=20)

    summarize_parser = subparsers.add_parser("summarize")
    summarize_parser.add_argument("--candidate", required=True)
    summarize_parser.add_argument("--json", action="store_true")

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    config = resolve_config()

    if args.command == "validate":
        raise SystemExit(validate_workspace(config))
    if args.command == "show-config":
        print(json.dumps(
            {
                "repo_root": str(config.repo_root),
                "bench_data_dir": str(config.bench_data_dir),
                "bench_pdf_dir": str(config.bench_pdf_dir),
                "results_dir": str(config.results_dir),
                "qwen_structured_candidate": config.qwen_structured_candidate,
                "qwen_structured_post_candidate": config.qwen_structured_post_candidate,
                "svr_ocr_candidate": config.svr_ocr_candidate,
                "olmocr2_candidate": config.olmocr2_candidate,
                "qwen_model": config.qwen_model,
                "olmocr_model": config.olmocr_model,
            },
            indent=2,
        ))
        return
    if args.command == "download-bench-data":
        download_bench_data(args, config)
        return
    if args.command == "convert-qwen-structured":
        run_olmocr_convert(
            config,
            candidate=config.qwen_structured_candidate,
            model=config.qwen_model,
            endpoint_env="QWEN_SERVER",
            api_key_env="QWEN_API_KEY",
            prompt_template="fullv3simple",
            response_template="plain",
            repeats=args.repeats,
            parallel=args.parallel,
            force=args.force,
        )
        return
    if args.command == "postprocess-qwen":
        input_candidate = args.input_candidate or config.qwen_structured_candidate
        output_candidate = args.output_candidate or config.qwen_structured_post_candidate
        copy_and_postprocess_candidate(
            bench_candidate_dir(config, input_candidate),
            bench_candidate_dir(config, output_candidate),
            force=args.force,
        )
        print(f"Wrote post-processed candidate: {bench_candidate_dir(config, output_candidate)}")
        return
    if args.command == "convert-olmocr2":
        run_olmocr_convert(
            config,
            candidate=config.olmocr2_candidate,
            model=config.olmocr_model,
            endpoint_env="OLMOCR_SERVER",
            api_key_env="OLMOCR_API_KEY",
            prompt_template="fullv3simple",
            response_template="plain",
            repeats=args.repeats,
            parallel=args.parallel,
            force=args.force,
        )
        return
    if args.command == "convert-svr":
        run_svr_convert(
            config,
            candidate=config.svr_ocr_candidate,
            repeats=args.repeats,
            parallel=args.parallel,
            force=args.force,
            target_longest_image_dim=args.target_longest_image_dim,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            write_provenance=args.write_provenance,
        )
        return
    if args.command == "clean-empty":
        candidate_dir = bench_candidate_dir(config, args.candidate)
        if args.delete:
            deleted = delete_empty_markdown_files(candidate_dir)
            print(f"Deleted {deleted} empty markdown files from {candidate_dir}")
        else:
            print(count_empty_markdown_files(candidate_dir))
        return
    if args.command == "benchmark":
        benchmark_candidate(
            config,
            candidate=args.candidate,
            bootstrap_samples=args.bootstrap_samples,
            max_reports=args.max_reports,
        )
        return
    if args.command == "summarize":
        summary = summarize_candidate(config, args.candidate)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print_summary(summary)
        return
    if args.command == "compare":
        candidates = [
            config.qwen_structured_candidate,
            config.qwen_structured_post_candidate,
            config.svr_ocr_candidate,
            config.olmocr2_candidate,
        ]
        summaries: list[dict[str, object]] = []
        for candidate in candidates:
            stdout_path = config.results_dir / f"{candidate}_stdout.txt"
            if stdout_path.exists():
                summaries.append(summarize_candidate(config, candidate))
        if args.json:
            print(json.dumps(summaries, indent=2))
        else:
            for summary in summaries:
                print_summary(summary)
        return


if __name__ == "__main__":
    main()
