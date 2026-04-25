"""Scheduler 单元测试"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.kernel.load_balancer import LoadBalancer, NodeMetric, NodeStatus
from src.kernel.scheduler import Scheduler


class TestLoadBalancer:

    def setup_method(self):
        self.lb = LoadBalancer(strategy="round_robin")
        self.lb.register_node(NodeMetric(id="n1", name="node-1", gpu_count=4, status=NodeStatus.ONLINE))
        self.lb.register_node(NodeMetric(id="n2", name="node-2", gpu_count=8, status=NodeStatus.ONLINE))
        self.lb.register_node(NodeMetric(id="n3", name="node-3", gpu_count=1, status=NodeStatus.ONLINE))

    def test_round_robin_alternates(self):
        """round_robin 应该轮询所有节点"""
        n1 = self.lb.select_node(1)
        n2 = self.lb.select_node(1)
        n3 = self.lb.select_node(1)
        n4 = self.lb.select_node(1)
        assert n1 == "n1"
        assert n2 == "n2"
        assert n3 == "n3"
        assert n4 == "n1"  # 循环回来了

    def test_least_connections(self):
        """least_connections 应该选中 queue_depth 最小的"""
        lb = LoadBalancer(strategy="least_connections")
        lb.register_node(NodeMetric(id="n1", name="busy", gpu_count=4, status=NodeStatus.ONLINE, queue_depth=10))
        lb.register_node(NodeMetric(id="n2", name="free", gpu_count=4, status=NodeStatus.ONLINE, queue_depth=1))
        selected = lb.select_node(1)
        assert selected == "n2"

    def test_no_available_node(self):
        """没有可用节点时返回 None"""
        lb = LoadBalancer(strategy="round_robin")
        lb.register_node(NodeMetric(id="n1", name="offline", gpu_count=4, status=NodeStatus.OFFLINE))
        selected = lb.select_node(1)
        assert selected is None

    def test_gpu_requirement(self):
        """GPU 需求过滤"""
        selected = self.lb.select_node(required_gpu=8)
        assert selected == "n2"  # only n2 has >= 8 GPUs

    def test_node_count_property(self):
        assert self.lb.node_count == 3

    def test_online_count_property(self):
        assert self.lb.online_count == 3
        self.lb.update_node_status("n1", NodeStatus.OFFLINE)
        assert self.lb.online_count == 2

    def test_set_strategy(self):
        self.lb.set_strategy("round_robin")
        assert self.lb.strategy == "round_robin"

    def test_invalid_strategy(self):
        self.lb.set_strategy("invalid_strat")
        assert self.lb.strategy != "invalid_strat"


class TestScheduler:

    def test_scheduler_init(self):
        s = Scheduler(strategy="round_robin")
        assert s.load_balancer.strategy == "round_robin"

    def test_scheduler_status(self):
        s = Scheduler()
        status = s.get_status()
        assert "load_balancer" in status
        assert "task_counter" in status
