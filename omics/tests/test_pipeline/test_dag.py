"""Tests for omics.pipeline.dag — DAG engine."""

import pytest
from omics.pipeline.dag import Pipeline, PipelineStage, StageStatus


class TestPipelineStage:
    def test_stage_creation(self):
        stage = PipelineStage(name="test", func=lambda x: x)
        assert stage.name == "test"
        assert stage.status == StageStatus.PENDING
        assert stage.depends_on == []

    def test_stage_with_dependencies(self):
        stage = PipelineStage(name="b", func=lambda x: x, depends_on=["a"])
        assert "a" in stage.depends_on

    def test_stage_gpu_flags(self):
        stage = PipelineStage(name="gpu_stage", func=lambda x: x, gpu_required=True, gpu_beneficial=True)
        assert stage.gpu_required
        assert stage.gpu_beneficial


class TestPipeline:
    def test_pipeline_creation(self):
        pipe = Pipeline(name="test_pipe")
        assert pipe.name == "test_pipe"
        assert len(pipe.stages) == 0

    def test_add_stage(self):
        pipe = Pipeline(name="test_pipe")
        pipe.add_stage("qc", lambda ctx: 1, description="QC step")
        assert "qc" in pipe.stages
        assert pipe.stages["qc"].description == "QC step"

    def test_topological_order(self):
        pipe = Pipeline(name="test")
        results = []

        def make_func(name):
            def f(ctx):
                results.append(name)
            return f

        pipe.add_stage("a", make_func("a"))
        pipe.add_stage("b", make_func("b"), depends_on=["a"])
        pipe.add_stage("c", make_func("c"), depends_on=["b"])
        pipe.add_stage("d", make_func("d"), depends_on=["a"])

        pipe.run()
        assert results.index("a") < results.index("b")
        assert results.index("b") < results.index("c")
        assert results.index("a") < results.index("d")

    def test_cycle_detection(self):
        pipe = Pipeline(name="cyclic")
        pipe.add_stage("a", lambda x: x, depends_on=["b"])
        pipe.add_stage("b", lambda x: x, depends_on=["a"])
        with pytest.raises(Exception):
            pipe.run()

    def test_skip_if_condition(self):
        pipe = Pipeline(name="test")
        pipe.add_stage("always_skip", lambda ctx: setattr(ctx, "skipped", True), skip_if=lambda ctx: True)
        ctx = {}
        pipe.run(context=ctx)
        assert not hasattr(ctx, "skipped")  # or check stage status

    def test_stage_status_after_run(self):
        pipe = Pipeline(name="test")
        pipe.add_stage("ok", lambda ctx: 42)
        pipe.run()
        assert pipe.stages["ok"].status == StageStatus.COMPLETED

    def test_stage_result(self):
        pipe = Pipeline(name="test")
        pipe.add_stage("compute", lambda ctx: 42)
        pipe.run()
        assert pipe.result("compute") == 42
