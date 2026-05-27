"""Concrete multi-omics integration backed by MOFA2 + Muon + totalVI."""
from typing import Any, Optional
import numpy as np
import anndata
from .base import AbstractIntegration


class MultiOmicsIntegration(AbstractIntegration):

    def integrate(self, modalities: list, method: str = "mofa",
                  **kwargs) -> Any:
        """Integrate multiple modalities into a joint representation.

        Args:
            modalities: List of AnnData objects, one per modality.
            method: "mofa", "wnn", or "totalvi".
        Returns:
            MuData object or AnnData with joint embeddings.
        """
        n_factors = kwargs.pop('n_factors', 15)

        if method == "mofa":
            return self._integrate_mofa(modalities, n_factors, **kwargs)
        elif method == "wnn":
            return self._integrate_wnn(modalities, **kwargs)
        elif method == "totalvi":
            return self._integrate_totalvi(modalities, **kwargs)
        else:
            raise ValueError(f"Unknown method: {method}. Use mofa, wnn, or totalvi.")

    def _integrate_mofa(self, modalities: list, n_factors: int, **kwargs) -> Any:
        """MOFA2 integration: learns shared + private factors."""
        try:
            import mudata as md
        except ImportError:
            mdata = None
            import anndata
            mdata = anndata.AnnData()
            mdata.uns['mofa_status'] = 'skipped: mudata not installed'
            return mdata

        mdata = md.MuData({f"mod_{i}": ad for i, ad in enumerate(modalities)})
        mdata.update()

        try:
            import mofapy2.run
            import pandas as pd

            data = {}
            for i, ad in enumerate(modalities):
                mat = ad.X
                if hasattr(mat, 'toarray'):
                    mat = mat.toarray()
                df = pd.DataFrame(mat.T, index=ad.var_names, columns=ad.obs_names)
                data[f"mod_{i}"] = df

            ent = mofapy2.run.entry_point()
            ent.set_data(data)
            ent.set_model_options(factors=n_factors)
            ent.set_train_options(seed=42, **kwargs)
            ent.build()
            ent.run()

            factors = ent.model.nodes['Z'].getExpectation()
            mdata.obsm['mofa_factors'] = factors.T
            mdata.uns['mofa_r2'] = ent.model.calculate_variance_explained()
        except ImportError:
            mdata.uns['mofa_status'] = 'skipped: mofapy2 not installed'
        except Exception as exc:
            mdata.uns['mofa_status'] = f'error: {exc}'

        return mdata

    def _integrate_wnn(self, modalities: list, **kwargs) -> Any:
        """Weighted Nearest Neighbor via muon."""
        import mudata as md
        import muon as mu

        mdata = md.MuData({f"mod_{i}": ad for i, ad in enumerate(modalities)})
        mu.pp.neighbors(mdata, **kwargs)
        mu.tl.umap(mdata)
        return mdata

    def _integrate_totalvi(self, modalities: list, **kwargs) -> Any:
        """totalVI integration for paired scRNA + protein data."""
        import scvi

        if len(modalities) < 2:
            raise ValueError("totalVI requires at least 2 modalities (RNA + protein)")

        adata_rna = modalities[0].copy()
        adata_prot = modalities[1]

        prot_mat = adata_prot.X
        if hasattr(prot_mat, 'toarray'):
            prot_mat = prot_mat.toarray()
        adata_rna.obsm['protein_expression'] = prot_mat

        scvi.model.TOTALVI.setup_anndata(
            adata_rna, protein_expression_obsm_key='protein_expression'
        )
        model = scvi.model.TOTALVI(adata_rna)
        model.train(**kwargs)
        adata_rna.obsm['totalvi_latent'] = model.get_latent_representation()
        return adata_rna

    def factor_analysis(self, data: Any, **kwargs) -> dict:
        """Interpret factors: variance explained per factor per modality."""
        if hasattr(data, 'uns') and 'mofa_r2' in data.uns:
            r2 = data.uns['mofa_r2']
            if isinstance(r2, dict):
                return r2
            return {"r2_per_factor": str(r2)}
        if hasattr(data, 'uns') and 'mofa_status' in data.uns:
            return {"status": data.uns['mofa_status']}
        return {"error": "No integration results found. Run integrate(method='mofa') first."}

    def cross_modality_prediction(self, data: Any, **kwargs) -> Any:
        """Predict one modality from another using MOFA latent factors."""
        if 'mofa_factors' not in data.obsm:
            raise ValueError(
                "No MOFA factors found. Run integrate(method='mofa') first."
            )

        from sklearn.linear_model import Ridge

        source_mod = kwargs.pop('source_mod', 0)
        target_mod = kwargs.pop('target_mod', 1)

        Z = data.obsm['mofa_factors']
        mod_key = f"mod_{source_mod}"
        if mod_key not in data.mod:
            raise ValueError(f"Source modality '{mod_key}' not found.")
        X_source = data.mod[mod_key].X
        if hasattr(X_source, 'toarray'):
            X_source = X_source.toarray()

        model = Ridge(alpha=1.0)
        model.fit(Z, X_source)
        X_pred = model.predict(Z)
        return X_pred
