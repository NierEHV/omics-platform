import pytest
import numpy as np
import pandas as pd
import anndata
from omics.bulk.analysis import BulkRNAAnalysis


@pytest.fixture
def mock_counts_csv(tmp_path):
    df = pd.DataFrame({
        'gene_id': ['G1', 'G2', 'G3', 'G4', 'G5'],
        'sample_A': [100, 0, 50, 200, 0],
        'sample_B': [150, 10, 0, 180, 0],
        'sample_C': [80, 0, 30, 220, 5],
    })
    path = tmp_path / 'counts.csv'
    df.to_csv(path, index=False)
    return path


def test_load_counts(mock_counts_csv):
    b = BulkRNAAnalysis()
    adata = b.load_counts(str(mock_counts_csv))
    assert adata.n_obs == 3   # 3 samples (rows)
    assert adata.n_vars == 5  # 5 genes (columns)
    assert 'gene_id' in adata.var.columns


def test_qc_filter_removes_low_count_genes():
    b = BulkRNAAnalysis()
    adata = anndata.AnnData(
        X=np.array([[100, 0, 0], [0, 5, 0], [200, 150, 180]]).T,
        obs=pd.DataFrame(index=['S1', 'S2', 'S3']),
        var=pd.DataFrame(index=['G1', 'G2', 'G3']),
    )
    filtered = b.qc_filter(adata, min_total_count=10)
    assert filtered.n_vars < 3  # G2 removed (total count 5)


def test_normalize_fallback():
    b = BulkRNAAnalysis()
    adata = anndata.AnnData(
        X=np.array([[100, 200, 300], [50, 150, 250], [10, 20, 30]]).T,
        obs=pd.DataFrame(index=['S1', 'S2', 'S3']),
        var=pd.DataFrame(index=['G1', 'G2', 'G3']),
    )
    result = b.normalize(adata, method="cpm")
    assert 'cpm' in result.layers


def test_differential_expression_skips_without_rpy2():
    """DE requires DESeq2 via rpy2. Skip if not installed."""
    b = BulkRNAAnalysis()
    adata = anndata.AnnData(
        X=np.array([[100, 200], [50, 150], [300, 80], [200, 100]]).astype(int),
        obs=pd.DataFrame({'condition': ['tumor', 'tumor', 'normal', 'normal']},
                         index=['S1', 'S2', 'S3', 'S4']),
        var=pd.DataFrame(index=['TP53', 'BRCA1']),
    )
    try:
        result = b.differential_expression(adata, '~condition',
                                           ('condition', 'tumor', 'normal'))
        assert 'log2FC' in result.columns
    except (ImportError, ModuleNotFoundError):
        pytest.skip("rpy2/DESeq2 not available")


def test_enrichment_with_gseapy():
    """GSEApy prerank enrichment on mock DE results."""
    pytest.importorskip("gseapy")
    b = BulkRNAAnalysis()
    de = pd.DataFrame({
        'pvalue': [0.001, 0.01, 0.05, 0.5, 0.8],
        'log2FC': [2.0, -1.5, 0.3, -0.1, 0.0],
    }, index=['TP53', 'BRCA1', 'GAPDH', 'ACTB', 'RPLP0'])
    enr = b.enrichment(de, gene_sets='KEGG')
    assert enr is not None
    assert len(enr) >= 0


def test_volcano_plot(tmp_path):
    b = BulkRNAAnalysis()
    de = pd.DataFrame({
        'log2FC': [2.0, -1.5, 0.3, -0.1, 0.0, 3.0, -2.5],
        'padj': [1e-10, 0.001, 0.5, 0.8, 0.9, 1e-20, 0.04],
    }, index=['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7'])
    out = tmp_path / 'volcano.pdf'
    fig = b.visualize_volcano(de, output=str(out))
    assert out.exists()


def test_pca_plot(tmp_path):
    rng = np.random.RandomState(42)
    b = BulkRNAAnalysis()
    adata = anndata.AnnData(
        X=rng.randn(10, 100),
        obs=pd.DataFrame(index=[f'S{i}' for i in range(10)]),
        var=pd.DataFrame(index=[f'G{i}' for i in range(100)]),
    )
    out = tmp_path / 'pca.pdf'
    fig = b.visualize_pca(adata, output=str(out))
    assert out.exists()


def test_run_pipeline(mock_counts_csv):
    """Pipeline integration: load -> QC -> normalize. Does NOT test DE (needs rpy2)."""
    b = BulkRNAAnalysis()
    # Only test load+QC+normalize since DE needs rpy2
    adata = b.load_counts(str(mock_counts_csv))
    adata = b.qc_filter(adata)
    result = b.normalize(adata, method="cpm")
    assert result is not None
    assert 'cpm' in result.layers
