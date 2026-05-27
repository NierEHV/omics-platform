import pytest
import numpy as np
import pandas as pd
import anndata
from omics.tcr.analysis import TCRAnalysis


@pytest.fixture
def mock_tcr_csv(tmp_path):
    df = pd.DataFrame({
        'cell_id': ['cell_1', 'cell_1', 'cell_2', 'cell_3', 'cell_3'],
        'locus': ['TRA', 'TRB', 'TRB', 'TRA', 'TRB'],
        'v_call': ['TRAV1-1', 'TRBV2', 'TRBV3', 'TRAV4', 'TRBV5'],
        'j_call': ['TRAJ1', 'TRBJ2', 'TRBJ3', 'TRAJ4', 'TRBJ5'],
        'cdr3_aa': ['CAA', 'CBB', 'CCC', 'CDD', 'CEE'],
        'cdr3_nt': ['NAA', 'NBB', 'NCC', 'NDD', 'NEE'],
    })
    path = tmp_path / 'tcr_data.csv'
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def mock_tcr_adata():
    return anndata.AnnData(obs=pd.DataFrame({
        'cdr3_aa': ['AAAA', 'AAAA', 'AAAA', 'BBBB', 'CCCC', 'DDDD', 'EEEE'],
        'v_call': ['TRBV1', 'TRBV1', 'TRBV1', 'TRBV2', 'TRBV3', 'TRBV4', 'TRBV5'],
        'j_call': ['TRBJ1', 'TRBJ1', 'TRBJ1', 'TRBJ2', 'TRBJ3', 'TRBJ4', 'TRBJ5'],
    }))


def test_load_vdj_csv(mock_tcr_csv):
    ta = TCRAnalysis()
    adata = ta.load_vdj(str(mock_tcr_csv))
    assert adata is not None
    assert adata.n_obs > 0


def test_repertoire_diversity(mock_tcr_adata):
    ta = TCRAnalysis()
    def _mock_define(x, **kw):
        x.obs['clonotype'] = ['c1', 'c1', 'c1', 'c2', 'c3', 'c4', 'c5']
        return x
    ta.define_clonotypes = _mock_define
    result = ta.repertoire_diversity(mock_tcr_adata)
    assert 'shannon' in result
    assert 'simpson' in result
    assert result['shannon'] > 0


def test_cdr3_analysis(mock_tcr_adata):
    ta = TCRAnalysis()
    result = ta.cdr3_analysis(mock_tcr_adata)
    assert 'mean_length' in result or 'error' in result


def test_clonotype_overlap():
    ta = TCRAnalysis()
    a1 = anndata.AnnData(obs=pd.DataFrame({'clonotype': ['c1', 'c1', 'c2', 'c3']}))
    a2 = anndata.AnnData(obs=pd.DataFrame({'clonotype': ['c1', 'c2', 'c4', 'c5']}))
    result = ta.clonotype_overlap([a1, a2])
    assert result.shape == (2, 2)
    assert np.isclose(result.iloc[0, 1], 2/5, atol=0.01)


def test_vj_usage(mock_tcr_adata):
    ta = TCRAnalysis()
    result = ta.vj_usage(mock_tcr_adata)
    assert 'gene' in result.columns
    assert 'frequency' in result.columns


def test_clonal_expansion(mock_tcr_adata):
    ta = TCRAnalysis()
    def _mock_define(x, **kw):
        x.obs['clonotype'] = ['c1', 'c1', 'c1', 'c2', 'c3', 'c4', 'c5']
        return x
    ta.define_clonotypes = _mock_define
    result = ta.clonal_expansion(mock_tcr_adata)
    assert result['total_clones'] == 5
    assert result['expanded_clones'] == 1


def test_immune_repertoire_profile(mock_tcr_adata):
    ta = TCRAnalysis()
    def _mock_define(x, **kw):
        x.obs['clonotype'] = ['c1', 'c1', 'c1', 'c2', 'c3', 'c4', 'c5']
        return x
    ta.define_clonotypes = _mock_define
    result = ta.immune_repertoire_profile(mock_tcr_adata)
    assert 'diversity' in result
    assert 'clonal_expansion' in result


def test_tcr_distance():
    ta = TCRAnalysis()
    adata = anndata.AnnData(obs=pd.DataFrame({
        'cdr3_aa': ['AAAA', 'AAAA', 'BBBB'],
    }))
    result = ta.tcr_distance(adata)
    assert result.shape == (3, 3)
    assert result[0, 1] == 0.0  # identical sequences
    assert result[0, 2] > 0  # different sequences
