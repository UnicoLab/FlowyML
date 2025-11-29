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
        # Get all dependencies of step2
        step2_deps = dag.get_all_dependencies(step2.name)

        # If step2 doesn't depend on anything in the group, they can be consecutive
        # (parallel steps in same group are OK if no dependencies)
        group_deps = step2_deps & group_step_names
        if not group_deps:
            # No dependencies from this group, consecutive is OK
            return True

        # If step2 depends on step1, check for intermediate group steps
        if step1.name in step2_deps:
            # Get all group steps that step2 depends on (excluding step1)
            intermediate = group_deps - {step1.name}

            # If there are NO intermediate group steps, they're consecutive
            return len(intermediate) == 0

        # step2 doesn't depend on step1, not consecutive
        return False

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

    # Get topological order of all nodes
    all_nodes = dag.topological_sort()

    # Build execution units, avoiding duplicates for grouped steps
    execution_units: list[Step | StepGroup] = []
    processed_groups: set[str] = set()

    for node in all_nodes:
        # Find the step object
        step = next((s for s in steps if s.name == node.name), None)
        if not step:
            continue

        # Check if this step belongs to a group
        if step.name in step_to_group:
            group = step_to_group[step.name]

            # Only add the group once (when we encounter its first step)
            if group.group_name not in processed_groups:
                execution_units.append(group)
                processed_groups.add(group.group_name)
        else:
            # Ungrouped step, add as-is
            execution_units.append(step)

    return execution_units
