"""Step Grouping - Analyze and group pipeline steps for efficient execution.

This module provides functionality to group multiple pipeline steps that should execute
together in the same environment (e.g., Docker container, remote worker). It analyzes
the DAG to ensure only consecutive steps are grouped and aggregates their resource
requirements intelligently.
"""

from collections import defaultdict
from dataclasses import dataclass

from flowyml.core.graph import DAG
from flowyml.core.step import Step
from flowyml.core.resources import ResourceRequirements


@dataclass
class StepGroup:
    """Represents a group of steps that execute together.

    Args:
        group_name: Name identifier for this group
        steps: List of Step objects in this group
        aggregated_resources: Combined resource requirements for the group
        execution_order: Ordered list of step names (topological order within group)
    """

    group_name: str
    steps: list[Step]
    aggregated_resources: ResourceRequirements | None
    execution_order: list[str]

    def __repr__(self) -> str:
        step_names = [s.name for s in self.steps]
        return f"StepGroup(name='{self.group_name}', steps={step_names})"


class StepGroupAnalyzer:
    """Analyzes pipeline DAG to create valid step groups.

    This analyzer ensures that:
    1. Only steps with the same execution_group name are grouped
    2. Grouped steps can execute consecutively (no gaps in DAG)
    3. Resources are aggregated intelligently (max CPU, memory, etc.)
    4. Execution order within groups is preserved
    """

    def analyze_groups(self, dag: DAG, steps: list[Step]) -> list[StepGroup]:
        """Analyze DAG and create valid step groups.

        Args:
            dag: Pipeline DAG
            steps: List of all pipeline steps

        Returns:
            List of StepGroup objects (excludes ungrouped steps)
        """
        # Collect steps by execution_group
        groups_dict: dict[str, list[Step]] = defaultdict(list)

        for step in steps:
            if step.execution_group:
                groups_dict[step.execution_group].append(step)

        # Process each group
        step_groups = []
        for group_name, group_steps in groups_dict.items():
            # Split into consecutive subgroups if needed
            subgroups = self._split_into_consecutive_groups(group_steps, dag)

            # Create StepGroup for each subgroup
            for i, subgroup in enumerate(subgroups):
                # If original group was split, append index to name
                final_name = group_name if len(subgroups) == 1 else f"{group_name}_{i}"

                # Get execution order for this subgroup
                exec_order = self._get_execution_order(subgroup, dag)

                # Aggregate resources
                aggregated = self._aggregate_resources(subgroup)

                step_groups.append(
                    StepGroup(
                        group_name=final_name,
                        steps=subgroup,
                        aggregated_resources=aggregated,
                        execution_order=exec_order,
                    ),
                )

        return step_groups

    def _split_into_consecutive_groups(
        self,
        steps: list[Step],
        dag: DAG,
    ) -> list[list[Step]]:
        """Split steps into subgroups that can execute consecutively.

        This handles cases where steps with the same execution_group are not
        actually consecutive in the DAG (e.g., parallel branches).

        Args:
            steps: Steps with the same execution_group
            dag: Pipeline DAG

        Returns:
            List of step sublists, where each sublist can execute consecutively
        """
        if len(steps) <= 1:
            return [steps] if steps else []

        # Build a mapping of step names to steps
        step_map = {s.name: s for s in steps}
        step_names = set(step_map.keys())

        # Get topological order for all nodes
        try:
            all_nodes = dag.topological_sort()
        except ValueError:
            # DAG has cycles, return each step as separate group
            return [[s] for s in steps]

        # Filter to only our steps, preserving topological order
        ordered_steps = [step_map[node.name] for node in all_nodes if node.name in step_names]

        # Now split into consecutive sequences
        # Two steps are consecutive if there are no other group steps between them
        subgroups: list[list[Step]] = []
        current_group: list[Step] = []

        for step in ordered_steps:
            if not current_group:
                # Start new group
                current_group.append(step)
            else:
                # Check if this step can join current group
                last_step = current_group[-1]

                if self._are_consecutive(last_step, step, dag, step_names):
                    current_group.append(step)
                else:
                    # Gap detected, finalize current group and start new one
                    subgroups.append(current_group)
                    current_group = [step]

        # Add final group
        if current_group:
            subgroups.append(current_group)

        return subgroups

    def _are_consecutive(
        self,
        step1: Step,
        step2: Step,
        dag: DAG,
        group_step_names: set[str],
    ) -> bool:
        """Check if two steps can execute consecutively in a group.

        Steps are consecutive if:
        - step2 depends on step1 (directly or transitively) OR they're independent
        - All intermediate dependencies are NOT in this group

        Args:
            step1: First step
            step2: Second step
            dag: Pipeline DAG
            group_step_names: Set of all step names in this group

        Returns:
            True if steps can execute consecutively
        """
        # Get ALL transitively producing and consuming nodes between step1 and step2
        # Steps are consecutive if there are no intermediate steps NOT in this group
        # that must execute between step1 and step2.
        all_deps_of_s2 = dag.get_all_dependencies(step2.name)

        # If step1 is not even a dependency of step2, they are independent.
        # They can be grouped as long as there is no path from step1 to step2
        # through an external step.

        # All nodes on any path from step1 to step2:
        all_successors_of_s1 = dag.get_all_dependents(step1.name)
        intermediate_nodes = all_successors_of_s1 & all_deps_of_s2

        # If any node on a path from s1 to s2 is NOT in the group, they are not consecutive
        external_intermediates = intermediate_nodes - group_step_names

        return len(external_intermediates) == 0

    def _get_execution_order(self, steps: list[Step], dag: DAG) -> list[str]:
        """Get topological execution order for steps in a group.

        Args:
            steps: Steps in the group
            dag: Pipeline DAG

        Returns:
            Ordered list of step names
        """
        step_names = {s.name for s in steps}

        # Get full topological order
        all_nodes = dag.topological_sort()

        # Filter to only our steps
        return [node.name for node in all_nodes if node.name in step_names]

    def _aggregate_resources(self, steps: list[Step]) -> ResourceRequirements | None:
        """Aggregate resource requirements from multiple steps.

        Strategy:
        - CPU: Take maximum
        - Memory: Take maximum
        - GPU: Merge configs (max count, best type)
        - Storage: Take maximum
        - Node affinity: Merge required/preferred labels

        Args:
            steps: Steps to aggregate resources from

        Returns:
            Aggregated ResourceRequirements or None if no steps have resources
        """
        resource_reqs = [s.resources for s in steps if s.resources and isinstance(s.resources, ResourceRequirements)]

        if not resource_reqs:
            return None

        # Start with first resource requirement
        aggregated = resource_reqs[0]

        # Merge with remaining
        for req in resource_reqs[1:]:
            aggregated = aggregated.merge_with(req)

        return aggregated


def get_execution_units(dag: DAG, steps: list[Step]) -> list[Step | StepGroup]:
    """Get ordered execution units (individual steps or groups).

    This is a convenience function that analyzes groups and returns a mixed list
    of ungrouped steps and StepGroups in topological order.

    Args:
        dag: Pipeline DAG
        steps: All pipeline steps

    Returns:
        List of execution units (Step or StepGroup) in execution order
    """
    analyzer = StepGroupAnalyzer()
    step_groups = analyzer.analyze_groups(dag, steps)

    # Build a mapping of step names to their groups
    step_to_group: dict[str, StepGroup] = {}
    for group in step_groups:
        for step in group.steps:
            step_to_group[step.name] = group

    # To correctly determine execution order of units (which may have changed due to grouping),
    # we build a new DAG where each node is an execution unit (Step or StepGroup).
    from flowyml.core.graph import Node as DAGNode

    units_dag = DAG()
    unit_map: dict[str, Step | StepGroup] = {}

    # Add units as nodes
    processed_steps = set()
    for step in steps:
        if step.name in processed_steps:
            continue

        unit: Step | StepGroup
        if step.name in step_to_group:
            unit = step_to_group[step.name]
            unit_name = f"group:{unit.group_name}"
            # Extract names for inputs/outputs
            u_inputs_set = set()
            u_outputs_set = set()
            for s in unit.steps:
                u_inputs_set.update(s.inputs)
                u_outputs_set.update(s.outputs)
                processed_steps.add(s.name)

            # External inputs are those not produced within the group
            u_inputs = list(u_inputs_set - u_outputs_set)
            u_outputs = list(u_outputs_set)
        else:
            unit = step
            unit_name = step.name
            u_inputs = step.inputs
            u_outputs = step.outputs
            processed_steps.add(step.name)

        unit_map[unit_name] = unit
        units_dag.add_node(DAGNode(name=unit_name, step=unit, inputs=u_inputs, outputs=u_outputs))

    # Build edges and sort
    units_dag.build_edges()
    sorted_unit_nodes = units_dag.topological_sort()

    return [unit_map[node.name] for node in sorted_unit_nodes]
