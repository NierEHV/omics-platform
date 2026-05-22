"""Utility decorators for validation, timing, and GPU acceleration."""

from __future__ import annotations

import functools
import logging
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


def timed(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"{func.__name__} completed in {elapsed:.2f}s")
        return result
    return wrapper


def validate_adata(required_obs: tuple[str, ...] = (), required_obsp: tuple[str, ...] = ()) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            adata = args[0] if args else kwargs.get("adata")
            if adata is None:
                raise ValueError("No AnnData argument found")
            for col in required_obs:
                if col not in adata.obs.columns:
                    raise ValueError(f"AnnData.obs missing required column '{col}'")
            for key in required_obsp:
                if key not in adata.obsp:
                    raise ValueError(f"AnnData.obsp missing required key '{key}'")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def requires_gpu(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from omics.gpu.manager import get_gpu_manager
        gpu = get_gpu_manager()
        if not gpu.available:
            from omics.utils.exceptions import GPUNotAvailableError
            raise GPUNotAvailableError(f"{func.__name__} requires GPU but none available")
        return func(*args, **kwargs)
    return wrapper
