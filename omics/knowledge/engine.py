"""Knowledge-Augmented Interpretation Engine.

Connects analysis results to known biology:
  - Gene set enrichment (hypergeometric test via scipy)
  - Cell type marker matching (Jaccard index)
  - Auto-generation of biological interpretation summaries
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    gene_set_name: str
    database: str
    p_value: float
    adjusted_p_value: float
    overlap_genes: list[str] = field(default_factory=list)
    overlap_count: int = 0
    gene_set_size: int = 0

    @property
    def name(self) -> str:
        return self.gene_set_name

    @property
    def overlap(self) -> int:
        return self.overlap_count


@dataclass
class CellTypeMatch:
    query_cluster: str
    matched_cell_type: str
    database: str
    overlap_count: int
    total_markers: int
    jaccard_index: float
    supporting_genes: list[str] = field(default_factory=list)


@dataclass
class KnowledgeContext:
    analysis_id: str = ""
    enrichment_results: list[EnrichmentResult] = field(default_factory=list)
    cell_type_matches: list[CellTypeMatch] = field(default_factory=list)
    literature_summary: str = ""
    suggested_followups: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = ["## Biological Interpretation", ""]
        if self.cell_type_matches:
            lines.append("### Cell Type Annotations")
            seen = set()
            for m in self.cell_type_matches[:15]:
                key = (m.query_cluster, m.matched_cell_type)
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"- Cluster **{m.query_cluster}**: {m.matched_cell_type} (Jaccard={m.jaccard_index:.3f})")
            lines.append("")
        if self.enrichment_results:
            lines.append("### Enriched Pathways")
            for r in self.enrichment_results[:10]:
                lines.append(f"- {r.gene_set_name}: p_adj={r.adjusted_p_value:.2e}")
            lines.append("")
        if self.suggested_followups:
            lines.append("### Suggested Follow-up Analyses")
            for s in self.suggested_followups:
                lines.append(f"- {s}")
        return "\n".join(lines)


class GeneSetLibrary:
    """Local gene set database loaded from bundled JSON files."""

    _FILE_MAP = {"hallmark": "hallmark.json", "go_bp": "go_biological_process.json",
                 "cell_markers": "cell_markers.json"}

    def __init__(self, gene_sets_dir: Optional[Path] = None):
        self._dir = gene_sets_dir or (Path(__file__).parent / "gene_sets")
        self._cache: dict[str, dict] = {}

    def load(self, database: str) -> dict:
        if database in self._cache:
            return self._cache[database]
        filename = self._FILE_MAP.get(database)
        if filename is None:
            logger.warning(f"Unknown database: {database}")
            return {}
        filepath = self._dir / filename
        if not filepath.exists():
            logger.warning(f"Gene set file not found: {filepath}")
            return {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cache[database] = data
            return data
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
            return {}

    @property
    def hallmark(self) -> dict:
        return self.load("hallmark")

    @property
    def go_bp(self) -> dict:
        return self.load("go_bp")

    @property
    def cell_markers(self) -> dict:
        return self.load("cell_markers")


class KnowledgeEngine:
    """Connects analysis results to known biology."""

    def __init__(self):
        self._gene_sets = GeneSetLibrary()

    def run_enrichment(self, gene_list: list[str], background_genes: list[str] | None = None,
                       databases: list[str] | None = None, p_threshold: float = 0.05,
                       min_overlap: int = 3) -> list[EnrichmentResult]:
        if not gene_list:
            return []
        gene_set_upper = set(g.upper() for g in gene_list)
        databases = databases or ["hallmark", "go_bp"]
        all_results = []

        for db_name in databases:
            db = self._gene_sets.load(db_name)
            if not db:
                continue
            for gs_name, gs_genes in db.items():
                gs_upper = set(g.upper() for g in gs_genes)
                overlap = gene_set_upper & gs_upper
                if len(overlap) < min_overlap:
                    continue
                background_size = len(background_genes) if background_genes else 20000
                from scipy.stats import hypergeom
                p_val = float(hypergeom.sf(len(overlap) - 1, background_size, len(gs_upper),
                                           len(gene_set_upper)))
                all_results.append(EnrichmentResult(
                    gene_set_name=gs_name, database=db_name, p_value=p_val,
                    adjusted_p_value=p_val, overlap_genes=list(overlap)[:10],
                    overlap_count=len(overlap), gene_set_size=len(gs_upper),
                ))

        all_results = self._correct_pvalues(all_results)
        all_results = [r for r in all_results if r.adjusted_p_value < p_threshold]
        all_results.sort(key=lambda x: x.adjusted_p_value)
        return all_results[:30]

    def _correct_pvalues(self, results: list[EnrichmentResult]) -> list[EnrichmentResult]:
        if len(results) <= 1:
            return results
        sorted_r = sorted(results, key=lambda x: x.p_value)
        n = len(sorted_r)
        for rank, result in enumerate(sorted_r, 1):
            result.adjusted_p_value = min(result.p_value * n / rank, 1.0)
        for i in range(n - 2, -1, -1):
            sorted_r[i].adjusted_p_value = min(sorted_r[i].adjusted_p_value,
                                               sorted_r[i + 1].adjusted_p_value)
        return sorted_r

    def match_cell_types(self, cluster_markers: dict[str, list[str]],
                         database: str = "cell_markers",
                         top_n_per_cluster: int = 50) -> list[CellTypeMatch]:
        db = self._gene_sets.load(database)
        if not db:
            return []
        matches = []
        for cluster_id, marker_genes in cluster_markers.items():
            marker_upper = set(g.upper() for g in marker_genes[:top_n_per_cluster])
            for cell_type, ct_markers in db.items():
                ct_upper = set(g.upper() for g in ct_markers)
                overlap = marker_upper & ct_upper
                if len(overlap) < 1:
                    continue
                union = len(marker_upper | ct_upper)
                jaccard = len(overlap) / union if union > 0 else 0
                if jaccard > 0.01:
                    matches.append(CellTypeMatch(
                        query_cluster=cluster_id, matched_cell_type=cell_type,
                        database=database, overlap_count=len(overlap),
                        total_markers=len(ct_upper), jaccard_index=round(jaccard, 4),
                        supporting_genes=list(overlap)[:8],
                    ))
        matches.sort(key=lambda x: x.jaccard_index, reverse=True)
        return matches

    def summarize_findings(self, kc: KnowledgeContext, adata=None) -> str:
        parts = []
        if kc.cell_type_matches:
            top = kc.cell_type_matches[:5]
            ct_list = ", ".join(f"{m.matched_cell_type} (cluster {m.query_cluster})" for m in top)
            parts.append(f"Cell type annotation identified: {ct_list}.")
        if kc.enrichment_results:
            sig = [r for r in kc.enrichment_results if r.adjusted_p_value < 0.05]
            if sig:
                pathways = ", ".join(r.gene_set_name for r in sig[:5])
                parts.append(f"Significantly enriched pathways: {pathways}.")
        if adata is not None and hasattr(adata, "n_obs") and "leiden" in adata.obs.columns:
            n_clusters = adata.obs["leiden"].nunique()
            parts.append(f"Analysis of {adata.n_obs:,} cells across {n_clusters} clusters.")
        kc.literature_summary = " ".join(parts)
        return kc.literature_summary

    def run_on_results(self, adata, analysis_id: str = "", groupby: str = "leiden") -> KnowledgeContext:
        kc = KnowledgeContext(analysis_id=analysis_id)
        marker_dict: dict[str, list[str]] = {}
        all_genes: list[str] = []
        if "rank_genes_groups" in adata.uns:
            rgg = adata.uns["rank_genes_groups"]
            group_names = rgg["names"].dtype.names if hasattr(rgg["names"], "dtype") else []
            for group in group_names:
                try:
                    genes = list(rgg["names"][group][:50])
                    marker_dict[group] = genes
                    all_genes.extend(genes[:20])
                except Exception:
                    continue
        else:
            all_genes = list(adata.var_names[:200])
        if all_genes:
            kc.enrichment_results = self.run_enrichment(
                list(set(all_genes)), background_genes=list(adata.var_names[:5000]),
                databases=["hallmark", "go_bp"],
            )
        if marker_dict:
            kc.cell_type_matches = self.match_cell_types(marker_dict)
        self.summarize_findings(kc, adata)
        kc.suggested_followups = []
        if kc.enrichment_results:
            kc.suggested_followups.append("Run trajectory analysis to study differentiation hierarchy")
        if kc.cell_type_matches:
            kc.suggested_followups.append("Perform cell-cell communication analysis between identified cell types")
        return kc


_engine: Optional[KnowledgeEngine] = None


def get_knowledge_engine() -> KnowledgeEngine:
    global _engine
    if _engine is None:
        _engine = KnowledgeEngine()
    return _engine
