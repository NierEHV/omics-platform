"""Pydantic models for Omics Copilot API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "tool"
    content: str
    tool_name: Optional[str] = None
    tool_result: Optional[dict[str, Any]] = None
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    files: list[str] = Field(default_factory=list)
    history: list[ChatMessage] = Field(default_factory=list)
    modality: str = "auto"


class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    extension: str
    created_at: str
    metadata: Optional[dict[str, Any]] = None


class DataSearchResult(BaseModel):
    accession: str
    title: str
    organism: str
    platform: str
    n_samples: int
    summary: str


class GPUInfo(BaseModel):
    available: bool
    devices: list[dict[str, Any]] = Field(default_factory=list)
    driver_version: Optional[str] = None


class ConfigInfo(BaseModel):
    data_dir: str
    output_dir: str
    n_jobs: int
    gpu_enabled: bool


class HealthResponse(BaseModel):
    status: str
    version: str
    omics_version: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    modality: str
    meta: Optional[dict[str, Any]] = None
