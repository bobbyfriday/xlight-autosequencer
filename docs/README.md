# XLight AutoSequencer Documentation

XLight AutoSequencer analyzes audio files and produces timing data for xLights holiday light sequences. It runs 35+ analysis algorithms across 6 audio stems, scores and ranks results, and exports timing marks and energy curves for import into xLights.

## Documentation Index

### Core Concepts
- **[Architecture Overview](architecture-overview.md)** — System diagram, component roles, data flow
- **[Analysis Pipeline](pipeline.md)** — End-to-end walkthrough from MP3 to xLights export
- **[Hierarchy Levels](hierarchy.md)** — The 7-level timing hierarchy (L0–L6)

### Algorithms
- **[Algorithm Reference](algorithms.md)** — Complete catalog of all 35+ algorithms
- **[Algorithm Categories](algorithm-categories.md)** — How algorithms group by purpose (beats, onsets, harmony, etc.)
- **[Stem Separation & Routing](stem-separation.md)** — Demucs 6-stem separation and algorithm-to-stem affinity

### Quality & Optimization
- **[Quality Scoring](quality-scoring.md)** — How tracks are scored, ranked, and filtered
- **[Parameter Sweep System](sweep-system.md)** — Automated parameter optimization across the algorithm×stem matrix

### Data & Export
- **[Data Structures](data-structures.md)** — TimingMark, TimingTrack, AnalysisResult, HierarchyResult
- **[Export Formats](export-formats.md)** — JSON, .xtiming XML, .xvc value curves

### Interface
- **[Review UI](review-ui.md)** — Flask server, Canvas timeline, library browser, phoneme editor

### Existing Design Docs
- [Musical Analysis Design](musical-analysis-design.md) — Original analysis design rationale
- [Orchestrator Design](orchestrator-design.md) — Hierarchy orchestrator design
- [Stem Affinity Rationale](stem-affinity-rationale.md) — Why algorithms prefer specific stems
- [xLight Grouping Design](xlight-grouping-design.md) — Light group tier mapping
- [Effect Themes Library](effect-themes-library.md) — Effect theme catalog
- [Quickstart](quickstart.md) — Getting started guide
