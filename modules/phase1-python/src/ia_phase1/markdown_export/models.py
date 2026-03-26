from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Literal, Optional

AssetMode = Literal["copy", "reference"]
PathMode = Literal["relative", "absolute"]


@dataclass(slots=True)
class MarkdownExportConfig:
    asset_mode: AssetMode = "copy"
    asset_path_mode: PathMode = "relative"
    include_frontmatter: bool = True
    include_page_markers: bool = False
    prefer_equation_latex: bool = True
    include_equation_fallback_assets: bool = True
    ensure_assets: bool = True
    overwrite: bool = True


@dataclass(slots=True)
class MarkdownExportResult:
    paper_id: int
    bundle_dir: Path
    markdown_path: Path
    manifest_path: Path
    markdown: str
    asset_counts: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)
    section_count: int = 0
