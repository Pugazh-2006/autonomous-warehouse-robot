"""Unit Tests for Warehouse Map Management and Random Map Generation.

Verifies map loading, node count constraints, graph connectivity, seed reproducibility,
and algorithm traversal across all predefined and procedurally generated maps.
"""

import unittest
import networkx as nx

from map_manager import MapManager, WarehouseMap
from map_generator import RandomMapGenerator
from warehouse_graph import WarehouseGraph, canonical_edge
from algorithms import bfs_search, dfs_search


class TestWarehouseMapGeneration(unittest.TestCase):
    """Test suite for warehouse maps and procedural generator."""

    def setUp(self) -> None:
        """Initialize map manager before each test."""
        self.map_mgr = MapManager()

    def test_predefined_maps_load_successfully(self) -> None:
        """Verify all standard predefined maps register and load into WarehouseGraph."""
        expected_keys = ["starter", "compact", "cross_aisle", "medium", "large"]
        for key in expected_keys:
            m = self.map_mgr.get_map(key)
            self.assertIsNotNone(m, f"Predefined map '{key}' must exist.")
            wh = WarehouseGraph(m)
            self.assertEqual(wh.get_node_count(), m.node_count)
            self.assertEqual(wh.get_edge_count(), m.edge_count)

    def test_predefined_map_node_counts(self) -> None:
        """Verify each map matches the requested scale requirements."""
        starter = self.map_mgr.get_map("starter")
        compact = self.map_mgr.get_map("compact")
        cross = self.map_mgr.get_map("cross_aisle")
        medium = self.map_mgr.get_map("medium")
        large = self.map_mgr.get_map("large")

        self.assertEqual(starter.node_count, 5)
        self.assertTrue(10 <= compact.node_count <= 14, f"Compact has {compact.node_count}")
        self.assertTrue(15 <= cross.node_count <= 22, f"Cross-aisle has {cross.node_count}")
        self.assertTrue(25 <= medium.node_count <= 32, f"Medium has {medium.node_count}")
        self.assertTrue(40 <= large.node_count <= 60, f"Large has {large.node_count}")

    def test_predefined_maps_are_connected(self) -> None:
        """Verify that every predefined warehouse graph is fully connected."""
        for m in self.map_mgr.get_all_maps():
            wh = WarehouseGraph(m)
            self.assertTrue(
                nx.is_connected(wh.graph),
                f"Map '{m.name}' must be connected without blockages.",
            )

    def test_no_self_loops_or_duplicate_edges(self) -> None:
        """Verify all maps contain no self-loops and no duplicate undirected edges."""
        for m in self.map_mgr.get_all_maps():
            wh = WarehouseGraph(m)
            # Check self-loops
            self.assertEqual(
                list(nx.nodes_with_selfloops(wh.graph)),
                [],
                f"Map '{m.name}' has self-loops.",
            )
            # Check edge duplication
            canonical_edges = [canonical_edge(u, v) for u, v in wh.graph.edges()]
            self.assertEqual(len(canonical_edges), len(set(canonical_edges)))

    def test_random_map_generation_connectivity_and_bounds(self) -> None:
        """Verify random map generator produces connected graphs within 8 to 60 nodes."""
        for target_count in [8, 15, 24, 40, 55]:
            rand_map, seed_used = RandomMapGenerator.generate(
                node_count=target_count, seed=target_count * 101
            )
            wh = WarehouseGraph(rand_map)

            self.assertEqual(wh.get_node_count(), target_count)
            self.assertTrue(nx.is_connected(wh.graph), "Random map must be connected.")
            self.assertEqual(list(nx.nodes_with_selfloops(wh.graph)), [])

    def test_random_map_seed_reproducibility(self) -> None:
        """Verify identical seed produces identical map structure."""
        map1, s1 = RandomMapGenerator.generate(node_count=20, seed=12345)
        map2, s2 = RandomMapGenerator.generate(node_count=20, seed=12345)

        self.assertEqual(s1, s2)
        self.assertEqual(map1.node_count, map2.node_count)
        self.assertEqual(sorted(map1.nodes.keys()), sorted(map2.nodes.keys()))
        self.assertEqual(sorted(map1.edges), sorted(map2.edges))
        self.assertEqual(map1.positions, map2.positions)

    def test_random_map_different_seeds_produce_different_maps(self) -> None:
        """Verify different seeds produce distinct layouts."""
        map_a, _ = RandomMapGenerator.generate(node_count=18, seed=1111)
        map_b, _ = RandomMapGenerator.generate(node_count=18, seed=9999)

        # Positions or edge sets should differ
        self.assertNotEqual(sorted(map_a.edges), sorted(map_b.edges))

    def test_bfs_and_dfs_on_every_predefined_map(self) -> None:
        """Verify BFS and DFS find valid routes on every predefined map."""
        for m in self.map_mgr.get_all_maps():
            wh = WarehouseGraph(m)
            src = m.default_source
            dst = m.default_destination

            # BFS
            res_bfs = bfs_search(wh.graph, src, dst)
            self.assertTrue(res_bfs.found, f"BFS should find route on '{m.name}'")
            self.assertEqual(res_bfs.path[0], src)
            self.assertEqual(res_bfs.path[-1], dst)
            self.assertTrue(res_bfs.is_shortest)

            # DFS
            res_dfs = dfs_search(wh.graph, src, dst)
            self.assertTrue(res_dfs.found, f"DFS should find route on '{m.name}'")
            self.assertEqual(res_dfs.path[0], src)
            self.assertEqual(res_dfs.path[-1], dst)

    def test_bfs_and_dfs_on_random_maps(self) -> None:
        """Verify BFS and DFS run successfully on procedurally generated maps."""
        for seed in [10, 2024, 777]:
            rand_map, _ = RandomMapGenerator.generate(node_count=25, seed=seed)
            wh = WarehouseGraph(rand_map)
            src = rand_map.default_source
            dst = rand_map.default_destination

            res_bfs = bfs_search(wh.graph, src, dst)
            self.assertTrue(res_bfs.found)
            self.assertTrue(res_bfs.is_shortest)

            res_dfs = dfs_search(wh.graph, src, dst)
            self.assertTrue(res_dfs.found)

    def test_blockage_and_rerouting_on_medium_map(self) -> None:
        """Verify dynamic detour on Medium Warehouse when a critical edge is blocked."""
        med_map = self.map_mgr.get_map("medium")
        wh = WarehouseGraph(med_map)
        src = med_map.default_source
        dst = med_map.default_destination

        # Baseline search
        baseline = bfs_search(wh.graph, src, dst)
        self.assertTrue(baseline.found)

        # Block the first edge along baseline path
        edge_to_block = (baseline.path[0], baseline.path[1])
        wh.block_edge(edge_to_block[0], edge_to_block[1])

        # Rerun search with blocked edges
        detour = bfs_search(wh.graph, src, dst, blocked_edges=set(wh.get_blocked_edges()))
        self.assertTrue(detour.found, "Medium warehouse has redundant paths for detour.")
        self.assertNotIn(canonical_edge(edge_to_block[0], edge_to_block[1]), [
            canonical_edge(detour.path[i], detour.path[i + 1])
            for i in range(len(detour.path) - 1)
        ])

    def test_reset_map_clears_blockages(self) -> None:
        """Verify resetting a map removes all blocked pathways."""
        wh = WarehouseGraph(self.map_mgr.get_map("compact"))
        wh.block_edge("S1", "X1")
        wh.block_edge("X1", "A1")
        self.assertEqual(len(wh.get_blocked_edges()), 2)

        wh.reset_blockages()
        self.assertEqual(len(wh.get_blocked_edges()), 0)


if __name__ == "__main__":
    unittest.main()
