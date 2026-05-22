"""Tool schema generation for LLM agents (OpenAI/Claude function calling format).

Each tool maps to a function in omics.scrna.*, omics.data.*, omics.viz.*, etc.
"""


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
    ]
    return tools
