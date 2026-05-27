"""Tool schema generation for LLM agents (OpenAI/Claude function calling format).

Each tool maps to a function in omics.scrna.*, omics.data.*, omics.viz.*, etc.
"""

from __future__ import annotations


def create_omics_tools_schema() -> list[dict]:
    """Generate JSON tool schema for LLM function calling."""

    tools = [
        # -- Data --
        {
            "name": "omics_data_info",
            "description": "Inspect an AnnData (.h5ad) or MuData (.h5mu) file: shape, available slots, gene/cell counts, basic statistics. Always run this first when given a new data file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to .h5ad or .h5mu file"}
                },
                "required": ["path"],
            },
        },
        {
            "name": "omics_data_import",
            "description": "Import data into the omics platform. Supports 10X Genomics (mtx/h5), Visium, h5ad, CSV/TSV, and more.",
            "parameters": {
                "type": "object",
                "properties": {
                    "modality": {"type": "string", "enum": ["scrna", "spatial", "amplicon", "metagenomics"]},
                    "input": {"type": "string", "description": "Path to input file or directory"}
                },
                "required": ["modality", "input"],
            },
        },
        {
            "name": "omics_data_fetch",
            "description": "Download a public dataset from GEO/SRA by accession number and convert to AnnData.",
            "parameters": {
                "type": "object",
                "properties": {
                    "accession": {"type": "string", "description": "GEO accession (e.g., GSE123456)"},
                    "output_dir": {"type": "string", "description": "Directory for downloaded files", "default": "data/raw"},
                },
                "required": ["accession"],
            },
        },
        {
            "name": "omics_data_search",
            "description": "Search GEO for public datasets by keyword (e.g., 'PBMC scRNA-seq', 'lung cancer single cell').",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Max results", "default": 20},
                },
                "required": ["query"],
            },
        },
        # -- scRNA Analysis --
        {
            "name": "omics_scrna_qc",
            "description": "Quality control: filter cells by min_genes/max_pct_mt, filter genes by min_cells.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "output": {"type": "string", "description": "Output path", "default": "qc_filtered.h5ad"},
                    "min_genes": {"type": "integer", "default": 200},
                    "min_cells": {"type": "integer", "default": 3},
                    "max_pct_mt": {"type": "number", "default": 20.0},
                },
                "required": ["input"],
            },
        },
        {
            "name": "omics_scrna_normalize",
            "description": "Normalize total counts per cell and log1p transform.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "output": {"type": "string", "description": "Output path"},
                    "target_sum": {"type": "integer", "default": 10000},
                },
                "required": ["input"],
            },
        },
        {
            "name": "omics_scrna_reduce",
            "description": "Dimensionality reduction: PCA + neighbors + UMAP in one step.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "output": {"type": "string", "description": "Output path"},
                    "n_pcs": {"type": "integer", "default": 50},
                    "n_neighbors": {"type": "integer", "default": 15},
                },
                "required": ["input"],
            },
        },
        {
            "name": "omics_scrna_cluster",
            "description": "Leiden clustering at given resolution (higher = more clusters).",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "output": {"type": "string", "description": "Output path"},
                    "resolution": {"type": "number", "default": 1.0},
                },
                "required": ["input"],
            },
        },
        {
            "name": "omics_scrna_markers",
            "description": "Find marker genes per cluster using Wilcoxon rank-sum. Returns top genes per group to CSV.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "group_by": {"type": "string", "default": "leiden"},
                    "n_genes": {"type": "integer", "default": 100},
                    "output": {"type": "string", "description": "CSV output path"},
                },
                "required": ["input"],
            },
        },
        {
            "name": "omics_scrna_annotate",
            "description": "Annotate cell types using marker-based scoring or CellTypist models.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "method": {"type": "string", "enum": ["marker_based", "celltypist"], "default": "marker_based"},
                    "cluster_key": {"type": "string", "default": "leiden"},
                },
                "required": ["input"],
            },
        },
        {
            "name": "omics_scrna_trajectory",
            "description": "Trajectory/pseudotime analysis: Diffusion Pseudotime (DPT), PAGA, or RNA velocity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "method": {"type": "string", "enum": ["dpt", "paga", "velocity"], "default": "dpt"},
                },
                "required": ["input"],
            },
        },
        {
            "name": "omics_scrna_cell_communication",
            "description": "Ligand-receptor cell communication analysis with curated LR pairs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "cluster_key": {"type": "string", "default": "leiden"},
                },
                "required": ["input"],
            },
        },
        # -- Pipeline --
        {
            "name": "omics_pipeline_run",
            "description": "Run full scRNA-seq pipeline: QC -> normalize -> HVG -> PCA -> UMAP -> cluster -> markers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "output_dir": {"type": "string", "default": "."},
                    "use_gpu": {"type": "boolean", "default": False},
                },
                "required": ["input"],
            },
        },
        # -- Visualization --
        {
            "name": "omics_visualize_umap",
            "description": "Generate a UMAP embedding plot colored by a metadata column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "color": {"type": "string", "default": "leiden"},
                    "output": {"type": "string", "description": "Output figure path (pdf/png/svg)"},
                },
                "required": ["input"],
            },
        },
        {
            "name": "omics_compose_figure",
            "description": "Compose a publication-ready multi-panel figure from a template. Templates: cell_type_atlas, differential_response, trajectory_analysis, qc_report, integration_overview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "template": {"type": "string", "enum": ["cell_type_atlas", "differential_response", "trajectory_analysis", "integration_overview", "qc_report"], "default": "cell_type_atlas"},
                    "output": {"type": "string", "description": "Output figure path (PDF recommended)", "default": "figure1.pdf"},
                },
                "required": ["input"],
            },
        },
        # -- Interpretation --
        {
            "name": "omics_ask_question",
            "description": "Interpret a natural language biological question and propose a concrete analysis plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Biological question in natural language"},
                    "input": {"type": "string", "description": "Optional path to .h5ad for data-aware recommendations"},
                },
                "required": ["question"],
            },
        },
        {
            "name": "omics_explain_results",
            "description": "Run biological interpretation: gene set enrichment, cell type matching, pathway analysis. Generates a natural language summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad with analysis results"},
                    "groupby": {"type": "string", "default": "leiden"},
                },
                "required": ["input"],
            },
        },
        # -- System --
        {
            "name": "omics_gpu_status",
            "description": "Check GPU availability, VRAM, and recommended settings.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "omics_config",
            "description": "View or set platform configuration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Config key to set (e.g., 'gpu.auto_fallback')"},
                    "value": {"type": "string", "description": "Value to set"},
                },
            },
        },
        # -- Bulk RNA-seq --
        {
            "name": "omics_bulk_import",
            "description": "Load bulk RNA-seq count matrix (STAR/RSEM/kallisto/HTSeq output, CSV or TSV). First column = gene IDs, remaining columns = sample counts.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path to count matrix file (CSV or TSV)"}}, "required": ["path"]},
        },
        {
            "name": "omics_bulk_de",
            "description": "Differential expression analysis via DESeq2 (default). Requires design formula and contrast. Returns log2FC, p-value, adjusted p-value per gene.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}, "design": {"type": "string", "description": "R formula, e.g. '~condition'"}, "contrast": {"type": "array", "items": {"type": "string"}, "description": "[variable, numerator, denominator] e.g. ['condition','tumor','normal']"}}, "required": ["input", "design", "contrast"]},
        },
        {
            "name": "omics_bulk_enrich",
            "description": "Gene set enrichment analysis via GSEApy. Supports GO, KEGG, MSigDB, Reactome gene sets.",
            "parameters": {"type": "object", "properties": {"de_results_path": {"type": "string", "description": "Path to DE results CSV"}, "gene_sets": {"type": "string", "enum": ["GO", "KEGG", "MSigDB"], "default": "GO"}}, "required": ["de_results_path"]},
        },
        {
            "name": "omics_bulk_visualize",
            "description": "Generate publication-ready plots from bulk RNA-seq data: volcano plot, heatmap, or PCA.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad or DE CSV"}, "plot_type": {"type": "string", "enum": ["volcano", "heatmap", "pca"], "default": "volcano"}, "gene_list": {"type": "array", "items": {"type": "string"}, "description": "Gene names for heatmap"}, "output": {"type": "string", "description": "Output figure path (pdf/png)"}}, "required": ["input", "plot_type"]},
        },
        {
            "name": "omics_bulk_pipeline",
            "description": "One-click bulk RNA-seq workflow: load counts -> QC filter -> normalize -> DE -> enrichment -> volcano plot.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to count matrix"}, "design": {"type": "string", "description": "R formula e.g. '~condition'"}, "contrast": {"type": "array", "items": {"type": "string"}, "description": "[variable, numerator, denominator]"}, "output_dir": {"type": "string", "default": "."}}, "required": ["input", "design", "contrast"]},
        },
        # -- Spatial --
        {
            "name": "omics_spatial_import",
            "description": "Load spatial transcriptomics data (10x Visium, MERFISH) into AnnData.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path to Visium output directory or .h5ad file"}, "modality": {"type": "string", "enum": ["visium", "merfish"], "default": "visium"}}, "required": ["path"]},
        },
        {
            "name": "omics_spatial_qc",
            "description": "Quality control for spatial data: filter spots by counts, filter genes, compute QC metrics via Squidpy.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}, "min_counts": {"type": "integer", "default": 100}, "min_spots": {"type": "integer", "default": 3}, "max_pct_mt": {"type": "number", "default": 20.0}}, "required": ["input"]},
        },
        {
            "name": "omics_spatial_cluster",
            "description": "Spatial-aware clustering: spatial neighbors -> PCA -> leiden -> UMAP.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}, "resolution": {"type": "number", "default": 1.0}, "n_neighbors": {"type": "integer", "default": 15}}, "required": ["input"]},
        },
        {
            "name": "omics_spatial_deconvolve",
            "description": "Cell-type deconvolution from spatial spots using cell2location with a scRNA-seq reference.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to spatial .h5ad file"}, "reference": {"type": "string", "description": "Path to scRNA-seq reference .h5ad file"}}, "required": ["input", "reference"]},
        },
        {
            "name": "omics_spatial_niche",
            "description": "Cellular neighborhood / niche analysis via Squidpy nhood_enrichment.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}, "cluster_key": {"type": "string", "default": "leiden"}}, "required": ["input"]},
        },
        {
            "name": "omics_spatial_lr",
            "description": "Spatially-aware ligand-receptor interaction analysis via Squidpy ligrec.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}, "cluster_key": {"type": "string", "default": "leiden"}}, "required": ["input"]},
        },
        {
            "name": "omics_spatial_svg",
            "description": "Detect spatially variable genes (SVGs) using SPARK-X with Squidpy Moran's I fallback.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}}, "required": ["input"]},
        },
        # -- TCR/BCR --
        {
            "name": "omics_tcr_load",
            "description": "Load TCR/BCR immune repertoire data (10X VDJ, MiXCR output, AIRR format, TRUST4).",
            "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Path to VDJ data file or directory"}}, "required": ["path"]},
        },
        {
            "name": "omics_tcr_clonotypes",
            "description": "Define clonotypes from CDR3 sequences and analyze clonal expansion.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file with TCR data"}}, "required": ["input"]},
        },
        {
            "name": "omics_tcr_diversity",
            "description": "Compute immune repertoire diversity metrics: Shannon, Simpson, Inverse Simpson, D50, Chao1.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}}, "required": ["input"]},
        },
        {
            "name": "omics_tcr_vj_usage",
            "description": "Analyze V and J gene segment usage frequency in TCR/BCR repertoire.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}}, "required": ["input"]},
        },
        {
            "name": "omics_tcr_overlap",
            "description": "Compute clonotype overlap (Jaccard index) between multiple samples.",
            "parameters": {"type": "object", "properties": {"inputs": {"type": "array", "items": {"type": "string"}, "description": "List of paths to .h5ad files"}}, "required": ["inputs"]},
        },
        {
            "name": "omics_tcr_integrate",
            "description": "Merge TCR clonotype information into scRNA-seq AnnData, linking immune repertoire to transcriptome.",
            "parameters": {"type": "object", "properties": {"tcr_input": {"type": "string", "description": "Path to TCR .h5ad"}, "scrna_input": {"type": "string", "description": "Path to scRNA-seq .h5ad"}}, "required": ["tcr_input", "scrna_input"]},
        },
        # -- Scoring --
        {
            "name": "omics_score_immune",
            "description": "Compute immune infiltration score from scRNA-seq data using canonical marker genes for 10 immune cell types.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}}, "required": ["input"]},
        },
        {
            "name": "omics_score_pathway",
            "description": "Compute pathway activity score across 14 cancer-relevant pathways (PROGENy gene sets).",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}}, "required": ["input"]},
        },
        {
            "name": "omics_score_clonality",
            "description": "Compute clonal expansion score from TCR/BCR repertoire diversity and expansion metrics.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file with TCR data"}}, "required": ["input"]},
        },
        {
            "name": "omics_score_spatial",
            "description": "Compute spatial niche heterogeneity score from spatial transcriptomics data.",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}}, "required": ["input"]},
        },
        {
            "name": "omics_score_drug",
            "description": "Predict drug response score from multi-omics features. (Placeholder for GDSC/DepMap-trained model integration.)",
            "parameters": {"type": "object", "properties": {"input": {"type": "string", "description": "Path to .h5ad file"}}, "required": ["input"]},
        },
        {
            "name": "omics_score_integrated",
            "description": "Compute AI-weighted composite multi-omics health score by fusing all per-modality scores into a unified biological narrative.",
            "parameters": {"type": "object", "properties": {"modality_scores": {"type": "object", "description": "JSON object mapping modality names to score values"}}, "required": ["modality_scores"]},
        },
    ]
    return tools
