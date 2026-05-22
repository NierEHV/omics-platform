# Publication Figure Generation SOP

## Overview
Generate Nature/Cell/Science-quality figures from omics analysis results.

## Steps

### 1. Choose Journal Theme
- Nature: Arial 7pt, 300 DPI, 89mm (single column) / 183mm (double column)
- Cell: Helvetica 7pt, 300 DPI, 85mm / 175mm
- Science: Helvetica 6pt, 300 DPI, 55mm / 115mm

### 2. Generate Individual Panels
For scRNA-seq data, typical panels:
- UMAP colored by cluster: `omics_visualize` type=umap, color_by=leiden, style=nature
- UMAP colored by cell type: `omics_visualize` type=umap, color_by=cell_type, style=nature
- Dotplot of markers: `omics_visualize` type=dotplot, style=nature
- Heatmap of top markers: `omics_visualize` type=heatmap, style=nature

### 3. Assemble Multi-Panel Figure
- Tool: `omics_visualize_multi_panel`
- Panels: ordered list of individual figure paths
- Output: figure1.pdf (vector), figure1.png (raster at 600 DPI)
- Automatic: letter labels (A, B, C...), consistent styling, aligned axes

### 4. Export for Submission
- PDF: vector format for manuscript submission
- TIFF: for some journals' online submission systems
- SVG: for further editing in Illustrator/Inkscape

## Quality Checklist
- [ ] All text readable at target print size (≥6pt)
- [ ] Color palette is colorblind-friendly (Okabe-Ito defaults)
- [ ] Legends not overlapping with data points
- [ ] Axis labels present and descriptive
- [ ] Consistent styling across all panels
- [ ] DPI matches journal requirements
- [ ] Figure dimensions match journal column widths
