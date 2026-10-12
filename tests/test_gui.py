"""Automated GUI Tests for Autonomous Warehouse Robot Desktop Application.

Tests widget initialization, combobox controls, algorithm execution via GUI,
pathway checkbox toggling, canvas click simulation, and animation frames.
"""

import unittest
import tkinter as tk
from app import AutonomousWarehouseApp
from warehouse_graph import canonical_edge


class TestAutonomousWarehouseGUI(unittest.TestCase):
    """Automated integration test suite for Tkinter GUI."""

    @classmethod
    def setUpClass(cls) -> None:
        """Create root window once for the test suite."""
        cls.root = tk.Tk()
        cls.app = AutonomousWarehouseApp(cls.root)
        cls.root.update_idletasks()
        cls.root.update()

    @classmethod
    def tearDownClass(cls) -> None:
        """Destroy root window after all tests complete."""
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self) -> None:
        """Reset the application to sample defaults before each test."""
        self.app.load_sample_warehouse()
        self.root.update_idletasks()
        self.root.update()

    def test_window_title_and_initialization(self) -> None:
        """Verify window title, defaults, and initial widget states."""
        self.assertIn("Autonomous Warehouse Robot", self.root.title())
        self.assertEqual(self.app._get_selected_source(), "S")
        self.assertEqual(self.app._get_selected_dest(), "C")
        self.assertEqual(self.app.algo_var.get(), "BFS")
        self.assertIsNone(self.app.current_result)

    def test_run_navigation_default_bfs(self) -> None:
        """Verify running default BFS updates result card, statistics, and treeview."""
        self.app.run_navigation_direct()
        self.root.update()

        result = self.app.current_result
        self.assertIsNotNone(result)
        self.assertTrue(result.found)
        self.assertEqual(result.path, ["S", "A", "C"])
        self.assertEqual(result.visited_order, ["S", "A", "B", "C"])
        self.assertEqual(result.edge_count, 2)
        self.assertTrue(result.is_shortest)

        # Verify UI text and badge update
        self.assertIn("Optimal Route Found", self.app.route_badge.cget("text"))
        self.assertIn("4", self.app.stat_visited_cnt_lbl.cget("text"))
        self.assertEqual(len(self.app.visited_tree.get_children()), 4)

    def test_run_navigation_dfs_suboptimal_path(self) -> None:
        """Verify selecting DFS from S to D yields 3-edge route S-A-C-D."""
        for val in self.app.dest_combo["values"]:
            if val.startswith("D:"):
                self.app.dest_combo.set(val)
                break
        self.app.algo_var.set("DFS")
        self.app.run_navigation_direct()
        self.root.update()

        result = self.app.current_result
        self.assertIsNotNone(result)
        self.assertTrue(result.found)
        self.assertEqual(result.path, ["S", "A", "C", "D"])
        self.assertEqual(result.edge_count, 3)

    def test_checkbox_toggle_pathway_blocking(self) -> None:
        """Verify toggling pathway checkbox blocks edge and reroutes BFS."""
        edge = canonical_edge("S", "A")
        var = self.app.edge_check_vars[edge]
        self.assertFalse(var.get())

        # Toggle to blocked
        var.set(True)
        self.app._on_checkbox_toggled(edge)
        self.root.update()

        self.assertTrue(self.app.warehouse.is_edge_blocked("S", "A"))

        # Run navigation -> should find detour S-B-D-C
        self.app.run_navigation_direct()
        self.root.update()
        result = self.app.current_result
        self.assertEqual(result.path, ["S", "B", "D", "C"])
        self.assertEqual(result.edge_count, 3)

    def test_canvas_click_edge_toggle(self) -> None:
        """Verify clicking canvas edge toggles blocked status cleanly."""
        self.assertFalse(self.app.warehouse.is_edge_blocked("B", "D"))
        self.app._on_canvas_edge_clicked("B", "D")
        self.assertTrue(self.app.warehouse.is_edge_blocked("B", "D"))
        self.app._on_canvas_edge_clicked("B", "D")
        self.assertFalse(self.app.warehouse.is_edge_blocked("B", "D"))

    def test_no_route_ui_handling(self) -> None:
        """Verify UI updates correctly when all paths are blocked."""
        self.app.warehouse.block_edge("S", "A")
        self.app.warehouse.block_edge("S", "B")
        self.app._refresh_pathway_checkboxes()
        self.app.run_navigation_direct()
        self.root.update()

        result = self.app.current_result
        self.assertFalse(result.found)
        self.assertEqual(result.path, [])
        self.assertIn("No Route Available", self.app.route_badge.cget("text"))
        self.assertIn("No route available", self.app.status_label.cget("text"))

    def test_clear_and_reset_controls(self) -> None:
        """Verify Clear Result and Reset All return controls to clean state."""
        self.app.run_navigation_direct()
        self.assertIsNotNone(self.app.current_result)

        self.app.clear_results()
        self.root.update()
        self.assertIsNone(self.app.current_result)
        self.assertEqual(len(self.app.visited_tree.get_children()), 0)

    def test_animation_start_pause_stop(self) -> None:
        """Verify animation lifecycle transitions."""
        self.app.start_animation()
        self.root.update()
        self.assertTrue(self.app.is_animating)
        self.assertFalse(self.app.animation_paused)

        # Pause
        self.app.toggle_pause_animation()
        self.root.update()
        self.assertTrue(self.app.animation_paused)

        # Resume
        self.app.toggle_pause_animation()
        self.root.update()
        self.assertFalse(self.app.animation_paused)

        # Advance a few frames
        self.app._step_animation_frame()
        self.root.update()
        self.assertGreaterEqual(len(self.app.animated_visited_nodes), 1)

        # Stop
        self.app.stop_animation()
        self.root.update()
        self.assertFalse(self.app.is_animating)

    def test_map_switch_in_gui(self) -> None:
        """Verify switching map in GUI rebuilds graph, endpoints, and allows search."""
        self.app.load_selected_map("compact")
        self.root.update()

        self.assertEqual(self.app.warehouse.get_node_count(), 12)
        self.assertIn("Compact Warehouse", self.app.map_metrics_lbl.cget("text"))
        self.assertEqual(len(self.app.source_combo["values"]), 12)

        # Run BFS navigation on compact map
        self.app.run_navigation_direct()
        self.root.update()
        self.assertTrue(self.app.current_result.found)
        self.assertGreater(self.app.current_result.edge_count, 0)

    def test_random_map_generation_in_gui(self) -> None:
        """Verify generating a random map with seed in GUI updates layout and executes search."""
        self.app.seed_var.set("777")
        self.app.generate_new_random_map()
        self.root.update()

        self.assertGreaterEqual(self.app.warehouse.get_node_count(), 8)
        self.app.run_navigation_direct()
        self.root.update()
        self.assertTrue(self.app.current_result.found)

    def test_node_inspection_on_click(self) -> None:
        """Verify clicking canvas node updates inspector metadata card."""
        self.app.load_selected_map("starter")
        self.root.update()

        self.app._on_canvas_node_clicked("A")
        self.root.update()
        self.assertIn("Rack A (A)", self.app.insp_name_lbl.cget("text"))
        self.assertIn("Rack", self.app.insp_type_lbl.cget("text"))


if __name__ == "__main__":
    unittest.main()
