# Multi-Omics Platform — Windows Install Script
# Requires: Miniconda or Anaconda installed
# Run: powershell -ExecutionPolicy Bypass -File install_windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Multi-Omics Platform Installer ===" -ForegroundColor Cyan
Write-Host ""

# Check conda
$conda = Get-Command conda -ErrorAction SilentlyContinue
if (-not $conda) {
    Write-Host "[ERROR] conda not found. Install Miniconda first:" -ForegroundColor Red
    Write-Host "  https://docs.conda.io/en/latest/miniconda.html"
    exit 1
}
Write-Host "[OK] conda found: $($conda.Source)" -ForegroundColor Green

# Check NVIDIA GPU
$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) {
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    Write-Host "[OK] NVIDIA GPU detected" -ForegroundColor Green
} else {
    Write-Host "[WARN] No NVIDIA GPU found — GPU acceleration disabled" -ForegroundColor Yellow
}

# Create conda environment
Write-Host ""
Write-Host "Creating conda environment 'omics-platform'..." -ForegroundColor Cyan
Write-Host "This may take 20-40 minutes on first run."

conda env create -f environment.yaml --yes

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[WARN] Full environment creation failed." -ForegroundColor Yellow
    Write-Host "Creating minimal environment for core functionality..."

    conda create -n omics-platform python=3.10 -y
    conda activate omics-platform
    conda install -c conda-forge anndata scanpy squidpy muon mudata matplotlib seaborn plotly click rich pandas numpy scipy scikit-learn umap-learn leidenalg pyyaml -y

    Write-Host "[WARN] GPU, QIIME2, and metagenomics tools not installed in minimal mode." -ForegroundColor Yellow
    Write-Host "Install them manually when needed:"
    Write-Host "  conda install -c conda-forge cupy cuml"
    Write-Host "  conda install qiime2"
    Write-Host "  conda install -c bioconda kraken2 humann metaphlan"
}

# Install omics-platform in development mode
Write-Host ""
Write-Host "Installing omics-platform package..." -ForegroundColor Cyan
conda activate omics-platform
pip install -e .

Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Activate and verify:" -ForegroundColor White
Write-Host "  conda activate omics-platform" -ForegroundColor Yellow
Write-Host "  omics --help" -ForegroundColor Yellow
Write-Host "  omics gpu status" -ForegroundColor Yellow
Write-Host ""
Write-Host "Quick start:" -ForegroundColor White
Write-Host "  omics data import scrna path/to/sample.h5ad" -ForegroundColor Yellow
Write-Host "  omics scrna pipeline --input sample.h5ad" -ForegroundColor Yellow
Write-Host ""
