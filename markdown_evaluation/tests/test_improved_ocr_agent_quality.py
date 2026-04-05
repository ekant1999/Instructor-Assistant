from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

BRIDGE_PATH = ROOT / "improved_ocr_agent" / "ia_phase1_bridge.py"
BRIDGE_SPEC = importlib.util.spec_from_file_location("test_ia_phase1_bridge", BRIDGE_PATH)
assert BRIDGE_SPEC is not None and BRIDGE_SPEC.loader is not None
BRIDGE_MODULE = importlib.util.module_from_spec(BRIDGE_SPEC)
sys.modules[BRIDGE_SPEC.name] = BRIDGE_MODULE
BRIDGE_SPEC.loader.exec_module(BRIDGE_MODULE)
IaPhase1Bridge = BRIDGE_MODULE.IaPhase1Bridge


def test_ia_phase1_bridge_copies_assets_and_rewrites_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = tmp_path / "bridge.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%bridge test\n")

    bundle_dir = tmp_path / "bundle"
    (bundle_dir / "assets" / "figures").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "assets" / "tables").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "assets" / "equations").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "assets" / "figures" / "figure.png").write_bytes(b"fig")
    (bundle_dir / "assets" / "tables" / "table.json").write_text("{}", encoding="utf-8")
    (bundle_dir / "assets" / "equations" / "equation.json").write_text("{}", encoding="utf-8")

    fake_result = SimpleNamespace(
        bundle_dir=bundle_dir,
        markdown=(
            "<!-- page:1 -->\n"
            "## Intro\n\n"
            "![Figure 1](assets/figures/figure.png)\n\n"
            "> Table JSON: `assets/tables/table.json`\n\n"
            "> Equation 1 JSON: `assets/equations/equation.json`\n"
        ),
        asset_counts={"figures": 1, "tables": 1, "equations": 1},
        render_mode="normal",
        sectioning_strategy="pdf_toc",
        metadata={"title": "Bridge Title"},
    )

    monkeypatch.setattr(BRIDGE_MODULE, "export_pdf_to_markdown", lambda *args, **kwargs: fake_result)

    bridge = IaPhase1Bridge(
        pdf_path=pdf_path,
        pdf_name="bridge",
        assets_root=tmp_path / "bridge_assets",
    )
    result = bridge.extract_non_ocr_pages(page_allowlist=[1])

    assert result.page_segments[1].startswith("## Intro")
    assert "bridge_assets/figures/figure.png" in result.page_segments[1]
    assert "bridge_assets/tables/table.json" in result.page_segments[1]
    assert "bridge_assets/equations/equation.json" in result.page_segments[1]
    assert (tmp_path / "bridge_assets" / "figures" / "figure.png").exists()
    assert (tmp_path / "bridge_assets" / "tables" / "table.json").exists()
    assert (tmp_path / "bridge_assets" / "equations" / "equation.json").exists()
    assert result.document_title == "Bridge Title"


def test_ia_phase1_bridge_renames_conflicting_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = tmp_path / "bridge.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%bridge test\n")

    bundle_dir = tmp_path / "bundle_collision"
    (bundle_dir / "assets" / "figures").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "assets" / "figures" / "figure.png").write_bytes(b"fig")

    assets_root = tmp_path / "bridge_assets_collision"
    (assets_root / "figures").mkdir(parents=True, exist_ok=True)
    (assets_root / "figures" / "figure.png").write_bytes(b"native")

    fake_result = SimpleNamespace(
        bundle_dir=bundle_dir,
        markdown="<!-- page:1 -->\n![Figure 1](assets/figures/figure.png)\n",
        asset_counts={"figures": 1, "tables": 0, "equations": 0},
        render_mode="normal",
        sectioning_strategy="pdf_toc",
        metadata={"title": "Bridge Title"},
    )

    monkeypatch.setattr(BRIDGE_MODULE, "export_pdf_to_markdown", lambda *args, **kwargs: fake_result)

    bridge = IaPhase1Bridge(
        pdf_path=pdf_path,
        pdf_name="bridge",
        assets_root=assets_root,
    )
    result = bridge.extract_non_ocr_pages(page_allowlist=[1])

    assert "bridge_assets/figures/ia_figure.png" in result.page_segments[1]
    assert (assets_root / "figures" / "figure.png").read_bytes() == b"native"
    assert (assets_root / "figures" / "ia_figure.png").read_bytes() == b"fig"
