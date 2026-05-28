const SCRNA = {
  modality: 'scrna', name: '单细胞转录组标准流程',
  nodes: [
    { id: 'import', label: '数据导入', type: 'import', params: [{ key: 'file', label: '数据文件', type: 'file_select', required: true }] },
    { id: 'qc', label: 'QC 质控', type: 'analysis', tool: 'omics_scrna_qc', params: [{ key: 'min_genes', label: '最低基因数', type: 'integer', default: 200 }, { key: 'min_cells', label: '最低细胞数', type: 'integer', default: 3 }, { key: 'max_pct_mt', label: '线粒体上限%', type: 'number', default: 20 }] },
    { id: 'normalize', label: '标准化', type: 'analysis', tool: 'omics_scrna_normalize', params: [{ key: 'target_sum', label: '标准化目标值', type: 'integer', default: 10000 }] },
    { id: 'reduce', label: '降维', type: 'analysis', tool: 'omics_scrna_reduce', params: [{ key: 'n_hvg', label: '高变基因数', type: 'integer', default: 2000 }, { key: 'n_pcs', label: '主成分数', type: 'integer', default: 50 }, { key: 'n_neighbors', label: '邻居数', type: 'integer', default: 15 }] },
    { id: 'cluster', label: '聚类', type: 'analysis', tool: 'omics_scrna_cluster', params: [{ key: 'resolution', label: '分辨率', type: 'number', default: 1.0, min: 0.1, max: 3.0, step: 0.1 }] },
    { id: 'markers', label: '标记基因', type: 'analysis', tool: 'omics_scrna_markers', params: [{ key: 'groupby', label: '分组列', type: 'string', default: 'leiden' }, { key: 'n_genes', label: 'Top N 基因', type: 'integer', default: 20 }] },
    { id: 'trajectory', label: '拟时序', type: 'branch_optional', tool: 'omics_scrna_trajectory', params: [{ key: 'method', label: '方法', type: 'select', options: ['dpt', 'velocity', 'paga'], default: 'dpt' }] },
    { id: 'annotate', label: '细胞注释', type: 'branch_optional', tool: 'omics_scrna_annotate', params: [{ key: 'method', label: '方法', type: 'select', options: ['marker_based', 'celltypist'], default: 'marker_based' }] },
    { id: 'visualize', label: '可视化', type: 'branch_optional', tool: 'omics_visualize_umap', params: [{ key: 'color', label: '着色列', type: 'string', default: 'leiden' }] },
  ],
  edges: [
    { source: 'import', target: 'qc' }, { source: 'qc', target: 'normalize' }, { source: 'normalize', target: 'reduce' },
    { source: 'reduce', target: 'cluster' }, { source: 'reduce', target: 'trajectory' }, { source: 'cluster', target: 'markers' },
    { source: 'markers', target: 'annotate' }, { source: 'cluster', target: 'visualize' }, { source: 'trajectory', target: 'visualize' },
  ],
}

const BULK_RNA = {
  modality: 'bulk_rna', name: 'Bulk RNA-seq 标准流程',
  nodes: [
    { id: 'import', label: '数据导入', type: 'import', params: [{ key: 'file', label: '表达矩阵', type: 'file_select', required: true }] },
    { id: 'qc', label: 'QC 质控', type: 'analysis', params: [{ key: 'min_counts', label: '最低counts', type: 'integer', default: 10 }, { key: 'min_samples', label: '最少样本数', type: 'integer', default: 3 }] },
    { id: 'normalize', label: '标准化', type: 'analysis', params: [{ key: 'method', label: '方法', type: 'select', options: ['tpm', 'fpkm', 'deseq2', 'voom'], default: 'deseq2' }] },
    { id: 'de', label: '差异表达', type: 'analysis', params: [{ key: 'group_col', label: '分组列', type: 'string', default: 'condition' }, { key: 'case', label: '实验组', type: 'string', default: 'treatment' }, { key: 'control', label: '对照组', type: 'string', default: 'control' }] },
    { id: 'enrich', label: '富集分析', type: 'analysis', params: [{ key: 'gene_col', label: '基因列', type: 'string', default: 'gene_id' }, { key: 'database', label: '数据库', type: 'select', options: ['GO', 'KEGG', 'Reactome', 'Hallmark'], default: 'KEGG' }] },
    { id: 'visualize', label: '可视化', type: 'branch_optional', params: [{ key: 'type', label: '图表类型', type: 'select', options: ['volcano', 'heatmap', 'ma_plot', 'pca'], default: 'volcano' }] },
  ],
  edges: [{ source: 'import', target: 'qc' }, { source: 'qc', target: 'normalize' }, { source: 'normalize', target: 'de' }, { source: 'de', target: 'enrich' }, { source: 'de', target: 'visualize' }],
}

const SPATIAL = {
  modality: 'spatial', name: '空间转录组分析流程',
  nodes: [
    { id: 'import', label: '数据导入', type: 'import', params: [{ key: 'file', label: 'Visium数据', type: 'file_select', required: true }] },
    { id: 'qc', label: 'QC 质控', type: 'analysis', params: [{ key: 'min_genes', label: '最低基因数', type: 'integer', default: 200 }, { key: 'min_counts', label: '最低UMI数', type: 'integer', default: 500 }] },
    { id: 'normalize', label: '标准化', type: 'analysis', params: [{ key: 'target_sum', label: '标准化目标值', type: 'integer', default: 10000 }] },
    { id: 'hvg', label: '高变基因', type: 'analysis', params: [{ key: 'n_top_genes', label: '高变基因数', type: 'integer', default: 2000 }] },
    { id: 'reduce', label: '降维', type: 'analysis', params: [{ key: 'n_pcs', label: '主成分数', type: 'integer', default: 50 }] },
    { id: 'cluster', label: '空间聚类', type: 'analysis', params: [{ key: 'resolution', label: '分辨率', type: 'number', default: 0.8, min: 0.1, max: 2.0, step: 0.1 }] },
    { id: 'spatial_de', label: '空间差异表达', type: 'analysis', params: [{ key: 'method', label: '方法', type: 'select', options: ['spark_x', 'trendsceek', 'spatialde'], default: 'spark_x' }] },
    { id: 'niche', label: '微环境分析', type: 'branch_optional', params: [{ key: 'method', label: '方法', type: 'select', options: ['cell2location', 'rctd', 'stereoscope'], default: 'cell2location' }] },
    { id: 'visualize', label: '可视化', type: 'branch_optional', params: [{ key: 'type', label: '图表类型', type: 'select', options: ['spatial_umap', 'spatial_heatmap', 'spatial_scatter'], default: 'spatial_umap' }] },
  ],
  edges: [{ source: 'import', target: 'qc' }, { source: 'qc', target: 'normalize' }, { source: 'normalize', target: 'hvg' }, { source: 'hvg', target: 'reduce' }, { source: 'reduce', target: 'cluster' }, { source: 'cluster', target: 'spatial_de' }, { source: 'cluster', target: 'niche' }, { source: 'cluster', target: 'visualize' }, { source: 'spatial_de', target: 'visualize' }],
}

const TCR = {
  modality: 'tcr', name: 'TCR 免疫组库分析流程',
  nodes: [
    { id: 'import', label: '数据导入', type: 'import', params: [{ key: 'file', label: 'TCR-seq数据', type: 'file_select', required: true }] },
    { id: 'qc', label: 'QC 质控', type: 'analysis', params: [{ key: 'min_reads', label: '最低reads数', type: 'integer', default: 1000 }, { key: 'min_umi', label: '最低UMI', type: 'integer', default: 3 }] },
    { id: 'clonotypes', label: '克隆型鉴定', type: 'analysis', params: [{ key: 'method', label: '方法', type: 'select', options: ['mixa_cr', 'trust4', 'trax'], default: 'mixa_cr' }] },
    { id: 'diversity', label: '多样性分析', type: 'analysis', params: [{ key: 'metrics', label: '指标', type: 'select', options: ['shannon', 'simpson', 'inv_simpson', 'chao1', 'all'], default: 'all' }] },
    { id: 'vj_usage', label: 'VJ 使用偏好', type: 'analysis', params: [{ key: 'chain', label: '链', type: 'select', options: ['TRA', 'TRB', 'both'], default: 'both' }] },
    { id: 'clonotype_tracking', label: '克隆追踪', type: 'branch_optional', params: [{ key: 'method', label: '追踪方法', type: 'select', options: ['tracking', 'overlap', 'venn'], default: 'tracking' }] },
    { id: 'visualize', label: '可视化', type: 'branch_optional', params: [{ key: 'type', label: '图表类型', type: 'select', options: ['circos', 'barplot', 'scatter', 'umap'], default: 'circos' }] },
  ],
  edges: [{ source: 'import', target: 'qc' }, { source: 'qc', target: 'clonotypes' }, { source: 'clonotypes', target: 'diversity' }, { source: 'clonotypes', target: 'vj_usage' }, { source: 'clonotypes', target: 'clonotype_tracking' }, { source: 'diversity', target: 'visualize' }, { source: 'vj_usage', target: 'visualize' }],
}

const AMPLICON = {
  modality: 'amplicon', name: '扩增子 (16S) 分析流程',
  nodes: [
    { id: 'import', label: '数据导入', type: 'import', params: [{ key: 'file', label: 'OTU/ASV表', type: 'file_select', required: true }] },
    { id: 'qc', label: 'QC 质控', type: 'analysis', params: [{ key: 'min_freq', label: '最低丰度', type: 'integer', default: 10 }, { key: 'min_samples', label: '最少样本', type: 'integer', default: 2 }] },
    { id: 'alpha_div', label: 'Alpha多样性', type: 'analysis', params: [{ key: 'metrics', label: '指标', type: 'select', options: ['shannon', 'simpson', 'chao1', 'observed', 'all'], default: 'all' }] },
    { id: 'beta_div', label: 'Beta多样性', type: 'analysis', params: [{ key: 'method', label: '距离方法', type: 'select', options: ['bray_curtis', 'jaccard', 'unifrac', 'wunifrac'], default: 'bray_curtis' }] },
    { id: 'taxonomy', label: '物种注释', type: 'analysis', params: [{ key: 'database', label: '数据库', type: 'select', options: ['silva', 'greengenes', 'rdp', 'unite'], default: 'silva' }, { key: 'level', label: '分类水平', type: 'select', options: ['phylum', 'class', 'order', 'family', 'genus', 'species'], default: 'genus' }] },
    { id: 'diff_abundance', label: '差异丰度', type: 'analysis', params: [{ key: 'method', label: '方法', type: 'select', options: ['aldex2', 'ancom', 'deseq2', 'lefse'], default: 'aldex2' }] },
    { id: 'visualize', label: '可视化', type: 'branch_optional', params: [{ key: 'type', label: '图表类型', type: 'select', options: ['pcoa', 'nmds', 'barplot', 'heatmap', 'phylogenetic_tree'], default: 'pcoa' }] },
  ],
  edges: [{ source: 'import', target: 'qc' }, { source: 'qc', target: 'alpha_div' }, { source: 'qc', target: 'beta_div' }, { source: 'qc', target: 'taxonomy' }, { source: 'taxonomy', target: 'diff_abundance' }, { source: 'beta_div', target: 'visualize' }, { source: 'taxonomy', target: 'visualize' }],
}

const METAGENOMICS = {
  modality: 'metagenomics', name: '宏基因组分析流程',
  nodes: [
    { id: 'import', label: '数据导入', type: 'import', params: [{ key: 'file', label: 'Kraken2报告', type: 'file_select', required: true }] },
    { id: 'qc', label: 'QC 质控', type: 'analysis', params: [{ key: 'min_reads', label: '最低reads', type: 'integer', default: 1000 }, { key: 'host_filter', label: '宿主过滤', type: 'select', options: ['human', 'mouse', 'none'], default: 'human' }] },
    { id: 'taxonomic_profile', label: '物种组成', type: 'analysis', params: [{ key: 'level', label: '分类水平', type: 'select', options: ['phylum', 'class', 'order', 'family', 'genus', 'species'], default: 'species' }] },
    { id: 'functional_annot', label: '功能注释', type: 'analysis', params: [{ key: 'database', label: '数据库', type: 'select', options: ['kegg', 'eggnog', 'cog', 'cazy', 'vfdb', 'card'], default: 'kegg' }] },
    { id: 'alpha_div', label: 'Alpha多样性', type: 'analysis', params: [{ key: 'metrics', label: '指标', type: 'select', options: ['shannon', 'simpson', 'chao1', 'all'], default: 'all' }] },
    { id: 'beta_div', label: 'Beta多样性', type: 'analysis', params: [{ key: 'method', label: '距离方法', type: 'select', options: ['bray_curtis', 'jaccard', 'aitchison'], default: 'bray_curtis' }] },
    { id: 'diff_abundance', label: '差异丰度', type: 'analysis', params: [{ key: 'method', label: '方法', type: 'select', options: ['aldex2', 'ancom_bc', 'maaslin2'], default: 'aldex2' }] },
    { id: 'visualize', label: '可视化', type: 'branch_optional', params: [{ key: 'type', label: '图表类型', type: 'select', options: ['pcoa', 'heatmap', 'sankey', 'krona', 'circos'], default: 'pcoa' }] },
  ],
  edges: [{ source: 'import', target: 'qc' }, { source: 'qc', target: 'taxonomic_profile' }, { source: 'qc', target: 'functional_annot' }, { source: 'taxonomic_profile', target: 'alpha_div' }, { source: 'taxonomic_profile', target: 'beta_div' }, { source: 'taxonomic_profile', target: 'diff_abundance' }, { source: 'beta_div', target: 'visualize' }, { source: 'functional_annot', target: 'visualize' }],
}

const PROTEOMICS = {
  modality: 'proteomics', name: '蛋白质组学分析流程',
  nodes: [
    { id: 'import', label: '数据导入', type: 'import', params: [{ key: 'file', label: '蛋白表达矩阵', type: 'file_select', required: true }] },
    { id: 'qc', label: 'QC 质控', type: 'analysis', params: [{ key: 'min_valid', label: '最低有效值比例', type: 'number', default: 0.5 }, { key: 'impute_method', label: '缺失值填充', type: 'select', options: ['min', 'knn', 'missforest', 'none'], default: 'knn' }] },
    { id: 'normalize', label: '标准化', type: 'analysis', params: [{ key: 'method', label: '方法', type: 'select', options: ['quantile', 'median', 'vsn', 'loess', 'total'], default: 'quantile' }] },
    { id: 'de', label: '差异蛋白', type: 'analysis', params: [{ key: 'method', label: '方法', type: 'select', options: ['limma', 'ttest', 'sam', 'deseq2'], default: 'limma' }, { key: 'p_cutoff', label: 'p值阈值', type: 'number', default: 0.05 }, { key: 'fc_cutoff', label: 'FC阈值', type: 'number', default: 1.5 }] },
    { id: 'enrich', label: '富集分析', type: 'analysis', params: [{ key: 'database', label: '数据库', type: 'select', options: ['GO', 'KEGG', 'Reactome', 'WikiPathways', 'STRING'], default: 'KEGG' }] },
    { id: 'ppi', label: '蛋白互作网络', type: 'branch_optional', params: [{ key: 'database', label: '数据库', type: 'select', options: ['string', 'biogrid', 'intact'], default: 'string' }, { key: 'confidence', label: '置信度', type: 'number', default: 0.7, min: 0.1, max: 1.0, step: 0.1 }] },
    { id: 'visualize', label: '可视化', type: 'branch_optional', params: [{ key: 'type', label: '图表类型', type: 'select', options: ['volcano', 'heatmap', 'network', 'bubble'], default: 'volcano' }] },
  ],
  edges: [{ source: 'import', target: 'qc' }, { source: 'qc', target: 'normalize' }, { source: 'normalize', target: 'de' }, { source: 'de', target: 'enrich' }, { source: 'de', target: 'ppi' }, { source: 'de', target: 'visualize' }, { source: 'enrich', target: 'visualize' }],
}

const TEMPLATES = { scrna: SCRNA, bulk_rna: BULK_RNA, spatial: SPATIAL, tcr: TCR, amplicon: AMPLICON, metagenomics: METAGENOMICS, proteomics: PROTEOMICS }

export function getTemplate(modality) { return TEMPLATES[modality] || SCRNA }
export function listTemplates() { return Object.entries(TEMPLATES).map(([key, tpl]) => ({ modality: key, name: tpl.name, nodeCount: tpl.nodes.length })) }
