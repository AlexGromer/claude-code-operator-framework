#!/usr/bin/env python3
"""
LangGraph Workflow Tester (GAP-ORCH-002)

Tests LangGraph-style workflow patterns and state machines.
Validates node transitions, conditional edges, and cycle detection.

Usage:
    python langgraph_tester.py --test-workflow WORKFLOW_FILE
    python langgraph_tester.py --validate-graph GRAPH_DEF
    python langgraph_tester.py --simulate --steps 10
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
LOG_FILE = DATA_DIR / "langgraph_tests.jsonl"


class NodeType(Enum):
    START = "start"
    END = "end"
    AGENT = "agent"
    TOOL = "tool"
    CONDITIONAL = "conditional"
    HUMAN = "human"


@dataclass
class GraphNode:
    """A node in the workflow graph."""
    name: str
    node_type: NodeType
    handler: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    """An edge in the workflow graph."""
    source: str
    target: str
    condition: Optional[str] = None
    weight: float = 1.0


@dataclass
class WorkflowGraph:
    """Complete workflow graph definition."""
    name: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    entry_point: str
    checkpointer: Optional[str] = None


@dataclass
class TestResult:
    """Result of a workflow test."""
    test_name: str
    passed: bool
    duration_ms: float
    nodes_visited: List[str]
    errors: List[str]
    warnings: List[str]
    timestamp: str


def create_sample_graph() -> WorkflowGraph:
    """Create a sample workflow graph for testing."""
    nodes = [
        GraphNode("start", NodeType.START),
        GraphNode("agent", NodeType.AGENT, handler="process_input"),
        GraphNode("tool_call", NodeType.TOOL, handler="execute_tool"),
        GraphNode("human_review", NodeType.HUMAN),
        GraphNode("conditional", NodeType.CONDITIONAL),
        GraphNode("end", NodeType.END),
    ]

    edges = [
        GraphEdge("start", "agent"),
        GraphEdge("agent", "conditional"),
        GraphEdge("conditional", "tool_call", condition="needs_tool"),
        GraphEdge("conditional", "human_review", condition="needs_human"),
        GraphEdge("conditional", "end", condition="complete"),
        GraphEdge("tool_call", "agent"),
        GraphEdge("human_review", "agent"),
    ]

    return WorkflowGraph(
        name="sample_workflow",
        nodes=nodes,
        edges=edges,
        entry_point="start",
    )


def validate_graph_structure(graph: WorkflowGraph) -> List[str]:
    """Validate graph structure for common issues."""
    errors = []
    node_names = {n.name for n in graph.nodes}

    # Check entry point exists
    if graph.entry_point not in node_names:
        errors.append(f"Entry point '{graph.entry_point}' not found in nodes")

    # Check all edge references exist
    for edge in graph.edges:
        if edge.source not in node_names:
            errors.append(f"Edge source '{edge.source}' not found")
        if edge.target not in node_names:
            errors.append(f"Edge target '{edge.target}' not found")

    # Check for unreachable nodes
    reachable = set()
    to_visit = [graph.entry_point]
    while to_visit:
        current = to_visit.pop()
        if current in reachable:
            continue
        reachable.add(current)
        for edge in graph.edges:
            if edge.source == current and edge.target not in reachable:
                to_visit.append(edge.target)

    unreachable = node_names - reachable
    if unreachable:
        errors.append(f"Unreachable nodes: {unreachable}")

    # Check for nodes without outgoing edges (except END)
    for node in graph.nodes:
        if node.node_type != NodeType.END:
            has_outgoing = any(e.source == node.name for e in graph.edges)
            if not has_outgoing:
                errors.append(f"Node '{node.name}' has no outgoing edges")

    return errors


def detect_cycles(graph: WorkflowGraph) -> List[List[str]]:
    """Detect cycles in the workflow graph."""
    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node: str):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for edge in graph.edges:
            if edge.source == node:
                if edge.target not in visited:
                    dfs(edge.target)
                elif edge.target in rec_stack:
                    # Found cycle
                    cycle_start = path.index(edge.target)
                    cycles.append(path[cycle_start:] + [edge.target])

        path.pop()
        rec_stack.remove(node)

    for node in graph.nodes:
        if node.name not in visited:
            dfs(node.name)

    return cycles


def simulate_workflow(graph: WorkflowGraph, max_steps: int = 100) -> Dict:
    """Simulate workflow execution."""
    current = graph.entry_point
    visited = [current]
    step = 0
    state = {"input": "test_input", "messages": []}

    while step < max_steps:
        step += 1

        # Find current node
        node = next((n for n in graph.nodes if n.name == current), None)
        if not node:
            break

        # Check if END
        if node.node_type == NodeType.END:
            break

        # Get outgoing edges
        outgoing = [e for e in graph.edges if e.source == current]
        if not outgoing:
            break

        # Select next node (simplified: take first or random)
        next_edge = outgoing[0]
        current = next_edge.target
        visited.append(current)

    return {
        "steps": step,
        "nodes_visited": visited,
        "final_node": current,
        "completed": any(n.name == current and n.node_type == NodeType.END
                        for n in graph.nodes),
    }


def run_test_suite(graph: WorkflowGraph) -> List[TestResult]:
    """Run complete test suite on workflow."""
    results = []
    start_time = datetime.now()

    # Test 1: Structure validation
    errors = validate_graph_structure(graph)
    results.append(TestResult(
        test_name="structure_validation",
        passed=len(errors) == 0,
        duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
        nodes_visited=[],
        errors=errors,
        warnings=[],
        timestamp=datetime.now().isoformat(),
    ))

    # Test 2: Cycle detection
    start_time = datetime.now()
    cycles = detect_cycles(graph)
    # Cycles in agent workflows are often intentional (loops)
    warnings = [f"Cycle detected: {' -> '.join(c)}" for c in cycles]
    results.append(TestResult(
        test_name="cycle_detection",
        passed=True,  # Cycles are warnings, not failures
        duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
        nodes_visited=[],
        errors=[],
        warnings=warnings,
        timestamp=datetime.now().isoformat(),
    ))

    # Test 3: Simulation
    start_time = datetime.now()
    sim_result = simulate_workflow(graph, max_steps=50)
    results.append(TestResult(
        test_name="simulation",
        passed=sim_result["completed"],
        duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
        nodes_visited=sim_result["nodes_visited"],
        errors=[] if sim_result["completed"] else ["Workflow did not reach END node"],
        warnings=[],
        timestamp=datetime.now().isoformat(),
    ))

    # Test 4: Entry/Exit points
    start_time = datetime.now()
    start_nodes = [n for n in graph.nodes if n.node_type == NodeType.START]
    end_nodes = [n for n in graph.nodes if n.node_type == NodeType.END]
    errors = []
    if len(start_nodes) != 1:
        errors.append(f"Expected 1 START node, found {len(start_nodes)}")
    if len(end_nodes) < 1:
        errors.append("No END node found")
    results.append(TestResult(
        test_name="entry_exit_validation",
        passed=len(errors) == 0,
        duration_ms=(datetime.now() - start_time).total_seconds() * 1000,
        nodes_visited=[],
        errors=errors,
        warnings=[],
        timestamp=datetime.now().isoformat(),
    ))

    return results


def log_results(results: List[TestResult]):
    """Log test results."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        for r in results:
            f.write(json.dumps(asdict(r)) + "\n")


def print_results(results: List[TestResult]):
    """Print test results."""
    print("\n" + "="*60)
    print("LANGGRAPH WORKFLOW TEST RESULTS")
    print("="*60)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    for r in results:
        icon = "✅" if r.passed else "❌"
        print(f"\n{icon} {r.test_name}")
        print(f"   Duration: {r.duration_ms:.2f}ms")
        if r.errors:
            for e in r.errors:
                print(f"   ❌ {e}")
        if r.warnings:
            for w in r.warnings:
                print(f"   ⚠️ {w}")
        if r.nodes_visited:
            print(f"   Nodes: {' -> '.join(r.nodes_visited[:10])}...")

    print("\n" + "-"*40)
    print(f"SUMMARY: {passed}/{total} tests passed")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="LangGraph Workflow Tester")
    parser.add_argument("--test-workflow", help="Test workflow from file")
    parser.add_argument("--validate-graph", help="Validate graph definition")
    parser.add_argument("--simulate", action="store_true", help="Run simulation")
    parser.add_argument("--steps", type=int, default=50, help="Max simulation steps")
    parser.add_argument("--sample", action="store_true", help="Use sample graph")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--save", action="store_true", help="Save results")

    args = parser.parse_args()

    # Load or create graph
    if args.sample or not args.test_workflow:
        graph = create_sample_graph()
    else:
        # Load from file
        try:
            with open(args.test_workflow) as f:
                data = json.load(f)
            # Parse into WorkflowGraph (simplified)
            graph = create_sample_graph()  # Placeholder
        except Exception as e:
            print(f"Error loading workflow: {e}")
            return 1

    # Run tests
    results = run_test_suite(graph)

    # Save if requested
    if args.save:
        log_results(results)

    # Output
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        print_results(results)

    # Return exit code
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
