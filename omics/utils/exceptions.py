"""Exception hierarchy for the omics platform."""


class OmicsError(Exception):
    """Base exception. All omics errors inherit from this."""
    exit_code: int = 1


class ConfigError(OmicsError):
    exit_code = 2


class ValidationError(OmicsError):
    exit_code = 3


class GPUError(OmicsError):
    exit_code = 4


class GPUNotAvailableError(GPUError):
    """GPU requested but not available."""


class GPUOutOfMemoryError(GPUError):
    """Insufficient GPU VRAM."""


class PipelineError(OmicsError):
    exit_code = 6


class PipelineCycleError(PipelineError):
    """Dependency cycle detected in pipeline DAG."""


class PipelineStageError(PipelineError):
    """Individual pipeline stage failed."""


class DataImportError(OmicsError):
    exit_code = 7


class ModalityNotSupportedError(DataImportError):
    """Modality not recognized."""


class ExternalToolError(OmicsError):
    exit_code = 8


class CacheError(OmicsError):
    exit_code = 9
