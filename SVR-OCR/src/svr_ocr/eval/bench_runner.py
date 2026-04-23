from __future__ import annotations

import argparse
import json
import threading
import traceback
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Literal

from ..config import EndpointConfig, SVROCRConfig
from ..io import (
    MarginAwareSeedOptions,
    PageSeedOptions,
    get_pdf_page_count,
    make_margin_aware_page_bundle,
    make_whole_page_bundle,
    render_pdf_page_to_png,
)
from ..pipeline import SVROCRPipeline, build_openai_compatible_pipeline

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - fallback for minimal environments
    tqdm = None


@dataclass
class BenchTaskResult:
    pdf_path: str
    page_num: int
    output_path: str
    ok: bool
    error: str | None = None


@dataclass
class BenchRunSummary:
    attempted: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list[BenchTaskResult] = field(default_factory=list)


@dataclass(frozen=True)
class BenchTask:
    pdf_path: Path
    page_num: int
    output_path: Path


class BenchRunner:
    def __init__(
        self,
        pipeline: SVROCRPipeline | None = None,
        *,
        pipeline_factory: Callable[[], SVROCRPipeline] | None = None,
        target_longest_image_dim: int = 2048,
        max_parallel: int = 1,
        page_seed_mode: Literal["whole_page", "margin_aware"] = "whole_page",
        margin_seed: MarginAwareSeedOptions | None = None,
    ):
        self.pipeline = pipeline
        self.pipeline_factory = pipeline_factory
        self.target_longest_image_dim = target_longest_image_dim
        self.max_parallel = max(1, int(max_parallel))
        self.page_seed_mode = page_seed_mode
        self.margin_seed = margin_seed
        self._thread_local = threading.local()

        if self.max_parallel > 1 and self.pipeline_factory is None:
            raise ValueError("BenchRunner with max_parallel > 1 requires pipeline_factory for thread-safe worker pipelines.")

    def run(
        self,
        *,
        pdf_directory: str | Path,
        output_directory: str | Path,
        repeats: int = 1,
        force: bool = False,
        limit: int | None = None,
        failfast: bool = False,
        write_provenance: bool = False,
        seed: PageSeedOptions | None = None,
    ) -> BenchRunSummary:
        pdf_directory = Path(pdf_directory)
        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        summary = BenchRunSummary()

        pdfs = sorted(pdf_directory.rglob('*.pdf'))
        if limit is not None:
            pdfs = pdfs[:limit]

        task_specs, skipped = self._build_tasks(
            pdf_directory=pdf_directory,
            output_directory=output_directory,
            pdfs=pdfs,
            repeats=repeats,
            force=force,
        )
        summary.skipped = skipped
        summary.attempted = len(task_specs)

        print(f"Discovered {len(pdfs)} PDFs under {pdf_directory}")
        print(f"Planned {summary.attempted} page tasks")
        if skipped:
            print(f"Skipping {skipped} existing outputs (rerun with --force to overwrite)")
        if not task_specs:
            print("No work to do.")
            return summary

        if self.max_parallel == 1:
            self._run_sequential(
                task_specs=task_specs,
                summary=summary,
                seed=seed,
                write_provenance=write_provenance,
                failfast=failfast,
            )
        else:
            self._run_parallel(
                task_specs=task_specs,
                summary=summary,
                seed=seed,
                write_provenance=write_provenance,
                failfast=failfast,
            )
        return summary

    def _run_sequential(
        self,
        *,
        task_specs: list[BenchTask],
        summary: BenchRunSummary,
        seed: PageSeedOptions | None,
        write_provenance: bool,
        failfast: bool,
    ) -> None:
        iterator = self._progress_iterator(task_specs)
        for task in iterator:
            task.output_path.parent.mkdir(parents=True, exist_ok=True)
            result = self._process_single_page_task(
                task=task,
                seed=seed,
                write_provenance=write_provenance,
            )
            self._record_result(summary, result)
            if not result.ok:
                self._progress_write(
                    f"FAIL {task.output_path.name}: "
                    f"{result.error.splitlines()[0] if result.error else 'unknown error'}"
                )
                if failfast:
                    raise RuntimeError(result.error or f"Failed task: {task.output_path}")

    def _run_parallel(
        self,
        *,
        task_specs: list[BenchTask],
        summary: BenchRunSummary,
        seed: PageSeedOptions | None,
        write_provenance: bool,
        failfast: bool,
    ) -> None:
        progress = self._make_progress(total=len(task_specs))
        try:
            with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
                task_iter = iter(task_specs)
                pending = {
                    executor.submit(
                        self._process_single_page_task,
                        task=task,
                        seed=seed,
                        write_provenance=write_provenance,
                    ): task
                    for task in list(task_specs[: self.max_parallel])
                }
                for _ in range(min(self.max_parallel, len(task_specs))):
                    next(task_iter, None)

                while pending:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        task = pending.pop(future)
                        result = future.result()
                        self._record_result(summary, result)
                        self._progress_advance(progress, 1)
                        if not result.ok:
                            self._progress_write(
                                f"FAIL {task.output_path.name}: "
                                f"{result.error.splitlines()[0] if result.error else 'unknown error'}"
                            )
                            if failfast:
                                for remaining in pending:
                                    remaining.cancel()
                                raise RuntimeError(result.error or f"Failed task: {task.output_path}")

                        next_task = next(task_iter, None)
                        if next_task is not None:
                            next_task.output_path.parent.mkdir(parents=True, exist_ok=True)
                            pending[
                                executor.submit(
                                    self._process_single_page_task,
                                    task=next_task,
                                    seed=seed,
                                    write_provenance=write_provenance,
                                )
                            ] = next_task
        finally:
            self._close_progress(progress)

    def _build_tasks(
        self,
        *,
        pdf_directory: Path,
        output_directory: Path,
        pdfs: list[Path],
        repeats: int,
        force: bool,
    ) -> tuple[list[BenchTask], int]:
        tasks: list[BenchTask] = []
        skipped = 0
        for pdf_path in pdfs:
            relative_dir = pdf_path.relative_to(pdf_directory).parent
            page_count = get_pdf_page_count(pdf_path)
            base_name = pdf_path.stem
            for repeat in range(1, repeats + 1):
                for page_num in range(1, page_count + 1):
                    output_path = output_directory / relative_dir / f'{base_name}_pg{page_num}_repeat{repeat}.md'
                    if output_path.exists() and not force:
                        skipped += 1
                        continue
                    tasks.append(
                        BenchTask(
                            pdf_path=pdf_path,
                            page_num=page_num,
                            output_path=output_path,
                        )
                    )
        return tasks, skipped

    def _progress_iterator(self, task_specs: list[BenchTask]):
        if tqdm is None:
            return task_specs
        return tqdm(task_specs, total=len(task_specs), desc="SVR-OCR convert")

    def _make_progress(self, total: int):
        if tqdm is None:
            return None
        return tqdm(total=total, desc=f"SVR-OCR convert x{self.max_parallel}")

    def _progress_advance(self, progress, amount: int) -> None:
        if progress is not None:
            progress.update(amount)

    def _close_progress(self, progress) -> None:
        if progress is not None:
            progress.close()

    def _progress_write(self, message: str) -> None:
        if tqdm is not None:
            tqdm.write(message)
        else:
            print(message)

    def _record_result(self, summary: BenchRunSummary, result: BenchTaskResult) -> None:
        if result.ok:
            summary.completed += 1
        else:
            summary.failed += 1
            summary.failures.append(result)

    def _process_single_page_task(
        self,
        *,
        task: BenchTask,
        seed: PageSeedOptions | None,
        write_provenance: bool,
    ) -> BenchTaskResult:
        task.output_path.parent.mkdir(parents=True, exist_ok=True)
        return self._process_single_page(
            pdf_path=task.pdf_path,
            page_num=task.page_num,
            output_path=task.output_path,
            seed=seed,
            write_provenance=write_provenance,
        )

    def _get_pipeline(self) -> SVROCRPipeline:
        if self.max_parallel == 1:
            assert self.pipeline is not None
            return self.pipeline
        pipeline = getattr(self._thread_local, "pipeline", None)
        if pipeline is None:
            assert self.pipeline_factory is not None
            pipeline = self.pipeline_factory()
            self._thread_local.pipeline = pipeline
        return pipeline

    def _process_single_page(
        self,
        *,
        pdf_path: Path,
        page_num: int,
        output_path: Path,
        seed: PageSeedOptions | None,
        write_provenance: bool,
    ) -> BenchTaskResult:
        try:
            with TemporaryDirectory(prefix='svr_ocr_bench_') as tmpdir:
                png_path = Path(tmpdir) / f'{pdf_path.stem}_pg{page_num}.png'
                render_pdf_page_to_png(
                    pdf_path,
                    page_num,
                    png_path,
                    target_longest_image_dim=self.target_longest_image_dim,
                )
                extra_metadata = {
                    'pdf_path': str(pdf_path),
                    'category': pdf_path.parent.name,
                    'page_num': page_num,
                }
                if self.page_seed_mode == "margin_aware":
                    page = make_margin_aware_page_bundle(
                        png_path,
                        page_id=f'{pdf_path.stem}_pg{page_num}',
                        seed=self.margin_seed,
                        extra_metadata=extra_metadata,
                    )
                else:
                    page = make_whole_page_bundle(
                        png_path,
                        page_id=f'{pdf_path.stem}_pg{page_num}',
                        seed=seed,
                        extra_metadata=extra_metadata,
                    )
                result = self._get_pipeline().process_page(page)
                output_path.write_text(result.markdown)
                if write_provenance:
                    provenance_path = output_path.with_suffix(output_path.suffix + '.provenance.json')
                    provenance_path.write_text(json.dumps(result.provenance, indent=2, sort_keys=True))
            return BenchTaskResult(
                pdf_path=str(pdf_path),
                page_num=page_num,
                output_path=str(output_path),
                ok=True,
            )
        except Exception as exc:
            output_path.write_text('')
            return BenchTaskResult(
                pdf_path=str(pdf_path),
                page_num=page_num,
                output_path=str(output_path),
                ok=False,
                error=f'{exc}\n{traceback.format_exc()}',
            )


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate olmOCR-Bench-compatible candidate files with SVR-OCR.')
    parser.add_argument('--pdf-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--failfast', action='store_true')
    parser.add_argument('--write-provenance', action='store_true')
    parser.add_argument('--target-longest-image-dim', type=int, default=2048)
    parser.add_argument('--base-url-env', default='QWEN_SERVER')
    parser.add_argument('--model-env', default='QWEN_MODEL')
    parser.add_argument('--api-key-env', default='QWEN_API_KEY')
    parser.add_argument('--max-tokens', type=int, default=2000)
    parser.add_argument('--temperature', type=float, default=0.0)
    parser.add_argument('--parallel', type=int, default=1)
    parser.add_argument('--page-seed-mode', choices=('whole_page', 'margin_aware'), default='whole_page')
    parser.add_argument('--top-margin-ratio', type=float, default=0.12)
    parser.add_argument('--bottom-margin-ratio', type=float, default=0.12)
    parser.add_argument('--min-margin-px', type=int, default=80)
    parser.add_argument('--max-margin-px', type=int, default=260)
    parser.add_argument('--body-overlap-px', type=int, default=16)
    args = parser.parse_args()

    def pipeline_factory() -> SVROCRPipeline:
        endpoint = EndpointConfig.from_env(
            base_url_env=args.base_url_env,
            model_env=args.model_env,
            api_key_env=args.api_key_env,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        config = SVROCRConfig(endpoint=endpoint, default_model_name=endpoint.model_name or 'svr-ocr-openai')
        return build_openai_compatible_pipeline(config=config, endpoint=endpoint)

    pipeline = pipeline_factory()
    runner = BenchRunner(
        pipeline=pipeline,
        pipeline_factory=pipeline_factory if args.parallel > 1 else None,
        target_longest_image_dim=args.target_longest_image_dim,
        max_parallel=args.parallel,
        page_seed_mode=args.page_seed_mode,
        margin_seed=MarginAwareSeedOptions(
            top_margin_ratio=args.top_margin_ratio,
            bottom_margin_ratio=args.bottom_margin_ratio,
            min_margin_px=args.min_margin_px,
            max_margin_px=args.max_margin_px,
            body_overlap_px=args.body_overlap_px,
        ),
    )
    summary = runner.run(
        pdf_directory=args.pdf_dir,
        output_directory=args.output_dir,
        repeats=args.repeats,
        force=args.force,
        limit=args.limit,
        failfast=args.failfast,
        write_provenance=args.write_provenance,
    )
    print(f'Attempted: {summary.attempted}')
    print(f'Completed: {summary.completed}')
    print(f'Failed: {summary.failed}')
    print(f'Skipped: {summary.skipped}')
    for failure in summary.failures[:20]:
        print(f'FAIL {failure.output_path}: {failure.error.splitlines()[0] if failure.error else "unknown error"}')


if __name__ == '__main__':
    main()
