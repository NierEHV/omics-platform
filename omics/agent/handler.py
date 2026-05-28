"""Omics Agent Handler — bridges omics-platform capabilities into LLM agent tools.

Each do_omics_* method is a tool the LLM can call. All methods delegate to
omics.scrna.* / omics.data.* / omics.viz.* functions directly — no subprocess,
no ad-hoc code strings.

Usage:
    from omics.agent.handler import OmicsAgentHandler, create_omics_tools_schema

    handler = OmicsAgentHandler()
    tools = create_omics_tools_schema()
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Optional GenericAgent integration
try:
    from agent_loop import BaseHandler, StepOutcome
    _HAS_GA = True
except ImportError:
    _HAS_GA = False

    class StepOutcome:
        def __init__(self, data, next_prompt="\n", should_exit=False):
            self.data = data
            self.next_prompt = next_prompt
            self.should_exit = should_exit

    class BaseHandler:
        pass


# ── Tool decorator: eliminates ~60% duplication across 43 do_omics_* methods ──

def _omics_tool(input_key=None, input_keys=None, required_params=None):
    """Decorator that handles path resolution, file validation, try/except,
    and StepOutcome construction for omics tool handlers.

    Usage:
        @_omics_tool(input_key="input")
        def do_omics_xxx(self, args, response):
            # just the domain logic
            return {"score": 0.8, "msg": "done"}

        @_omics_tool(input_keys=["input", "reference"])
        def do_omics_xxx(self, args, response):
            # validates both input and reference paths exist
            return {"msg": "done"}
    """
    def decorator(func):
        def wrapper(self, args, response):
            if required_params:
                for p in required_params:
                    if p not in args:
                        return StepOutcome(
                            {"status": "error", "msg": f"Missing required param: {p}"},
                            next_prompt="\n",
                        )
            for key in (input_keys or []):
                path = self._resolve(args.get(key, ""))
                if not path or not os.path.exists(path):
                    return StepOutcome(
                        {"status": "error", "msg": f"File not found: {path}"},
                        next_prompt="\n",
                    )
            if input_key:
                path = self._resolve(args.get(input_key, ""))
                if not path or not os.path.exists(path):
                    return StepOutcome(
                        {"status": "error", "msg": f"File not found: {path}"},
                        next_prompt="\n",
                    )
            try:
                result = func(self, args, response)
                if isinstance(result, dict):
                    result.setdefault("status", "success")
                    return StepOutcome(result, next_prompt="\n")
                return result
            except Exception as e:
                return StepOutcome(
                    {"status": "error", "msg": str(e)}, next_prompt="\n"
                )
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


class OmicsAgentHandler(BaseHandler):
    """Agent handler exposing multi-omics analysis as callable tools."""

    def __init__(self, parent=None, cwd: str = "."):
        if _HAS_GA:
            super().__init__()
        self.parent = parent
        self.cwd = os.path.abspath(cwd)
        self.working: dict[str, Any] = {}
        self.history_info: list[str] = []
        self.current_turn = 0
        self.max_turns = 70

    def _resolve(self, path: str) -> str:
        if not path:
            return ""
        p = Path(path)
        return str(p if p.is_absolute() else Path(self.cwd) / p)

    # ── Data Tools ──

    @_omics_tool(input_key="path")
    def do_omics_data_info(self, args: dict, response) -> StepOutcome:
        from omics.utils.io import get_adata_summary, read_h5ad
        adata = read_h5ad(Path(self._resolve(args["path"])))
        summary = get_adata_summary(adata)
        return {"summary": summary}

    @_omics_tool(input_key="input")
    def do_omics_data_import(self, args: dict, response) -> StepOutcome:
        modality = args.get("modality", "scrna")
        from omics.sdk import OmicsSDK
        sdk = OmicsSDK()
        if modality == "scrna":
            adata = sdk.data.import_scrna(self._resolve(args["input"]))
        elif modality == "spatial":
            adata = sdk.data.import_spatial(self._resolve(args["input"]))
        else:
            return {"status": "error", "msg": f"Unsupported modality: {modality}"}
        return {
            "n_obs": adata.n_obs,
            "n_vars": adata.n_vars,
            "msg": f"Imported {modality}: {adata.n_obs} cells x {adata.n_vars} genes",
        }

    @_omics_tool(required_params=["accession"])
    def do_omics_data_fetch(self, args: dict, response) -> StepOutcome:
        from omics.sdk import OmicsSDK
        sdk = OmicsSDK()
        adata = sdk.data.fetch_geo(args["accession"], Path(args.get("output_dir", "data/raw")))
        return {
            "n_obs": adata.n_obs,
            "n_vars": adata.n_vars,
            "msg": f"Fetched {args['accession']}: {adata.n_obs} samples x {adata.n_vars} genes",
        }

    @_omics_tool(required_params=["query"])
    def do_omics_data_search(self, args: dict, response) -> StepOutcome:
        from omics.sdk import OmicsSDK
        sdk = OmicsSDK()
        results = sdk.data.search_geo(args["query"], args.get("max_results", 20))
        rows = [[r.accession, r.title[:60], str(r.n_samples), r.organism, r.platform[:30]] for r in results]
        return {"total": len(results), "results": rows}

    # ── scRNA-seq Tools ──

    @_omics_tool(input_key="input")
    def do_omics_scrna_qc(self, args: dict, response) -> StepOutcome:
        from omics.scrna.qc import run_qc
        from omics.utils.io import read_h5ad, write_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        adata = run_qc(adata, min_genes=args.get("min_genes", 200),
                       min_cells=args.get("min_cells", 3),
                       max_pct_mt=args.get("max_pct_mt", 20.0))
        output = self._resolve(args.get("output", "qc_filtered.h5ad"))
        write_h5ad(adata, Path(output))
        return {
            "n_obs": adata.n_obs, "n_vars": adata.n_vars,
            "msg": f"QC complete: {adata.n_obs} cells, {adata.n_vars} genes -> {output}",
        }

    @_omics_tool(input_key="input")
    def do_omics_scrna_normalize(self, args: dict, response) -> StepOutcome:
        from omics.scrna.normalize import run_normalize
        from omics.utils.io import read_h5ad, write_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        adata = run_normalize(adata, target_sum=args.get("target_sum", 10000))
        output = self._resolve(args.get("output", ""))
        if output:
            write_h5ad(adata, Path(output))
        return {"msg": f"Normalized: {adata.n_obs} cells"}

    @_omics_tool(input_key="input")
    def do_omics_scrna_reduce(self, args: dict, response) -> StepOutcome:
        from omics.scrna.pca import run_pca
        from omics.scrna.neighbors import run_neighbors
        from omics.scrna.umap import run_umap
        from omics.utils.io import read_h5ad, write_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        adata = run_pca(adata, n_comps=args.get("n_pcs", 50))
        adata = run_neighbors(adata, n_neighbors=args.get("n_neighbors", 15))
        adata = run_umap(adata)
        output = self._resolve(args.get("output", ""))
        if output:
            write_h5ad(adata, Path(output))
        return {"msg": f"PCA+UMAP complete: {adata.n_obs} cells"}

    @_omics_tool(input_key="input")
    def do_omics_scrna_cluster(self, args: dict, response) -> StepOutcome:
        from omics.scrna.cluster import run_leiden
        from omics.utils.io import read_h5ad, write_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        resolution = args.get("resolution", 1.0)
        adata = run_leiden(adata, resolution=resolution)
        n = adata.obs["leiden"].nunique()
        output = self._resolve(args.get("output", ""))
        if output:
            write_h5ad(adata, Path(output))
        return {
            "n_clusters": n,
            "msg": f"Clustering: {n} clusters at resolution={resolution}",
        }

    @_omics_tool(input_key="input")
    def do_omics_scrna_markers(self, args: dict, response) -> StepOutcome:
        from omics.scrna.markers import run_markers, get_marker_table
        from omics.utils.io import read_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        group_by = args.get("group_by", "leiden")
        n_genes = args.get("n_genes", 100)
        adata = run_markers(adata, groupby=group_by, n_genes=n_genes)
        df = get_marker_table(adata)
        top5 = df[df["pval_adj"] < 0.05].groupby("group").head(5) if "pval_adj" in df.columns else df.head(20)
        return {
            "n_genes": len(df),
            "top_markers": top5.to_dict(orient="records")[:30],
        }

    @_omics_tool(input_key="input")
    def do_omics_scrna_annotate(self, args: dict, response) -> StepOutcome:
        from omics.scrna.annotation import run_marker_annotation, run_celltypist
        from omics.utils.io import read_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        method = args.get("method", "marker_based")
        if method == "celltypist":
            adata = run_celltypist(adata)
            label_col = "celltypist_label"
        else:
            adata = run_marker_annotation(adata, cluster_key=args.get("cluster_key", "leiden"))
            label_col = "marker_based_label"
        counts = adata.obs[label_col].value_counts().to_dict() if label_col in adata.obs else {}
        return {
            "n_cell_types": len(counts),
            "label_column": label_col,
            "cell_type_counts": {str(k): v for k, v in counts.items()},
        }

    @_omics_tool(input_key="input")
    def do_omics_scrna_trajectory(self, args: dict, response) -> StepOutcome:
        from omics.scrna.trajectory import run_dpt, run_paga, run_velocity
        from omics.utils.io import read_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        method = args.get("method", "dpt")
        if method == "dpt":
            adata = run_dpt(adata)
        elif method == "paga":
            adata = run_paga(adata)
        elif method == "velocity":
            adata = run_velocity(adata)
        has_pt = "dpt_pseudotime" in adata.obs
        return {
            "method": method,
            "has_pseudotime": has_pt,
            "msg": f"Trajectory ({method}) complete",
        }

    @_omics_tool(input_key="input")
    def do_omics_scrna_cell_communication(self, args: dict, response) -> StepOutcome:
        from omics.scrna.communication import run_lr_analysis
        from omics.utils.io import read_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        adata = run_lr_analysis(adata, cluster_key=args.get("cluster_key", "leiden"))
        return {"msg": "Cell communication analysis complete"}

    # ── Pipeline ──

    @_omics_tool(input_key="input")
    def do_omics_pipeline_run(self, args: dict, response) -> StepOutcome:
        from omics.scrna.pipeline import run_standard_pipeline
        from omics.utils.io import read_h5ad, write_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        adata = run_standard_pipeline(adata, use_gpu=args.get("use_gpu", False))
        p = Path(self._resolve(args["input"]))
        output_dir = self._resolve(args.get("output_dir", "."))
        out = Path(output_dir) / f"{p.stem}_processed.h5ad"
        write_h5ad(adata, out)
        n_clusters = adata.obs["leiden"].nunique() if "leiden" in adata.obs else 0
        return {
            "n_obs": adata.n_obs,
            "n_vars": adata.n_vars,
            "n_clusters": n_clusters,
            "obsm_keys": list(adata.obsm.keys()),
            "output": str(out),
        }

    # ── Visualization ──

    @_omics_tool(input_key="input")
    def do_omics_visualize_umap(self, args: dict, response) -> StepOutcome:
        from omics.sdk import VizSDK
        from omics.utils.io import read_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        sdk_viz = VizSDK(None)
        color = args.get("color", "leiden")
        output = self._resolve(args.get("output", "umap.pdf"))
        sdk_viz.umap(adata, color=color, output_path=output)
        return {"output": output, "color": color}

    @_omics_tool(input_key="input")
    def do_omics_compose_figure(self, args: dict, response) -> StepOutcome:
        from omics.sdk import VizSDK
        from omics.utils.io import read_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        sdk_viz = VizSDK(None)
        template = args.get("template", "cell_type_atlas")
        output = self._resolve(args.get("output", "figure1.pdf"))
        sdk_viz.compose(template, adata, output_path=Path(output))
        return {"output": output, "template": template}

    # ── Interpretation ──

    @_omics_tool(required_params=["question"])
    def do_omics_ask_question(self, args: dict, response) -> StepOutcome:
        from omics.agent.semantic import AnalysisPlanner, get_planner
        planner = get_planner()
        profile = None
        input_path = self._resolve(args.get("input", ""))
        if input_path and os.path.exists(input_path):
            from omics.utils.io import read_h5ad
            adata = read_h5ad(Path(input_path))
            profile = planner.create_profile(adata)
        plan = planner.plan_analysis(args["question"], profile)
        return {
            "plan": plan.to_dict(),
            "markdown": plan.to_markdown(),
            "n_steps": len(plan.steps),
            "primary_intent": plan.intent.primary_intent.value,
        }

    @_omics_tool(input_key="input")
    def do_omics_explain_results(self, args: dict, response) -> StepOutcome:
        from omics.utils.io import read_h5ad
        from omics.knowledge.engine import KnowledgeEngine
        adata = read_h5ad(Path(self._resolve(args["input"])))
        engine = KnowledgeEngine()
        kc = engine.run_on_results(adata, groupby=args.get("groupby", "leiden"))
        return {
            "summary": kc.to_markdown(),
            "top_pathways": [
                {"name": r.gene_set_name, "database": r.database, "p_adj": r.adjusted_p_value}
                for r in kc.enrichment_results[:5]
            ],
            "cell_type_matches": [
                {"cluster": m.query_cluster, "matched_type": m.matched_cell_type,
                 "jaccard": m.jaccard_index, "supporting_genes": m.supporting_genes[:5]}
                for m in kc.cell_type_matches[:10]
            ],
        }

    # ── System ──

    @_omics_tool()
    def do_omics_gpu_status(self, args: dict, response) -> StepOutcome:
        from omics.gpu.manager import get_gpu_manager
        gm = get_gpu_manager()
        info = gm.summary()
        return {"gpu_info": info}

    @_omics_tool()
    def do_omics_config(self, args: dict, response) -> StepOutcome:
        from omics.utils.config import Config, _dataclass_to_dict
        cfg = Config.load()
        key = args.get("key", "")
        value = args.get("value", "")
        if key and value:
            keys = key.split(".")
            target = cfg
            for k in keys[:-1]:
                target = getattr(target, k)
            setattr(target, keys[-1], value)
            cfg.save()
            return {"msg": f"Config updated: {key} = {value}"}
        return {"config": _dataclass_to_dict(cfg)}

    # ── Bulk RNA-seq Tools ──

    @_omics_tool(input_key="path")
    def do_omics_bulk_import(self, args: dict, response) -> StepOutcome:
        from omics.bulk.analysis import BulkRNAAnalysis
        b = BulkRNAAnalysis()
        adata = b.load_counts(self._resolve(args["path"]))
        return {
            "n_samples": adata.n_obs,
            "n_genes": adata.n_vars,
            "msg": f"Loaded {adata.n_obs} samples x {adata.n_vars} genes",
        }

    @_omics_tool(input_key="input", required_params=["design", "contrast"])
    def do_omics_bulk_de(self, args: dict, response) -> StepOutcome:
        import anndata
        from omics.bulk.analysis import BulkRNAAnalysis
        b = BulkRNAAnalysis()
        adata = anndata.read_h5ad(self._resolve(args["input"]))
        de = b.differential_expression(adata, args["design"], tuple(args["contrast"]))
        n_sig = int((de["padj"] < 0.05).sum()) if "padj" in de.columns else 0
        return {
            "n_genes": len(de),
            "n_significant": n_sig,
            "top_genes": de.head(10).index.tolist(),
            "msg": f"DE complete: {n_sig} significant genes",
        }

    @_omics_tool(input_key="de_results_path")
    def do_omics_bulk_enrich(self, args: dict, response) -> StepOutcome:
        import pandas as pd
        from omics.bulk.analysis import BulkRNAAnalysis
        b = BulkRNAAnalysis()
        gene_sets = args.get("gene_sets", "GO")
        de_results = pd.read_csv(self._resolve(args["de_results_path"]))
        enrich = b.enrichment(de_results, gene_sets=gene_sets)
        n_pathways = len(enrich) if hasattr(enrich, "__len__") else 0
        return {
            "gene_sets": gene_sets,
            "n_pathways": n_pathways,
            "top_results": enrich.head(10).to_dict(orient="records") if hasattr(enrich, "head") else [],
            "msg": f"GSEA complete using {gene_sets}",
        }

    @_omics_tool(input_key="input")
    def do_omics_bulk_visualize(self, args: dict, response) -> StepOutcome:
        from omics.bulk.visualization import BulkViz
        bv = BulkViz()
        plot_type = args.get("plot_type", "volcano")
        output = self._resolve(args.get("output", f"bulk_{plot_type}.pdf"))
        gene_list = args.get("gene_list")
        bv.plot(self._resolve(args["input"]), plot_type=plot_type,
                gene_list=gene_list, output=output)
        return {
            "plot_type": plot_type,
            "output": output,
            "msg": f"{plot_type} plot saved to {output}",
        }

    @_omics_tool(input_key="input", required_params=["design", "contrast"])
    def do_omics_bulk_pipeline(self, args: dict, response) -> StepOutcome:
        from omics.bulk.pipeline import run_bulk_pipeline
        output_dir = self._resolve(args.get("output_dir", "."))
        result = run_bulk_pipeline(
            self._resolve(args["input"]),
            design=args["design"],
            contrast=tuple(args["contrast"]),
            output_dir=Path(output_dir),
        )
        return {
            "n_de_genes": result.get("n_de_genes", 0),
            "n_significant": result.get("n_significant", 0),
            "output_dir": str(output_dir),
            "msg": "Bulk RNA-seq pipeline complete",
        }

    # ── Spatial Tools ──

    @_omics_tool(input_key="path")
    def do_omics_spatial_import(self, args: dict, response) -> StepOutcome:
        from omics.spatial.io import import_spatial
        modality = args.get("modality", "visium")
        adata = import_spatial(self._resolve(args["path"]), modality=modality)
        return {
            "n_spots": adata.n_obs,
            "n_genes": adata.n_vars,
            "modality": modality,
            "msg": f"Imported {modality}: {adata.n_obs} spots x {adata.n_vars} genes",
        }

    @_omics_tool(input_key="input")
    def do_omics_spatial_qc(self, args: dict, response) -> StepOutcome:
        from omics.spatial.qc import run_spatial_qc
        from omics.utils.io import read_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        adata = run_spatial_qc(adata, min_counts=args.get("min_counts", 100),
                               min_spots=args.get("min_spots", 3),
                               max_pct_mt=args.get("max_pct_mt", 20.0))
        return {
            "n_spots": adata.n_obs,
            "n_genes": adata.n_vars,
            "msg": f"Spatial QC complete: {adata.n_obs} spots x {adata.n_vars} genes",
        }

    @_omics_tool(input_key="input")
    def do_omics_spatial_cluster(self, args: dict, response) -> StepOutcome:
        from omics.spatial.analysis import run_spatial_cluster
        from omics.utils.io import read_h5ad
        adata = read_h5ad(Path(self._resolve(args["input"])))
        adata = run_spatial_cluster(adata, resolution=args.get("resolution", 1.0),
                                     n_neighbors=args.get("n_neighbors", 15))
        n_clusters = adata.obs["leiden"].nunique() if "leiden" in adata.obs else 0
        return {"n_clusters": n_clusters, "msg": f"Spatial clustering: {n_clusters} clusters"}

    @_omics_tool(input_keys=["input", "reference"])
    def do_omics_spatial_deconvolve(self, args: dict, response) -> StepOutcome:
        from omics.spatial.deconvolution import run_cell2location
        adata = run_cell2location(
            self._resolve(args["input"]), self._resolve(args["reference"]))
        n_types = adata.uns.get("n_cell_types", 0) if hasattr(adata, "uns") else 0
        return {
            "n_cell_types": n_types,
            "msg": f"Spatial deconvolution complete: {n_types} cell types",
        }

    @_omics_tool(input_key="input")
    def do_omics_spatial_niche(self, args: dict, response) -> StepOutcome:
        from omics.spatial.analysis import run_niche_analysis
        cluster_key = args.get("cluster_key", "leiden")
        result = run_niche_analysis(self._resolve(args["input"]), cluster_key=cluster_key)
        return {
            "cluster_key": cluster_key,
            "n_niches": result.get("n_niches", 0),
            "msg": f"Niche analysis complete: {result.get('n_niches', 0)} niches",
        }

    @_omics_tool(input_key="input")
    def do_omics_spatial_lr(self, args: dict, response) -> StepOutcome:
        from omics.spatial.analysis import run_spatial_lr
        cluster_key = args.get("cluster_key", "leiden")
        result = run_spatial_lr(self._resolve(args["input"]), cluster_key=cluster_key)
        return {
            "n_interactions": result.get("n_interactions", 0),
            "msg": f"Spatial LR analysis: {result.get('n_interactions', 0)} interactions",
        }

    @_omics_tool(input_key="input")
    def do_omics_spatial_svg(self, args: dict, response) -> StepOutcome:
        from omics.spatial.analysis import detect_spatial_variable_genes
        result = detect_spatial_variable_genes(self._resolve(args["input"]))
        return {
            "n_svg": result.get("n_svg", 0),
            "top_genes": result.get("top_genes", [])[:10],
            "msg": f"SVG detection: {result.get('n_svg', 0)} genes",
        }

    # ── TCR/BCR Tools ──

    @_omics_tool(input_key="path")
    def do_omics_tcr_load(self, args: dict, response) -> StepOutcome:
        from omics.tcr.io import load_tcr_data
        adata = load_tcr_data(self._resolve(args["path"]))
        return {
            "n_cells": adata.n_obs,
            "msg": f"Loaded TCR/BCR data: {adata.n_obs} cells",
        }

    @_omics_tool(input_key="input")
    def do_omics_tcr_clonotypes(self, args: dict, response) -> StepOutcome:
        from omics.tcr.analysis import define_clonotypes
        import anndata
        adata = anndata.read_h5ad(self._resolve(args["input"]))
        adata = define_clonotypes(adata)
        n_clonotypes = adata.obs["clonotype_id"].nunique() if "clonotype_id" in adata.obs else 0
        return {
            "n_clonotypes": n_clonotypes,
            "msg": f"Clonotype analysis: {n_clonotypes} clonotypes",
        }

    @_omics_tool(input_key="input")
    def do_omics_tcr_diversity(self, args: dict, response) -> StepOutcome:
        from omics.tcr.analysis import compute_diversity
        import anndata
        adata = anndata.read_h5ad(self._resolve(args["input"]))
        metrics = compute_diversity(adata)
        return {
            "diversity_metrics": metrics,
            "msg": f"Diversity: Shannon={metrics.get('shannon', 'N/A')}",
        }

    @_omics_tool(input_key="input")
    def do_omics_tcr_vj_usage(self, args: dict, response) -> StepOutcome:
        from omics.tcr.analysis import TCRAnalysis
        import anndata
        adata = anndata.read_h5ad(self._resolve(args["input"]))
        result = TCRAnalysis().vj_usage(adata)
        return {
            "v_usage": result.to_dict() if hasattr(result, "to_dict") else str(result),
            "msg": "V-J usage analysis complete",
        }

    @_omics_tool(required_params=["inputs"])
    def do_omics_tcr_overlap(self, args: dict, response) -> StepOutcome:
        from omics.tcr.analysis import TCRAnalysis
        import anndata
        adatas = [anndata.read_h5ad(self._resolve(p)) for p in args["inputs"]]
        overlap_matrix = TCRAnalysis().clonotype_overlap(adatas)
        return {
            "n_samples": len(args["inputs"]),
            "overlap_matrix": overlap_matrix.tolist() if hasattr(overlap_matrix, "tolist") else overlap_matrix,
            "msg": f"Clonotype overlap computed for {len(args['inputs'])} samples",
        }

    @_omics_tool(input_keys=["tcr_input", "scrna_input"])
    def do_omics_tcr_integrate(self, args: dict, response) -> StepOutcome:
        from omics.tcr.analysis import TCRAnalysis
        import anndata
        tcr_adata = anndata.read_h5ad(self._resolve(args["tcr_input"]))
        scrna_adata = anndata.read_h5ad(self._resolve(args["scrna_input"]))
        adata = TCRAnalysis().integrate_with_scrna(tcr_adata, scrna_adata)
        return {
            "n_cells": adata.n_obs,
            "n_genes": adata.n_vars,
            "msg": f"TCR-scRNA integration: {adata.n_obs} cells x {adata.n_vars} genes",
        }

    # ── Scoring Tools ──

    @_omics_tool(input_key="input")
    def do_omics_score_immune(self, args: dict, response) -> StepOutcome:
        from omics.score.scorers import ImmuneInfiltrationScore
        import anndata
        scorer = ImmuneInfiltrationScore()
        adata = anndata.read_h5ad(self._resolve(args["input"]))
        result = scorer.compute(adata)
        scorer.explain(result)
        return {
            "score": result.score,
            "confidence": result.confidence,
            "interpretation": result.interpretation,
            "msg": f"Immune score: {result.score:.3f} (confidence: {result.confidence:.3f})",
        }

    @_omics_tool(input_key="input")
    def do_omics_score_pathway(self, args: dict, response) -> StepOutcome:
        from omics.score.scorers import PathwayActivityScore
        import anndata
        scorer = PathwayActivityScore()
        adata = anndata.read_h5ad(self._resolve(args["input"]))
        result = scorer.compute(adata)
        return {
            "score": result.score,
            "confidence": result.confidence,
            "pathway_activities": getattr(result, "pathway_activities", {}),
            "msg": f"Pathway score: {result.score:.3f}",
        }

    @_omics_tool(input_key="input")
    def do_omics_score_clonality(self, args: dict, response) -> StepOutcome:
        from omics.score.scorers import ClonalExpansionScore
        import anndata
        scorer = ClonalExpansionScore()
        adata = anndata.read_h5ad(self._resolve(args["input"]))
        result = scorer.compute(adata)
        return {
            "score": result.score,
            "confidence": result.confidence,
            "interpretation": result.interpretation,
            "msg": f"Clonality score: {result.score:.3f}",
        }

    @_omics_tool(input_key="input")
    def do_omics_score_spatial(self, args: dict, response) -> StepOutcome:
        from omics.score.scorers import SpatialNicheScore
        import anndata
        scorer = SpatialNicheScore()
        adata = anndata.read_h5ad(self._resolve(args["input"]))
        result = scorer.compute(adata)
        return {
            "score": result.score,
            "confidence": result.confidence,
            "interpretation": result.interpretation,
            "msg": f"Spatial heterogeneity score: {result.score:.3f}",
        }

    @_omics_tool()
    def do_omics_score_drug(self, args: dict, response) -> StepOutcome:
        return {
            "status": "error",
            "msg": "DrugResponseScore is not yet implemented."
                   " Requires GDSC/DepMap model integration (planned for future phase).",
        }

    @_omics_tool()
    def do_omics_score_integrated(self, args: dict, response) -> StepOutcome:
        from omics.score.scorers import IntegratedHealthScore
        from omics.score.base import ScoreCategory, ScoreResult
        scorer = IntegratedHealthScore()
        raw = args.get("modality_scores", {})
        scores = {}
        for cat_name, val in raw.items():
            cat = ScoreCategory(cat_name)
            scores[cat] = ScoreResult(
                score=float(val.get("score", 0)),
                category=cat,
                confidence=float(val.get("confidence", 1.0)),
            )
        result = scorer.compute(scores)
        return {
            "score": result.score,
            "confidence": result.confidence,
            "interpretation": result.interpretation,
            "msg": f"Integrated health score: {result.score:.3f}",
        }

    # ── Dispatch (GenericAgent convention) ──

    def dispatch(self, tool_name, args, response, index=0):
        method_name = f"do_{tool_name}"
        if hasattr(self, method_name):
            args["_index"] = index
            gen = getattr(self, method_name)(args, response)
            try:
                v = next(gen)
                outcome = yield from self._proxy_gen(gen, v)
            except StopIteration as e:
                outcome = e.value
            return outcome
        yield f"Unknown tool: {tool_name}\n"
        return StepOutcome(
            None,
            next_prompt=f"Unknown tool '{tool_name}'. Available: {list(self._tool_names())}",
            should_exit=False,
        )

    def _proxy_gen(self, gen, first_value):
        yield first_value
        return (yield from gen)

    def _tool_names(self) -> list[str]:
        return [m[3:] for m in dir(self) if m.startswith("do_omics_")]
