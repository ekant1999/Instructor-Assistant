from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set

from _common import EVAL_PAPER_ID_START, METADATA_PATH, PDF_DIR, ensure_dirs, write_jsonl


ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}
CATEGORY_TARGETS = {
    "cs.AI": 5,
    "cs.LG": 5,
    "cs.CL": 5,
    "cs.CV": 5,
}


def fetch_entries(category: str, start: int, batch_size: int) -> List[Dict[str, str]]:
    params = urllib.parse.urlencode(
        {
            "search_query": f"cat:{category}",
            "start": start,
            "max_results": batch_size,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = f"http://export.arxiv.org/api/query?{params}"
    data = urllib.request.urlopen(url, timeout=60).read()
    root = ET.fromstring(data)
    entries: List[Dict[str, str]] = []
    for entry in root.findall("a:entry", ARXIV_NS):
        arxiv_id = (entry.findtext("a:id", default="", namespaces=ARXIV_NS) or "").rsplit("/", 1)[-1]
        pdf_url = ""
        categories = []
        for link in entry.findall("a:link", ARXIV_NS):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href", "")
        for category_node in entry.findall("a:category", ARXIV_NS):
            term = category_node.attrib.get("term")
            if term:
                categories.append(term)
        if not arxiv_id or not pdf_url:
            continue
        entries.append(
            {
                "arxiv_id": arxiv_id,
                "title": " ".join((entry.findtext("a:title", default="", namespaces=ARXIV_NS) or "").split()),
                "summary": " ".join((entry.findtext("a:summary", default="", namespaces=ARXIV_NS) or "").split()),
                "published": entry.findtext("a:published", default="", namespaces=ARXIV_NS) or "",
                "updated": entry.findtext("a:updated", default="", namespaces=ARXIV_NS) or "",
                "pdf_url": pdf_url,
                "categories": categories,
                "primary_category": categories[0] if categories else category,
            }
        )
    return entries


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    dest.write_bytes(data)


def select_recent_corpus() -> List[Dict[str, str]]:
    selected: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for category, target_count in CATEGORY_TARGETS.items():
        chosen = 0
        start = 0
        while chosen < target_count:
            batch = fetch_entries(category, start=start, batch_size=20)
            if not batch:
                break
            for entry in batch:
                arxiv_id = entry["arxiv_id"]
                if arxiv_id in seen:
                    continue
                seen.add(arxiv_id)
                entry["benchmark_category"] = category
                selected.append(entry)
                chosen += 1
                if chosen >= target_count:
                    break
            start += len(batch)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a 20-paper recent arXiv benchmark corpus.")
    parser.add_argument("--refresh", action="store_true", help="Re-download PDFs even if they already exist.")
    args = parser.parse_args()

    ensure_dirs()
    selected = select_recent_corpus()
    records: List[Dict[str, object]] = []
    for idx, entry in enumerate(selected):
        pdf_name = f"{entry['arxiv_id']}.pdf"
        pdf_path = PDF_DIR / pdf_name
        if args.refresh or not pdf_path.exists():
            download_file(entry["pdf_url"], pdf_path)
        records.append(
            {
                "paper_id": EVAL_PAPER_ID_START + idx,
                "arxiv_id": entry["arxiv_id"],
                "title": entry["title"],
                "summary": entry["summary"],
                "published": entry["published"],
                "updated": entry["updated"],
                "pdf_url": entry["pdf_url"],
                "pdf_path": str(pdf_path),
                "benchmark_category": entry["benchmark_category"],
                "primary_category": entry["primary_category"],
                "categories": entry["categories"],
            }
        )

    write_jsonl(METADATA_PATH, records)
    print(json.dumps({"downloaded": len(records), "metadata_path": str(METADATA_PATH)}, indent=2))


if __name__ == "__main__":
    main()
