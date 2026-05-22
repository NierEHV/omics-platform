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
