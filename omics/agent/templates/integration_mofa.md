# Multi-Omics Integration SOP (MOFA / Mowgli)

## Overview
Multi-omics factor analysis integrates scRNA-seq, spatial, 16S, and metagenomics data
into a shared latent space for cross-modality pattern discovery.

## Prerequisites
- [ ] Each modality processed separately (QC, normalization, clustering)
- [ ] All modalities share the same samples (or have overlapping features)
- [ ] MuData object built with all modalities
- [ ] GPU recommended for datasets >100k total observations

## Steps

### 1. Prepare Each Modality
- scRNA: Run scrna_standard SOP first
- Spatial: Spatial preprocessing (squidpy)
- 16S: DADA2 → taxonomy → diversity metrics
- Metagenomics: Kraken2 → species abundance → functional annotation

### 2. Build MuData
- Tool: `omics_data_import` modality=integration
- Input: list of per-modality .h5ad files
- Verify: `omics_data_info` on .h5mu file

### 3. Run Integration
- Tool: `omics_integrate` method=moa, modalities=scrna,spatial,16s
- Parameters: n_factors=15 (default), scale=True
- GPU: recommended for MOFA with >20 factors

### 4. Interpret Factors
- Check: factor variance explained per modality
- Identify: factors that capture cross-modality covariance
- Plot: factor values on UMAP (omics_visualize color_by=Factor1)

### 5. Cross-Kingdom Analysis (optional)
- Tool: `omics_integrate` method=cross_kingdom
- Identifies: host-microbiome correlations
- Requires: paired host scRNA + 16S/metagenomics per sample

## Expected Outputs
- Factor loadings (which genes/ASVs/species drive each factor)
- Sample scores (factor values per sample, can be mapped to UMAP)
- Variance decomposition: how much each modality contributes to each factor
- Cross-modality correlation matrix

## Common Issues
- **Zero variance in a modality**: check if data is properly normalized
- **Factors dominated by one modality**: scale weights or reduce n_factors
- **Convergence failure**: increase iterations, reduce factors, or subset features
