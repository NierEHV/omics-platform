"""ConversationRunner — LLM-powered multi-turn omics analysis with tool calling."""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import time
from pathlib import Path
from typing import Optional

from .llm_gateway import llm_gateway

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"

async def _run_in_thread(func, *args, **kwargs):
    """Python 3.8 compat: asyncio.to_thread was added in 3.9."""
    loop = asyncio.get_event_loop()
    if kwargs:
        func = functools.partial(func, **kwargs)
    return await loop.run_in_executor(None, func, *args)

def _get_handler(cwd="."):
    try:
        from omics.agent.handler import OmicsAgentHandler
        return OmicsAgentHandler(cwd=cwd)
    except ImportError:
        return None

logger = logging.getLogger(__name__)

OMICS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "omics_data_info",
            "description": "Inspect an omics data file (.h5ad, .csv, etc.) to get its shape, columns, and metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the data file"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_scrna_qc",
            "description": "Run quality control on scRNA-seq data: filter cells by gene count, filter genes by cell count, remove high mitochondrial percentage cells.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to input .h5ad file"},
                    "output": {"type": "string", "description": "Path to output .h5ad file (default: qc_filtered.h5ad)"},
                    "min_genes": {"type": "integer", "description": "Min genes per cell (default: 200)"},
                    "min_cells": {"type": "integer", "description": "Min cells per gene (default: 3)"},
                    "max_pct_mt": {"type": "number", "description": "Max mitochondrial percentage (default: 20)"},
                },
                "required": ["input"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_scrna_normalize",
            "description": "Normalize scRNA-seq data: library-size normalization + log1p transform. Saves result back to input file if no output specified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to input .h5ad file"},
                    "output": {"type": "string", "description": "Path to output .h5ad file (defaults to overwriting input)"},
                    "target_sum": {"type": "integer", "description": "Normalization target sum (default: 10000)"},
                },
                "required": ["input"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_scrna_reduce",
            "description": "Dimensionality reduction: select highly variable genes, PCA, neighbor graph, UMAP. Automatically normalizes if needed. Saves result back to input file if no output specified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to input .h5ad file"},
                    "output": {"type": "string", "description": "Path to output .h5ad file (defaults to overwriting input)"},
                    "n_hvg": {"type": "integer", "description": "Number of highly variable genes (default: 2000)"},
                    "n_pcs": {"type": "integer", "description": "Number of PCs (default: 50)"},
                    "n_neighbors": {"type": "integer", "description": "Number of neighbors (default: 15)"},
                },
                "required": ["input"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_scrna_cluster",
            "description": "Cluster cells using Leiden algorithm. Automatically runs PCA+neighbors if needed. Saves result back to input file if no output specified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to input .h5ad file"},
                    "output": {"type": "string", "description": "Path to output .h5ad file (defaults to overwriting input)"},
                    "resolution": {"type": "number", "description": "Clustering resolution (default: 1.0)"},
                },
                "required": ["input"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_scrna_markers",
            "description": "Find marker genes for each cluster using differential expression. Saves result back to input file if no output specified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to input .h5ad file"},
                    "output": {"type": "string", "description": "Path to output .h5ad file (defaults to overwriting input)"},
                    "groupby": {"type": "string", "description": "Column to group by (default: 'leiden')"},
                    "n_genes": {"type": "integer", "description": "Top N marker genes per cluster (default: 10)"},
                },
                "required": ["input"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_scrna_trajectory",
            "description": "Run trajectory/pseudotime analysis using diffusion pseudotime or RNA velocity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "method": {"type": "string", "description": "Method: dpt or velocity (default: dpt)"},
                },
                "required": ["input"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_bulk_de",
            "description": "Run differential expression analysis on bulk RNA-seq data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to expression matrix"},
                    "group_col": {"type": "string", "description": "Column with group labels"},
                    "case": {"type": "string", "description": "Case/treatment group name"},
                    "control": {"type": "string", "description": "Control group name"},
                },
                "required": ["input", "group_col", "case", "control"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_bulk_enrich",
            "description": "Run pathway enrichment analysis on DE results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to DE results file"},
                    "gene_col": {"type": "string", "description": "Column name for gene IDs"},
                    "pvalue_col": {"type": "string", "description": "Column name for p-values"},
                },
                "required": ["input", "gene_col"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_visualize_umap",
            "description": "Generate UMAP or other visualization plots from analysis results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Path to .h5ad file"},
                    "color_by": {"type": "string", "description": "Column to color cells by (e.g., 'leiden', 'cell_type')"},
                },
                "required": ["input"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_data_search",
            "description": "Search GEO database for public omics datasets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (e.g., 'lung cancer scRNA-seq')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_gpu_status",
            "description": "Check GPU availability and status on the server.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "omics_config",
            "description": "Get the current omics platform configuration (data dir, output dir, etc.).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

SYSTEM_PROMPT = """# 角色
你是 Omics Visual Pipeline 的科学计算助手。用户是生物信息学研究人员。
平台提供可视化 DAG 分析流程，用户可手动点击节点运行分析。你是可选增强工具。

# 分析能力
- scRNA-seq: QC、标准化、降维(PCA+UMAP)、聚类(Leiden)、标记基因、拟时序、细胞通讯
- Bulk RNA-seq: 差异表达、富集分析
- Spatial transcriptomics: 空间聚类、反卷积
- TCR/免疫组库: 克隆型分析、多样性

# 强制规则
1. 【工具优先】收到分析请求时立即调用对应function。不说"让我检查一下"或"我建议"。
2. 【禁止猜测】不编造输出文件名、分析结果或数据内容。只引用工具返回的实际值。
3. 【精确参数】用户明确指定的参数值必须逐字传递。不用默认值替代。
4. 【路径传递】工具返回的"output"字段是下一步的"input"。逐字传递，不修改。
5. 【失败即报告】工具返回错误时直接报告error message原文。不自行为原因推测或建议修复方案。
6. 【简洁】每次回复≤5句话。不需要问候语、"当然可以"、总结已完成操作。
7. 【中文回复】使用中文。代码、参数名、文件路径保持英文。
8. 【无幻觉调用】只调用tools列表中实际存在的函数。不在文本中伪造<invoke>或<tool_call>等XML标签。
9. 【无冗余检查】用户要求执行操作时不要先调用omics_data_info。直接执行。
10. 【诚实】不知道答案就说不知道，不编造。

# 文件规则
每个工具默认写回INPUT文件。工具响应的"output"字段显示实际文件路径。
当链式调用时，使用前一工具返回的output路径作为下一工具的input。"""


class ConversationRunner:
    """LLM-powered conversation orchestrator for omics analysis."""

    def __init__(self):
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.handler = _get_handler(cwd=str(UPLOADS_DIR))
        self.uploads_dir = UPLOADS_DIR

    async def run(
        self,
        user_message: str,
        files: list[str] | None = None,
        history: list[dict] | None = None,
    ):
        files = files or []
        history = history or []

        if not llm_gateway.ready:
            yield ("error", json.dumps({
                "msg": "LLM not configured. Please set up an API key in Settings first."
            }, ensure_ascii=False))
            yield ("done", json.dumps({"status": "error"}))
            return

        # Build messages
        system_content = SYSTEM_PROMPT
        if files:
            system_content += f"\n\nCurrently uploaded files: {', '.join(files)}"

        messages = [{"role": "system", "content": system_content}]

        for h in history[-10:]:
            role = h.get("role", "user")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": h.get("content", "")})

        messages.append({"role": "user", "content": user_message})

        # Notify frontend
        yield ("meta", json.dumps({"type": "thinking"}))

        try:
            # LLM call with tool calling
            response = await _run_in_thread(
                llm_gateway.client.chat.completions.create,
                model=llm_gateway.model,
                messages=messages,
                tools=OMICS_TOOLS,
                tool_choice="auto",
                temperature=0.3,
                stream=False,
            )
        except Exception as e:
            logger.exception("LLM call failed")
            yield ("error", json.dumps({"msg": f"LLM error: {str(e)}"}))
            yield ("done", json.dumps({"status": "error"}))
            return

        msg = response.choices[0].message

        # If no tool calls, just return the text response
        if not msg.tool_calls:
            yield ("message", json.dumps({
                "role": "assistant",
                "content": msg.content or "",
            }, ensure_ascii=False))
            yield ("done", json.dumps({"status": "completed"}))
            return

        # If omics platform is not installed, return text response without tools
        if self.handler is None:
            yield ("message", json.dumps({
                "role": "assistant",
                "content": (msg.content or "") + "\n\n> Omics platform not installed (requires Python >=3.10). Tools cannot be executed.",
            }, ensure_ascii=False))
            yield ("done", json.dumps({"status": "completed"}))
            return

        # Execute tool calls
        tool_results = []
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            yield ("meta", json.dumps({
                "type": "tool_start",
                "tool": tool_name,
                "args": args,
            }))

            start = time.time()
            try:
                result = await _run_in_thread(self._execute_tool, tool_name, args)
                elapsed = time.time() - start
                tool_data = {
                    "tool": tool_name,
                    "status": result.data.get("status", "success"),
                    "data": self._clean_result(result.data),
                    "elapsed_ms": int(elapsed * 1000),
                    "description": tool_name,
                }
                tool_results.append(tool_data)
                yield ("tool", json.dumps(tool_data, ensure_ascii=False))
            except Exception as e:
                yield ("tool", json.dumps({
                    "tool": tool_name,
                    "status": "error",
                    "data": {"msg": str(e)},
                    "description": tool_name,
                }, ensure_ascii=False))

        # Send tool results back to LLM for summarization
        messages.append({"role": "assistant", "content": None, "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]})

        for i, tc in enumerate(msg.tool_calls):
            tr = tool_results[i] if i < len(tool_results) else {"status": "error", "data": {"msg": "no result"}}
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(tr, ensure_ascii=False),
            })

        messages.append({
            "role": "user",
            "content": "Please summarize the results above in a clear, concise way. Explain what each tool did and what the key findings are.",
        })

        try:
            response2 = await _run_in_thread(
                llm_gateway.client.chat.completions.create,
                model=llm_gateway.model,
                messages=messages,
                temperature=0.5,
                stream=False,
            )
            summary = response2.choices[0].message.content or ""
            yield ("message", json.dumps({
                "role": "assistant",
                "content": summary,
            }, ensure_ascii=False))
        except Exception as e:
            logger.exception("Summary call failed")
            yield ("message", json.dumps({
                "role": "assistant",
                "content": f"Tools executed. Results: {json.dumps([t['tool'] for t in tool_results])}",
            }, ensure_ascii=False))

        yield ("done", json.dumps({"status": "completed"}))

    class _StepOutcome:
        def __init__(self, data):
            self.data = data

    def _execute_tool(self, tool_name: str, args: dict):
        if self.handler is None:
            return self._StepOutcome({"status": "error", "msg": "Omics platform not installed. Requires Python >=3.10."})
        method = getattr(self.handler, f"do_{tool_name}", None)
        if method is None:
            return self._StepOutcome({"status": "error", "msg": f"Unknown tool: {tool_name}"})
        return method(args, None)

    def _clean_result(self, data: dict) -> dict:
        result = {}
        for k, v in data.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                result[k] = v
            elif isinstance(v, (list, tuple)):
                result[k] = [
                    str(x) if not isinstance(x, (str, int, float, bool, type(None))) else x
                    for x in v[:20]
                ]
            else:
                result[k] = str(v)[:500]
        return result
