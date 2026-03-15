from __future__ import annotations

import argparse
import asyncio
import json

from _common import METADATA_PATH, read_jsonl


async def _cleanup() -> dict:
    from backend.core.postgres import close_pool, get_pool

    metadata = read_jsonl(METADATA_PATH)
    paper_ids = [int(row["paper_id"]) for row in metadata]
    if not paper_ids:
        return {"removed_papers": 0, "removed_blocks": 0}

    pool = await get_pool()
    async with pool.acquire() as conn:
        deleted_blocks = await conn.execute(
            "DELETE FROM text_blocks WHERE paper_id = ANY($1::int[])",
            paper_ids,
        )
        deleted_papers = await conn.execute(
            "DELETE FROM papers WHERE id = ANY($1::int[])",
            paper_ids,
        )
    await close_pool()
    return {
        "removed_papers": int((deleted_papers or "DELETE 0").split()[-1]),
        "removed_blocks": int((deleted_blocks or "DELETE 0").split()[-1]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove benchmark papers from PostgreSQL pgvector tables.")
    parser.parse_args()
    result = asyncio.run(_cleanup())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
