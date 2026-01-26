from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def caption_image(image_path: str) -> Optional[str]:
    model = os.getenv("VISION_CAPTION_MODEL")
    if not model:
        return None
    url = (os.getenv("LOCAL_LLM_URL") or "http://localhost:11434").rstrip("/") + "/api/generate"
    timeout = int(os.getenv("LOCAL_LLM_TIMEOUT", "60"))
    prompt = os.getenv(
        "VISION_CAPTION_PROMPT",
        "Describe this figure in detail. Focus on axes, trends, labels, and any key values.",
    )
    path = Path(image_path)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if isinstance(data.get("response"), str):
            return data["response"].strip()
    except Exception as exc:
        logger.warning("Vision caption failed for %s: %s", image_path, exc)
    return None
