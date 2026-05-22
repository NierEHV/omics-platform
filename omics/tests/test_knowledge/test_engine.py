"""Tests for omics.knowledge.engine."""

import json
from pathlib import Path
from omics.knowledge.engine import GeneSetLibrary, KnowledgeEngine


class TestGeneSetLibrary:
    def test_load_hallmark(self):
        lib = GeneSetLibrary()
        hallmark = lib.load("hallmark")
        assert hallmark is not None
        assert len(hallmark) > 0

    def test_load_cell_markers(self):
        lib = GeneSetLibrary()
        markers = lib.load("cell_markers")
        assert markers is not None
        assert len(markers) > 0

    def test_file_map_has_all_sets(self):
        lib = GeneSetLibrary()
        assert "hallmark" in lib._file_map
        assert "go_bp" in lib._file_map
        assert "cell_markers" in lib._file_map


class TestKnowledgeEngine:
    def test_enrichment_runs(self, full_adata):
        engine = KnowledgeEngine()
        engine._gene_sets._cache = {}  # ensure fresh load
        results = engine.run_enrichment(
            gene_list=["GENE_5", "GENE_10", "GENE_15", "GENE_20", "GENE_25"],
            background=full_adata.var_names.tolist(),
            database="go_bp",
        )
        assert isinstance(results, list)

    def test_match_cell_types(self, full_adata):
        engine = KnowledgeEngine()
        cluster_genes = {
            "0": ["GENE_0", "GENE_5", "GENE_10"],
            "1": ["GENE_20", "GENE_25", "GENE_30"],
        }
        matches = engine.match_cell_types(cluster_genes)
        assert isinstance(matches, list)

    def test_summarize_findings(self, full_adata):
        engine = KnowledgeEngine()
        engine._gene_sets._cache = {}
        kc = engine.run_on_results(full_adata, groupby="leiden")
        assert kc is not None
        summary = kc.to_markdown()
        assert isinstance(summary, str)
        assert len(summary) > 0
