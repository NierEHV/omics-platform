"""Concrete TCR/BCR analysis backed by Scirpy + MiXCR + Immunarch."""
from typing import Any, Optional
import numpy as np
import pandas as pd
import anndata
from .base import AbstractTCRAnalysis


class TCRAnalysis(AbstractTCRAnalysis):

    def load_vdj(self, path: str, **kwargs) -> anndata.AnnData:
        """Load TCR/BCR data. Supports scirpy AIRR, 10X, CSV."""
        ext = str(path).lower()
        if 'all_contig' in ext:
            import scirpy as ir
            return ir.io.read_10x_vdj(path)
        if ext.endswith('.h5ad'):
            return anndata.read_h5ad(path)
        try:
            import scirpy as ir
            return ir.io.read_airr(path)
        except (ImportError, Exception):
            raw = pd.read_csv(path, **kwargs)
            return anndata.AnnData(obs=raw)

    def define_clonotypes(self, adata: anndata.AnnData, **kwargs) -> anndata.AnnData:
        """Define clonotypes from CDR3 AA sequences via Scirpy."""
        import scirpy as ir
        receptor_arms = kwargs.pop('receptor_arms', 'any')
        ir.tl.chain_qc(adata)
        ir.pp.ir_dist(adata)
        ir.tl.define_clonotypes(adata, receptor_arms=receptor_arms, **kwargs)
        return adata

    def clonal_expansion(self, adata: anndata.AnnData, **kwargs) -> dict:
        """Clonal expansion: clone size distribution, expansion categories."""
        if 'clonotype' not in adata.obs.columns:
            self.define_clonotypes(adata)

        clone_sizes = adata.obs['clonotype'].value_counts()
        n_expanded = int((clone_sizes > 1).sum())
        total_clones = len(clone_sizes)

        try:
            import scirpy as ir
            ir.tl.clonal_expansion(adata, **kwargs)
        except Exception:
            pass

        return {
            'total_clones': total_clones,
            'expanded_clones': n_expanded,
            'expansion_pct': round(n_expanded / total_clones * 100, 1) if total_clones else 0,
            'max_clone_size': int(clone_sizes.max()),
            'mean_clone_size': round(float(clone_sizes.mean()), 2),
            'clone_sizes': clone_sizes.to_dict(),
        }

    def vj_usage(self, adata: anndata.AnnData, groupby: str = None,
                 **kwargs) -> pd.DataFrame:
        """V and J gene segment usage frequency."""
        try:
            import scirpy as ir
            ir.tl.chain_qc(adata)
        except Exception:
            pass

        def _count_genes(col):
            values = adata.obs.get(col, pd.Series([''] * adata.n_obs, index=adata.obs.index))
            gene_map = {}
            for val in values:
                for gene in str(val).split(';'):
                    gene = gene.strip()
                    if gene and gene != 'nan' and gene:
                        gene_map[gene] = gene_map.get(gene, 0) + 1
            return pd.Series(gene_map).sort_values(ascending=False)

        v_usage = _count_genes('v_call')
        j_usage = _count_genes('j_call')
        result = pd.DataFrame({
            'gene': list(v_usage.index) + list(j_usage.index),
            'type': ['V'] * len(v_usage) + ['J'] * len(j_usage),
            'count': list(v_usage.values) + list(j_usage.values),
        })
        total_cells = adata.n_obs
        result['frequency'] = result['count'] / total_cells if total_cells else 0
        return result.sort_values('frequency', ascending=False)

    def cdr3_analysis(self, adata: anndata.AnnData, **kwargs) -> dict:
        """CDR3 length distribution and amino acid composition."""
        cdr3_col = 'cdr3_aa'
        if cdr3_col not in adata.obs.columns:
            return {'error': f'No {cdr3_col} column in .obs'}

        cdr3_seqs = adata.obs[cdr3_col].dropna().astype(str)
        if len(cdr3_seqs) == 0:
            return {'error': 'No valid CDR3 sequences found'}

        lengths = cdr3_seqs.str.len()
        aa_counts = {}
        for seq in cdr3_seqs:
            for aa in seq:
                aa_counts[aa] = aa_counts.get(aa, 0) + 1

        return {
            'mean_length': round(float(lengths.mean()), 2),
            'median_length': int(lengths.median()),
            'min_length': int(lengths.min()),
            'max_length': int(lengths.max()),
            'length_distribution': lengths.value_counts().sort_index().to_dict(),
            'aa_composition': dict(sorted(aa_counts.items(), key=lambda x: -x[1])[:20]),
        }

    def repertoire_diversity(self, adata: anndata.AnnData, **kwargs) -> dict:
        """Diversity metrics: Shannon, Simpson, InvSimpson, D50, Chao1."""
        if 'clonotype' in adata.obs.columns:
            clone_counts = adata.obs['clonotype'].value_counts().values.astype(np.float64)
        else:
            clone_counts = np.array([1] * adata.n_obs)

        total = clone_counts.sum()
        proportions = clone_counts / total

        shannon = -np.sum(proportions * np.log(proportions + 1e-300))
        simpson = float(np.sum(proportions ** 2))
        inv_simpson = 1.0 / simpson if simpson > 0 else float('inf')
        d50_idx = int(np.cumsum(np.sort(proportions)[::-1]).searchsorted(0.5) + 1)

        n1 = int(np.sum(clone_counts == 1))
        n2 = int(np.sum(clone_counts == 2))
        n = int(len(clone_counts))
        chao1 = n + (n1 * (n1 - 1)) / (2 * (n2 + 1)) if n2 > 0 else float(n)

        return {
            'shannon': round(shannon, 4),
            'simpson': round(simpson, 6),
            'inverse_simpson': round(inv_simpson, 2),
            'd50': d50_idx,
            'chao1': round(chao1, 2),
        }

    def clonotype_overlap(self, adata_list: list, **kwargs) -> pd.DataFrame:
        """Multi-sample clonotype overlap via Jaccard index."""
        samples = []
        for adata in adata_list:
            if 'clonotype' not in adata.obs.columns:
                self.define_clonotypes(adata)
            samples.append(set(adata.obs['clonotype'].unique()))

        n = len(samples)
        mat = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    mat[i, j] = 1.0
                else:
                    inter = len(samples[i] & samples[j])
                    union = len(samples[i] | samples[j])
                    mat[i, j] = inter / union if union > 0 else 0.0

        return pd.DataFrame(mat,
                            columns=[f'sample_{i}' for i in range(n)],
                            index=[f'sample_{i}' for i in range(n)])

    def tcr_distance(self, adata: anndata.AnnData, **kwargs) -> np.ndarray:
        """TCR sequence distance via TCRdist or Levenshtein fallback."""
        try:
            from tcrdist.repertoire import TCRrep
            tc = TCRrep(cell_df=adata.obs, organism='human')
            tc.compute_distances()
            return tc.pw_beta
        except ImportError:
            cdr3_col = 'cdr3_aa'
            if cdr3_col not in adata.obs.columns:
                raise ValueError(f"No '{cdr3_col}' column for TCR distance computation")
            seqs = adata.obs[cdr3_col].dropna().astype(str).tolist()
            n = len(seqs)
            dist = np.zeros((n, n))
            for i in range(n):
                for j in range(i + 1, n):
                    a, b = seqs[i], seqs[j]
                    m, n_a = len(a), len(b)
                    d = np.zeros((m + 1, n_a + 1))
                    for di in range(m + 1):
                        d[di, 0] = di
                    for dj in range(n_a + 1):
                        d[0, dj] = dj
                    for di in range(1, m + 1):
                        for dj in range(1, n_a + 1):
                            cost = 0 if a[di-1] == b[dj-1] else 1
                            d[di, dj] = min(d[di-1, dj] + 1, d[di, dj-1] + 1, d[di-1, dj-1] + cost)
                    dist[i, j] = dist[j, i] = d[m, n_a]
            return dist

    def integrate_with_scrna(self, tcr_adata: anndata.AnnData,
                             scrna_adata: anndata.AnnData, **kwargs) -> anndata.AnnData:
        """Merge TCR clonotype info into scRNA-seq AnnData.obs."""
        import scirpy as ir
        return ir.pp.merge_with_ir(scrna_adata, tcr_adata, **kwargs)

    def immune_repertoire_profile(self, adata: anndata.AnnData,
                                  groupby: str = 'clonotype', **kwargs) -> dict:
        """Composite immune repertoire profile report."""
        return {
            'modality': self.modality,
            'n_cells': int(adata.n_obs),
            'clonal_expansion': self.clonal_expansion(adata),
            'diversity': self.repertoire_diversity(adata),
            'vj_usage': self.vj_usage(adata).head(20).to_dict(orient='records'),
            'cdr3': self.cdr3_analysis(adata),
        }
