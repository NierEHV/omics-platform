"""Validate AnnData against modality schemas."""

from dataclasses import dataclass, field
from omics.data.slots import get_schema


@dataclass
class ValidationReport:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        parts = []
        parts.append(f"Validation: {'PASSED' if self.is_valid else 'FAILED'}")
        for e in self.errors:
            parts.append(f"  [ERROR] {e}")
        for w in self.warnings:
            parts.append(f"  [WARN]  {w}")
        for s in self.suggestions:
            parts.append(f"  [HINT]  {s}")
        return "\n".join(parts)


def validate_adata(adata, modality: str = "scrna") -> ValidationReport:
    """Validate an AnnData object against a modality schema."""
    schema = get_schema(modality)
    report = ValidationReport()

    if adata.n_obs == 0:
        report.errors.append("No observations (cells)")
    if adata.n_vars == 0:
        report.errors.append("No variables (genes/features)")

    for col in schema.obs_columns:
        if col not in adata.obs.columns:
            report.warnings.append(f"Missing .obs column: '{col}'")

    for col in schema.var_columns:
        if col not in adata.var.columns:
            report.warnings.append(f"Missing .var column: '{col}'")

    for key in schema.obsm_keys:
        if key not in adata.obsm:
            report.suggestions.append(f"Consider computing: .obsm['{key}']")

    for key in schema.obsp_keys:
        if key not in adata.obsp:
            report.suggestions.append(f"Not yet computed: .obsp['{key}']")

    for key in schema.uns_keys:
        if key not in adata.uns:
            report.suggestions.append(f"Not yet computed: .uns['{key}']")

    if "cell_type" not in adata.obs.columns and "leiden" not in adata.obs.columns:
        report.suggestions.append("No clustering or cell type annotation found")

    report.is_valid = len(report.errors) == 0
    return report
