from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from svr_ocr.assemble.page_assembler import MarkdownPageAssembler
from svr_ocr.config import SVROCRConfig
from svr_ocr.contracts import (
    BlockCandidate,
    BlockNode,
    BlockType,
    BoundingBox,
    GenerationMetadata,
    LayoutGraph,
    PageImageBundle,
    PromptType,
    SelectedBlock,
    VerificationBreakdown,
)
from svr_ocr.crops.refinement_policy import TypedRefinementPlanner
from svr_ocr.io import make_margin_aware_page_bundle
from svr_ocr.layout.graph_builder import HeuristicLayoutGraphBuilder
from svr_ocr.verify.header_footer_verifier import HeaderFooterBlockVerifier


class HeaderFooterTests(unittest.TestCase):
    def test_margin_aware_page_bundle_seeds_top_body_bottom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "page.png"
            _write_png_header(image_path, width=1000, height=2000)

            page = make_margin_aware_page_bundle(
                image_path,
                page_id="page_1",
                extra_metadata={"page_num": 1},
            )

        blocks = page.metadata["blocks"]
        self.assertEqual([block["block_id"] for block in blocks], ["top_margin", "body", "bottom_margin"])
        self.assertEqual(blocks[0]["block_type"], BlockType.HEADER_FOOTER.value)
        self.assertEqual(blocks[1]["block_type"], BlockType.PARAGRAPH.value)
        self.assertEqual(blocks[2]["block_type"], BlockType.HEADER_FOOTER.value)
        self.assertEqual(blocks[0]["metadata"]["position_band"], "top")
        self.assertEqual(blocks[1]["metadata"]["position_band"], "body")
        self.assertEqual(blocks[2]["metadata"]["position_band"], "bottom")
        self.assertIs(blocks[0]["metadata"]["drop_candidate"], True)
        self.assertIs(blocks[1]["metadata"]["drop_candidate"], False)
        self.assertLess(blocks[1]["bbox"][1], blocks[1]["bbox"][3])

    def test_refinement_planner_routes_header_footer_to_dedicated_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "page.png"
            _write_png_header(image_path, width=1000, height=2000)
            page = make_margin_aware_page_bundle(image_path, page_id="page_1")
            graph = HeuristicLayoutGraphBuilder().build(page)

        plan = TypedRefinementPlanner(SVROCRConfig()).plan(page, graph)
        decisions = plan.by_block_id()

        self.assertEqual(decisions["top_margin"].prompt_type, PromptType.HEADER_FOOTER)
        self.assertEqual(decisions["bottom_margin"].prompt_type, PromptType.HEADER_FOOTER)
        self.assertIn("header_footer_candidate", decisions["top_margin"].reasons)

    def test_header_footer_verifier_treats_drop_marker_as_successful_omission(self):
        verifier = HeaderFooterBlockVerifier()
        block = _block("top_margin", BlockType.HEADER_FOOTER, "top")
        graph = _graph([block])
        candidate = _candidate(block, "<<SVR_DROP_HEADER_FOOTER>>", PromptType.HEADER_FOOTER)

        verified = verifier.verify(block, candidate, graph)

        self.assertIs(verified.verification.emit, False)
        self.assertEqual(verified.verification.drop_reason, "model_drop_marker")
        self.assertGreaterEqual(verified.verification.final_score, 0.85)

    def test_header_footer_verifier_drops_obvious_boilerplate(self):
        verifier = HeaderFooterBlockVerifier()
        block = _block("bottom_margin", BlockType.HEADER_FOOTER, "bottom")
        graph = _graph([block])

        for content in ("Page 3", "https://example.com/paper", "doi:10.1000/example"):
            with self.subTest(content=content):
                candidate = _candidate(block, content, PromptType.HEADER_FOOTER)
                verified = verifier.verify(block, candidate, graph)
                self.assertIs(verified.verification.emit, False)
                self.assertEqual(verified.verification.drop_reason, "boilerplate_pattern")

    def test_header_footer_verifier_can_emit_title_like_margin_content(self):
        verifier = HeaderFooterBlockVerifier()
        block = _block("top_margin", BlockType.HEADER_FOOTER, "top")
        graph = _graph([block])
        candidate = _candidate(
            block,
            "A Unified Framework for Document Understanding",
            PromptType.HEADER_FOOTER,
        )

        verified = verifier.verify(block, candidate, graph)

        self.assertIs(verified.verification.emit, True)
        self.assertIsNone(verified.verification.drop_reason)

    def test_header_footer_verifier_does_not_treat_words_as_roman_page_numbers(self):
        verifier = HeaderFooterBlockVerifier()
        block = _block("top_margin", BlockType.HEADER_FOOTER, "top")
        graph = _graph([block])
        candidate = _candidate(block, "CIVIL", PromptType.HEADER_FOOTER)

        verified = verifier.verify(block, candidate, graph)

        self.assertIs(verified.verification.emit, True)

    def test_page_assembler_omits_non_emitted_margin_blocks(self):
        top = _block("top_margin", BlockType.HEADER_FOOTER, "top")
        body = _block("body", BlockType.PARAGRAPH, "body")
        bottom = _block("bottom_margin", BlockType.HEADER_FOOTER, "bottom")
        graph = _graph([top, body, bottom])
        page = PageImageBundle(page_id="page_1", image_path="page.png", width=1000, height=2000)
        selected = {
            "top_margin": _selected(top, "<<SVR_DROP_HEADER_FOOTER>>", emit=False, drop_reason="model_drop_marker"),
            "body": _selected(body, "Body text", emit=True),
            "bottom_margin": _selected(bottom, "Page 3", emit=False, drop_reason="boilerplate_pattern"),
        }

        result = MarkdownPageAssembler().assemble(page, graph, selected)

        self.assertEqual(result.markdown, "Body text")
        self.assertEqual(result.ordered_blocks, ["body"])
        self.assertIs(result.provenance["top_margin"]["emitted"], False)
        self.assertEqual(result.provenance["bottom_margin"]["drop_reason"], "boilerplate_pattern")

    def test_page_assembler_strips_outer_markdown_code_fence(self):
        body = _block("body", BlockType.PARAGRAPH, "body")
        graph = _graph([body])
        page = PageImageBundle(page_id="page_1", image_path="page.png", width=1000, height=2000)
        selected = {
            "body": _selected(body, "```markdown\n# Title\n\nBody text\n```", emit=True),
        }

        result = MarkdownPageAssembler().assemble(page, graph, selected)

        self.assertEqual(result.markdown, "# Title\n\nBody text")
        self.assertEqual(result.provenance["body"]["content_preview"], "# Title\n\nBody text")

    def test_page_assembler_strips_unclosed_outer_markdown_code_fence(self):
        body = _block("body", BlockType.PARAGRAPH, "body")
        graph = _graph([body])
        page = PageImageBundle(page_id="page_1", image_path="page.png", width=1000, height=2000)
        selected = {
            "body": _selected(body, "```markdown\n# Title\n\nBody text", emit=True),
        }

        result = MarkdownPageAssembler().assemble(page, graph, selected)

        self.assertEqual(result.markdown, "# Title\n\nBody text")

    def test_page_assembler_suppresses_margin_duplicate_of_body_prefix(self):
        top = _block("top_margin", BlockType.HEADER_FOOTER, "top")
        body = _block("body", BlockType.PARAGRAPH, "body")
        graph = _graph([top, body])
        page = PageImageBundle(page_id="page_1", image_path="page.png", width=1000, height=2000)
        selected = {
            "top_margin": _selected(top, "Chapter 1\nElementary and Secondary", emit=True),
            "body": _selected(body, "# Chapter 1\nElementary and Secondary\nMathematics", emit=True),
        }

        result = MarkdownPageAssembler().assemble(page, graph, selected)

        self.assertEqual(result.markdown, "# Chapter 1\nElementary and Secondary\nMathematics")
        self.assertEqual(result.ordered_blocks, ["body"])
        self.assertIs(result.provenance["top_margin"]["emitted"], False)
        self.assertEqual(result.provenance["top_margin"]["drop_reason"], "duplicate_body_prefix")


def _write_png_header(path: Path, *, width: int, height: int) -> None:
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", width, height))


def _block(block_id: str, block_type: BlockType, position_band: str) -> BlockNode:
    bbox = {
        "top": BoundingBox(0, 0, 1000, 200),
        "body": BoundingBox(0, 200, 1000, 1800),
        "bottom": BoundingBox(0, 1800, 1000, 2000),
    }[position_band]
    return BlockNode(
        block_id=block_id,
        bbox=bbox,
        block_type=block_type,
        metadata={"position_band": position_band, "reading_order": len(position_band)},
    )


def _graph(blocks: list[BlockNode]) -> LayoutGraph:
    return LayoutGraph(page_id="page_1", page_size=(1000, 2000), blocks=blocks)


def _candidate(block: BlockNode, content: str, prompt_type: PromptType) -> BlockCandidate:
    return BlockCandidate(
        page_id="page_1",
        block_id=block.block_id,
        candidate_id=f"{block.block_id}_candidate",
        block_type=block.block_type,
        prompt_type=prompt_type,
        content=content,
        raw_model_output=content,
        generation_metadata=GenerationMetadata(prompt_type=prompt_type),
    )


def _selected(
    block: BlockNode,
    content: str,
    *,
    emit: bool,
    drop_reason: str | None = None,
) -> SelectedBlock:
    prompt_type = PromptType.HEADER_FOOTER if block.block_type == BlockType.HEADER_FOOTER else PromptType.PARAGRAPH
    return SelectedBlock(
        block_id=block.block_id,
        candidate=_candidate(block, content, prompt_type),
        verification=VerificationBreakdown(
            renderable=True,
            final_score=0.95,
            emit=emit,
            drop_reason=drop_reason,
        ),
    )


if __name__ == "__main__":
    unittest.main()
