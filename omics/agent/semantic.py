"""Semantic Analysis Engine — maps natural language to analysis workflows.

Rule-based intent classification (no LLM dependency). Keyword + pattern
matching for entity extraction (CN + EN). Data-aware parameter adjustment.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from omics.utils.constants import AnalysisIntent

logger = logging.getLogger(__name__)


@dataclass
class EntityExtraction:
    cell_types: list[str] = field(default_factory=list)
    genes: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    modalities: list[str] = field(default_factory=list)
    comparison_groups: list[str] = field(default_factory=list)
    quantitative_terms: dict = field(default_factory=dict)


@dataclass
class IntentClassification:
    primary_intent: AnalysisIntent
    secondary_intents: list[AnalysisIntent] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class AnalysisStep:
    order: int
    plugin_name: str
    description: str
    parameters: dict = field(default_factory=dict)
    gpu_beneficial: bool = False
    depends_on: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "plugin_name": self.plugin_name,
            "description": self.description,
            "parameters": self.parameters,
            "gpu_beneficial": self.gpu_beneficial,
            "depends_on": self.depends_on,
        }


@dataclass
class AnalysisPlan:
    query: str = ""
    intent: IntentClassification = field(
        default_factory=lambda: IntentClassification(primary_intent=AnalysisIntent.UNKNOWN)
    )
    entities: EntityExtraction = field(default_factory=EntityExtraction)
    steps: list[AnalysisStep] = field(default_factory=list)
    estimated_runtime_minutes: float = 0.0
    gpu_recommended: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "intent": {
                "primary": self.intent.primary_intent.value,
                "secondary": [s.value for s in self.intent.secondary_intents],
                "confidence": self.intent.confidence,
            },
            "entities": {
                "cell_types": self.entities.cell_types,
                "genes": self.entities.genes,
                "conditions": self.entities.conditions,
                "modalities": self.entities.modalities,
            },
            "steps": [s.to_dict() for s in self.steps],
            "estimated_runtime_minutes": self.estimated_runtime_minutes,
            "gpu_recommended": self.gpu_recommended,
            "warnings": self.warnings,
        }

    def to_markdown(self) -> str:
        lines = [
            f"## Analysis Plan",
            f'> Query: "{self.query}"',
            "",
            f"**Intent**: {self.intent.primary_intent.value} (confidence: {self.intent.confidence:.0%})",
            "",
        ]
        if self.entities.cell_types:
            lines.append(f"**Cell Types**: {', '.join(self.entities.cell_types)}")
        if self.entities.genes:
            lines.append(f"**Genes**: {', '.join(self.entities.genes[:10])}")
        if self.entities.conditions:
            lines.append(f"**Conditions**: {', '.join(self.entities.conditions)}")
        lines.append("")
        lines.append("### Steps")
        for step in self.steps:
            gpu = " [GPU]" if step.gpu_beneficial else ""
            deps = f" (depends on: {step.depends_on})" if step.depends_on else ""
            lines.append(f"{step.order}. **{step.plugin_name}**{gpu} — {step.description}{deps}")
        lines.append("")
        lines.append(
            f"Estimated: ~{self.estimated_runtime_minutes:.1f} min | "
            f"GPU: {'recommended' if self.gpu_recommended else 'not needed'}"
        )
        if self.warnings:
            lines.append("")
            lines.append("### Warnings")
            for w in self.warnings:
                lines.append(f"- :warning: {w}")
        return "\n".join(lines)


@dataclass
class DataProfile:
    n_cells: int = 0
    n_genes: int = 0
    modality: str = "scrna"
    has_batch: bool = False
    has_spatial: bool = False
    scRNA_quality: str = "unknown"
    available_slots: list[str] = field(default_factory=list)
    cluster_count: int = 0


class AnalysisPlanner:
    """Maps NL questions + data profiles to AnalysisPlans (keyword-based, no LLM)."""

    _INTENT_PATTERNS: dict[str, list[str]] = {
        AnalysisIntent.DIFFERENTIAL: [
            "differential", "deg", "compare", "versus", "vs", "upregulated",
            "downregulated", "de", "differentially", "expression difference",
            "differ", "volcano", "deg analysis", "diff", "diff exp",
            "变化", "差异", "上调", "下调", "差异分析", "差异基因",
        ],
        AnalysisIntent.CLUSTERING: [
            "cluster", "clustering", "leiden", "louvain", "group",
            "subpopulation", "subtype", "sub-population", "subgroup",
            "聚类", "分群", "亚群", "亚型",
        ],
        AnalysisIntent.TRAJECTORY: [
            "trajectory", "pseudotime", "differentiation", "lineage",
            "developmental", "transition", "dpt", "paga", "velocity",
            "branch", "rna velocity", "fate",
            "拟时序", "分化", "发育", "轨迹", "起源",
        ],
        AnalysisIntent.INTEGRATION: [
            "integration", "integrate", "multi-omics", "multiomics",
            "cross-modality", "combine", "merge data", "batch correct",
            "harmony", "scvi", "mofa", "mowgli",
            "整合", "多组学", "融合",
        ],
        AnalysisIntent.VISUALIZATION: [
            "visualize", "plot", "figure", "umap", "tsne", "heatmap",
            "volcano", "dotplot", "draw", "show", "display",
            "可视化", "画图", "展示", "图",
        ],
        AnalysisIntent.ANNOTATION: [
            "annotate", "cell type", "cell-type", "celltype",
            "identify cells", "what cells", "cell identity", "label", "name cells",
            "注释", "细胞类型", "鉴定", "细胞鉴定",
        ],
        AnalysisIntent.QUALITY_CONTROL: [
            "qc", "quality", "filter", "filtering", "preprocess",
            "clean", "remove bad cells",
            "质量控制", "过滤", "预处理", "清洗",
        ],
        AnalysisIntent.CELL_COMMUNICATION: [
            "communication", "interaction", "ligand", "receptor",
            "cellchat", "cellphonedb", "signaling", "cell talk", "lr pair", "cci",
            "通讯", "互作", "配体", "受体", "细胞通讯",
        ],
    }

    _KNOWN_CELL_TYPES: set[str] = {
        "t cell", "b cell", "nk cell", "monocyte", "macrophage",
        "dendritic", "dendritic cell", "neutrophil", "erythrocyte", "platelet",
        "plasma cell", "cd4", "cd8", "cd4+", "cd8+", "cd4 t", "cd8 t",
        "regulatory t", "treg", "th1", "th2", "th17",
        "fibroblast", "endothelial", "epithelial",
        "neuron", "astrocyte", "oligodendrocyte", "microglia",
        "hepatocyte", "cardiomyocyte", "myeloid", "lymphoid",
        "mast cell", "basophil", "eosinophil", "stem cell",
        "pbmc", "pbmcs", "tumor", "cancer", "malignant",
    }

    _MODALITY_KEYWORDS: dict[str, list[str]] = {
        "scrna": ["scrna", "scRNA", "single cell", "single-cell", "scRNA-seq", "单细胞"],
        "spatial": ["spatial", "visium", "merfish", "spatial transcriptom", "空间"],
        "amplicon": ["16s", "16S", "rrna", "amplicon", "microbiome", "微生物"],
        "metagenomics": ["metagenom", "shotgun", "wgs", "宏基因组"],
    }

    def classify_intent(self, query: str) -> IntentClassification:
        q = query.lower()
        scores = {}
        for intent, keywords in self._INTENT_PATTERNS.items():
            score = sum(1 for kw in keywords if kw.lower() in q)
            if score > 0:
                scores[intent] = score
        if not scores:
            return IntentClassification(
                primary_intent=AnalysisIntent.UNKNOWN,
                confidence=0.0,
                reasoning="No known intent keywords matched.",
            )
        primary = max(scores, key=scores.get)
        max_score = scores[primary]
        scores.pop(primary)
        secondaries = [k for k, v in scores.items() if v >= max_score * 0.5]
        confidence = min(max_score / 5.0, 1.0)
        return IntentClassification(
            primary_intent=primary,
            secondary_intents=secondaries[:2],
            confidence=confidence,
            reasoning=f"Matched {max_score} keyword(s) for '{primary.value}'.",
        )

    def extract_entities(self, query: str) -> EntityExtraction:
        q = query.lower()
        entities = EntityExtraction()
        for ct in self._KNOWN_CELL_TYPES:
            if ct.lower() in q:
                entities.cell_types.append(ct)
        gene_matches = re.findall(r'\b[A-Z][A-Z0-9]{1,8}\b', query)
        common_false = {"A", "B", "C", "I", "II", "III", "IV", "V", "VI", "RNA", "DNA", "QC", "PCA", "UMAP", "TSNE"}
        entities.genes = [g for g in gene_matches if g not in common_false and len(g) >= 2][:20]
        for modality, keywords in self._MODALITY_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in q and modality not in entities.modalities:
                    entities.modalities.append(modality)
                    break
        comp_patterns = [
            (r'(\w+)\s+(?:vs|versus|vs\.)\s+(\w+)', 2),
            (r'between\s+(\w+)\s+and\s+(\w+)', 2),
            (r'(\w+)\s+(?:treated|control|wildtype|wt|mutant|ko)', 1),
            (r'(?:treated|control|wildtype|mutant|ko)\s+(\w+)', 1),
        ]
        for pattern, _ in comp_patterns:
            for match in re.findall(pattern, q):
                if isinstance(match, tuple):
                    entities.comparison_groups.extend(match)
                else:
                    entities.comparison_groups.append(match)
        entities.comparison_groups = list(set(entities.comparison_groups))[:4]
        if "up" in q or "upregulated" in q or "上调" in q:
            entities.quantitative_terms["direction"] = "up"
        if "down" in q or "downregulated" in q or "下调" in q:
            entities.quantitative_terms["direction"] = "down"
        return entities

    def create_profile(self, adata) -> DataProfile:
        profile = DataProfile(n_cells=adata.n_obs, n_genes=adata.n_vars, modality="scrna")
        if "batch" in adata.obs.columns:
            profile.has_batch = True
        if "spatial" in adata.uns:
            profile.has_spatial = True
        if "leiden" in adata.obs.columns:
            profile.cluster_count = adata.obs["leiden"].nunique()
        if "X_umap" in adata.obsm:
            profile.available_slots.append("X_umap")
        if "X_pca" in adata.obsm:
            profile.available_slots.append("X_pca")
        if adata.n_obs < 1000:
            profile.scRNA_quality = "warning"
        elif adata.n_obs > 10000:
            profile.scRNA_quality = "good"
        return profile

    def plan_analysis(self, query: str, data_profile: Optional[DataProfile] = None) -> AnalysisPlan:
        intent = self.classify_intent(query)
        entities = self.extract_entities(query)
        steps = self._route_to_workflow(intent, entities, data_profile)
        plan = AnalysisPlan(query=query, intent=intent, entities=entities, steps=steps)
        if data_profile:
            plan.estimated_runtime_minutes = self._estimate_runtime(steps, data_profile)
            plan.gpu_recommended = data_profile.n_cells > 50000
            if data_profile.n_cells > 100000:
                plan.warnings.append(
                    f"Large dataset ({data_profile.n_cells:,} cells). Use GPU (use_gpu=True)."
                )
            if data_profile.n_cells < 200:
                plan.warnings.append(
                    f"Small dataset ({data_profile.n_cells} cells). Results may have low statistical power."
                )
            if data_profile.has_batch:
                plan.warnings.append("Batch effects detected. Consider adding batch correction.")
        return plan

    def _route_to_workflow(
        self, intent: IntentClassification, entities: EntityExtraction, profile: Optional[DataProfile]
    ) -> list[AnalysisStep]:
        pi = intent.primary_intent
        if pi == AnalysisIntent.QUALITY_CONTROL:
            return [AnalysisStep(1, "scrna_qc", "Quality control", {"min_genes": 200, "min_cells": 3, "max_pct_mt": 20})]
        if pi == AnalysisIntent.CLUSTERING:
            steps = [
                AnalysisStep(1, "scrna_qc", "Quality control", {"min_genes": 200, "min_cells": 3}),
                AnalysisStep(2, "scrna_normalize", "Normalize and log-transform", {"target_sum": 10000}, depends_on=[1]),
                AnalysisStep(3, "scrna_hvg", "HVG selection", {"n_top_genes": 2000}, depends_on=[2]),
                AnalysisStep(4, "scrna_pca", "PCA", {"n_comps": 50}, depends_on=[3]),
                AnalysisStep(5, "scrna_neighbors", "kNN graph", {"n_neighbors": 15}, depends_on=[4]),
                AnalysisStep(6, "scrna_umap", "UMAP embedding", depends_on=[5]),
                AnalysisStep(7, "scrna_leiden", "Leiden clustering", {"resolution": 1.0}, depends_on=[5]),
            ]
            if AnalysisIntent.ANNOTATION in intent.secondary_intents:
                steps.append(AnalysisStep(8, "scrna_annotate", "Cell type annotation", {"method": "marker_based"}, depends_on=[7]))
            return steps
        if pi == AnalysisIntent.DIFFERENTIAL:
            return [
                AnalysisStep(1, "scrna_qc", "Quality control", {"min_genes": 200}),
                AnalysisStep(2, "scrna_normalize", "Normalize", depends_on=[1]),
                AnalysisStep(3, "scrna_markers", "Differential genes", {"groupby": "leiden", "method": "wilcoxon", "n_genes": 100}, depends_on=[2]),
            ]
        if pi == AnalysisIntent.VISUALIZATION:
            return [
                AnalysisStep(1, "scrna_qc", "Quality control", {"min_genes": 200}),
                AnalysisStep(2, "scrna_normalize", "Normalize", depends_on=[1]),
                AnalysisStep(3, "scrna_hvg", "HVG selection", depends_on=[2]),
                AnalysisStep(4, "scrna_pca", "PCA", depends_on=[3]),
                AnalysisStep(5, "scrna_neighbors", "Neighbors", depends_on=[4]),
                AnalysisStep(6, "scrna_umap", "UMAP", depends_on=[5]),
                AnalysisStep(7, "scrna_leiden", "Clustering", depends_on=[5]),
                AnalysisStep(8, "viz_umap", "UMAP plot", {"color_by": "leiden", "style": "nature"}, depends_on=[6, 7]),
            ]
        if pi == AnalysisIntent.ANNOTATION:
            return [
                AnalysisStep(1, "scrna_qc", "Quality control", {"min_genes": 200}),
                AnalysisStep(2, "scrna_normalize", "Normalize", depends_on=[1]),
                AnalysisStep(3, "scrna_hvg", "HVG selection", depends_on=[2]),
                AnalysisStep(4, "scrna_pca", "PCA", depends_on=[3]),
                AnalysisStep(5, "scrna_neighbors", "Neighbors", depends_on=[4]),
                AnalysisStep(6, "scrna_umap", "UMAP", depends_on=[5]),
                AnalysisStep(7, "scrna_leiden", "Clustering", depends_on=[5]),
                AnalysisStep(8, "scrna_markers", "Find markers", {"n_genes": 50}, depends_on=[7]),
                AnalysisStep(9, "scrna_annotate", "Annotate cell types", {"method": "marker_based"}, depends_on=[8]),
            ]
        if pi == AnalysisIntent.TRAJECTORY:
            return [
                AnalysisStep(1, "scrna_qc", "QC filtering", {"min_genes": 200}),
                AnalysisStep(2, "scrna_normalize", "Normalize", depends_on=[1]),
                AnalysisStep(3, "scrna_hvg", "HVG", depends_on=[2]),
                AnalysisStep(4, "scrna_pca", "PCA", depends_on=[3]),
                AnalysisStep(5, "scrna_neighbors", "kNN graph", depends_on=[4]),
                AnalysisStep(6, "scrna_leiden", "Clustering", depends_on=[5]),
                AnalysisStep(7, "scrna_trajectory", "Trajectory/pseudotime", {"method": "dpt"}, depends_on=[4, 5]),
            ]
        if pi == AnalysisIntent.CELL_COMMUNICATION:
            return [
                AnalysisStep(1, "scrna_qc", "QC filtering", {"min_genes": 200}),
                AnalysisStep(2, "scrna_normalize", "Normalize", depends_on=[1]),
                AnalysisStep(3, "scrna_leiden", "Clustering", depends_on=[2]),
                AnalysisStep(4, "scrna_cell_communication", "Ligand-receptor analysis", depends_on=[3]),
            ]
        if pi == AnalysisIntent.INTEGRATION:
            return [AnalysisStep(1, "integration_mofa", "MOFA integration", {"n_factors": 15})]
        return [
            AnalysisStep(1, "scrna_qc", "Quality control", {"min_genes": 200}),
            AnalysisStep(2, "scrna_normalize", "Normalize", depends_on=[1]),
            AnalysisStep(3, "scrna_hvg", "HVG selection", depends_on=[2]),
            AnalysisStep(4, "scrna_pca", "PCA", depends_on=[3]),
            AnalysisStep(5, "scrna_umap", "UMAP visualization", depends_on=[4]),
        ]

    def _estimate_runtime(self, steps: list[AnalysisStep], profile: Optional[DataProfile]) -> float:
        if profile is None or profile.n_cells == 0:
            return len(steps) * 2.0
        base = len(steps) * 0.5
        scale = profile.n_cells / 10000
        gpu_steps = sum(1 for s in steps if s.gpu_beneficial)
        return base * scale * (0.3 if gpu_steps > 0 else 1.0)


_planner: Optional[AnalysisPlanner] = None


def get_planner() -> AnalysisPlanner:
    global _planner
    if _planner is None:
        _planner = AnalysisPlanner()
    return _planner
