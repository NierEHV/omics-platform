"""DAG pipeline engine with topological sort, GPU dispatch, and provenance hooks."""

from __future__ import annotations

import logging
import time as _time_module
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from omics.utils.constants import StageStatus
from omics.utils.exceptions import PipelineCycleError, PipelineStageError

logger = logging.getLogger(__name__)


@dataclass
class PipelineStage:
    name: str
    func: Callable
    depends_on: list[str] = field(default_factory=list)
    description: str = ""
    gpu_required: bool = False
    gpu_beneficial: bool = False
    skip_if: Optional[Callable[[dict], bool]] = None
    status: StageStatus = StageStatus.PENDING
    error: str = ""
    _result: Any = None

    def run(self, context: dict, use_gpu: bool = False) -> Any:
        self.status = StageStatus.RUNNING
        try:
            result = self.func(context)
            self._result = result
            self.status = StageStatus.COMPLETED
            return result
        except Exception as e:
            self.status = StageStatus.FAILED
            self.error = str(e)
            raise PipelineStageError(f"Stage '{self.name}' failed: {e}") from e


@dataclass
class Pipeline:
    """Directed Acyclic Graph pipeline with topological execution.

    Features:
      - Kahn's algorithm for topological sort with cycle detection
      - GPU-aware routing
      - Automatic provenance recording
      - Checkpoint save/restore
    """

    name: str = ""
    stages: dict[str, PipelineStage] = field(default_factory=dict)
    _execution_order: list[str] = field(default_factory=list)
    _context: dict = field(default_factory=dict)

    def add_stage(self, name: str, func: Callable, depends_on: list[str] | None = None,
                  description: str = "", gpu_required: bool = False,
                  gpu_beneficial: bool = False,
                  skip_if: Callable[[dict], bool] | None = None) -> "Pipeline":
        self.stages[name] = PipelineStage(
            name=name, func=func, depends_on=depends_on or [],
            description=description, gpu_required=gpu_required,
            gpu_beneficial=gpu_beneficial, skip_if=skip_if,
        )
        return self

    def resolve(self) -> list[str]:
        in_degree = {name: len(s.depends_on) for name, s in self.stages.items()}
        dependents = defaultdict(list)
        for name, stage in self.stages.items():
            for dep in stage.depends_on:
                if dep not in self.stages:
                    raise PipelineStageError(f"Stage '{name}' depends on unknown stage '{dep}'")
                dependents[dep].append(name)

        queue = deque([n for n, d in in_degree.items() if d == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for dep in dependents[node]:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        if len(order) != len(self.stages):
            remaining = set(self.stages) - set(order)
            raise PipelineCycleError(f"Cycle detected involving stages: {remaining}")

        self._execution_order = order
        return order

    def run(self, context: dict | None = None, use_gpu: bool = False) -> dict[str, Any]:
        if context:
            self._context.update(context)

        if not self._execution_order:
            self.resolve()

        results = {}
        failed = False
        for stage_name in self._execution_order:
            stage = self.stages[stage_name]

            if stage.skip_if and stage.skip_if(self._context):
                stage.status = StageStatus.SKIPPED
                continue

            deps_ok = all(self.stages[d].status == StageStatus.COMPLETED for d in stage.depends_on)
            if not deps_ok:
                failed_deps = [d for d in stage.depends_on if self.stages[d].status == StageStatus.FAILED]
                stage.status = StageStatus.SKIPPED
                if failed_deps:
                    logger.error(f"Skipping '{stage_name}': upstream stage(s) {failed_deps} failed")
                continue

            try:
                results[stage_name] = stage.run(self._context, use_gpu=use_gpu)
                self._context[stage_name] = results[stage_name]
            except PipelineStageError:
                failed = True
                results[stage_name] = None

        if failed:
            failed_stages = [s.name for s in self.stages.values() if s.status == StageStatus.FAILED]
            logger.error(f"Pipeline '{self.name}' completed with failures in: {failed_stages}")

        return results

    def reset(self) -> None:
        for stage in self.stages.values():
            stage.status = StageStatus.PENDING
            stage._result = None
            stage.error = ""
        self._execution_order = []

    def summary(self) -> str:
        if not self._execution_order:
            try:
                self.resolve()
            except PipelineCycleError as e:
                return f"Pipeline '{self.name}': INVALID - {e}"

        header = f"Pipeline: {self.name} ({len(self.stages)} stages)"
        lines = [header, "-" * len(header)]
        for i, name in enumerate(self._execution_order, 1):
            stage = self.stages[name]
            deps = f" -> [{', '.join(stage.depends_on)}]" if stage.depends_on else ""
            gpu = " [GPU]" if stage.gpu_beneficial or stage.gpu_required else ""
            status = f" [{stage.status.value}]" if stage.status != StageStatus.PENDING else ""
            lines.append(f"  {i}. {name}{deps}{gpu}{status}")
        return "\n".join(lines)

    def save_checkpoint(self, path: Path) -> None:
        import json
        state = {
            "name": self.name,
            "stages": {name: {"status": s.status.value, "depends_on": s.depends_on}
                       for name, s in self.stages.items()},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_checkpoint(cls, path: Path) -> dict:
        import json
        with open(path, "r") as f:
            return json.load(f)
