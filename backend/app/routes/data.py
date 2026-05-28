"""Data routes — data info, GEO search, GEO fetch."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ..schemas import DataSearchResult

router = APIRouter(tags=["data"])


@router.post("/data/info")
async def data_info(req: dict):
    path = req.get("path", "")
    if not path:
        raise HTTPException(400, "Missing 'path' field")
    try:
        from omics.agent.handler import OmicsAgentHandler
        h = OmicsAgentHandler()
        result = h.do_omics_data_info({"path": path}, None)
        if result.data.get("status") == "error":
            raise HTTPException(400, result.data.get("msg", "Unknown error"))
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/data/search", response_model=List[DataSearchResult])
async def data_search(req: dict):
    query = req.get("query", "")
    if not query:
        raise HTTPException(400, "Missing 'query' field")
    try:
        from omics.agent.handler import OmicsAgentHandler
        h = OmicsAgentHandler()
        result = h.do_omics_data_search({"query": query}, None)
        if result.data.get("status") == "error":
            raise HTTPException(400, result.data.get("msg", "Unknown error"))
        results = result.data.get("results", [])
        return [DataSearchResult(**r) for r in results]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/data/fetch")
async def data_fetch(req: dict):
    accession = req.get("accession", "")
    if not accession:
        raise HTTPException(400, "Missing 'accession' field")
    try:
        from omics.agent.handler import OmicsAgentHandler
        h = OmicsAgentHandler()
        result = h.do_omics_data_fetch({"accession": accession}, None)
        if result.data.get("status") == "error":
            raise HTTPException(400, result.data.get("msg", "Unknown error"))
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
