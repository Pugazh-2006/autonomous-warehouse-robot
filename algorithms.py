"""Search Algorithms Module for Autonomous Warehouse Robot.

This module implements uninformed graph search algorithms (BFS and DFS)
for path planning on the warehouse graph.

Key guarantees:
1. Breadth First Search (BFS) explores level-by-level using collections.deque,
   guaranteeing the shortest path in terms of edge count when all edges have
   equal cost.
2. Depth First Search (DFS) explores branch-by-branch using an explicit LIFO
   stack, finding a valid path without optimality guarantees.
3. Both algorithms respect blocked pathways and preserve deterministic neighbor
   ordering for reproducible results.
4. Algorithms do not mutate the input graph.
5. Search execution captures live trace steps (frontier snapshots, timestamps)
   for educational visual simulation.
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Set, Tuple
import networkx as nx

from warehouse_graph import canonical_edge


@dataclass
class SearchTraceStep:
    """Snapshot of a single step during graph search expansion."""

    node: str
    frontier_size: int
    frontier_snapshot: List[str]
    predecessor_snapshot: Dict[str, Optional[str]]
    visited_so_far: List[str]
    action: str  # 'visit', 'target_found', 'exhausted'


@dataclass
class SearchResult:
    """Encapsulates the complete result and statistics of a graph search."""

    path: List[str] = field(default_factory=list)
    visited_order: List[str] = field(default_factory=list)
    found: bool = False
    edge_count: int = 0
    visited_count: int = 0
    blocked_edges: List[Tuple[str, str]] = field(default_factory=list)
    algorithm_name: str = ""
    is_shortest: bool = False
    trace: List[SearchTraceStep] = field(default_factory=list)
    execution_time_ms: float = 0.0

    def get_path_display(self, node_labels: Optional[Dict[str, str]] = None) -> str:
        """Format the path into a readable multi-line arrow sequence."""
        if not self.found or not self.path:
            return "No route available"
        if node_labels is None:
            node_labels = {}
        lines = []
        for i, node in enumerate(self.path):
            label = node_labels.get(node, node)
            lines.append(f"{label} ({node})")
            if i < len(self.path) - 1:
                lines.append("   ↓")
        return "\n".join(lines)

    def get_path_arrow_string(self) -> str:
        """Format the path as a compact inline string like 'S → A → C'."""
        if not self.found or not self.path:
            return "None"
        return " → ".join(self.path)


def reconstruct_path(
    destination: str, predecessor: Dict[str, Optional[str]]
) -> List[str]:
    """Reconstruct path from destination to source using predecessor map.

    Args:
        destination: Destination node ID.
        predecessor: Mapping of node ID to its parent node.

    Returns:
        List of node IDs from source to destination.
    """
    path: List[str] = []
    curr: Optional[str] = destination
    while curr is not None:
        path.append(curr)
        curr = predecessor.get(curr)
    path.reverse()
    return path


def _validate_endpoints(graph: nx.Graph, source: str, destination: str) -> None:
    """Validate that source and destination nodes exist in the graph.

    Raises:
        ValueError: If source or destination is not present in graph.
    """
    if source not in graph:
        raise ValueError(
            f"Invalid source location '{source}'. Node does not exist in the warehouse graph."
        )
    if destination not in graph:
        raise ValueError(
            f"Invalid destination location '{destination}'. Node does not exist in the warehouse graph."
        )


def bfs_search(
    graph: nx.Graph,
    source: str,
    destination: str,
    blocked_edges: Optional[Set[Tuple[str, str]]] = None,
) -> SearchResult:
    """Perform Breadth First Search (BFS) to find the shortest path.

    BFS explores nodes level-by-level using a FIFO queue (collections.deque).
    In graphs where all edges have uniform cost, BFS is guaranteed to find
    a path with the minimum number of edges.

    Args:
        graph: NetworkX graph representing the warehouse.
        source: Starting node identifier.
        destination: Target node identifier.
        blocked_edges: Set of edge tuples (u, v) that cannot be traversed.

    Returns:
        SearchResult containing the route, visited order, trace, and statistics.

    Raises:
        ValueError: If source or destination is invalid.
    """
    _validate_endpoints(graph, source, destination)
    start_time = time.perf_counter()

    normalized_blocked: Set[Tuple[str, str]] = {
        canonical_edge(u, v) for u, v in (blocked_edges or set())
    }
    sorted_blocked_list = sorted(list(normalized_blocked))

    # Trivial case: source is destination
    if source == destination:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        step = SearchTraceStep(
            node=source,
            frontier_size=0,
            frontier_snapshot=[],
            predecessor_snapshot={source: None},
            visited_so_far=[source],
            action="target_found",
        )
        return SearchResult(
            path=[source],
            visited_order=[source],
            found=True,
            edge_count=0,
            visited_count=1,
            blocked_edges=sorted_blocked_list,
            algorithm_name="Breadth First Search (BFS)",
            is_shortest=True,
            trace=[step],
            execution_time_ms=elapsed,
        )

    queue: deque[str] = deque([source])
    visited: Set[str] = {source}
    predecessor: Dict[str, Optional[str]] = {source: None}
    visited_order: List[str] = []
    trace: List[SearchTraceStep] = []
    found: bool = False

    while queue:
        current = queue.popleft()
        visited_order.append(current)

        step_action = "target_found" if current == destination else "visit"
        trace.append(
            SearchTraceStep(
                node=current,
                frontier_size=len(queue),
                frontier_snapshot=list(queue),
                predecessor_snapshot=dict(predecessor),
                visited_so_far=list(visited_order),
                action=step_action,
            )
        )

        if current == destination:
            found = True
            break

        # Deterministic neighbor traversal: sorted alphabetically
        for neighbor in sorted(graph.neighbors(current)):
            edge = canonical_edge(current, neighbor)
            if edge in normalized_blocked:
                continue

            if neighbor not in visited:
                visited.add(neighbor)
                predecessor[neighbor] = current
                queue.append(neighbor)

    elapsed = (time.perf_counter() - start_time) * 1000.0

    if found:
        path = reconstruct_path(destination, predecessor)
        edge_count = len(path) - 1
        return SearchResult(
            path=path,
            visited_order=visited_order,
            found=True,
            edge_count=edge_count,
            visited_count=len(visited_order),
            blocked_edges=sorted_blocked_list,
            algorithm_name="Breadth First Search (BFS)",
            is_shortest=True,  # BFS is always optimal for unweighted graphs
            trace=trace,
            execution_time_ms=elapsed,
        )
    else:
        return SearchResult(
            path=[],
            visited_order=visited_order,
            found=False,
            edge_count=0,
            visited_count=len(visited_order),
            blocked_edges=sorted_blocked_list,
            algorithm_name="Breadth First Search (BFS)",
            is_shortest=False,
            trace=trace,
            execution_time_ms=elapsed,
        )


def dfs_search(
    graph: nx.Graph,
    source: str,
    destination: str,
    blocked_edges: Optional[Set[Tuple[str, str]]] = None,
) -> SearchResult:
    """Perform Depth First Search (DFS) using an explicit LIFO stack.

    DFS explores along each branch as deeply as possible before backtracking.
    DFS does not guarantee the shortest path.

    Args:
        graph: NetworkX graph representing the warehouse.
        source: Starting node identifier.
        destination: Target node identifier.
        blocked_edges: Set of edge tuples (u, v) that cannot be traversed.

    Returns:
        SearchResult containing the route, visited order, trace, and statistics.

    Raises:
        ValueError: If source or destination is invalid.
    """
    _validate_endpoints(graph, source, destination)
    start_time = time.perf_counter()

    normalized_blocked: Set[Tuple[str, str]] = {
        canonical_edge(u, v) for u, v in (blocked_edges or set())
    }
    sorted_blocked_list = sorted(list(normalized_blocked))

    # Trivial case: source is destination
    if source == destination:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        step = SearchTraceStep(
            node=source,
            frontier_size=0,
            frontier_snapshot=[],
            predecessor_snapshot={source: None},
            visited_so_far=[source],
            action="target_found",
        )
        return SearchResult(
            path=[source],
            visited_order=[source],
            found=True,
            edge_count=0,
            visited_count=1,
            blocked_edges=sorted_blocked_list,
            algorithm_name="Depth First Search (DFS)",
            is_shortest=True,
            trace=[step],
            execution_time_ms=elapsed,
        )

    # Stack holds tuples of (current_node, parent_node)
    stack: List[Tuple[str, Optional[str]]] = [(source, None)]
    visited: Set[str] = set()
    predecessor: Dict[str, Optional[str]] = {}
    visited_order: List[str] = []
    trace: List[SearchTraceStep] = []
    found: bool = False

    while stack:
        current, parent = stack.pop()
        if current in visited:
            continue

        visited.add(current)
        predecessor[current] = parent
        visited_order.append(current)

        step_action = "target_found" if current == destination else "visit"
        trace.append(
            SearchTraceStep(
                node=current,
                frontier_size=len(stack),
                frontier_snapshot=[node for node, _ in stack],
                predecessor_snapshot=dict(predecessor),
                visited_so_far=list(visited_order),
                action=step_action,
            )
        )

        if current == destination:
            found = True
            break

        # Deterministic neighbor traversal:
        # Sort in reverse order so that alphabetical neighbors are popped first from the LIFO stack.
        active_neighbors = [
            nbr
            for nbr in sorted(graph.neighbors(current), reverse=True)
            if canonical_edge(current, nbr) not in normalized_blocked
            and nbr not in visited
        ]

        for neighbor in active_neighbors:
            stack.append((neighbor, current))

    elapsed = (time.perf_counter() - start_time) * 1000.0

    if found:
        path = reconstruct_path(destination, predecessor)
        edge_count = len(path) - 1

        # Check if the DFS path happens to match the shortest edge count
        bfs_res = bfs_search(graph, source, destination, blocked_edges)
        is_shortest = bfs_res.found and (edge_count == bfs_res.edge_count)

        return SearchResult(
            path=path,
            visited_order=visited_order,
            found=True,
            edge_count=edge_count,
            visited_count=len(visited_order),
            blocked_edges=sorted_blocked_list,
            algorithm_name="Depth First Search (DFS)",
            is_shortest=is_shortest,
            trace=trace,
            execution_time_ms=elapsed,
        )
    else:
        return SearchResult(
            path=[],
            visited_order=visited_order,
            found=False,
            edge_count=0,
            visited_count=len(visited_order),
            blocked_edges=sorted_blocked_list,
            algorithm_name="Depth First Search (DFS)",
            is_shortest=False,
            trace=trace,
            execution_time_ms=elapsed,
        )
