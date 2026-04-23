#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from svr_ocr import EndpointConfig, SVROCRConfig, build_openai_compatible_pipeline
from svr_ocr.io import make_margin_aware_page_bundle, make_whole_page_bundle, render_pdf_page_to_png


def main() -> None:
    parser = argparse.ArgumentParser(description='Run a live SVR-OCR smoke test against an OpenAI-compatible vision endpoint.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--image')
    group.add_argument('--pdf')
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--base-url-env', default='QWEN_SERVER')
    parser.add_argument('--model-env', default='QWEN_MODEL')
    parser.add_argument('--api-key-env', default='QWEN_API_KEY')
    parser.add_argument('--max-tokens', type=int, default=2000)
    parser.add_argument('--temperature', type=float, default=0.0)
    parser.add_argument('--target-longest-image-dim', type=int, default=2048)
    parser.add_argument('--page-seed-mode', choices=('whole_page', 'margin_aware'), default='whole_page')
    parser.add_argument('--show-provenance', action='store_true')
    args = parser.parse_args()

    endpoint = EndpointConfig.from_env(
        base_url_env=args.base_url_env,
        model_env=args.model_env,
        api_key_env=args.api_key_env,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    config = SVROCRConfig(endpoint=endpoint, default_model_name=endpoint.model_name or 'svr-ocr-openai')
    pipeline = build_openai_compatible_pipeline(config=config, endpoint=endpoint)

    if args.image:
        page = _make_page_bundle(args.image, page_id='smoke_page', page_seed_mode=args.page_seed_mode)
        result = pipeline.process_page(page)
    else:
        with TemporaryDirectory(prefix='svr_ocr_smoke_') as tmpdir:
            png_path = Path(tmpdir) / 'smoke_page.png'
            render_pdf_page_to_png(args.pdf, args.page, png_path, target_longest_image_dim=args.target_longest_image_dim)
            page = _make_page_bundle(
                png_path,
                page_id=f'smoke_page_{args.page}',
                page_seed_mode=args.page_seed_mode,
            )
            result = pipeline.process_page(page)

    print(result.markdown)
    if args.show_provenance:
        print('\n--- PROVENANCE ---')
        print(json.dumps(result.provenance, indent=2, sort_keys=True))


def _make_page_bundle(image_path, *, page_id: str, page_seed_mode: str):
    if page_seed_mode == 'margin_aware':
        return make_margin_aware_page_bundle(image_path, page_id=page_id)
    return make_whole_page_bundle(image_path, page_id=page_id)


if __name__ == '__main__':
    main()
