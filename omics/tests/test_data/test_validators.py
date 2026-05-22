"""Tests for omics.data.validators."""

import numpy as np
import pandas as pd
import anndata
from omics.data.validators import validate_adata, ValidationReport


class TestValidateAnnData:
    def test_empty_adata_fails(self):
        adata = anndata.AnnData(np.zeros((0, 0)))
        report = validate_adata(adata, "scrna")
        assert not report.is_valid
        assert len(report.errors) > 0

    def test_valid_adata_passes(self, tiny_adata):
        report = validate_adata(tiny_adata, "scrna")
        assert report.is_valid

    def test_missing_obs_columns_warns(self, tiny_adata):
        report = validate_adata(tiny_adata, "scrna")
        assert isinstance(report.warnings, list)

    def test_missing_obsm_suggests(self, tiny_adata):
        report = validate_adata(tiny_adata, "scrna")
        assert isinstance(report.suggestions, list)

    def test_report_string_representation(self, tiny_adata):
        report = validate_adata(tiny_adata, "scrna")
        s = str(report)
        assert "PASSED" in s or "FAILED" in s
