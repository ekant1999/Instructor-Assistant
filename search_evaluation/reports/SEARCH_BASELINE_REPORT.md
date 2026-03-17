# Search Baseline Report

Current system under test: unified hybrid library search.

## Benchmark Construction

- corpus source: recent arXiv PDFs downloaded into `search_evaluation/pdfs/`
- corpus size: 20 papers across `cs.AI`, `cs.LG`, `cs.CL`, and `cs.CV`
- query count: 100
- positive queries: 80
- no-match queries: 20
- gold set quality: manually curated from the downloaded PDFs using the review notes in `search_evaluation/reviews/`
- gold fields: expected paper, expected page when confident, expected section canonical when the extracted section map was reliable

This benchmark is intentionally paper-retrieval first. Page and section metrics are included as secondary localization checks.

## Corpus

- papers: `20`
- queries: `100`

### Papers

- `910001` `2603.12261v1`: The Latent Color Subspace: Emergent Order in High-Dimensional Chaos
- `910002` `2603.12249v1`: SciMDR: Benchmarking and Advancing Scientific Multimodal Document Reasoning
- `910003` `2603.12246v1`: Examining Reasoning LLMs-as-Judges in Non-Verifiable LLM Post-Training
- `910004` `2603.12244v1`: Separable neural architectures as a primitive for unified predictive and generative intelligence
- `910005` `2603.12232v1`: Incremental Neural Network Verification via Learned Conflicts
- `910006` `2603.12255v1`: Spatial-TTT: Streaming Visual-based Spatial Intelligence with Test-Time Training
- `910007` `2603.12248v1`: Matching Features, Not Tokens: Energy-Based Fine-Tuning of Language Models
- `910008` `2603.12240v1`: BiGain: Unified Token Compression for Joint Generation and Classification
- `910009` `2603.12237v1`: STAMP: Selective Task-Aware Mechanism for Text Privacy
- `910010` `2603.12231v1`: Temporal Straightening for Latent Planning
- `910011` `2603.12252v1`: EndoCoT: Scaling Endogenous Chain-of-Thought Reasoning in Diffusion Models
- `910012` `2603.12226v1`: Sparking Scientific Creativity via LLM-Driven Interdisciplinary Inspiration
- `910013` `2603.12206v1`: CLASP: Defending Hybrid Large Language Models Against Hidden State Poisoning Attacks
- `910014` `2603.12201v1`: IndexCache: Accelerating Sparse Attention via Cross-Layer Index Reuse
- `910015` `2603.12191v1`: Long-Context Encoder Models for Polish Language Understanding
- `910016` `2603.12267v1`: EVATok: Adaptive Length Video Tokenization for Efficient Visual Autoregressive Generation
- `910017` `2603.12266v1`: MM-CondChain: A Programmatically Verified Benchmark for Visually Grounded Deep Compositional Reasoning
- `910018` `2603.12265v1`: OmniStream: Mastering Perception, Reconstruction and Action in Continuous Streams
- `910019` `2603.12264v1`: GRADE: Benchmarking Discipline-Informed Reasoning in Image Editing
- `910020` `2603.12262v1`: Video Streaming Thinking: VideoLLMs Can Watch and Think Simultaneously

## Aggregate Metrics

- hit_at_1: `0.910`
- hit_at_3: `0.920`
- hit_at_5: `0.920`
- mrr: `0.913`
- no_match_accuracy: `0.800`
- page_hit_at_1: `0.250`
- page_hit_at_3: `0.512`
- section_hit_at_1: `0.675`
- section_hit_at_3: `0.812`
- section_hit_in_top_5: `0.812`
- latency_mean_ms: `1352.8`
- latency_p50_ms: `1497.9`
- latency_p95_ms: `2018.9`

## Per-Query Results

| Query | Type | Top Paper | Correct | Page@1 | Page@3 | Section@1 | Section@3 | Section@5 |
|---|---|---|---|---|---|---|---|---|
| latent color subspace | topical | The Latent Color Subspace: Emergent Order in High-Dimensional Chaos | yes | yes | yes | yes | yes | yes |
| how FLUX latent space reflects hue saturation and lightness | paraphrase | The Latent Color Subspace: Emergent Order in High-Dimensional Chaos | yes | yes | yes | yes | yes | yes |
| training-free closed-form color control in FLUX latent space | method | The Latent Color Subspace: Emergent Order in High-Dimensional Chaos | yes | yes | yes | no | no | no |
| predicting and explicitly controlling color through latent manipulation in FLUX | application | The Latent Color Subspace: Emergent Order in High-Dimensional Chaos | yes | no | yes | no | yes | yes |
| SciMDR | benchmark | SciMDR: Benchmarking and Advancing Scientific Multimodal Document Reasoning | yes | yes | yes | yes | yes | yes |
| claim-centric QA synthesis for scientific multimodal documents | method | SciMDR: Benchmarking and Advancing Scientific Multimodal Document Reasoning | yes | no | yes | no | yes | yes |
| document-scale regrounding into realistic full scientific workflows | method | SciMDR: Benchmarking and Advancing Scientific Multimodal Document Reasoning | yes | no | no | no | no | no |
| large-scale scientific multimodal reasoning benchmark with expert evaluation | evaluation | SciMDR: Benchmarking and Advancing Scientific Multimodal Document Reasoning | yes | yes | yes | yes | yes | yes |
| reasoning judges | topical | Examining Reasoning LLMs-as-Judges in Non-Verifiable LLM Post-Training | yes | no | no | no | yes | yes |
| reasoning LLM judges for non-verifiable post-training alignment | topical | Examining Reasoning LLMs-as-Judges in Non-Verifiable LLM Post-Training | yes | no | no | yes | yes | yes |
| reward hacking under non-reasoning judges in reinforcement learning alignment | analysis | Examining Reasoning LLMs-as-Judges in Non-Verifiable LLM Post-Training | yes | no | no | yes | yes | yes |
| adversarial outputs that fool Arena-Hard and other LLM judges | analysis | Examining Reasoning LLMs-as-Judges in Non-Verifiable LLM Post-Training | yes | yes | yes | yes | yes | yes |
| SNA | acronym | Separable neural architectures as a primitive for unified predictive and generative intelligence | yes | no | no | yes | yes | yes |
| separable neural architectures as a unified predictive generative primitive | topical | Separable neural architectures as a primitive for unified predictive and generative intelligence | yes | no | yes | yes | yes | yes |
| factorizing high-dimensional mappings through interaction order and tensor rank | method | Separable neural architectures as a primitive for unified predictive and generative intelligence | yes | no | yes | yes | yes | yes |
| unifying chaotic dynamics and linguistic autoregression with separable representations | paraphrase | Separable neural architectures as a primitive for unified predictive and generative intelligence | yes | no | no | yes | yes | yes |
| learned conflicts | topical | Incremental Neural Network Verification via Learned Conflicts | yes | no | no | yes | yes | yes |
| incremental neural network verification via reusable learned conflicts | topical | Incremental Neural Network Verification via Learned Conflicts | yes | no | yes | yes | yes | yes |
| conflict inheritance under refinement relations across verification queries | method | Incremental Neural Network Verification via Learned Conflicts | yes | no | no | yes | yes | yes |
| using SAT consistency checks to prune infeasible verification subproblems | method | Incremental Neural Network Verification via Learned Conflicts | yes | no | no | yes | yes | yes |
| Spatial-TTT | topical | Spatial-TTT: Streaming Visual-based Spatial Intelligence with Test-Time Training | yes | no | yes | yes | yes | yes |
| streaming spatial intelligence with test-time training over long video streams | topical | Spatial-TTT: Streaming Visual-based Spatial Intelligence with Test-Time Training | yes | yes | yes | no | no | no |
| fast weights for maintaining and organizing spatial evidence over time | method | None | no | no | no | no | no | no |
| hybrid spatial video processing with large chunks and sliding-window attention | method | OmniStream: Mastering Perception, Reconstruction and Action in Continuous Streams | no | no | no | no | no | no |
| EBFT | acronym | Matching Features, Not Tokens: Energy-Based Fine-Tuning of Language Models | yes | no | yes | no | yes | yes |
| feature matching objective for sequence-level language model fine-tuning | method | Matching Features, Not Tokens: Energy-Based Fine-Tuning of Language Models | yes | no | no | yes | yes | yes |
| strided block-parallel sampling for efficient on-policy language model updates | method | Matching Features, Not Tokens: Energy-Based Fine-Tuning of Language Models | yes | no | yes | yes | yes | yes |
| energy-based fine-tuning that matches rollout feature statistics | paraphrase | Matching Features, Not Tokens: Energy-Based Fine-Tuning of Language Models | yes | no | yes | yes | yes | yes |
| BiGain | topical | BiGain: Unified Token Compression for Joint Generation and Classification | yes | no | no | yes | yes | yes |
| frequency-aware token compression for joint generation and classification | topical | BiGain: Unified Token Compression for Joint Generation and Classification | yes | yes | yes | yes | yes | yes |
| laplacian-gated token merging and inter-extrapolate KV downsampling | method | BiGain: Unified Token Compression for Joint Generation and Classification | yes | yes | yes | yes | yes | yes |
| balanced spectral retention for accelerated diffusion generation and classification | analysis | BiGain: Unified Token Compression for Joint Generation and Classification | yes | no | yes | no | yes | yes |
| STAMP | topical | STAMP: Selective Task-Aware Mechanism for Text Privacy | yes | yes | yes | no | no | no |
| selective task-aware text privatization with token-level privacy budgets | topical | STAMP: Selective Task-Aware Mechanism for Text Privacy | yes | yes | yes | yes | yes | yes |
| polar mechanism that perturbs embedding directions on the unit sphere | method | STAMP: Selective Task-Aware Mechanism for Text Privacy | yes | yes | yes | yes | yes | yes |
| improved privacy utility trade-off for text under metric local differential privacy | evaluation | STAMP: Selective Task-Aware Mechanism for Text Privacy | yes | yes | yes | yes | yes | yes |
| temporal straightening | topical | Temporal Straightening for Latent Planning | yes | no | no | no | no | no |
| curvature regularization for latent planning with world models | method | Temporal Straightening for Latent Planning | yes | no | no | no | yes | yes |
| straightened latent dynamics for more stable gradient-based goal planning | application | Temporal Straightening for Latent Planning | yes | no | no | no | no | no |
| making Euclidean distance better approximate geodesic distance in latent space | analysis | Temporal Straightening for Latent Planning | yes | no | no | no | no | no |
| EndoCoT | topical | EndoCoT: Scaling Endogenous Chain-of-Thought Reasoning in Diffusion Models | yes | no | no | yes | yes | yes |
| endogenous chain-of-thought guidance inside diffusion model decoding | topical | EndoCoT: Scaling Endogenous Chain-of-Thought Reasoning in Diffusion Models | yes | yes | yes | no | no | no |
| iteratively refining latent thought states to guide denoising steps | method | EndoCoT: Scaling Endogenous Chain-of-Thought Reasoning in Diffusion Models | yes | yes | yes | yes | yes | yes |
| terminal thought grounding for reasoned guidance in diffusion models | method | EndoCoT: Scaling Endogenous Chain-of-Thought Reasoning in Diffusion Models | yes | yes | yes | yes | yes | yes |
| Idea-Catalyst | topical | Sparking Scientific Creativity via LLM-Driven Interdisciplinary Inspiration | yes | no | no | no | yes | yes |
| LLM-driven interdisciplinary inspiration for scientific creativity support | topical | Sparking Scientific Creativity via LLM-Driven Interdisciplinary Inspiration | yes | no | no | no | yes | yes |
| reformulating target-domain challenges into domain-agnostic conceptual problems | method | Sparking Scientific Creativity via LLM-Driven Interdisciplinary Inspiration | yes | no | yes | yes | yes | yes |
| ranking source disciplines by interdisciplinary potential during brainstorming | results | Sparking Scientific Creativity via LLM-Driven Interdisciplinary Inspiration | yes | yes | yes | yes | yes | yes |
| CLASP | topical | CLASP: Defending Hybrid Large Language Models Against Hidden State Poisoning Attacks | yes | no | no | no | no | no |
| defending hybrid large language models from hidden state poisoning attacks | topical | CLASP: Defending Hybrid Large Language Models Against Hidden State Poisoning Attacks | yes | no | no | no | yes | yes |
| token-level malicious token detection for résumé screening pipelines | application | CLASP: Defending Hybrid Large Language Models Against Hidden State Poisoning Attacks | yes | no | yes | yes | yes | yes |
| xgboost classifier over mamba block output embeddings for HiSPA defense | method | CLASP: Defending Hybrid Large Language Models Against Hidden State Poisoning Attacks | yes | yes | yes | yes | yes | yes |
| IndexCache | topical | IndexCache: Accelerating Sparse Attention via Cross-Layer Index Reuse | yes | no | yes | yes | yes | yes |
| cross-layer top-k index reuse for accelerating sparse attention | topical | IndexCache: Accelerating Sparse Attention via Cross-Layer Index Reuse | yes | no | no | no | no | no |
| training-free greedy layer selection for sparse attention indexers | method | IndexCache: Accelerating Sparse Attention via Cross-Layer Index Reuse | yes | no | no | yes | yes | yes |
| training-aware distillation of retained indexers against shared layers | method | IndexCache: Accelerating Sparse Attention via Cross-Layer Index Reuse | yes | no | yes | yes | yes | yes |
| Polish encoders | topical | Long-Context Encoder Models for Polish Language Understanding | yes | no | no | yes | yes | yes |
| long-context encoder models for Polish language understanding | topical | Long-Context Encoder Models for Polish Language Understanding | yes | no | no | yes | yes | yes |
| two-stage training with positional adaptation and continuous pre-training | method | OmniStream: Mastering Perception, Reconstruction and Action in Continuous Streams | no | no | yes | no | no | no |
| knowledge-distilled compressed Polish encoders for long-document tasks | method | Long-Context Encoder Models for Polish Language Understanding | yes | no | no | yes | yes | yes |
| EVATok | topical | EVATok: Adaptive Length Video Tokenization for Efficient Visual Autoregressive Generation | yes | no | yes | no | yes | yes |
| adaptive length video tokenization for efficient autoregressive generation | topical | EVATok: Adaptive Length Video Tokenization for Efficient Visual Autoregressive Generation | yes | no | no | yes | yes | yes |
| routers that predict optimal token assignments for each video | method | EVATok: Adaptive Length Video Tokenization for Efficient Visual Autoregressive Generation | yes | no | yes | yes | yes | yes |
| better quality-cost trade-offs through adaptive video token budgets | analysis | EVATok: Adaptive Length Video Tokenization for Efficient Visual Autoregressive Generation | yes | no | no | no | no | no |
| MM-CondChain | topical | MM-CondChain: A Programmatically Verified Benchmark for Visually Grounded Deep Compositional Reasoning | yes | no | no | yes | yes | yes |
| programmatically verified benchmark for visually grounded compositional reasoning | topical | MM-CondChain: A Programmatically Verified Benchmark for Visually Grounded Deep Compositional Reasoning | yes | no | no | yes | yes | yes |
| VPIR based agentic pipeline for verified multi-layer visual conditions | method | MM-CondChain: A Programmatically Verified Benchmark for Visually Grounded Deep Compositional Reasoning | yes | yes | yes | yes | yes | yes |
| deep reasoning chains over natural images charts and GUI trajectories | application | MM-CondChain: A Programmatically Verified Benchmark for Visually Grounded Deep Compositional Reasoning | yes | no | no | yes | yes | yes |
| OmniStream | topical | OmniStream: Mastering Perception, Reconstruction and Action in Continuous Streams | yes | no | no | yes | yes | yes |
| unified streaming visual backbone for perception reconstruction and action | topical | OmniStream: Mastering Perception, Reconstruction and Action in Continuous Streams | yes | no | yes | yes | yes | yes |
| causal spatiotemporal attention with 3D-RoPE and persistent KV-cache | method | OmniStream: Mastering Perception, Reconstruction and Action in Continuous Streams | yes | yes | yes | yes | yes | yes |
| frozen backbone transfer across image video spatial and robotic tasks | results | OmniStream: Mastering Perception, Reconstruction and Action in Continuous Streams | yes | no | no | yes | yes | yes |
| GRADE | benchmark | GRADE: Benchmarking Discipline-Informed Reasoning in Image Editing | yes | no | yes | no | yes | yes |
| discipline-informed reasoning benchmark for image editing across ten academic domains | benchmark | GRADE: Benchmarking Discipline-Informed Reasoning in Image Editing | yes | no | yes | yes | yes | yes |
| multi-dimensional evaluation of discipline reasoning visual consistency and readability | evaluation | GRADE: Benchmarking Discipline-Informed Reasoning in Image Editing | yes | no | no | yes | yes | yes |
| analysis of current multimodal model limits under knowledge-intensive image editing | analysis | The Latent Color Subspace: Emergent Order in High-Dimensional Chaos | no | no | no | yes | yes | yes |
| VST | acronym | Video Streaming Thinking: VideoLLMs Can Watch and Think Simultaneously | yes | no | no | yes | yes | yes |
| thinking while watching for online video language models | method | Video Streaming Thinking: VideoLLMs Can Watch and Think Simultaneously | yes | no | yes | yes | yes | yes |
| post-training pipeline with VST-SFT VST-RL and streaming QA synthesis | method | Video Streaming Thinking: VideoLLMs Can Watch and Think Simultaneously | yes | no | no | yes | yes | yes |
| faster streaming video reasoning than test-time scaling baselines | results | EndoCoT: Scaling Endogenous Chain-of-Thought Reasoning in Diffusion Models | no | no | no | no | no | no |
| federated learning with severe client drift | no_match | None | yes | no | no | no | no | no |
| protein folding with geometric transformers | no_match | None | yes | no | no | no | no | no |
| automatic speech recognition for noisy meetings | no_match | None | yes | no | no | no | no | no |
| molecular docking with diffusion priors | no_match | None | yes | no | no | no | no | no |
| personalized recommendation systems for ecommerce catalogs | no_match | None | yes | no | no | no | no | no |
| legal retrieval over appellate case databases | no_match | None | yes | no | no | no | no | no |
| global weather forecasting with diffusion models | no_match | None | yes | no | no | no | no | no |
| medical image segmentation with anatomical priors | no_match | GRADE: Benchmarking Discipline-Informed Reasoning in Image Editing | no | no | no | no | no | no |
| dialog summarization for customer support transcripts | no_match | None | yes | no | no | no | no | no |
| database SQL optimization with learned indexes | no_match | None | yes | no | no | no | no | no |
| graph chemistry for molecular property prediction | no_match | None | yes | no | no | no | no | no |
| neural radiance fields for indoor scene capture | no_match | None | yes | no | no | no | no | no |
| federated optimization under extreme client heterogeneity | no_match | None | yes | no | no | no | no | no |
| end-to-end speech translation for university lectures | no_match | None | yes | no | no | no | no | no |
| retrieval augmented legal case ranking with citations | no_match | Sparking Scientific Creativity via LLM-Driven Interdisciplinary Inspiration | no | no | no | no | no | no |
| protein structure prediction using denoising diffusion | no_match | EndoCoT: Scaling Endogenous Chain-of-Thought Reasoning in Diffusion Models | no | no | no | no | no | no |
| code generation directly from unit tests | no_match | Matching Features, Not Tokens: Energy-Based Fine-Tuning of Language Models | no | no | no | no | no | no |
| household robot planning under object uncertainty | no_match | None | yes | no | no | no | no | no |
| retail demand forecasting across seasonal promotions | no_match | None | yes | no | no | no | no | no |
| drug interaction extraction from biomedical abstracts | no_match | None | yes | no | no | no | no | no |

## Takeaways

- Top-1 paper accuracy is `0.910` on this benchmark.
- No-match accuracy is `0.800` on the unsupported-query slice.
- Page localization is `0.250` at top-1 and `0.512` within the top 3 localized hits.
- Section localization is `0.675` at top-1, `0.812` within the top 3 localized hits, and `0.812` within the top 5 localized hits.

## Failure Cases

- `fast weights for maintaining and organizing spatial evidence over time` expected `910006` but got `no result`
- `hybrid spatial video processing with large chunks and sliding-window attention` expected `910006` but got `910018, 910014`
- `two-stage training with positional adaptation and continuous pre-training` expected `910015` but got `910018, 910014, 910015`
- `analysis of current multimodal model limits under knowledge-intensive image editing` expected `910019` but got `910001`
- `faster streaming video reasoning than test-time scaling baselines` expected `910020` but got `910011, 910018`
- `medical image segmentation with anatomical priors` expected `no result` but got `910019`
- `retrieval augmented legal case ranking with citations` expected `no result` but got `910012, 910014`
- `protein structure prediction using denoising diffusion` expected `no result` but got `910011, 910008`
- `code generation directly from unit tests` expected `no result` but got `910007, 910002, 910005, 910004, 910019`
