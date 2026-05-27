import pytest
import numpy as np
import pandas as pd
import anndata
from omics.score.base import ScoreResult, ScoreCategory
from omics.score.scorers import (
    ImmuneInfiltrationScore,
    PathwayActivityScore,
    IntegratedHealthScore,
)


def test_immune_infiltration_score():
    scorer = ImmuneInfiltrationScore()
    rng = np.random.RandomState(42)
    genes = ['CD8A', 'CD4', 'FOXP3', 'NKG7', 'CD19', 'CD14', 'GAPDH'] + [f'G{i}' for i in range(100)]
    adata = anndata.AnnData(
        X=rng.poisson(3, (500, len(genes))).astype(np.float64),
        obs=pd.DataFrame(index=[f'cell_{i}' for i in range(500)]),
        var=pd.DataFrame(index=genes),
    )
    result = scorer.compute(adata)
    assert 0.0 <= result.score <= 1.0
    assert result.category == ScoreCategory.IMMUNE_INFILTRATION
    assert len(result.contributing_features) > 0


def test_pathway_activity_score():
    scorer = PathwayActivityScore()
    rng = np.random.RandomState(42)
    genes = ['VEGFA', 'HIF1A', 'MYC', 'CDKN1A', 'MDM2'] + [f'G{i}' for i in range(200)]
    adata = anndata.AnnData(
        X=rng.poisson(5, (100, len(genes))).astype(np.float64),
        obs=pd.DataFrame(index=[f'sample_{i}' for i in range(100)]),
        var=pd.DataFrame(index=genes),
    )
    result = scorer.compute(adata)
    assert 0.0 <= result.score <= 1.0
    assert result.category == ScoreCategory.PATHWAY_ACTIVITY


def test_integrated_health_score():
    scorer = IntegratedHealthScore()
    scores = {
        ScoreCategory.IMMUNE_INFILTRATION: ScoreResult(
            0.8, ScoreCategory.IMMUNE_INFILTRATION,
            confidence=0.9, contributing_features=['CD8_T_cell(2.5)']
        ),
        ScoreCategory.PATHWAY_ACTIVITY: ScoreResult(
            0.6, ScoreCategory.PATHWAY_ACTIVITY,
            confidence=0.85, contributing_features=['Hypoxia(z=3.2)']
        ),
    }
    result = scorer.compute(scores)
    assert 0.0 <= result.score <= 1.0
    assert result.category == ScoreCategory.INTEGRATED_HEALTH
    assert len(result.interpretation) > 0


def test_score_result_dataclass():
    sr = ScoreResult(
        score=0.75, category=ScoreCategory.CLONAL_EXPANSION,
        confidence=0.9, contributing_features=['expansion_pct=45%'],
        interpretation="Moderate clonal expansion detected."
    )
    assert sr.score == 0.75
    assert sr.category == ScoreCategory.CLONAL_EXPANSION


def test_explain_adds_interpretation():
    scorer = ImmuneInfiltrationScore()
    result = ScoreResult(0.5, ScoreCategory.IMMUNE_INFILTRATION,
                         confidence=0.8, contributing_features=['CD8_T_cell(3.2)'])
    text = scorer.explain(result)
    assert '0.500' in text or '0.5' in text
    assert 'immune_infiltration' in text


def test_empty_data_returns_zero_score():
    scorer = ImmuneInfiltrationScore()
    adata = anndata.AnnData(
        X=np.random.poisson(3, (100, 10)).astype(np.float64),
        obs=pd.DataFrame(index=[f'cell_{i}' for i in range(100)]),
        var=pd.DataFrame(index=[f'RANDOM{i}' for i in range(10)]),
    )
    result = scorer.compute(adata)
    assert result.score == 0.0
    assert result.confidence == 0.0
