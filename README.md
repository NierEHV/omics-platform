# Multi-Omics Analysis Platform

A comprehensive, extensible platform for multi-omics data analysis covering:
- **scRNA-seq** — Single-cell transcriptomics (Scanpy + scvi-tools + GPU)
- **Spatial Transcriptomics** — Tissue-level spatial gene expression (Squidpy + Spyrrow)
- **16S rRNA** — Microbiome amplicon sequencing (QIIME2-powered)
- **Metagenomics** — Shotgun microbiome sequencing (Kraken2 + HUMAnN3)
- **Multi-Omics Integration** — Cross-modality analysis (MOFA2, Mowgli, muon)
- **Publication Figures** — Nature/Cell/Science standard visualization

## Status

**Phase 1: Foundation** — Core framework, data layer, CLI, SDK, scRNA-seq pipeline operational.

## Quick Start

```bash
# Install (conda recommended)
conda env create -f environment.yaml
conda activate omics-platform
pip install -e .

# Verify installation
omics --help
omics gpu status

# Quick scRNA-seq analysis
omics data import scrna path/to/sample.h5ad
omics scrna pipeline --input sample.h5ad --gpu

# Using the SDK
python -c "from omics import OmicsSDK; sdk = OmicsSDK(); print(sdk.gpu.summary())"
```

## Project Structure

```
omics-platform/
├── core/              # Config, GPU, pipeline, registry, cache
├── data_layer/        # AnnData/MuData builders, validators
├── plugins/           # Analysis plugins (modular, extensible)
│   ├── scrna/         # scRNA-seq plugins
│   ├── spatial/       # Spatial transcriptomics plugins
│   ├── amplicon/      # 16S rRNA plugins
│   ├── metagenomics/   # Metagenomics plugins
│   ├── integration/   # Multi-omics integration plugins
│   └── visualization/ # Figure generation plugins
├── viz/               # Visualization themes, multi-panel assembly
├── web_ui/            # Streamlit web application
├── cli.py             # CLI entry point
├── sdk.py             # Python SDK
└── projects/          # User project directories
```

## Architecture

- **Unified Data Model**: All modalities map to AnnData with standardized slots; multi-omics uses MuData.
- **Plugin Architecture**: Add new analysis methods as self-contained plugins — auto-discovered, no core code changes.
- **GPU Acceleration**: rapids_singlecell + scvi-tools + PyTorch for 10-15x speedups.
- **External Tool Wrappers**: QIIME2, Kraken2, HUMAnN3 integrated via subprocess wrappers.
- **Three Entry Points**: CLI (automation) + SDK (notebooks) + Streamlit Web UI (interactive).

## License

MIT
