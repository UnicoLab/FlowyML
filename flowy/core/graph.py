"""
Graph Module - DAG construction and analysis for pipelines.
"""

from typing import Dict, List, Set, Optional
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class Node:
    """A node in the pipeline DAG."""
    name: str
    step: any  # Step object
    inputs: List[str]
    outputs: List[str]
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        return isinstance(other, Node) and self.name == other.name


class DAG:
    """
    Directed Acyclic Graph for pipeline execution planning.
    """
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Set[str]] = defaultdict(set)  # node -> dependencies
        self.reverse_edges: Dict[str, Set[str]] = defaultdict(set)  # node -> dependents
        self.asset_producers: Dict[str, str] = {}  # asset -> producing node
        self.asset_consumers: Dict[str, Set[str]] = defaultdict(set)  # asset -> consuming nodes
    
    def add_node(self, node: Node):
        """Add a node to the graph."""
        self.nodes[node.name] = node
        
        # Track asset production
        for output in node.outputs:
            self.asset_producers[output] = node.name
        
        # Track asset consumption
        for input_asset in node.inputs:
            self.asset_consumers[input_asset].add(node.name)
    
    def build_edges(self):
        """Build edges based on asset dependencies."""
        for node_name, node in self.nodes.items():
            for input_asset in node.inputs:
                if input_asset in self.asset_producers:
                    producer = self.asset_producers[input_asset]
                    self.edges[node_name].add(producer)
                    self.reverse_edges[producer].add(node_name)
    
    def topological_sort(self) -> List[Node]:
        """
        Return nodes in topological order (dependencies before dependents).
        
        Returns:
            List of nodes in execution order
            
        Raises:
            ValueError: If graph contains cycles
        """
        in_degree = {name: len(deps) for name, deps in self.edges.items()}
        
        # Add nodes with no dependencies
        for name in self.nodes:
            if name not in in_degree:
                in_degree[name] = 0
        
        # Find starting nodes (no dependencies)
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node_name = queue.popleft()
            result.append(self.nodes[node_name])
            
            # Reduce in-degree for dependent nodes
            for dependent in self.reverse_edges[node_name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.nodes):
            raise ValueError("Pipeline contains cycles!")
        
        return result
    
    def get_dependencies(self, node_name: str) -> Set[str]:
        """Get direct dependencies of a node."""
        return self.edges.get(node_name, set())
    
    def get_dependents(self, node_name: str) -> Set[str]:
        """Get direct dependents of a node."""
        return self.reverse_edges.get(node_name, set())
    
    def get_all_dependencies(self, node_name: str) -> Set[str]:
        """Get all transitive dependencies of a node."""
        visited = set()
        queue = deque([node_name])
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            for dep in self.edges.get(current, set()):
                if dep not in visited:
                    queue.append(dep)
        
        visited.discard(node_name)
        return visited
    
    def get_all_dependents(self, node_name: str) -> Set[str]:
        """Get all transitive dependents of a node."""
        visited = set()
        queue = deque([node_name])
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            for dep in self.reverse_edges.get(current, set()):
                if dep not in visited:
                    queue.append(dep)
        
        visited.discard(node_name)
        return visited
    
    def validate(self) -> List[str]:
        """
        Validate the graph for common issues.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check for undefined inputs
        for node_name, node in self.nodes.items():
            for input_asset in node.inputs:
                if input_asset not in self.asset_producers:
                    errors.append(
                        f"Node '{node_name}' requires undefined asset '{input_asset}'"
                    )
        
        # Check for cycles
        try:
            self.topological_sort()
        except ValueError as e:
            errors.append(str(e))
        
        # Check for duplicate outputs
        output_counts = defaultdict(int)
        for node in self.nodes.values():
            for output in node.outputs:
                output_counts[output] += 1
        
        for output, count in output_counts.items():
            if count > 1:
                errors.append(f"Multiple nodes produce asset '{output}'")
        
        return errors
    
    def visualize(self) -> str:
        """Generate a simple text visualization of the DAG."""
        lines = ["Pipeline DAG:"]
        lines.append("=" * 50)
        
        try:
            sorted_nodes = self.topological_sort()
            for i, node in enumerate(sorted_nodes, 1):
                deps = self.get_dependencies(node.name)
                deps_str = ", ".join(deps) if deps else "none"
                lines.append(f"{i}. {node.name}")
                lines.append(f"   Inputs: {node.inputs}")
                lines.append(f"   Outputs: {node.outputs}")
                lines.append(f"   Dependencies: {deps_str}")
                lines.append("")
        except ValueError as e:
            lines.append(f"ERROR: {e}")
        
        return "\n".join(lines)
