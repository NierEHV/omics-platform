"""Setup configuration for the omics-platform package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="omics-platform",
    version="0.2.0",
    description="Multi-Omics Analysis Platform — scRNA-seq, Spatial, 16S, Metagenomics, Integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Omics Platform Team",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "anndata>=0.10",
        "scanpy>=1.9",
        "matplotlib>=3.8",
        "seaborn>=0.13",
        "plotly>=5.17",
        "click>=8.1",
        "rich>=13.7",
        "pandas>=2.1",
        "numpy>=1.24",
        "scipy>=1.11",
        "scikit-learn>=1.3",
        "umap-learn>=0.5",
        "leidenalg",
        "pyyaml>=6.0",
        "pydantic>=2.4",
        "tqdm",
        "requests>=2.31",
        "GEOparse>=2.0",
    ],
    extras_require={
        "gpu": [
            "cupy>=12.0",
            "cuml>=23.12",
            "pynvml",
            "rapids-singlecell",
        ],
        "spatial": [
            "squidpy>=1.4",
        ],
        "r": [
            "rpy2>=3.5",
        ],
        "integration": [
            "muon>=0.1",
            "mudata>=0.8",
        ],
        "deep": [
            "scvi-tools>=1.1",
        ],
        "dev": [
            "pytest>=7.4",
            "pytest-cov",
            "black",
            "ruff",
            "pre-commit",
            "ipython",
            "jupyterlab",
        ],
        "all": [
            "cupy>=12.0",
            "cuml>=23.12",
            "rapids-singlecell",
            "squidpy>=1.4",
            "muon>=0.1",
            "mudata>=0.8",
            "scvi-tools>=1.1",
            "rpy2>=3.5",
        ],
    },
    entry_points={
        "console_scripts": [
            "omics=omics.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
    ],
)
