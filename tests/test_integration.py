import pytest
import numpy as np
import pandas as pd
import anndata
from omics.integrate.base import AbstractIntegration
from omics.integrate.analysis import MultiOmicsIntegration


@pytest.fixture
def two_modalities():
    rng = np.random.RandomState(42)
    adata1 = anndata.AnnData(
        X=rng.poisson(3, (100, 50)).astype(np.float64),
        obs=pd.DataFrame(index=[f'cell_{i}' for i in range(100)]),
        var=pd.DataFrame(index=[f'G{i}' for i in range(50)]),
    )
    adata2 = anndata.AnnData(
        X=rng.poisson(2, (100, 30)).astype(np.float64),
        obs=pd.DataFrame(index=[f'cell_{i}' for i in range(100)]),
        var=pd.DataFrame(index=[f'P{i}' for i in range(30)]),
    )
    return [adata1, adata2]


def test_integrate_wnn(two_modalities):
    pytest.importorskip("muon")
    mi = MultiOmicsIntegration()
    result = mi.integrate(two_modalities, method="wnn")
    assert result is not None


def test_integrate_mofa_graceful_fallback(two_modalities):
    """MOFA2 may not be installed; should return MuData with status, not crash."""
    mi = MultiOmicsIntegration()
    result = mi.integrate(two_modalities, method="mofa")
    assert result is not None
    # Should have either mofa results or a status message
    has_results = 'mofa_factors' in result.obsm or 'mofa_status' in result.uns
    assert has_results, "MOFA integration should set factors or status"


def test_abstract_integration_abc():
    assert hasattr(AbstractIntegration, 'integrate')
    assert hasattr(AbstractIntegration, 'factor_analysis')
    assert hasattr(AbstractIntegration, 'cross_modality_prediction')


def test_factor_analysis_no_results():
    mi = MultiOmicsIntegration()
    adata = anndata.AnnData(X=np.eye(10))
    result = mi.factor_analysis(adata)
    assert 'error' in result


def test_cross_modality_prediction_no_factors():
    mi = MultiOmicsIntegration()
    adata = anndata.AnnData(X=np.eye(10))
    with pytest.raises(ValueError, match="No MOFA factors"):
        mi.cross_modality_prediction(adata)


def test_invalid_method(two_modalities):
    mi = MultiOmicsIntegration()
    with pytest.raises(ValueError, match="Unknown method"):
        mi.integrate(two_modalities, method="invalid_method")
