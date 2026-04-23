# ComputeHub Tests - Kernel Unit Tests
import sys
sys.path.insert(0, '../')
from src.kernel.kernel import DeterministicKernel, TaskUnit, TaskPriority
from src.kernel.load_balancer import LoadBalancer, NodeStatus, NodeMetric

def test_kernel_submit():
    kernel = DeterministicKernel()
    task = TaskUnit(id="test-1", action="STATUS", priority=TaskPriority.HIGH)
    result = kernel.submit(task)
    assert result.id == "test-1"
    status = kernel.get_status()
    assert status["queue_depth"] == 1
    kernel.stop()
    print("✅ test_kernel_submit")

def test_load_balancer():
    lb = LoadBalancer()
    lb.register_node(NodeMetric(id="n1", name="gpu-1", status=NodeStatus.ONLINE, gpu_count=2))
    lb.register_node(NodeMetric(id="n2", name="gpu-2", status=NodeStatus.ONLINE, gpu_count=4))
    node_id = lb.select_node(required_gpu=1)
    assert node_id is not None
    print("✅ test_load_balancer")

if __name__ == "__main__":
    test_kernel_submit()
    test_load_balancer()
    print("✅ All tests passed")
