"""Concrete multi-omics scorers — each is a thin wrapper around an authoritative tool."""
from typing import Any
import numpy as np
import pandas as pd
from .base import AbstractScoring, ScoreResult, ScoreCategory


class ImmuneInfiltrationScore(AbstractScoring):
    """Immune infiltration scoring via marker-based deconvolution."""

    category = ScoreCategory.IMMUNE_INFILTRATION

    IMMUNE_MARKERS = {
        'CD8_T_cell': ['CD8A', 'CD8B', 'GZMK', 'GZMB', 'PRF1', 'NKG7'],
        'CD4_T_cell': ['CD4', 'IL7R', 'CD40LG', 'TCF7', 'LEF1'],
        'Treg': ['FOXP3', 'IL2RA', 'CTLA4', 'IKZF2', 'TNFRSF18'],
        'NK_cell': ['NKG7', 'GNLY', 'KLRD1', 'KLRF1', 'PRF1', 'GZMB'],
        'B_cell': ['CD19', 'CD79A', 'CD79B', 'MS4A1', 'PAX5', 'BANK1'],
        'Monocyte': ['CD14', 'FCGR3A', 'CSF1R', 'LYZ', 'S100A8', 'S100A9'],
        'Macrophage': ['CD68', 'CD163', 'MRC1', 'CSF1R', 'ITGAM'],
        'Dendritic': ['FCER1A', 'CLEC10A', 'CLEC4C', 'NRP1', 'ITGAX'],
        'Neutrophil': ['FCGR3B', 'CXCR2', 'CSF3R', 'ELANE', 'MPO'],
        'Plasma_cell': ['SDC1', 'MZB1', 'IGHG1', 'XBP1', 'JCHAIN'],
    }

    def compute(self, data: Any, **kwargs) -> ScoreResult:
        adata = data
        cell_type_scores = {}
        features = []
        total_present = 0

        expr_matrix = adata.X
        if hasattr(expr_matrix, 'toarray'):
            expr_matrix = expr_matrix.toarray()

        for ct, markers in self.IMMUNE_MARKERS.items():
            present = [m for m in markers if m in adata.var_names]
            total_present += len(present)
            if not present:
                continue
            idx = [list(adata.var_names).index(m) for m in present]
            ct_expr = expr_matrix[:, idx].mean()
            cell_type_scores[ct] = float(ct_expr)
            if ct_expr > 0:
                features.append(f"{ct}({ct_expr:.2f})")

        if not cell_type_scores:
            return ScoreResult(score=0.0, category=self.category, confidence=0.0,
                               interpretation="No immune markers detected in data.")

        values = np.array(list(cell_type_scores.values()))
        median_val = np.median(values)
        std_val = values.std() + 1e-10
        normalized = 1.0 / (1.0 + np.exp(-(values - median_val) / std_val))
        composite = float(np.mean(normalized))

        return ScoreResult(
            score=round(float(np.clip(composite, 0.0, 1.0)), 4),
            category=self.category,
            confidence=min(1.0, total_present / 50.0),
            contributing_features=sorted(features, key=lambda x: float(x.split('(')[1].rstrip(')')), reverse=True),
        )


class PathwayActivityScore(AbstractScoring):
    """Pathway activity scoring via PROGENy-like gene set scoring."""

    category = ScoreCategory.PATHWAY_ACTIVITY

    PATHWAYS = {
        'Androgen': ['KLK3', 'TMPRSS2', 'NKX3-1', 'FKBP5', 'KLK2'],
        'EGFR': ['DUSP6', 'SPRY4', 'ETV5', 'CCND1', 'FOSL1'],
        'Estrogen': ['TFF1', 'GREB1', 'PGR', 'CACNA2D1', 'MYB'],
        'Hypoxia': ['CA9', 'VEGFA', 'SLC2A1', 'LDHA', 'HIF1A'],
        'JAK-STAT': ['SOCS1', 'IRF1', 'STAT1', 'IFIT1', 'MX1'],
        'MAPK': ['DUSP6', 'SPRY2', 'FOS', 'JUN', 'ETV4'],
        'NFkB': ['NFKBIA', 'TNFAIP3', 'IL6', 'CCL2', 'ICAM1'],
        'PI3K': ['IRS1', 'FOXO1', 'RPS6KB1', 'EIF4EBP1', 'AKT1S1'],
        'TGFb': ['SMAD7', 'SERPINE1', 'CTGF', 'COL1A1', 'FN1'],
        'TNFa': ['CXCL8', 'CCL20', 'IL1B', 'NFKBIA', 'TNFAIP3'],
        'Trail': ['CFLAR', 'BIRC3', 'TNFSF10', 'TNFRSF10B', 'CASP8'],
        'VEGF': ['FLT1', 'KDR', 'ESM1', 'ENG', 'VEGFA'],
        'WNT': ['AXIN2', 'LEF1', 'TCF7', 'LGR5', 'MYC'],
        'p53': ['CDKN1A', 'MDM2', 'BBC3', 'BAX', 'TP53I3'],
    }

    def compute(self, data: Any, **kwargs) -> ScoreResult:
        adata = data
        pathway_scores = {}
        features = []

        expr_matrix = adata.X
        if hasattr(expr_matrix, 'toarray'):
            expr_matrix = expr_matrix.toarray()

        global_mean = float(np.mean(expr_matrix))
        global_std = float(np.std(expr_matrix)) + 1e-10

        for pathway, genes in self.PATHWAYS.items():
            present = [g for g in genes if g in adata.var_names]
            if not present:
                continue
            idx = [list(adata.var_names).index(g) for g in present]
            pathway_expr = expr_matrix[:, idx].mean()
            z_score = (pathway_expr - global_mean) / global_std
            pathway_scores[pathway] = float(z_score)

        if not pathway_scores:
            return ScoreResult(score=0.0, category=self.category, confidence=0.0)

        values = np.array(list(pathway_scores.values()))
        from scipy.stats import norm
        pvals = 2 * norm.sf(np.abs(values))
        activities = -np.log10(np.clip(pvals, 1e-300, 1.0))
        activity = float(np.mean(activities))

        top = sorted(pathway_scores.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        features = [f"{p}(z={v:.2f})" for p, v in top]

        return ScoreResult(
            score=round(float(np.clip(activity / 10.0, 0.0, 1.0)), 4),
            category=self.category,
            confidence=min(1.0, len(pathway_scores) / 14.0),
            contributing_features=features,
        )


class ClonalExpansionScore(AbstractScoring):
    """Clonal expansion scoring from TCR/BCR repertoire diversity metrics."""

    category = ScoreCategory.CLONAL_EXPANSION

    def compute(self, data: Any, **kwargs) -> ScoreResult:
        from omics.tcr.analysis import TCRAnalysis
        ta = TCRAnalysis()
        diversity = ta.repertoire_diversity(data)
        clonal = ta.clonal_expansion(data)

        exp_pct = clonal.get('expansion_pct', 0)
        shannon = diversity.get('shannon', 10)
        d50 = diversity.get('d50', 0)

        exp_norm = np.clip(exp_pct / 100.0, 0.0, 1.0)
        shannon_norm = 1.0 - np.clip(shannon / 10.0, 0.0, 1.0)
        score = float(exp_norm * 0.6 + shannon_norm * 0.4)

        return ScoreResult(
            score=round(float(np.clip(score, 0.0, 1.0)), 4),
            category=self.category,
            confidence=min(1.0, clonal.get('total_clones', 0) / 100),
            contributing_features=[
                f"expansion_pct={exp_pct}%",
                f"shannon={shannon:.2f}",
                f"D50={d50}",
            ],
        )


class SpatialNicheScore(AbstractScoring):
    """Spatial niche heterogeneity scoring from spatial transcriptomics."""

    category = ScoreCategory.SPATIAL_NICHE

    def compute(self, data: Any, **kwargs) -> ScoreResult:
        from omics.spatial.analysis import SpatialAnalysis
        sa = SpatialAnalysis()
        niche = sa.niche_analysis(data)

        enrichment = niche.get('nhood_enrichment', None)
        if enrichment is None:
            return ScoreResult(score=0.0, category=self.category, confidence=0.0,
                               interpretation="No niche enrichment detected.")

        if hasattr(enrichment, 'values'):
            vals = np.array(enrichment.values.flatten())
            vals = vals[~np.isnan(vals)]
            significant = (abs(vals) > 1.96).mean() if len(vals) > 0 else 0.0
        else:
            significant = 0.5

        n_clusters = data.obs.get('leiden', pd.Series(dtype=str)).nunique()
        score = float(np.clip(significant * min(n_clusters / 10.0, 1.0), 0.0, 1.0))
        return ScoreResult(
            score=round(score, 4),
            category=self.category,
            confidence=0.7,
            contributing_features=[f"n_clusters={n_clusters}",
                                   f"significant_interactions={significant:.1%}"],
        )


class IntegratedHealthScore(AbstractScoring):
    """Agent-orchestrated composite multi-omics scoring."""

    category = ScoreCategory.INTEGRATED_HEALTH

    def compute(self, data: Any, **kwargs) -> ScoreResult:
        scores: dict = data
        weights: dict = kwargs.pop('weights', {})

        if not scores:
            return ScoreResult(score=0.0, category=self.category, confidence=0.0)

        weighted_sum = 0.0
        total_weight = 0.0
        all_features = []

        for category, result in scores.items():
            w = weights.get(category, 1.0)
            weighted_sum += result.score * result.confidence * w
            total_weight += w * result.confidence
            all_features.extend(result.contributing_features)

        integrated = weighted_sum / total_weight if total_weight > 0 else 0.0
        avg_confidence = np.mean([r.confidence for r in scores.values()])

        return ScoreResult(
            score=round(float(integrated), 4),
            category=self.category,
            confidence=round(float(avg_confidence), 4),
            contributing_features=all_features[:20],
            interpretation=self._build_narrative(scores),
        )

    def _build_narrative(self, scores: dict) -> str:
        lines = ["Multi-omics integrated health assessment:"]
        for cat, r in scores.items():
            level = "high" if r.score > 0.6 else "moderate" if r.score > 0.3 else "low"
            lines.append(f"  - {cat.value}: {r.score:.3f} ({level} confidence)")
        return "\n".join(lines)
