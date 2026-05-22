"""AnnData caching layer with hash-keyed persistence."""

import hashlib
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from omics.utils.constants import DEFAULT_CACHE_DIR
from omics.utils.exceptions import CacheError

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    key: str
    path: Path
    size_bytes: int
    source_path: str = ""
    modality: str = ""


class CacheManager:
    """MD5-hash-keyed cache for AnnData and MuData files."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def key(self, file_path: Path, params: Optional[dict] = None) -> str:
        hasher = hashlib.md5()
        if file_path.exists():
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
        else:
            hasher.update(str(file_path).encode())
        if params:
            hasher.update(str(sorted(params.items())).encode())
        return hasher.hexdigest()

    def key_from_str(self, identifier: str) -> str:
        return hashlib.md5(identifier.encode()).hexdigest()

    def get_path(self, key: str, suffix: str = ".h5ad") -> Path:
        return self._cache_dir / f"{key}{suffix}"

    def has(self, key: str, suffix: str = ".h5ad") -> bool:
        return self.get_path(key, suffix).exists()

    def read(self, key: str, suffix: str = ".h5ad") -> Path:
        path = self.get_path(key, suffix)
        if not path.exists():
            raise CacheError(f"Cache miss for key {key}")
        logger.debug(f"Cache hit: {path}")
        return path

    def write(self, key: str, source_path: Path, suffix: str = ".h5ad") -> CacheEntry:
        dest = self.get_path(key, suffix)
        shutil.copy2(source_path, dest)
        size = dest.stat().st_size
        logger.debug(f"Cached: {dest} ({size} bytes)")
        return CacheEntry(key=key, path=dest, size_bytes=size, source_path=str(source_path))

    def write_data(self, key: str, data, suffix: str = ".h5ad") -> Path:
        dest = self.get_path(key, suffix)
        data.write(dest)
        logger.debug(f"Cached: {dest}")
        return dest

    def list_entries(self) -> list[CacheEntry]:
        entries = []
        for f in sorted(self._cache_dir.iterdir()):
            if f.is_file():
                entries.append(CacheEntry(key=f.stem, path=f, size_bytes=f.stat().st_size))
        return entries

    def clear(self) -> int:
        count = 0
        for f in self._cache_dir.iterdir():
            f.unlink()
            count += 1
        logger.info(f"Cleared {count} cached files")
        return count

    def gc(self, keep_count: int = 100) -> int:
        files = sorted(self._cache_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        removed = 0
        for f in files[keep_count:]:
            f.unlink()
            removed += 1
        if removed:
            logger.info(f"GC: removed {removed} old cache files")
        return removed

    @property
    def size_bytes(self) -> int:
        return sum(f.stat().st_size for f in self._cache_dir.iterdir() if f.is_file())
