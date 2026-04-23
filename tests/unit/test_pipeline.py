# ComputeHub Tests - Pipeline Unit Tests
import sys
sys.path.insert(0, '../')
from src.pipeline.pipeline import TaskPipeline

def test_pipeline_passes_valid():
    pipeline = TaskPipeline()
    ok, data, err = pipeline.process({"framework": "pytorch", "gpu_required": 2})
    assert ok, f"Should pass: {err}"
    assert data.get("pipeline_version") == "2.0"
    print("✅ test_pipeline_passes_valid")

def test_pipeline_blocks_invalid():
    pipeline = TaskPipeline()
    ok, data, err = pipeline.process({"code_url": "http://evil.com/rm -rf /"})
    assert not ok
    print("✅ test_pipeline_blocks_invalid")

if __name__ == "__main__":
    test_pipeline_passes_valid()
    test_pipeline_blocks_invalid()
    print("✅ All tests passed")
