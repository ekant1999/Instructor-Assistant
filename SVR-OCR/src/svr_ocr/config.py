from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Thresholds:
    low_confidence: float = 0.60
    high_text_density: float = 0.70
    high_difficulty: float = 0.60
    accept_score: float = 0.85
    repair_score: float = 0.65


@dataclass
class CandidatePolicy:
    default_candidates: int = 1
    hard_block_candidates: int = 2
    very_hard_block_candidates: int = 3
    hard_block_crop_scale: float = 1.5
    very_hard_block_crop_scale: float = 2.0


@dataclass
class RepairPolicy:
    default_repairs: int = 0
    hard_block_repairs: int = 1
    very_hard_block_repairs: int = 2


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


@dataclass
class EndpointConfig:
    base_url: str = ""
    model_name: str = ""
    api_key: str | None = None
    api_key_env: str = "QWEN_API_KEY"
    timeout_seconds: int = 180
    max_tokens: int = 2000
    temperature: float = 0.0
    response_path: str = "chat/completions"
    extra_headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(
        cls,
        *,
        base_url_env: str = "QWEN_SERVER",
        model_env: str = "QWEN_MODEL",
        api_key_env: str = "QWEN_API_KEY",
        **kwargs,
    ) -> "EndpointConfig":
        return cls(
            base_url=os.getenv(base_url_env, ""),
            model_name=os.getenv(model_env, ""),
            api_key_env=api_key_env,
            **kwargs,
        )

    def resolved_api_key(self) -> str | None:
        if self.api_key:
            return self.api_key
        if not self.api_key_env:
            return None
        value = os.getenv(self.api_key_env)
        return value or None

    def chat_completions_url(self) -> str:
        base = self.base_url.strip().rstrip("/")
        if not base:
            return ""
        response_path = self.response_path.strip("/")
        if base.endswith(response_path):
            return base
        return f"{base}/{response_path}"


@dataclass
class SVROCRConfig:
    thresholds: Thresholds = field(default_factory=Thresholds)
    candidate_policy: CandidatePolicy = field(default_factory=CandidatePolicy)
    repair_policy: RepairPolicy = field(default_factory=RepairPolicy)
    header_footer: HeaderFooterPolicy = field(default_factory=HeaderFooterPolicy)
    endpoint: EndpointConfig | None = None
    crop_context_margin: int = 24
    default_model_name: str = "svr-ocr-scaffold"
