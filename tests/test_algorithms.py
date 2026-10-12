"""Unit Tests for Warehouse Graph Algorithms.

Verifies correctness, edge cases, deterministic behavior, and graph immutability.
"""

import unittest
from warehouse_graph import WarehouseGraph, canonical_edge
from algorithms import bfs_search, dfs_search, reconstruct_path, SearchResult


class TestWarehouseAlgorithms(unittest.TestCase):
    """Test suite for warehouse graph search algorithms."""

    def setUp(self) -> None:
        """Initialize a fresh warehouse graph before each test."""
        self.warehouse = WarehouseGraph()
        self.graph = self.warehouse.graph

    def test_bfs_returns_sac_for_s_to_c(self) -> None:
        """BFS from Storage Area (S) to Packing Station (C) returns S -> A -> C."""
        result = bfs_search(self.graph, "S", "C")
        self.assertTrue(result.found)
        self.assertEqual(result.path, ["S", "A", "C"])
        self.assertEqual(result.edge_count, 2)
        self.assertEqual(result.visited_order, ["S", "A", "B", "C"])

    def test_bfs_returns_shortest_route(self) -> None:
        """BFS returns the shortest route in edge count."""
        # For S to D, two paths exist: S-B-D (2 edges) and S-A-C-D (3 edges)
        result = bfs_search(self.graph, "S", "D")
        self.assertTrue(result.found)
        self.assertEqual(result.path, ["S", "B", "D"])
        self.assertEqual(result.edge_count, 2)
        self.assertTrue(result.is_shortest)

    def test_dfs_returns_valid_route(self) -> None:
        """DFS returns a valid connected route from source to destination."""
        result = dfs_search(self.graph, "S", "D")
        self.assertTrue(result.found)
        # Verify valid path connectivity
        for i in range(len(result.path) - 1):
            u, v = result.path[i], result.path[i + 1]
            self.assertTrue(self.graph.has_edge(u, v))
        self.assertEqual(result.path[0], "S")
        self.assertEqual(result.path[-1], "D")
        # DFS explores S -> A -> C -> D due to alphabetical preference
        self.assertEqual(result.path, ["S", "A", "C", "D"])
        self.assertEqual(result.edge_count, 3)

    def test_source_equal_to_destination(self) -> None:
        """When source == destination, path has only that node and 0 edges."""
        for algo in (bfs_search, dfs_search):
            result = algo(self.graph, "A", "A")
            self.assertTrue(result.found)
            self.assertEqual(result.path, ["A"])
            self.assertEqual(result.visited_order, ["A"])
            self.assertEqual(result.edge_count, 0)
            self.assertEqual(result.visited_count, 1)

    def test_invalid_source_raises_error(self) -> None:
        """Invalid source node raises ValueError with informative message."""
        for algo in (bfs_search, dfs_search):
            with self.assertRaises(ValueError) as ctx:
                algo(self.graph, "INVALID_NODE", "C")
            self.assertIn("Invalid source location", str(ctx.exception))

    def test_invalid_destination_raises_error(self) -> None:
        """Invalid destination node raises ValueError with informative message."""
        for algo in (bfs_search, dfs_search):
            with self.assertRaises(ValueError) as ctx:
                algo(self.graph, "S", "NON_EXISTENT")
            self.assertIn("Invalid destination location", str(ctx.exception))

    def test_no_route_available_when_disconnected(self) -> None:
        """When all routes are severed, algorithm reports found=False and empty path."""
        # Block both pathways leading out of S
        blocked = {canonical_edge("S", "A"), canonical_edge("S", "B")}
        result = bfs_search(self.graph, "S", "C", blocked_edges=blocked)
        self.assertFalse(result.found)
        self.assertEqual(result.path, [])
        self.assertEqual(result.edge_count, 0)
        self.assertEqual(result.visited_order, ["S"])

        result_dfs = dfs_search(self.graph, "S", "C", blocked_edges=blocked)
        self.assertFalse(result_dfs.found)
        self.assertEqual(result_dfs.path, [])
        self.assertEqual(result_dfs.visited_order, ["S"])

    def test_blocked_edge_is_avoided(self) -> None:
        """When S-A is blocked, BFS dynamically finds alternate route S-B-D-C."""
        blocked = {canonical_edge("S", "A")}
        result = bfs_search(self.graph, "S", "C", blocked_edges=blocked)
        self.assertTrue(result.found)
        self.assertEqual(result.path, ["S", "B", "D", "C"])
        self.assertEqual(result.edge_count, 3)
        self.assertIn(canonical_edge("S", "A"), result.blocked_edges)

    def test_multiple_blocked_edges(self) -> None:
        """Multiple blocked pathways are correctly avoided or trigger no-route."""
        # Block S-A and C-D
        blocked = {canonical_edge("S", "A"), canonical_edge("C", "D")}
        # S can reach B, D, but C is unreachable because A-C and C-D are isolated
        result = bfs_search(self.graph, "S", "C", blocked_edges=blocked)
        self.assertFalse(result.found)
        self.assertEqual(result.path, [])

        # But S can still reach D via B
        result_to_d = bfs_search(self.graph, "S", "D", blocked_edges=blocked)
        self.assertTrue(result_to_d.found)
        self.assertEqual(result_to_d.path, ["S", "B", "D"])

    def test_search_result_contains_correct_visited_order(self) -> None:
        """Visited order correctly records exact sequence nodes were dequeued/expanded."""
        result = bfs_search(self.graph, "S", "C")
        # Deterministic alphabetical neighbor order: S -> A, B -> C
        self.assertEqual(result.visited_order, ["S", "A", "B", "C"])
        self.assertEqual(result.visited_count, 4)

    def test_original_graph_is_not_permanently_modified(self) -> None:
        """Running searches with blocked edges does not mutate the original graph."""
        nodes_before = sorted(list(self.graph.nodes()))
        edges_before = sorted(list(self.graph.edges()))

        blocked = {canonical_edge("S", "A"), canonical_edge("B", "D")}
        bfs_search(self.graph, "S", "C", blocked_edges=blocked)
        dfs_search(self.graph, "S", "D", blocked_edges=blocked)

        nodes_after = sorted(list(self.graph.nodes()))
        edges_after = sorted(list(self.graph.edges()))

        self.assertEqual(nodes_before, nodes_after)
        self.assertEqual(edges_before, edges_after)

    def test_path_reconstruction_helper(self) -> None:
        """Path reconstruction correctly reverses chain of predecessors."""
        predecessors = {"C": "A", "A": "S", "S": None}
        path = reconstruct_path("C", predecessors)
        self.assertEqual(path, ["S", "A", "C"])


if __name__ == "__main__":
    unittest.main()
