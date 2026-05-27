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

    def do_omics_data_info(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("path", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.utils.io import get_adata_summary, read_h5ad
            adata = read_h5ad(Path(path))
            summary = get_adata_summary(adata)
            return StepOutcome({"status": "success", "summary": summary}, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_data_import(self, args: dict, response) -> StepOutcome:
        modality = args.get("modality", "scrna")
        input_path = self._resolve(args.get("input", ""))
        if not input_path:
            return StepOutcome({"status": "error", "msg": "input path is required"}, next_prompt="\n")
        try:
            from omics.sdk import OmicsSDK
            sdk = OmicsSDK()
            if modality == "scrna":
                adata = sdk.data.import_scrna(input_path)
            elif modality == "spatial":
                adata = sdk.data.import_spatial(input_path)
            else:
                return StepOutcome({"status": "error", "msg": f"Unsupported modality: {modality}"}, next_prompt="\n")
            return StepOutcome({
                "status": "success",
                "n_obs": adata.n_obs,
                "n_vars": adata.n_vars,
                "msg": f"Imported {modality}: {adata.n_obs} cells x {adata.n_vars} genes",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_data_fetch(self, args: dict, response) -> StepOutcome:
        accession = args.get("accession", "")
        output_dir = args.get("output_dir", "data/raw")
        if not accession:
            return StepOutcome({"status": "error", "msg": "accession is required"}, next_prompt="\n")
        try:
            from omics.sdk import OmicsSDK
            sdk = OmicsSDK()
            adata = sdk.data.fetch_geo(accession, Path(output_dir))
            return StepOutcome({
                "status": "success",
                "n_obs": adata.n_obs,
                "n_vars": adata.n_vars,
                "msg": f"Fetched {accession}: {adata.n_obs} samples x {adata.n_vars} genes",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_data_search(self, args: dict, response) -> StepOutcome:
        query = args.get("query", "")
        max_results = args.get("max_results", 20)
        if not query:
            return StepOutcome({"status": "error", "msg": "query is required"}, next_prompt="\n")
        try:
            from omics.sdk import OmicsSDK
            sdk = OmicsSDK()
            results = sdk.data.search_geo(query, max_results)
            rows = [[r.accession, r.title[:60], str(r.n_samples), r.organism, r.platform[:30]] for r in results]
            return StepOutcome({"status": "success", "total": len(results), "results": rows}, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    # ── scRNA-seq Tools ──

    def do_omics_scrna_qc(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        output = self._resolve(args.get("output", "qc_filtered.h5ad"))
        try:
            from omics.scrna.qc import run_qc
            from omics.utils.io import read_h5ad, write_h5ad
            adata = read_h5ad(Path(path))
            adata = run_qc(adata, min_genes=args.get("min_genes", 200),
                           min_cells=args.get("min_cells", 3),
                           max_pct_mt=args.get("max_pct_mt", 20.0))
            write_h5ad(adata, Path(output))
            return StepOutcome({
                "status": "success",
                "n_obs": adata.n_obs, "n_vars": adata.n_vars,
                "msg": f"QC complete: {adata.n_obs} cells, {adata.n_vars} genes -> {output}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_scrna_normalize(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        output = self._resolve(args.get("output", ""))
        try:
            from omics.scrna.normalize import run_normalize
            from omics.utils.io import read_h5ad, write_h5ad
            adata = read_h5ad(Path(path))
            adata = run_normalize(adata, target_sum=args.get("target_sum", 10000))
            if output:
                write_h5ad(adata, Path(output))
            return StepOutcome({"status": "success", "msg": f"Normalized: {adata.n_obs} cells"}, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_scrna_reduce(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        output = self._resolve(args.get("output", ""))
        try:
            from omics.scrna.pca import run_pca
            from omics.scrna.neighbors import run_neighbors
            from omics.scrna.umap import run_umap
            from omics.utils.io import read_h5ad, write_h5ad
            adata = read_h5ad(Path(path))
            adata = run_pca(adata, n_comps=args.get("n_pcs", 50))
            adata = run_neighbors(adata, n_neighbors=args.get("n_neighbors", 15))
            adata = run_umap(adata)
            if output:
                write_h5ad(adata, Path(output))
            return StepOutcome({"status": "success", "msg": f"PCA+UMAP complete: {adata.n_obs} cells"}, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_scrna_cluster(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        output = self._resolve(args.get("output", ""))
        resolution = args.get("resolution", 1.0)
        try:
            from omics.scrna.cluster import run_leiden
            from omics.utils.io import read_h5ad, write_h5ad
            adata = read_h5ad(Path(path))
            adata = run_leiden(adata, resolution=resolution)
            n = adata.obs["leiden"].nunique()
            if output:
                write_h5ad(adata, Path(output))
            return StepOutcome({
                "status": "success",
                "n_clusters": n,
                "msg": f"Clustering: {n} clusters at resolution={resolution}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_scrna_markers(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        group_by = args.get("group_by", "leiden")
        n_genes = args.get("n_genes", 100)
        try:
            from omics.scrna.markers import run_markers, get_marker_table
            from omics.utils.io import read_h5ad
            adata = read_h5ad(Path(path))
            adata = run_markers(adata, groupby=group_by, n_genes=n_genes)
            df = get_marker_table(adata)
            top5 = df[df["pval_adj"] < 0.05].groupby("group").head(5) if "pval_adj" in df.columns else df.head(20)
            return StepOutcome({
                "status": "success",
                "n_genes": len(df),
                "top_markers": top5.to_dict(orient="records")[:30],
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_scrna_annotate(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        method = args.get("method", "marker_based")
        try:
            from omics.scrna.annotation import run_marker_annotation, run_celltypist
            from omics.utils.io import read_h5ad
            adata = read_h5ad(Path(path))
            if method == "celltypist":
                adata = run_celltypist(adata)
                label_col = "celltypist_label"
            else:
                adata = run_marker_annotation(adata, cluster_key=args.get("cluster_key", "leiden"))
                label_col = "marker_based_label"
            counts = adata.obs[label_col].value_counts().to_dict() if label_col in adata.obs else {}
            return StepOutcome({
                "status": "success",
                "n_cell_types": len(counts),
                "label_column": label_col,
                "cell_type_counts": {str(k): v for k, v in counts.items()},
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_scrna_trajectory(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        method = args.get("method", "dpt")
        try:
            from omics.scrna.trajectory import run_dpt, run_paga, run_velocity
            from omics.utils.io import read_h5ad
            adata = read_h5ad(Path(path))
            if method == "dpt":
                adata = run_dpt(adata)
            elif method == "paga":
                adata = run_paga(adata)
            elif method == "velocity":
                adata = run_velocity(adata)
            has_pt = "dpt_pseudotime" in adata.obs
            return StepOutcome({
                "status": "success",
                "method": method,
                "has_pseudotime": has_pt,
                "msg": f"Trajectory ({method}) complete",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_scrna_cell_communication(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        try:
            from omics.scrna.communication import run_lr_analysis
            from omics.utils.io import read_h5ad
            adata = read_h5ad(Path(path))
            adata = run_lr_analysis(adata, cluster_key=args.get("cluster_key", "leiden"))
            return StepOutcome({"status": "success", "msg": "Cell communication analysis complete"}, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    # ── Pipeline ──

    def do_omics_pipeline_run(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        output_dir = self._resolve(args.get("output_dir", "."))
        try:
            from omics.scrna.pipeline import run_standard_pipeline
            from omics.utils.io import read_h5ad, write_h5ad
            adata = read_h5ad(Path(path))
            adata = run_standard_pipeline(adata, use_gpu=args.get("use_gpu", False))
            p = Path(path)
            out = Path(output_dir) / f"{p.stem}_processed.h5ad"
            write_h5ad(adata, out)
            n_clusters = adata.obs["leiden"].nunique() if "leiden" in adata.obs else 0
            return StepOutcome({
                "status": "success",
                "n_obs": adata.n_obs,
                "n_vars": adata.n_vars,
                "n_clusters": n_clusters,
                "obsm_keys": list(adata.obsm.keys()),
                "output": str(out),
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    # ── Visualization ──

    def do_omics_visualize_umap(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        color = args.get("color", "leiden")
        output = self._resolve(args.get("output", "umap.pdf"))
        try:
            from omics.sdk import VizSDK
            from omics.utils.io import read_h5ad
            adata = read_h5ad(Path(path))
            sdk_viz = VizSDK(None)
            sdk_viz.umap(adata, color=color, output_path=output)
            return StepOutcome({"status": "success", "output": output, "color": color}, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_compose_figure(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        template = args.get("template", "cell_type_atlas")
        output = self._resolve(args.get("output", "figure1.pdf"))
        try:
            from omics.sdk import VizSDK
            from omics.utils.io import read_h5ad
            adata = read_h5ad(Path(path))
            sdk_viz = VizSDK(None)
            sdk_viz.compose(template, adata, output_path=Path(output))
            return StepOutcome({
                "status": "success", "output": output, "template": template,
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    # ── Interpretation ──

    def do_omics_ask_question(self, args: dict, response) -> StepOutcome:
        query = args.get("question", "")
        input_path = self._resolve(args.get("input", ""))
        if not query:
            return StepOutcome({"status": "error", "msg": "question is required"}, next_prompt="\n")
        try:
            from omics.agent.semantic import AnalysisPlanner, get_planner
            planner = get_planner()
            profile = None
            if input_path and os.path.exists(input_path):
                from omics.utils.io import read_h5ad
                adata = read_h5ad(Path(input_path))
                profile = planner.create_profile(adata)
            plan = planner.plan_analysis(query, profile)
            return StepOutcome({
                "status": "success",
                "plan": plan.to_dict(),
                "markdown": plan.to_markdown(),
                "n_steps": len(plan.steps),
                "primary_intent": plan.intent.primary_intent.value,
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_explain_results(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.utils.io import read_h5ad
            from omics.knowledge.engine import KnowledgeEngine
            adata = read_h5ad(Path(path))
            engine = KnowledgeEngine()
            kc = engine.run_on_results(adata, groupby=args.get("groupby", "leiden"))
            return StepOutcome({
                "status": "success",
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
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    # ── System ──

    def do_omics_gpu_status(self, args: dict, response) -> StepOutcome:
        try:
            from omics.gpu.manager import get_gpu_manager
            gm = get_gpu_manager()
            info = gm.summary()
            return StepOutcome({"status": "success", "gpu_info": info}, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_config(self, args: dict, response) -> StepOutcome:
        try:
            from omics.utils.config import Config
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
                return StepOutcome({"status": "success", "msg": f"Config updated: {key} = {value}"}, next_prompt="\n")
            return StepOutcome({"status": "success", "config": cfg.to_dict()}, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    # ── Bulk RNA-seq Tools ──

    def do_omics_bulk_import(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("path", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.bulk.analysis import BulkRNAAnalysis
            b = BulkRNAAnalysis()
            adata = b.load_counts(path)
            return StepOutcome({
                "status": "success",
                "n_samples": adata.n_obs,
                "n_genes": adata.n_vars,
                "msg": f"Loaded {adata.n_obs} samples x {adata.n_vars} genes",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_bulk_de(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            import anndata
            from omics.bulk.analysis import BulkRNAAnalysis
            b = BulkRNAAnalysis()
            adata = anndata.read_h5ad(path)
            de = b.differential_expression(adata, args["design"], tuple(args["contrast"]))
            n_sig = int((de["padj"] < 0.05).sum()) if "padj" in de.columns else 0
            return StepOutcome({
                "status": "success",
                "n_genes": len(de),
                "n_significant": n_sig,
                "top_genes": de.head(10).index.tolist(),
                "msg": f"DE complete: {n_sig} significant genes",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_bulk_enrich(self, args: dict, response) -> StepOutcome:
        de_path = self._resolve(args.get("de_results_path", ""))
        if not de_path or not os.path.exists(de_path):
            return StepOutcome({"status": "error", "msg": f"File not found: {de_path}"}, next_prompt="\n")
        try:
            from omics.bulk.analysis import BulkRNAAnalysis
            b = BulkRNAAnalysis()
            gene_sets = args.get("gene_sets", "GO")
            enrich = b.gene_set_enrichment(de_path, gene_sets=gene_sets)
            n_pathways = len(enrich) if hasattr(enrich, "__len__") else 0
            return StepOutcome({
                "status": "success",
                "gene_sets": gene_sets,
                "n_pathways": n_pathways,
                "top_results": enrich.head(10).to_dict(orient="records") if hasattr(enrich, "head") else [],
                "msg": f"GSEA complete using {gene_sets}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_bulk_visualize(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        plot_type = args.get("plot_type", "volcano")
        output = self._resolve(args.get("output", f"bulk_{plot_type}.pdf"))
        try:
            from omics.bulk.visualization import BulkViz
            bv = BulkViz()
            gene_list = args.get("gene_list")
            bv.plot(path, plot_type=plot_type, gene_list=gene_list, output=output)
            return StepOutcome({
                "status": "success",
                "plot_type": plot_type,
                "output": output,
                "msg": f"{plot_type} plot saved to {output}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_bulk_pipeline(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        output_dir = self._resolve(args.get("output_dir", "."))
        try:
            from omics.bulk.pipeline import run_bulk_pipeline
            result = run_bulk_pipeline(
                path,
                design=args["design"],
                contrast=tuple(args["contrast"]),
                output_dir=Path(output_dir),
            )
            return StepOutcome({
                "status": "success",
                "n_de_genes": result.get("n_de_genes", 0),
                "n_significant": result.get("n_significant", 0),
                "output_dir": str(output_dir),
                "msg": "Bulk RNA-seq pipeline complete",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    # ── Spatial Tools ──

    def do_omics_spatial_import(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("path", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.spatial.io import import_spatial
            modality = args.get("modality", "visium")
            adata = import_spatial(path, modality=modality)
            return StepOutcome({
                "status": "success",
                "n_spots": adata.n_obs,
                "n_genes": adata.n_vars,
                "modality": modality,
                "msg": f"Imported {modality}: {adata.n_obs} spots x {adata.n_vars} genes",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_spatial_qc(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.spatial.qc import run_spatial_qc
            from omics.utils.io import read_h5ad
            adata = read_h5ad(Path(path))
            adata = run_spatial_qc(adata, min_counts=args.get("min_counts", 100),
                                   min_spots=args.get("min_spots", 3),
                                   max_pct_mt=args.get("max_pct_mt", 20.0))
            return StepOutcome({
                "status": "success",
                "n_spots": adata.n_obs,
                "n_genes": adata.n_vars,
                "msg": f"Spatial QC complete: {adata.n_obs} spots x {adata.n_vars} genes",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_spatial_cluster(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.spatial.analysis import run_spatial_cluster
            from omics.utils.io import read_h5ad
            adata = read_h5ad(Path(path))
            adata = run_spatial_cluster(adata, resolution=args.get("resolution", 1.0),
                                         n_neighbors=args.get("n_neighbors", 15))
            n_clusters = adata.obs["leiden"].nunique() if "leiden" in adata.obs else 0
            return StepOutcome({
                "status": "success",
                "n_clusters": n_clusters,
                "msg": f"Spatial clustering: {n_clusters} clusters",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_spatial_deconvolve(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        reference = self._resolve(args.get("reference", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        if not reference or not os.path.exists(reference):
            return StepOutcome({"status": "error", "msg": f"Reference file not found: {reference}"}, next_prompt="\n")
        try:
            from omics.spatial.deconvolution import run_cell2location
            adata = run_cell2location(path, reference)
            n_types = adata.uns.get("n_cell_types", 0) if hasattr(adata, "uns") else 0
            return StepOutcome({
                "status": "success",
                "n_cell_types": n_types,
                "msg": f"Spatial deconvolution complete: {n_types} cell types",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_spatial_niche(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.spatial.analysis import run_niche_analysis
            cluster_key = args.get("cluster_key", "leiden")
            result = run_niche_analysis(path, cluster_key=cluster_key)
            return StepOutcome({
                "status": "success",
                "cluster_key": cluster_key,
                "n_niches": result.get("n_niches", 0),
                "msg": f"Niche analysis complete: {result.get('n_niches', 0)} niches",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_spatial_lr(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.spatial.analysis import run_spatial_lr
            cluster_key = args.get("cluster_key", "leiden")
            result = run_spatial_lr(path, cluster_key=cluster_key)
            return StepOutcome({
                "status": "success",
                "n_interactions": result.get("n_interactions", 0),
                "msg": f"Spatial LR analysis: {result.get('n_interactions', 0)} interactions",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_spatial_svg(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.spatial.analysis import detect_spatial_variable_genes
            result = detect_spatial_variable_genes(path)
            return StepOutcome({
                "status": "success",
                "n_svg": result.get("n_svg", 0),
                "top_genes": result.get("top_genes", [])[:10],
                "msg": f"SVG detection: {result.get('n_svg', 0)} genes",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    # ── TCR/BCR Tools ──

    def do_omics_tcr_load(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("path", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.tcr.io import load_tcr_data
            adata = load_tcr_data(path)
            return StepOutcome({
                "status": "success",
                "n_cells": adata.n_obs,
                "msg": f"Loaded TCR/BCR data: {adata.n_obs} cells",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_tcr_clonotypes(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.tcr.analysis import define_clonotypes
            import anndata
            adata = anndata.read_h5ad(path)
            adata = define_clonotypes(adata)
            n_clonotypes = adata.obs["clonotype_id"].nunique() if "clonotype_id" in adata.obs else 0
            return StepOutcome({
                "status": "success",
                "n_clonotypes": n_clonotypes,
                "msg": f"Clonotype analysis: {n_clonotypes} clonotypes",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_tcr_diversity(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.tcr.analysis import compute_diversity
            import anndata
            adata = anndata.read_h5ad(path)
            metrics = compute_diversity(adata)
            return StepOutcome({
                "status": "success",
                "diversity_metrics": metrics,
                "msg": f"Diversity: Shannon={metrics.get('shannon', 'N/A')}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_tcr_vj_usage(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.tcr.analysis import analyze_vj_usage
            import anndata
            adata = anndata.read_h5ad(path)
            result = analyze_vj_usage(adata)
            return StepOutcome({
                "status": "success",
                "v_usage": result.get("v_usage", {}),
                "j_usage": result.get("j_usage", {}),
                "msg": "V-J usage analysis complete",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_tcr_overlap(self, args: dict, response) -> StepOutcome:
        inputs = args.get("inputs", [])
        if not inputs:
            return StepOutcome({"status": "error", "msg": "inputs (list of .h5ad paths) is required"}, next_prompt="\n")
        try:
            from omics.tcr.analysis import compute_clonotype_overlap
            import anndata
            adatas = [anndata.read_h5ad(self._resolve(p)) for p in inputs]
            overlap_matrix = compute_clonotype_overlap(adatas)
            return StepOutcome({
                "status": "success",
                "n_samples": len(inputs),
                "overlap_matrix": overlap_matrix.tolist() if hasattr(overlap_matrix, "tolist") else overlap_matrix,
                "msg": f"Clonotype overlap computed for {len(inputs)} samples",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_tcr_integrate(self, args: dict, response) -> StepOutcome:
        tcr_path = self._resolve(args.get("tcr_input", ""))
        scrna_path = self._resolve(args.get("scrna_input", ""))
        if not tcr_path or not os.path.exists(tcr_path):
            return StepOutcome({"status": "error", "msg": f"TCR file not found: {tcr_path}"}, next_prompt="\n")
        if not scrna_path or not os.path.exists(scrna_path):
            return StepOutcome({"status": "error", "msg": f"scRNA file not found: {scrna_path}"}, next_prompt="\n")
        try:
            from omics.tcr.integration import integrate_tcr_scrna
            adata = integrate_tcr_scrna(tcr_path, scrna_path)
            return StepOutcome({
                "status": "success",
                "n_cells": adata.n_obs,
                "n_genes": adata.n_vars,
                "msg": f"TCR-scRNA integration: {adata.n_obs} cells x {adata.n_vars} genes",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    # ── Scoring Tools ──

    def do_omics_score_immune(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.score.scorers import ImmuneInfiltrationScore
            import anndata
            scorer = ImmuneInfiltrationScore()
            adata = anndata.read_h5ad(path)
            result = scorer.compute(adata)
            scorer.explain(result)
            return StepOutcome({
                "status": "success",
                "score": result.score,
                "confidence": result.confidence,
                "interpretation": result.interpretation,
                "msg": f"Immune score: {result.score:.3f} (confidence: {result.confidence:.3f})",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_score_pathway(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.score.scorers import PathwayActivityScore
            import anndata
            scorer = PathwayActivityScore()
            adata = anndata.read_h5ad(path)
            result = scorer.compute(adata)
            return StepOutcome({
                "status": "success",
                "score": result.score,
                "confidence": result.confidence,
                "pathway_activities": getattr(result, "pathway_activities", {}),
                "msg": f"Pathway score: {result.score:.3f}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_score_clonality(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.score.scorers import ClonalityScore
            import anndata
            scorer = ClonalityScore()
            adata = anndata.read_h5ad(path)
            result = scorer.compute(adata)
            return StepOutcome({
                "status": "success",
                "score": result.score,
                "confidence": result.confidence,
                "interpretation": result.interpretation,
                "msg": f"Clonality score: {result.score:.3f}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_score_spatial(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.score.scorers import SpatialHeterogeneityScore
            import anndata
            scorer = SpatialHeterogeneityScore()
            adata = anndata.read_h5ad(path)
            result = scorer.compute(adata)
            return StepOutcome({
                "status": "success",
                "score": result.score,
                "confidence": result.confidence,
                "interpretation": result.interpretation,
                "msg": f"Spatial heterogeneity score: {result.score:.3f}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_score_drug(self, args: dict, response) -> StepOutcome:
        path = self._resolve(args.get("input", ""))
        if not path or not os.path.exists(path):
            return StepOutcome({"status": "error", "msg": f"File not found: {path}"}, next_prompt="\n")
        try:
            from omics.score.scorers import DrugResponseScore
            import anndata
            scorer = DrugResponseScore()
            adata = anndata.read_h5ad(path)
            result = scorer.compute(adata)
            return StepOutcome({
                "status": "success",
                "score": result.score,
                "confidence": result.confidence,
                "top_drugs": getattr(result, "top_drugs", []),
                "msg": f"Drug response score: {result.score:.3f}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

    def do_omics_score_integrated(self, args: dict, response) -> StepOutcome:
        try:
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
            return StepOutcome({
                "status": "success",
                "score": result.score,
                "confidence": result.confidence,
                "interpretation": result.interpretation,
                "msg": f"Integrated health score: {result.score:.3f}",
            }, next_prompt="\n")
        except Exception as e:
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")

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
