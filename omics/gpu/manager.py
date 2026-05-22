"""GPU resource manager: detection, memory budgeting, transparent CPU fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from omics.utils.exceptions import GPUNotAvailableError, GPUOutOfMemoryError

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    available: bool = False
    count: int = 0
    name: str = ""
    driver_version: str = ""
    cuda_version: str = ""
    total_vram_mb: int = 0
    free_vram_mb: int = 0
    devices: list[dict] = field(default_factory=list)


class GPUManager:
    """Singleton GPU resource manager.

    Handles NVIDIA GPU detection, VRAM budgeting, and transparent CPU
    fallback for all GPU-accelerated operations.
    """

    _instance: Optional["GPUManager"] = None

    def __new__(cls) -> "GPUManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._nvml = None
        self._handle = None
        self._cuda_available = False
        self._info: Optional[GPUInfo] = None
        self._reserved_mb: int = 0
        self._try_init()

    def _try_init(self) -> None:
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml = pynvml
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            self._nvml = None
            self._handle = None

        try:
            import cupy
            self._cuda_available = True
        except Exception:
            self._cuda_available = False

    @property
    def available(self) -> bool:
        return self._handle is not None and self._cuda_available

    def detect(self) -> GPUInfo:
        if self._info is not None:
            return self._info

        info = GPUInfo()
        if not self._nvml or not self._handle:
            self._info = info
            return info

        try:
            info.count = self._nvml.nvmlDeviceGetCount()
            for i in range(info.count):
                handle = self._nvml.nvmlDeviceGetHandleByIndex(i)
                name = self._nvml.nvmlDeviceGetName(handle)
                mem = self._nvml.nvmlDeviceGetMemoryInfo(handle)
                info.devices.append({
                    "index": i,
                    "name": name,
                    "total_mb": mem.total // (1024 * 1024),
                    "free_mb": mem.free // (1024 * 1024),
                })
            info.name = info.devices[0]["name"] if info.devices else ""
            info.total_vram_mb = sum(d["total_mb"] for d in info.devices)
            info.free_vram_mb = sum(d["free_mb"] for d in info.devices)
            info.driver_version = self._nvml.nvmlSystemGetDriverVersion()
            try:
                import cupy
                info.cuda_version = str(cupy.cuda.runtime.runtimeGetVersion())
            except Exception:
                info.cuda_version = "unknown"
            info.available = info.count > 0 and self._cuda_available
        except Exception as e:
            logger.warning(f"GPU detection error: {e}")

        self._info = info
        return info

    def summary(self) -> str:
        info = self.detect()
        if not info.available:
            return "GPU: Not available (CPU mode)"
        lines = [
            f"GPU: {info.name}",
            f"  CUDA:     {info.cuda_version}",
            f"  Driver:   {info.driver_version}",
            f"  Devices:  {info.count}",
            f"  VRAM:     {info.free_vram_mb} MB free / {info.total_vram_mb} MB total",
        ]
        return "\n".join(lines)

    def get_device(self) -> str:
        return "cuda:0" if self.available else "cpu"

    def require_gpu(self) -> None:
        if not self.available:
            raise GPUNotAvailableError("GPU required but not available. Check CUDA installation.")

    def ensure_vram(self, mb: int) -> None:
        info = self.detect()
        if info.free_vram_mb < mb:
            raise GPUOutOfMemoryError(f"Need {mb} MB VRAM, only {info.free_vram_mb} MB available.")


def get_gpu_manager() -> GPUManager:
    return GPUManager()
