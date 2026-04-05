from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROOT_STR = str(ROOT)
PKG_DIR = ROOT / "improved_ocr_agent"
INIT_PY = PKG_DIR / "__init__.py"

if ROOT_STR in sys.path:
    sys.path.remove(ROOT_STR)
sys.path.insert(0, ROOT_STR)

for module_name in list(sys.modules):
    if module_name == "improved_ocr_agent" or module_name.startswith("improved_ocr_agent."):
        sys.modules.pop(module_name, None)

spec = importlib.util.spec_from_file_location(
    "improved_ocr_agent",
    INIT_PY,
    submodule_search_locations=[str(PKG_DIR)],
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules["improved_ocr_agent"] = module
spec.loader.exec_module(module)
