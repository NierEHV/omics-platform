#!/usr/bin/env python
"""Multi-Omics Analysis Platform — CLI entry point.

Usage:
    omics data import scrna PATH
    omics data fetch GEO_ACCESSION
    omics scrna pipeline --input sample.h5ad
    omics viz umap --input adata.h5ad --color cell_type
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from omics.utils.config import Config, scaffold_project
from omics.utils.logging import setup_logging, status, success, error, print_table

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option("--config", "-c", "config_path", type=click.Path(), help="Path to config.yaml")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose (DEBUG) output")
@click.option("--gpu/--no-gpu", default=True, help="Enable/disable GPU acceleration")
@click.pass_context
def omics(ctx, config_path, verbose, gpu):
    """Multi-Omics Analysis Platform — scRNA-seq, Spatial, 16S, Metagenomics."""
    ctx.ensure_object(dict)
    ctx.obj["gpu_enabled"] = gpu
    ctx.obj["config"] = Config.load(Path(config_path)) if config_path else Config.load()
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)


# ---- data ----

@omics.group()
def data():
    """Data import, fetch, and inspection."""


@data.command("import")
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output .h5ad path")
def data_import(path, output):
    """Import scRNA-seq data (h5ad, 10x mtx, CSV, TSV)."""
    from omics.data.loader import SCRNABuilder
    from omics.utils.io import write_h5ad
    status(f"Importing: {path}")
    p = Path(path)
    if p.suffix == ".h5ad":
        adata = SCRNABuilder.from_h5ad(p)
    elif p.is_dir():
        adata = SCRNABuilder.from_10x_mtx(p)
    elif p.suffix in (".csv", ".tsv", ".txt"):
        import pandas as pd
        df = pd.read_csv(p, sep="\t" if p.suffix == ".tsv" else ",", index_col=0)
        adata = SCRNABuilder.from_dataframe(df)
    else:
        error(f"Unsupported format: {p.suffix}")
        raise SystemExit(1)
    out = Path(output) if output else Path.cwd() / f"{p.stem}_imported.h5ad"
    write_h5ad(adata, out)
    success(f"Imported: {adata.n_obs} cells x {adata.n_vars} genes -> {out}")


@data.command("fetch")
@click.argument("accession")
@click.option("--output-dir", "-o", type=click.Path(), default="data/raw")
@click.pass_context
def data_fetch(ctx, accession, output_dir):
    """Download public data from GEO/SRA/ENA."""
    from omics.data.geo import geo_to_anndata
    from omics.utils.io import write_h5ad
    status(f"Fetching {accession} from GEO...")
    try:
        adata = geo_to_anndata(accession, Path(output_dir))
        out = Path(output_dir) / f"{accession}.h5ad"
        write_h5ad(adata, out)
        success(f"Downloaded: {adata.n_obs} samples x {adata.n_vars} features -> {out}")
    except Exception as e:
        error(f"Failed to fetch {accession}: {e}")
        raise SystemExit(1)


@data.command("search")
@click.argument("query")
@click.option("--max-results", "-n", type=int, default=20)
def data_search(query, max_results):
    """Search GEO for datasets by keyword."""
    from omics.data.geo import search_geo_datasets
    status(f"Searching GEO for: {query}")
    results = search_geo_datasets(query, max_results)
    if not results:
        click.echo("No results found.")
        return
    rows = [[r.accession, r.title[:60], str(r.n_samples), r.organism, r.platform[:30]]
            for r in results]
    print_table(["Accession", "Title", "Samples", "Organism", "Platform"], rows)


@data.command("info")
@click.argument("path", type=click.Path(exists=True))
def data_info(path):
    """Show AnnData structure and contents."""
    from omics.utils.io import get_adata_summary, read_h5ad
    adata = read_h5ad(Path(path))
    click.echo(get_adata_summary(adata))


# ---- scrna ----

@omics.group()
def scrna():
    """Single-cell RNA-seq analysis."""


@scrna.command("qc")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), required=True)
@click.option("--min-genes", type=int, default=200)
@click.option("--min-cells", type=int, default=3)
@click.option("--max-pct-mt", type=float, default=20.0)
@click.option("--output", "-o", help="Output .h5ad path")
def scrna_qc(input_path, min_genes, min_cells, max_pct_mt, output):
    """Quality control: filter cells and genes."""
    from omics.scrna.qc import run_qc
    from omics.utils.io import read_h5ad, write_h5ad
    status("Running QC...")
    adata = read_h5ad(Path(input_path))
    adata = run_qc(adata, min_genes=min_genes, min_cells=min_cells, max_pct_mt=max_pct_mt)
    out = Path(output) if output else Path(input_path).parent / f"{Path(input_path).stem}_qc.h5ad"
    write_h5ad(adata, out)
    success(f"QC: {adata.n_obs} cells x {adata.n_vars} genes -> {out}")


@scrna.command("normalize")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), required=True)
@click.option("--target-sum", type=int, default=10000)
@click.option("--output", "-o", help="Output .h5ad path")
def scrna_normalize(input_path, target_sum, output):
    """Normalize and log-transform expression."""
    from omics.scrna.normalize import run_normalize
    from omics.utils.io import read_h5ad, write_h5ad
    status("Normalizing...")
    adata = read_h5ad(Path(input_path))
    adata = run_normalize(adata, target_sum=target_sum)
    out = Path(output) if output else Path(input_path).parent / f"{Path(input_path).stem}_norm.h5ad"
    write_h5ad(adata, out)
    success(f"Normalized: target_sum={target_sum} -> {out}")


@scrna.command("hvg")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), required=True)
@click.option("--n-hvg", type=int, default=2000)
@click.option("--output", "-o", help="Output .h5ad path")
def scrna_hvg(input_path, n_hvg, output):
    """Select highly variable genes."""
    from omics.scrna.hvg import run_hvg
    from omics.utils.io import read_h5ad, write_h5ad
    status("Selecting HVGs...")
    adata = read_h5ad(Path(input_path))
    adata = run_hvg(adata, n_top_genes=n_hvg)
    out = Path(output) if output else Path(input_path).parent / f"{Path(input_path).stem}_hvg.h5ad"
    write_h5ad(adata, out)
    success(f"HVGs: {adata.var.highly_variable.sum()} selected -> {out}")


@scrna.command("reduce")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), required=True)
@click.option("--n-pcs", type=int, default=50)
@click.option("--n-neighbors", type=int, default=15)
@click.option("--output", "-o", help="Output .h5ad path")
@click.pass_context
def scrna_reduce(ctx, input_path, n_pcs, n_neighbors, output):
    """Dimensionality reduction (PCA + UMAP)."""
    from omics.scrna.pca import run_pca
    from omics.scrna.neighbors import run_neighbors
    from omics.scrna.umap import run_umap
    from omics.utils.io import read_h5ad, write_h5ad
    status("Reducing dimensions...")
    use_gpu = ctx.obj.get("gpu_enabled", False)
    adata = read_h5ad(Path(input_path))
    adata = run_pca(adata, n_comps=n_pcs, use_gpu=use_gpu)
    adata = run_neighbors(adata, n_neighbors=n_neighbors)
    adata = run_umap(adata, use_gpu=use_gpu)
    out = Path(output) if output else Path(input_path).parent / f"{Path(input_path).stem}_reduced.h5ad"
    write_h5ad(adata, out)
    success(f"PCA ({n_pcs}) + UMAP complete -> {out}")


@scrna.command("cluster")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), required=True)
@click.option("--resolution", type=float, default=1.0)
@click.option("--output", "-o", help="Output .h5ad path")
def scrna_cluster(input_path, resolution, output):
    """Leiden clustering."""
    from omics.scrna.cluster import run_leiden
    from omics.utils.io import read_h5ad, write_h5ad
    status("Clustering...")
    adata = read_h5ad(Path(input_path))
    adata = run_leiden(adata, resolution=resolution)
    n = adata.obs["leiden"].nunique()
    out = Path(output) if output else Path(input_path).parent / f"{Path(input_path).stem}_clustered.h5ad"
    write_h5ad(adata, out)
    success(f"{n} clusters (resolution={resolution}) -> {out}")


@scrna.command("markers")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), required=True)
@click.option("--group-by", default="leiden")
@click.option("--n-genes", type=int, default=100)
@click.option("--output", help="Output CSV path")
def scrna_markers(input_path, group_by, n_genes, output):
    """Find marker genes per cluster."""
    from omics.scrna.markers import run_markers, get_marker_table
    from omics.utils.io import read_h5ad
    status("Finding markers...")
    adata = read_h5ad(Path(input_path))
    adata = run_markers(adata, groupby=group_by, n_genes=n_genes)
    df = get_marker_table(adata)
    out = Path(output) if output else Path.cwd() / "marker_genes.csv"
    df.to_csv(out, index=False)
    success(f"Markers: top {n_genes} per group -> {out}")


@scrna.command("pipeline")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), required=True)
@click.option("--output-dir", "-o", type=click.Path(), default=".")
@click.pass_context
def scrna_pipeline(ctx, input_path, output_dir):
    """Run full scRNA-seq pipeline (QC -> normalize -> HVG -> PCA -> UMAP -> cluster -> markers)."""
    from omics.scrna.pipeline import run_standard_pipeline
    from omics.utils.io import read_h5ad, write_h5ad
    status("Running full scRNA-seq pipeline...")
    p = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    adata = read_h5ad(p)
    use_gpu = ctx.obj.get("gpu_enabled", False)
    adata = run_standard_pipeline(adata, use_gpu=use_gpu)
    out = out_dir / f"{p.stem}_processed.h5ad"
    write_h5ad(adata, out)
    success(f"Pipeline complete: {adata.n_obs} cells, {adata.obs['leiden'].nunique()} clusters -> {out}")


# ---- viz ----

@omics.group()
def viz():
    """Publication-ready figure generation."""


@viz.command("umap")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), required=True)
@click.option("--color", default="leiden")
@click.option("--output", "-o", help="Output figure path")
def viz_umap(input_path, color, output):
    """UMAP embedding plot."""
    from omics.sdk import VizSDK
    from omics.utils.io import read_h5ad
    adata = read_h5ad(Path(input_path))
    sdk_viz = VizSDK(None)
    sdk_viz.umap(adata, color=color, output_path=output)
    out = output or "umap.pdf"
    success(f"UMAP -> {out}")


@viz.command("compose")
@click.option("--input", "-i", "input_path", type=click.Path(exists=True), required=True)
@click.option("--template", "-t", type=click.Choice(["cell_type_atlas", "differential_response",
                "trajectory_analysis", "qc_report", "integration_overview"]), default="cell_type_atlas")
@click.option("--output", "-o", help="Output figure path (PDF)")
def viz_compose(input_path, template, output):
    """Compose a multi-panel publication figure from a template."""
    from omics.viz.composer import SmartComposer
    from omics.utils.io import read_h5ad
    status(f"Composing '{template}' figure...")
    adata = read_h5ad(Path(input_path))
    story = SmartComposer.load_template(template)
    composer = SmartComposer()
    out = Path(output) if output else Path.cwd() / f"{template}.pdf"
    composer.compose(story, adata, output_path=out)
    success(f"Figure -> {out}")


# ---- gpu ----

@omics.group()
def gpu():
    """GPU management and monitoring."""


@gpu.command("status")
def gpu_status():
    """Show GPU information."""
    from omics.gpu.manager import get_gpu_manager
    click.echo(get_gpu_manager().summary())


# ---- project ----

@omics.group()
def project():
    """Project management."""


@project.command("new")
@click.argument("title", required=False)
@click.option("--description", "-d", default="")
@click.option("--base-dir", "-b", type=click.Path(), default="projects")
def project_new(title, description, base_dir):
    """Create a new analysis project."""
    meta = scaffold_project(Path(base_dir), title or "Untitled Project", description)
    success(f"Created project: {meta['project_id']} — '{meta['title']}'")


# ---- provenance ----

@omics.group()
def provenance():
    """Analysis provenance: track and reproduce analyses."""


@provenance.command("list")
@click.option("--limit", type=int, default=20)
def provenance_list(limit):
    """List recent provenance records."""
    from omics.pipeline.provenance import ProvenanceStore
    store = ProvenanceStore()
    records = store.list_all(limit=limit)
    if not records:
        click.echo("No provenance records.")
        return
    rows = [[r.analysis_id, r.timestamp[:19], r.pipeline_name or "-", r.status,
             f"{r.duration_seconds:.1f}s" if r.duration_seconds else "-"]
            for r in records]
    print_table(["Analysis ID", "Timestamp", "Pipeline", "Status", "Duration"], rows)


@provenance.command("show")
@click.argument("analysis_id")
def provenance_show(analysis_id):
    """Show detailed provenance for an analysis."""
    from omics.pipeline.provenance import ProvenanceStore
    store = ProvenanceStore()
    record = store.load(analysis_id)
    if record is None:
        error(f"Analysis '{analysis_id}' not found.")
        return
    click.echo(f"Analysis: {record.analysis_id}")
    click.echo(f"Pipeline: {record.pipeline_name}")
    click.echo(f"Status: {record.status}")
    click.echo(f"Duration: {record.duration_seconds:.2f}s")
    click.echo(f"Parameters: {record.parameters}")


# ---- Entry point ----

def main():
    omics()


if __name__ == "__main__":
    main()
