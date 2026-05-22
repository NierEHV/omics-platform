# scRNA-seq Standard Analysis SOP

## Overview
Standard scRNA-seq analysis pipeline: QC → Normalize → HVG → PCA → UMAP → Leiden → Markers → Annotate

## Steps

### 1. Data Inspection
- Tool: `omics_data_info`
- Check: n_obs, n_vars, available .obs columns (look for batch, condition)
- Verify: raw counts in .X (not log-normalized)
- Note: if 'leiden' or 'X_umap' already present, data may be preprocessed

### 2. Quality Control
- Tool: `omics_scrna_qc`
- Parameters: min_genes=200, min_cells=3, max_mt_pct=20
- Expected: 10-30% cell filtering is normal
- Warning: if >50% cells filtered, review thresholds or input quality

### 3. Standard Pipeline
- Tool: `omics_pipeline_run` preset=quick
- This runs: Normalize → HVG(2000) → PCA(50) → Neighbors(15) → UMAP → Leiden(1.0) → Markers
- GPU: use_gpu=True for datasets >50k cells
- Check output: number of clusters, UMAP embedding shape

### 4. Marker Gene Analysis
- Tool: `omics_scrna_markers`
- Parameters: method=wilcoxon, n_genes=50-100
- Review: top 5 markers per cluster, check p_adj < 0.05 and |log2FC| > 1
- Validate: are markers biologically meaningful for the tissue?

### 5. Cell Type Annotation
- Tool: `omics_scrna_annotate`
- Method: marker_based (fast) or celltypist (automatic, requires internet)
- If using marker_based: provide tissue-appropriate marker gene list
- Review: do cell type proportions match expected tissue composition?

### 6. Visualization
- Tool: `omics_visualize` type=umap, color_by=leiden (or cell_type)
- Tool: `omics_visualize` type=dotplot (for marker gene expression)
- Style: nature for publication, default for exploration

### 7. Optional: Trajectory Analysis
- Tool: `omics_scrna_trajectory` method=dpt
- Requires: PCA and neighbors already computed
- Useful for: developmental systems, differentiation hierarchies

### 8. Optional: Cell Communication
- Tool: `omics_scrna_cell_communication`
- Identifies: ligand-receptor pairs between cell types
- Useful for: tumor microenvironment, immune cell interactions

## Quality Checks After Each Step
- [ ] QC: >1000 cells retained
- [ ] PCA: explained variance >30% in first 50 PCs
- [ ] UMAP: distinct clusters visible
- [ ] Clustering: 5-30 clusters typical for PBMC, adjust resolution if needed
- [ ] Markers: known markers appear for expected cell types
- [ ] Annotation: >80% cells annotated with confidence
