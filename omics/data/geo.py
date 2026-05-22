"""NCBI GEO/SRA data fetching via e-utils API and GEOparse.

Provides programmatic access to public genomics data:
- Search GEO for datasets by keyword
- Download GEO series and convert to AnnData
- Fetch SRA/ENA metadata

NCBI requires an email for e-utils (rate limiting). Set via:
    export OMICS_GEO_EMAIL=your@email.com
"""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ENA_FTP_BASE = "ftp://ftp.sra.ebi.ac.uk/vol1/fastq"


@dataclass
class GeoSummary:
    accession: str
    title: str
    n_samples: int = 0
    platform: str = ""
    organism: str = ""
    summary: str = ""


@dataclass
class SRARun:
    run_accession: str
    sample_accession: str
    experiment_accession: str
    library_layout: str = ""
    platform: str = ""
    fastq_urls: list[str] = field(default_factory=list)


def _get_email() -> str:
    import os
    email = os.environ.get("OMICS_GEO_EMAIL", "")
    if not email:
        email = "omics-platform@example.com"
        logger.warning("No NCBI email set. Set OMICS_GEO_EMAIL env var for better rate limits.")
    return email


def _ncbi_request(endpoint: str, params: dict, email: str = "") -> str:
    """Make a rate-limited request to NCBI e-utils."""
    params.setdefault("email", email or _get_email())
    params.setdefault("tool", "omics-platform")
    url = f"{NCBI_EUTILS_BASE}/{endpoint}?{urlencode(params)}"
    time.sleep(0.34)  # NCBI rate limit: ~3 requests/second
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def search_geo_datasets(query: str, max_results: int = 20, email: str = "") -> list[GeoSummary]:
    """Search GEO datasets by keyword.

    Args:
        query: Search term (e.g., "PBMC scRNA-seq", "lung cancer single cell").
        max_results: Maximum results to return.
        email: NCBI contact email (set OMICS_GEO_EMAIL env var instead).

    Returns:
        List of GeoSummary objects with accession, title, sample count.
    """
    xml = _ncbi_request("esearch.fcgi", {
        "db": "gds", "term": query, "retmax": str(max_results), "retmode": "xml",
    }, email)
    root = ET.fromstring(xml)
    ids = [e.text for e in root.findall(".//Id") if e.text]

    if not ids:
        return []

    summaries_xml = _ncbi_request("esummary.fcgi", {
        "db": "gds", "id": ",".join(ids), "retmode": "xml",
    }, email)
    sum_root = ET.fromstring(summaries_xml)

    results = []
    for doc in sum_root.findall(".//DocSum"):
        items = {}
        for item in doc.findall("Item"):
            name = item.get("Name", "")
            items[name] = (item.text or "").strip()
        acc = items.get("Accession", "")
        if acc:
            results.append(GeoSummary(
                acc,
                items.get("title", ""),
                int(items.get("n_samples", "0") or 0),
                items.get("GPL", ""),
                items.get("taxon", ""),
                items.get("summary", ""),
            ))
    return results


def get_geo_metadata(accession: str, email: str = "") -> dict:
    """Fetch detailed metadata for a GEO series.

    Args:
        accession: GEO series accession (e.g., "GSE123456").
        email: NCBI contact email.

    Returns:
        Dict with title, description, platform, sample_count, submitter, pubmed_id.
    """
    xml = _ncbi_request("esearch.fcgi", {
        "db": "gds", "term": f"{accession}[Accession]", "retmax": "1", "retmode": "xml",
    }, email)
    root = ET.fromstring(xml)
    ids = [e.text for e in root.findall(".//Id") if e.text]
    if not ids:
        return {}

    summaries_xml = _ncbi_request("esummary.fcgi", {
        "db": "gds", "id": ids[0], "retmode": "xml",
    }, email)
    sum_root = ET.fromstring(summaries_xml)
    doc = sum_root.find(".//DocSum")
    if doc is None:
        return {}
    items = {}
    for item in doc.findall("Item"):
        name = item.get("Name", "")
        items[name] = (item.text or "").strip()

    return {
        "accession": accession,
        "title": items.get("title", ""),
        "description": items.get("summary", ""),
        "platform": items.get("GPL", ""),
        "sample_count": int(items.get("n_samples", "0") or 0),
        "organism": items.get("taxon", ""),
        "submitter": items.get("PDAT", ""),
        "pubmed_id": items.get("PubMedIds", ""),
    }


def download_geo_series(accession: str, output_dir: Path, email: str = "") -> list[Path]:
    """Download supplementary files for a GEO series using GEOparse.

    Args:
        accession: GEO series accession (e.g., "GSE123456").
        output_dir: Directory to save downloaded files.
        email: NCBI contact email.

    Returns:
        List of paths to downloaded files.
    """
    try:
        import GEOparse
    except ImportError:
        raise ImportError("GEOparse is required. Run: pip install GEOparse")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading {accession} from GEO...")
    gse = GEOparse.get_GEO(geo=accession, destdir=str(output_dir), silent=True)

    downloaded = list(output_dir.glob(f"{accession}*"))

    # Extract expression matrix if available
    for gsm_name, gsm in gse.gsms.items():
        if hasattr(gsm, 'table'):
            table_path = output_dir / f"{gsm_name}_table.txt"
            gsm.table.to_csv(table_path, sep="\t")
            downloaded.append(table_path)

    logger.info(f"Downloaded {len(downloaded)} files for {accession}")
    return downloaded


def geo_to_anndata(accession: str, output_dir: Optional[Path] = None, email: str = "") -> "anndata.AnnData":
    """Download a GEO scRNA-seq dataset and convert to AnnData.

    This is the main end-to-end function for users.

    Args:
        accession: GEO series accession (e.g., "GSE123456").
        output_dir: Directory for downloaded files. Uses temp dir if None.
        email: NCBI contact email.

    Returns:
        AnnData object with expression data.
    """
    import tempfile
    import anndata as ad
    import pandas as pd
    import numpy as np

    try:
        import GEOparse
    except ImportError:
        raise ImportError("GEOparse is required. Run: pip install GEOparse")

    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix=f"{accession}_"))
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Fetching {accession} from GEO...")
    gse = GEOparse.get_GEO(geo=accession, destdir=str(output_dir), silent=True)

    # Collect expression from all samples
    gene_lists = []
    sample_names = []
    for gsm_name, gsm in gse.gsms.items():
        if hasattr(gsm, 'table') and gsm.table is not None:
            table = gsm.table
            if 'IDENTIFIER' in table.columns and 'VALUE' in table.columns:
                gene_lists.append(table.set_index('IDENTIFIER')['VALUE'])
                sample_names.append(gsm_name)

    if not gene_lists:
        raise DataImportError(f"No expression data found in {accession}. "
                             "The dataset may not contain count matrices.")

    # Merge all samples
    expr_df = pd.concat(gene_lists, axis=1)
    expr_df.columns = sample_names

    # Create AnnData
    adata = ad.AnnData(expr_df.T.values.astype(np.float32))
    adata.obs_names = sample_names
    adata.var_names = expr_df.index.tolist()
    adata.uns["geo_accession"] = accession
    adata.uns["geo_title"] = gse.metadata.get("title", [""])[0] if gse.metadata.get("title") else ""

    logger.info(f"Built AnnData: {adata.n_obs} samples x {adata.n_vars} genes")
    return adata


def search_sra_runs(accession: str, email: str = "") -> list[SRARun]:
    """Get SRA run accessions for a study.

    Args:
        accession: SRA study accession (SRP/ERP/DRP prefix).
        email: NCBI contact email.

    Returns:
        List of SRARun objects.
    """
    xml = _ncbi_request("esearch.fcgi", {
        "db": "sra", "term": f"{accession}[Accession]", "retmax": "100", "retmode": "xml",
    }, email)
    root = ET.fromstring(xml)
    ids = [e.text for e in root.findall(".//Id") if e.text]
    if not ids:
        return []

    fetch_xml = _ncbi_request("efetch.fcgi", {
        "db": "sra", "id": ",".join(ids), "rettype": "runinfo", "retmode": "xml",
    }, email)

    runs = []
    try:
        fetch_root = ET.fromstring(fetch_xml)
        for run_elem in fetch_root.findall(".//Row") or fetch_root.findall(".//Run"):
            run_acc = _get_elem_text(run_elem, "Run") or run_elem.get("acc", "")
            runs.append(SRARun(
                run_accession=run_acc,
                sample_accession=_get_elem_text(run_elem, "Sample") or "",
                experiment_accession=_get_elem_text(run_elem, "Experiment") or "",
                library_layout=_get_elem_text(run_elem, "LibraryLayout") or "",
                platform=_get_elem_text(run_elem, "Platform") or "",
            ))
    except ET.ParseError:
        pass

    return runs


def download_fastq_ena(run_accession: str, output_dir: Path) -> Path:
    """Download FASTQ files from ENA FTP.

    Args:
        run_accession: SRA run accession (SRR/ERR/DRR prefix).
        output_dir: Output directory.

    Returns:
        Path to downloaded file(s).
    """
    import subprocess
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ENA FTP path pattern: ftp.sra.ebi.ac.uk/vol1/fastq/{prefix}/{run}/{run}_1.fastq.gz
    prefix = run_accession[:6]
    url_base = f"ftp://ftp.sra.ebi.ac.uk/vol1/fastq/{prefix}/{run_accession}"

    try:
        subprocess.run([
            "wget", "-P", str(output_dir), "-r", "-np", "-nH", "--cut-dirs=6",
            "--accept", "*.fastq.gz", f"{url_base}/"
        ], check=True, timeout=3600)
    except FileNotFoundError:
        logger.warning("wget not found. Trying Python download...")
        try:
            resp = requests.get(f"{url_base}/{run_accession}_1.fastq.gz", stream=True, timeout=600)
            if resp.status_code == 200:
                out_path = output_dir / f"{run_accession}_1.fastq.gz"
                with open(out_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return out_path
        except Exception as e:
            raise RuntimeError(f"Failed to download {run_accession}: {e}")

    return output_dir


def _get_elem_text(elem, tag: str) -> str:
    child = elem.find(tag) if hasattr(elem, "find") else None
    return child.text.strip() if child is not None and child.text else ""


from omics.utils.exceptions import DataImportError
