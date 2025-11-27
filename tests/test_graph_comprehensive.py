"""Comprehensive test suite for graph/DAG functionality."""

import unittest
from uniflow.core.graph import DAG, Node
from uniflow import Pipeline, step
from tests.base import BaseTestCase


class TestGraphComprehensive(BaseTestCase):
    """Comprehensive test suite for DAG functionality."""

    def test_dag_empty_initialization(self):
        """Test empty DAG initialization."""
        dag = DAG()

        self.assertEqual(len(dag.nodes), 0)
        self.assertEqual(len(dag.edges), 0)

    def test_dag_single_node(self):
        """Test DAG with single node."""
        dag = DAG()
        node = Node("single", None, [], ["output"])
        dag.add_node(node)

        self.assertEqual(len(dag.nodes), 1)
        self.assertIn("single", dag.nodes)

    def test_dag_asset_producers(self):
        """Test DAG tracks asset producers."""
        dag = DAG()

        node1 = Node("producer", None, [], ["data"])
        dag.add_node(node1)

        self.assertEqual(dag.asset_producers["data"], "producer")

    def test_dag_asset_consumers(self):
        """Test DAG tracks asset consumers."""
        dag = DAG()

        node1 = Node("producer", None, [], ["data"])
        node2 = Node("consumer", None, ["data"], ["result"])

        dag.add_node(node1)
        dag.add_node(node2)

        self.assertIn("consumer", dag.asset_consumers["data"])

    def test_dag_dependencies(self):
        """Test DAG dependency tracking."""
        dag = DAG()

        node1 = Node("step1", None, [], ["data1"])
        node2 = Node("step2", None, ["data1"], ["data2"])

        dag.add_node(node1)
        dag.add_node(node2)
        dag.build_edges()

        deps = dag.get_dependencies("step2")
        self.assertIn("step1", deps)

    def test_dag_dependents(self):
        """Test DAG dependent tracking."""
        dag = DAG()

        node1 = Node("step1", None, [], ["data1"])
        node2 = Node("step2", None, ["data1"], ["data2"])

        dag.add_node(node1)
        dag.add_node(node2)
        dag.build_edges()

        dependents = dag.get_dependents("step1")
        self.assertIn("step2", dependents)

    def test_dag_linear_chain(self):
        """Test DAG with linear chain of nodes."""
        dag = DAG()

        for i in range(5):
            node = Node(
                f"step{i}",
                None,
                [f"data{i-1}"] if i > 0 else [],
                [f"data{i}"],
            )
            dag.add_node(node)

        dag.build_edges()
        sorted_nodes = dag.topological_sort()

        # Verify order
        for i in range(5):
            self.assertEqual(sorted_nodes[i].name, f"step{i}")

    def test_dag_diamond_pattern(self):
        """Test DAG with diamond dependency pattern."""
        dag = DAG()

        # Diamond: A -> B, A -> C, B -> D, C -> D
        nodeA = Node("A", None, [], ["dataA"])
        nodeB = Node("B", None, ["dataA"], ["dataB"])
        nodeC = Node("C", None, ["dataA"], ["dataC"])
        nodeD = Node("D", None, ["dataB", "dataC"], ["dataD"])

        dag.add_node(nodeA)
        dag.add_node(nodeB)
        dag.add_node(nodeC)
        dag.add_node(nodeD)
        dag.build_edges()

        sorted_nodes = dag.topological_sort()
        names = [n.name for n in sorted_nodes]

        # A must be first, D must be last
        self.assertEqual(names[0], "A")
        self.assertEqual(names[-1], "D")
        # B and C must be in middle
        self.assertIn("B", names[1:3])
        self.assertIn("C", names[1:3])

    def test_dag_validation_success(self):
        """Test DAG validation with valid graph."""
        dag = DAG()

        node1 = Node("step1", None, [], ["data"])
        node2 = Node("step2", None, ["data"], ["result"])

        dag.add_node(node1)
        dag.add_node(node2)
        dag.build_edges()

        errors = dag.validate()
        self.assertEqual(len(errors), 0)

    def test_dag_visualization(self):
        """Test DAG visualization output."""
        dag = DAG()

        node1 = Node("step1", None, [], ["data"])
        node2 = Node("step2", None, ["data"], ["result"])

        dag.add_node(node1)
        dag.add_node(node2)
        dag.build_edges()

        viz = dag.visualize()

        self.assertIn("Pipeline DAG", viz)
        self.assertIn("step1", viz)
        self.assertIn("step2", viz)


if __name__ == "__main__":
    unittest.main()
