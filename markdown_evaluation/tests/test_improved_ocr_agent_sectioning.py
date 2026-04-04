from improved_ocr_agent.sectioning import build_document_model, normalize_markdown


def test_algorithm_pseudocode_stays_in_code_blocks() -> None:
    model = build_document_model(
        "\n".join(
            [
                "## Methodology",
                "Algorithm 1 VLA-OPD Training Procedure",
                "Input: Student Policy πθ, Teacher Policy πtea",
                "1: Initialize iteration counter k ←0",
                "2: while not converged do",
                "3:",
                "",
                "Sample a batch of prompts {oj} from Dprompt",
                "4:",
                "",
                "for each prompt o in batch do",
                "5:",
                "",
                "// Phase 1: Group Sampling (On-Policy)",
                "6:",
                "",
                "Generate G trajectories {τ1, . . . , τG} using student πθ(·|o)",
                "7:",
                "for each trajectory τi in group do",
                "8:",
                "// Phase 2: Dense Teacher Labeling",
                "20: end while",
                "that remains frozen during distillation.",
            ]
        ),
        title_hint="VLA-OPD",
    )

    section = model.sections[0]
    kinds = [block.kind for block in section.blocks if block.text.strip()]
    assert kinds[:15] == ["code"] * 15
    assert kinds[-1] == "text"

    markdown = normalize_markdown(
        "\n".join(
            [
                "## Methodology",
                "Algorithm 1 VLA-OPD Training Procedure",
                "Input: Student Policy πθ, Teacher Policy πtea",
                "1: Initialize iteration counter k ←0",
                "2: while not converged do",
                "3:",
                "Sample a batch of prompts {oj} from Dprompt",
                "4:",
                "for each prompt o in batch do",
                "5:",
                "// Phase 1: Group Sampling (On-Policy)",
                "6:",
                "Generate G trajectories {τ1, . . . , τG} using student πθ(·|o)",
                "20: end while",
                "that remains frozen during distillation.",
            ]
        ),
        title_hint="VLA-OPD",
    )
    assert "```text\nAlgorithm 1 VLA-OPD Training Procedure" in markdown
    assert "$$\nInput: Student Policy" not in markdown
    assert "$$\n// Phase 1: Group Sampling" not in markdown
    assert "\nthat remains frozen during distillation.\n" in markdown


def test_source_fences_are_parsed_not_reemitted_as_text() -> None:
    markdown = normalize_markdown(
        "\n".join(
            [
                "## Methodology",
                "```text",
                "Algorithm 1 VLA-OPD Training Procedure",
                "Input: Student Policy πθ, Teacher Policy πtea",
                "```",
                "$$",
                "// Phase 1: Group Sampling (On-Policy)",
                "$$",
                "that remains frozen during distillation.",
            ]
        ),
        title_hint="VLA-OPD",
    )

    assert "```text\nAlgorithm 1 VLA-OPD Training Procedure" in markdown
    assert "$$\n// Phase 1: Group Sampling" not in markdown
    assert "\nthat remains frozen during distillation.\n" in markdown


def test_normal_prose_is_not_fenced_as_code() -> None:
    markdown = normalize_markdown(
        "\n".join(
            [
                "## Evaluation Protocol",
                "For reproducibility, we detail the full evaluation protocol used for all ImageNet-256 generation results.",
                "For all reported FID numbers in the main paper (Tab. 1), we use the adaptive fifth-order Dormand–Prince solver.",
            ]
        ),
        title_hint="UNITE",
    )

    assert "```text" not in markdown
    assert "For reproducibility, we detail the full evaluation protocol" in markdown
