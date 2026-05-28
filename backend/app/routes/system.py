"""System routes — health, GPU status, config."""

from fastapi import APIRouter

from ..schemas import ConfigInfo, GPUInfo, HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health():
    try:
        import omics
        ver = getattr(omics, "__version__", None)
    except ImportError:
        ver = None
    return HealthResponse(status="ok", version="0.1.0", omics_version=ver)


@router.get("/system/gpu", response_model=GPUInfo)
async def gpu_status():
    try:
        from omics.agent.handler import OmicsAgentHandler
        h = OmicsAgentHandler()
        result = h.do_omics_gpu_status({}, None)
        return GPUInfo(**result.data.get("gpu_info", {"available": False}))
    except Exception:
        return GPUInfo(available=False)


@router.get("/system/config", response_model=ConfigInfo)
async def config():
    try:
        from omics.agent.handler import OmicsAgentHandler
        h = OmicsAgentHandler()
        result = h.do_omics_config({}, None)
        cfg = result.data.get("config", {})
        return ConfigInfo(
            data_dir=cfg.get("data_dir", ""),
            output_dir=cfg.get("output_dir", ""),
            n_jobs=cfg.get("n_jobs", 1),
            gpu_enabled=cfg.get("gpu_enabled", False),
        )
    except Exception:
        return ConfigInfo(data_dir="", output_dir="", n_jobs=1, gpu_enabled=False)
