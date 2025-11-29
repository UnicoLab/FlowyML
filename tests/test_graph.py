"""Test suite for graph/DAG functionality."""

import unittest
from flowyml.core.graph import DAG, Node
from flowyml import Pipeline, step
from tests.base import BaseTestCase


class TestGraph(BaseTestCase):
    """Test suite for DAG functionality."""

    def test_dag_creation(self):
        """Test DAG creation."""
        dag = DAG()
        self.assertEqual(len(dag.nodes), 0)

    def test_dag_add_node(self):
        """Test adding nodes to DAG."""
        dag = DAG()

        node1 = Node("step1", None, [], ["output1"])
        node2 = Node("step2", None, ["output1"], ["output2"])

        dag.add_node(node1)
        dag.add_node(node2)

        self.assertEqual(len(dag.nodes), 2)
        self.assertIn("step1", dag.nodes)
        self.assertIn("step2", dag.nodes)

    def test_dag_build_edges(self):
        """Test building edges based on dependencies."""
        dag = DAG()

        node1 = Node("step1", None, [], ["data"])
        node2 = Node("step2", None, ["data"], ["result"])

        dag.add_node(node1)
        dag.add_node(node2)
        dag.build_edges()

        # step2 depends on step1
        self.assertIn("step1", dag.edges["step2"])

    def test_dag_topological_sort(self):
        """Test topological sorting of DAG."""
        dag = DAG()

        # Create a simple dependency chain: step1 -> step2 -> step3
        node1 = Node("step1", None, [], ["data1"])
        node2 = Node("step2", None, ["data1"], ["data2"])
        node3 = Node("step3", None, ["data2"], ["data3"])

        dag.add_node(node1)
        dag.add_node(node2)
        dag.add_node(node3)
        dag.build_edges()

        sorted_nodes = dag.topological_sort()
        sorted_names = [n.name for n in sorted_nodes]

        # Verify order
        step1_idx = sorted_names.index("step1")
        step2_idx = sorted_names.index("step2")
        step3_idx = sorted_names.index("step3")

        self.assertLess(step1_idx, step2_idx)
        self.assertLess(step2_idx, step3_idx)

    def test_dag_parallel_branches(self):
        """Test DAG with parallel branches."""
        dag = DAG()

        # Create: step1 -> [step2, step3] -> step4
        node1 = Node("step1", None, [], ["data1"])
        node2 = Node("step2", None, ["data1"], ["data2"])
        node3 = Node("step3", None, ["data1"], ["data3"])
        node4 = Node("step4", None, ["data2", "data3"], ["final"])

        dag.add_node(node1)
        dag.add_node(node2)
        dag.add_node(node3)
        dag.add_node(node4)
        dag.build_edges()

        sorted_nodes = dag.topological_sort()
        sorted_names = [n.name for n in sorted_nodes]

        # step1 should be first
        self.assertEqual(sorted_names[0], "step1")
        # step4 should be last
        self.assertEqual(sorted_names[-1], "step4")
        # step2 and step3 should be in the middle (order doesn't matter)
        self.assertIn("step2", sorted_names[1:3])
        self.assertIn("step3", sorted_names[1:3])


if __name__ == "__main__":
    unittest.main()
