"""Autonomous Warehouse Robot Desktop Application.

A professional multi-map warehouse navigation simulator demonstrating graph traversal
and uninformed search algorithms (BFS and DFS) with realistic aisle layouts, procedural
random map generation, interactive path planning, dynamic obstacle avoidance, and animation.

Author: Senior Python Developer & AI Educator
"""

from __future__ import annotations
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Tuple

from warehouse_graph import WarehouseGraph, canonical_edge
from map_manager import MapManager, WarehouseMap
from map_generator import RandomMapGenerator
from algorithms import bfs_search, dfs_search, SearchResult, SearchTraceStep
from visualization import WarehouseVisualizer

# Enable High-DPI awareness on Windows if available
if sys.platform.startswith("win"):
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


class AutonomousWarehouseApp:
    """Main desktop application class for Autonomous Warehouse Robot."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the application, map manager, UI components, and state."""
        self.root = root
        self.root.title("Autonomous Warehouse Robot - Multi-Map Navigation Simulator")
        self.root.geometry("1380x900")
        self.root.minsize(1120, 740)

        # Core data models
        self.map_manager = MapManager()
        self.warehouse = WarehouseGraph(self.map_manager.get_current_map())
        self.current_result: Optional[SearchResult] = None
        self.current_seed_val: int = 42

        # Animation state
        self.is_animating: bool = False
        self.animation_paused: bool = False
        self.anim_stage: str = "visited"  # "visited" then "path"
        self.anim_index: int = 0
        self.anim_timer_id: Optional[str] = None
        self.animated_visited_nodes: List[str] = []
        self.animated_path_nodes: List[str] = []

        # Edge checkbox variables
        self.edge_check_vars: Dict[Tuple[str, str], tk.BooleanVar] = {}

        # Configure modern TTK styles
        self._configure_styles()

        # Build complete 3-panel UI
        self._build_ui()

        # Initial map load
        self.load_selected_map("starter")

    def _configure_styles(self) -> None:
        """Configure modern ttk styles and clean professional palette."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        bg_main = "#f1f5f9"
        style.configure(".", background=bg_main, font=("Segoe UI", 9))
        style.configure("Header.TFrame", background="#0f172a")
        style.configure("TLabelframe", background="#ffffff")
        style.configure(
            "TLabelframe.Label",
            background="#ffffff",
            font=("Segoe UI", 9, "bold"),
            foreground="#1e293b",
        )

        # Button Styles
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#2563eb",
            foreground="#ffffff",
            padding=5,
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1d4ed8"), ("disabled", "#94a3b8")],
            foreground=[("disabled", "#cbd5e1")],
        )

        style.configure(
            "Teal.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#0d9488",
            foreground="#ffffff",
            padding=5,
        )
        style.map(
            "Teal.TButton",
            background=[("active", "#0f766e"), ("disabled", "#94a3b8")],
            foreground=[("disabled", "#cbd5e1")],
        )

        style.configure(
            "Outline.TButton",
            font=("Segoe UI", 9),
            background="#ffffff",
            foreground="#334155",
            padding=4,
        )
        style.map(
            "Outline.TButton",
            background=[("active", "#f1f5f9")],
        )

        style.configure(
            "Mini.TButton",
            font=("Segoe UI", 8),
            background="#f8fafc",
            foreground="#475569",
            padding=2,
        )

    def _build_ui(self) -> None:
        """Construct the entire application window layout using a 3-area architecture."""
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 1. Header (Top)
        self._build_header(main_container)

        # 2. Body: Three-area layout (Left Controls, Center Canvas, Right Results)
        body_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        body_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Left Panel (Fixed width scrollable controls)
        left_frame = ttk.Frame(body_paned, width=340)
        body_paned.add(left_frame, weight=0)

        # Center Panel (Large Map Canvas)
        center_frame = ttk.Frame(body_paned)
        body_paned.add(center_frame, weight=3)

        # Right Panel (Results & Inspector)
        right_frame = ttk.Frame(body_paned, width=350)
        body_paned.add(right_frame, weight=1)

        # Populate panels
        self._build_left_panel(left_frame)
        self._build_center_panel(center_frame)
        self._build_right_panel(right_frame)

        # 3. Status Bar (Bottom)
        self._build_status_bar(main_container)

    def _build_header(self, parent: ttk.Frame) -> None:
        """Build the top title and subtitle banner."""
        header_frame = tk.Frame(parent, bg="#0f172a", height=68)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_label = tk.Label(
            header_frame,
            text="Autonomous Warehouse Robot",
            font=("Segoe UI", 15, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
        )
        title_label.pack(anchor="w", padx=16, pady=(6, 0))

        sub_label = tk.Label(
            header_frame,
            text="Multi-Map Warehouse Navigation Simulator  •  Breadth First Search (BFS) & Depth First Search (DFS)",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a",
        )
        sub_label.pack(anchor="w", padx=16, pady=(1, 6))

    # =========================================================================
    # LEFT PANEL: Map Selection, Controls, Animation, Pathways
    # =========================================================================
    def _build_left_panel(self, parent: ttk.Frame) -> None:
        """Construct the scrollable left control panel."""
        canvas = tk.Canvas(parent, bg="#f1f5f9", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll_content = ttk.Frame(canvas)

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _on_canvas_resize(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_resize)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 1. Map Selection Card
        self._build_map_selection_card(scroll_content)

        # 2. Navigation Controls Card
        self._build_navigation_controls_card(scroll_content)

        # 3. Pathway Status & Blockages Card
        self._build_pathway_control_card(scroll_content)

    def _build_map_selection_card(self, parent: ttk.Frame) -> None:
        """Build Map Selection dropdown, seed control, and generation buttons."""
        map_card = ttk.LabelFrame(parent, text=" Warehouse Map Selector ", padding=8)
        map_card.pack(fill=tk.X, pady=(0, 6), padx=4)

        # Map Selector Dropdown
        ttk.Label(map_card, text="Select Layout:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))

        self.map_choices = [
            f"{m.name} — {m.node_count_label}"
            for m in self.map_manager.get_all_maps()
        ]
        self.map_choices.append("Random Warehouse (Procedural)")

        self.map_combo = ttk.Combobox(
            map_card,
            values=self.map_choices,
            state="readonly",
            font=("Segoe UI", 9),
        )
        self.map_combo.current(0)
        self.map_combo.pack(fill=tk.X, pady=(0, 4))
        self.map_combo.bind("<<ComboboxSelected>>", self._on_map_selection_changed)

        # Map Description
        self.map_desc_lbl = ttk.Label(
            map_card,
            text=self.map_manager.get_current_map().description,
            font=("Segoe UI", 8),
            foreground="#475569",
            wraplength=300,
        )
        self.map_desc_lbl.pack(anchor="w", pady=(0, 6))

        # Seed Row for Random Map
        seed_frame = ttk.Frame(map_card)
        seed_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(seed_frame, text="Seed:", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.seed_var = tk.StringVar(value="42")
        self.seed_entry = ttk.Entry(seed_frame, textvariable=self.seed_var, width=12, font=("Segoe UI", 8))
        self.seed_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_gen_random = ttk.Button(
            seed_frame,
            text="🎲 Random",
            style="Outline.TButton",
            command=self.generate_new_random_map,
        )
        self.btn_gen_random.pack(side=tk.RIGHT)

        # Map Action Buttons
        btn_grid = ttk.Frame(map_card)
        btn_grid.pack(fill=tk.X)

        ttk.Button(
            btn_grid,
            text="Load Map",
            style="Teal.TButton",
            command=self._load_selected_map_from_combo,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        ttk.Button(
            btn_grid,
            text="Reset Map",
            style="Outline.TButton",
            command=self.reset_current_map,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

    def _build_navigation_controls_card(self, parent: ttk.Frame) -> None:
        """Build Source, Destination, Algorithm, and Animation controls."""
        ctrl_card = ttk.LabelFrame(parent, text=" Navigation & Search ", padding=8)
        ctrl_card.pack(fill=tk.X, pady=(0, 6), padx=4)

        # Source Selection
        ttk.Label(ctrl_card, text="Source (Start):", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.source_combo = ttk.Combobox(ctrl_card, state="readonly", font=("Segoe UI", 9))
        self.source_combo.pack(fill=tk.X, pady=(0, 5))
        self.source_combo.bind("<<ComboboxSelected>>", self._on_endpoint_changed)

        # Destination Selection
        ttk.Label(ctrl_card, text="Destination (Target):", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.dest_combo = ttk.Combobox(ctrl_card, state="readonly", font=("Segoe UI", 9))
        self.dest_combo.pack(fill=tk.X, pady=(0, 6))
        self.dest_combo.bind("<<ComboboxSelected>>", self._on_endpoint_changed)

        # Algorithm Selection
        ttk.Label(ctrl_card, text="Algorithm:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self.algo_var = tk.StringVar(value="BFS")

        algo_box = ttk.Frame(ctrl_card)
        algo_box.pack(fill=tk.X, pady=(0, 6))
        ttk.Radiobutton(
            algo_box,
            text="Breadth First Search (BFS)",
            variable=self.algo_var,
            value="BFS",
            command=self._on_algorithm_changed,
        ).pack(anchor="w", pady=1)
        ttk.Radiobutton(
            algo_box,
            text="Depth First Search (DFS)",
            variable=self.algo_var,
            value="DFS",
            command=self._on_algorithm_changed,
        ).pack(anchor="w", pady=1)

        # Run Navigation button
        self.btn_run = ttk.Button(
            ctrl_card,
            text="🚀  Run Navigation",
            style="Primary.TButton",
            command=self.run_navigation_direct,
        )
        self.btn_run.pack(fill=tk.X, pady=(2, 4))

        # Animation Buttons
        anim_box = ttk.Frame(ctrl_card)
        anim_box.pack(fill=tk.X, pady=(2, 4))

        self.btn_animate = ttk.Button(
            anim_box,
            text="▶ Start Animation",
            style="Teal.TButton",
            command=self.start_animation,
        )
        self.btn_animate.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        self.btn_pause = ttk.Button(
            anim_box,
            text="⏸ Pause",
            style="Outline.TButton",
            command=self.toggle_pause_animation,
            state="disabled",
        )
        self.btn_pause.pack(side=tk.LEFT, padx=2)

        # Speed Control
        speed_box = ttk.Frame(ctrl_card)
        speed_box.pack(fill=tk.X, pady=(2, 4))
        ttk.Label(speed_box, text="Speed:", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.speed_var = tk.IntVar(value=400)
        self.speed_slider = ttk.Scale(
            speed_box,
            from_=900,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
        )
        self.speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Label(speed_box, text="Fast", font=("Segoe UI", 8)).pack(side=tk.RIGHT)

        # Clear Results button
        ttk.Button(
            ctrl_card,
            text="Clear Results",
            style="Outline.TButton",
            command=self.clear_results,
        ).pack(fill=tk.X, pady=(2, 0))

    def _build_pathway_control_card(self, parent: ttk.Frame) -> None:
        """Build scrollable list of warehouse pathways with blockage toggles."""
        pathway_card = ttk.LabelFrame(parent, text=" Pathway Status & Blockages ", padding=8)
        pathway_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6), padx=4)

        info_lbl = ttk.Label(
            pathway_card,
            text="Toggle checkboxes or click graph edges to block corridors:",
            wraplength=300,
            font=("Segoe UI", 8),
            foreground="#475569",
        )
        info_lbl.pack(anchor="w", pady=(0, 4))

        # Scrollable container for checkboxes
        list_container = ttk.Frame(pathway_card, height=180)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.edge_canvas = tk.Canvas(list_container, bg="#ffffff", highlightthickness=1, highlightbackground="#cbd5e1", height=160)
        edge_scroll = ttk.Scrollbar(list_container, orient="vertical", command=self.edge_canvas.yview)
        self.edge_scroll_content = ttk.Frame(self.edge_canvas)

        self.edge_scroll_content.bind(
            "<Configure>",
            lambda e: self.edge_canvas.configure(scrollregion=self.edge_canvas.bbox("all")),
        )
        self.edge_canvas_win = self.edge_canvas.create_window((0, 0), window=self.edge_scroll_content, anchor="nw")

        def _on_pw_resize(event):
            self.edge_canvas.itemconfig(self.edge_canvas_win, width=event.width)

        self.edge_canvas.bind("<Configure>", _on_pw_resize)
        self.edge_canvas.configure(yscrollcommand=edge_scroll.set)

        self.edge_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        edge_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Batch Controls
        batch_box = ttk.Frame(pathway_card)
        batch_box.pack(fill=tk.X, pady=(6, 0))

        ttk.Button(
            batch_box,
            text="Unblock All",
            style="Outline.TButton",
            command=self.unblock_all_pathways,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        ttk.Button(
            batch_box,
            text="Clear Blockages",
            style="Outline.TButton",
            command=self.unblock_all_pathways,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

    # =========================================================================
    # CENTER PANEL: Map Banner & Interactive Matplotlib Canvas
    # =========================================================================
    def _build_center_panel(self, parent: ttk.Frame) -> None:
        """Construct the central visualization canvas with top status bar and zoom."""
        center_card = ttk.LabelFrame(parent, text=" Warehouse Floor Topology (Interactive Canvas) ", padding=4)
        center_card.pack(fill=tk.BOTH, expand=True)

        # Top Canvas Info & Zoom Toolbar
        top_bar = ttk.Frame(center_card)
        top_bar.pack(fill=tk.X, padx=4, pady=(2, 4))

        self.map_metrics_lbl = ttk.Label(
            top_bar,
            text="Map: Starter Map  •  5 Nodes  •  5 Pathways",
            font=("Segoe UI", 9, "bold"),
            foreground="#1e293b",
        )
        self.map_metrics_lbl.pack(side=tk.LEFT)

        # Zoom buttons
        zoom_box = ttk.Frame(top_bar)
        zoom_box.pack(side=tk.RIGHT)

        ttk.Button(zoom_box, text="🔍 Reset", style="Mini.TButton", command=self._on_reset_view).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_box, text="＋", width=3, style="Mini.TButton", command=self._on_zoom_in).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_box, text="－", width=3, style="Mini.TButton", command=self._on_zoom_out).pack(side=tk.LEFT, padx=1)

        # Matplotlib visualizer
        self.visualizer = WarehouseVisualizer(
            master_widget=center_card,
            warehouse=self.warehouse,
            on_edge_toggle_cb=self._on_canvas_edge_clicked,
            on_node_click_cb=self._on_canvas_node_clicked,
        )
        self.visualizer.get_widget().pack(fill=tk.BOTH, expand=True)

    # =========================================================================
    # RIGHT PANEL: Results, Node Inspector, Path, Visited Breakdown
    # =========================================================================
    def _build_right_panel(self, parent: ttk.Frame) -> None:
        """Construct the right-hand panel with results, node inspector, and tabs."""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Search Metrics & Navigation Path
        res_tab = ttk.Frame(notebook, padding=6)
        notebook.add(res_tab, text=" Results & Metrics ")

        self._build_results_card(res_tab)
        self._build_node_inspector_card(res_tab)
        self._build_path_sequence_card(res_tab)

        # Tab 2: Visited Order Treeview
        visited_tab = ttk.Frame(notebook, padding=6)
        notebook.add(visited_tab, text=" Visited Sequence ")
        self._build_visited_table(visited_tab)

        # Tab 3: AI Theory & Concepts
        theory_tab = ttk.Frame(notebook, padding=6)
        notebook.add(theory_tab, text=" AI Theory ")
        self._build_theory_view(theory_tab)

    def _build_results_card(self, parent: ttk.Frame) -> None:
        """Build status banner and metric summary rows."""
        self.route_badge = tk.Label(
            parent,
            text="No Search Run Yet",
            font=("Segoe UI", 9, "bold"),
            fg="#475569",
            bg="#f1f5f9",
            pady=5,
        )
        self.route_badge.pack(fill=tk.X, pady=(0, 6))

        stats_card = ttk.LabelFrame(parent, text=" Search Metrics ", padding=6)
        stats_card.pack(fill=tk.X, pady=(0, 6))

        # Metrics rows
        self.stat_algo_lbl = ttk.Label(stats_card, text="Algorithm: —", font=("Segoe UI", 9))
        self.stat_algo_lbl.pack(anchor="w", pady=1)

        self.stat_route_len_lbl = ttk.Label(stats_card, text="Path Length: —", font=("Segoe UI", 9))
        self.stat_route_len_lbl.pack(anchor="w", pady=1)

        self.stat_visited_cnt_lbl = ttk.Label(stats_card, text="Nodes Visited: —", font=("Segoe UI", 9))
        self.stat_visited_cnt_lbl.pack(anchor="w", pady=1)

        self.stat_time_lbl = ttk.Label(stats_card, text="Search Time: —", font=("Segoe UI", 9))
        self.stat_time_lbl.pack(anchor="w", pady=1)

        # Wrapped label for Guaranteed Shortest to avoid any truncation
        self.stat_optimal_lbl = ttk.Label(
            stats_card,
            text="Guaranteed Shortest: —",
            font=("Segoe UI", 9),
            wraplength=310,
        )
        self.stat_optimal_lbl.pack(anchor="w", pady=1)

        self.stat_blocked_lbl = ttk.Label(
            stats_card,
            text="Blocked Pathways: None",
            font=("Segoe UI", 9),
            wraplength=310,
        )
        self.stat_blocked_lbl.pack(anchor="w", pady=1)

    def _build_node_inspector_card(self, parent: ttk.Frame) -> None:
        """Build card displaying full metadata of clicked/inspected node."""
        insp_card = ttk.LabelFrame(parent, text=" Selected Node Details ", padding=6)
        insp_card.pack(fill=tk.X, pady=(0, 6))

        self.insp_name_lbl = ttk.Label(insp_card, text="Click any node to inspect details", font=("Segoe UI", 9, "bold"))
        self.insp_name_lbl.pack(anchor="w")

        self.insp_type_lbl = ttk.Label(insp_card, text="Type: —  •  Coordinates: —", font=("Segoe UI", 8), foreground="#475569")
        self.insp_type_lbl.pack(anchor="w", pady=(1, 1))

        self.insp_degree_lbl = ttk.Label(insp_card, text="Connected Corridors: —", font=("Segoe UI", 8), foreground="#475569", wraplength=310)
        self.insp_degree_lbl.pack(anchor="w")

    def _build_path_sequence_card(self, parent: ttk.Frame) -> None:
        """Build path text area with scrollbar."""
        path_card = ttk.LabelFrame(parent, text=" Robot Navigation Path ", padding=6)
        path_card.pack(fill=tk.BOTH, expand=True)

        box_frame = ttk.Frame(path_card)
        box_frame.pack(fill=tk.BOTH, expand=True)

        self.path_text = tk.Text(
            box_frame,
            height=6,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#f8fafc",
            fg="#0f172a",
            relief="solid",
            bd=1,
        )
        self.path_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        path_scroll = ttk.Scrollbar(box_frame, orient=tk.VERTICAL, command=self.path_text.yview)
        path_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.path_text.config(yscrollcommand=path_scroll.set)
        self.path_text.insert(tk.END, "Select source & destination, then run navigation.")
        self.path_text.config(state="disabled")

    def _build_visited_table(self, parent: ttk.Frame) -> None:
        """Build chronological treeview table of visited nodes."""
        intro = ttk.Label(
            parent,
            text="Chronological node expansion sequence:",
            font=("Segoe UI", 9, "bold"),
        )
        intro.pack(anchor="w", pady=(0, 4))

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("step", "node_id", "label", "type", "in_final_path")
        self.visited_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.visited_tree.heading("step", text="Step #")
        self.visited_tree.heading("node_id", text="Node ID")
        self.visited_tree.heading("label", text="Warehouse Location")
        self.visited_tree.heading("type", text="Facility Type")
        self.visited_tree.heading("in_final_path", text="Final Route?")

        self.visited_tree.column("step", width=55, anchor="center")
        self.visited_tree.column("node_id", width=70, anchor="center")
        self.visited_tree.column("label", width=140, anchor="w")
        self.visited_tree.column("type", width=95, anchor="w")
        self.visited_tree.column("in_final_path", width=80, anchor="center")

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.visited_tree.yview)
        self.visited_tree.configure(yscrollcommand=tree_scroll.set)
        self.visited_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_theory_view(self, parent: ttk.Frame) -> None:
        """Construct the AI Theory explanation view."""
        txt = tk.Text(parent, font=("Segoe UI", 9), wrap=tk.WORD, bg="#ffffff", fg="#0f172a", relief="flat", padx=8, pady=8)
        theory_content = (
            "1. Why Breadth First Search (BFS) Guarantees Optimality\n"
            "----------------------------------------------------------------------\n"
            "• BFS systematically explores the warehouse graph in concentric layers (distance d = 0, 1, 2, ...).\n"
            "• In uniform-cost graphs (where every corridor hop has equal cost), the first time BFS\n"
            "  encounters the destination at depth d, no shorter path of length < d can exist.\n"
            "• Frontier Data Structure: FIFO Queue (collections.deque).\n"
            "• Time Complexity: O(V + E)  •  Space Complexity: O(V).\n\n"
            "2. Why Depth First Search (DFS) Does Not Guarantee Optimality\n"
            "----------------------------------------------------------------------\n"
            "• DFS plunges down a single branch as deeply as possible before backtracking.\n"
            "• Frontier Data Structure: LIFO Stack.\n"
            "• DFS frequently returns circuitous, suboptimal routes because it commits to the\n"
            "  first branch examined rather than expanding radially.\n\n"
            "3. Dynamic Detour Routing & Obstacle Avoidance\n"
            "----------------------------------------------------------------------\n"
            "• Blocked corridors (maintenance, pallets) are bypassed in real time.\n"
            "• BFS recalculates the shortest available detour.\n"
            "• If all routes to the target are severed, the system halts safely without crashing."
        )
        txt.insert(tk.END, theory_content)
        txt.config(state="disabled")
        txt.pack(fill=tk.BOTH, expand=True)

    def _build_status_bar(self, parent: ttk.Frame) -> None:
        """Build bottom status notification bar."""
        self.status_frame = tk.Frame(parent, bg="#1e293b", height=26)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_icon = tk.Label(self.status_frame, text="●", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#1e293b")
        self.status_icon.pack(side=tk.LEFT, padx=(10, 4))

        self.status_label = tk.Label(
            self.status_frame,
            text="Ready. Select source, destination, and search algorithm.",
            font=("Segoe UI", 9),
            fg="#f8fafc",
            bg="#1e293b",
        )
        self.status_label.pack(side=tk.LEFT, padx=2)

    def update_status(self, message: str, status_type: str = "info") -> None:
        """Update status bar message with colored indicator."""
        color_map = {
            "info": "#10b981",      # Emerald
            "warning": "#f59e0b",   # Amber
            "error": "#ef4444",     # Red
            "busy": "#3b82f6",      # Blue
        }
        self.status_icon.config(fg=color_map.get(status_type, "#10b981"))
        self.status_label.config(text=message)

    # =========================================================================
    # MAP SELECTION & REBUILDING
    # =========================================================================
    def load_selected_map(self, map_key: str) -> None:
        """Load and activate a warehouse map by key."""
        target_map = self.map_manager.get_map(map_key)
        if not target_map:
            return

        self._cancel_animation_if_running()
        self.map_manager.set_current_map(map_key)
        self.warehouse.load_map(target_map)

        # Update description & banner
        self.map_desc_lbl.config(text=target_map.description)
        self.map_metrics_lbl.config(
            text=f"Map: {target_map.name}  •  {target_map.node_count} Nodes  •  {target_map.edge_count} Pathways"
        )

        # Rebuild endpoint dropdowns
        node_choices = [
            self.warehouse.get_node_display(nid)
            for nid in self.warehouse.get_node_ids()
        ]
        self.source_combo["values"] = node_choices
        self.dest_combo["values"] = node_choices

        # Set default source and destination
        src_disp = self.warehouse.get_node_display(target_map.default_source)
        dst_disp = self.warehouse.get_node_display(target_map.default_destination)
        self.source_combo.set(src_disp if src_disp in node_choices else node_choices[0])
        self.dest_combo.set(dst_disp if dst_disp in node_choices else node_choices[-1])

        # Rebuild pathway list
        self._refresh_pathway_checkboxes()

        # Clear old results & reset visualizer
        self.clear_results()
        self.visualizer.reset_view()
        self._sync_visualization()

        self.update_status(f"Loaded {target_map.name} ({target_map.node_count} nodes).", "info")

    def _on_map_selection_changed(self, event=None) -> None:
        """Handle combobox map selection change."""
        idx = self.map_combo.current()
        all_maps = self.map_manager.get_all_maps()

        if idx < len(all_maps):
            key = all_maps[idx].key
            self.load_selected_map(key)
        else:
            # Procedural Random Map option
            self.generate_new_random_map()

    def _load_selected_map_from_combo(self) -> None:
        """Trigger loading from current combo selection."""
        self._on_map_selection_changed()

    def generate_new_random_map(self) -> None:
        """Generate and load a new procedural warehouse map using the seed entry."""
        seed_str = self.seed_var.get().strip()
        gen_map, actual_seed = RandomMapGenerator.generate(seed=seed_str if seed_str else None)
        self.seed_var.set(str(actual_seed))
        self.current_seed_val = actual_seed

        # Register and load
        self.map_manager.register_map(gen_map)
        self.load_selected_map(gen_map.key)

        # Update combobox text
        self.map_combo.set(f"{gen_map.name} — {gen_map.node_count_label}")

    def reset_current_map(self) -> None:
        """Reset blockages and results on the currently active map."""
        self._cancel_animation_if_running()
        curr_map = self.map_manager.get_current_map()
        self.load_selected_map(curr_map.key)
        self.update_status("Map reset to initial clean layout.", "info")

    def _refresh_pathway_checkboxes(self) -> None:
        """Populate the edge checkboxes with current blocked status."""
        for child in self.edge_scroll_content.winfo_children():
            child.destroy()

        self.edge_check_vars.clear()
        edges = self.warehouse.get_all_edges()

        for u, v in edges:
            edge = canonical_edge(u, v)
            is_blocked = self.warehouse.is_edge_blocked(u, v)
            var = tk.BooleanVar(value=is_blocked)
            self.edge_check_vars[edge] = var

            lbl_u = self.warehouse.get_node_label(u)
            lbl_v = self.warehouse.get_node_label(v)

            row = ttk.Frame(self.edge_scroll_content)
            row.pack(fill=tk.X, pady=1)

            cb = ttk.Checkbutton(
                row,
                text=f"{u} ↔ {v} ({lbl_u} - {lbl_v})",
                variable=var,
                command=lambda e=edge: self._on_checkbox_toggled(e),
            )
            cb.pack(side=tk.LEFT, anchor="w")

            status_text = "BLOCKED" if is_blocked else "OPEN"
            status_color = "#dc2626" if is_blocked else "#059669"

            tag = tk.Label(
                row,
                text=status_text,
                font=("Segoe UI", 8, "bold"),
                fg=status_color,
                bg="#ffffff",
                padx=3,
                pady=1,
            )
            tag.pack(side=tk.RIGHT, padx=4)

    # =========================================================================
    # EVENT HANDLERS & CANVAS INTERACTION
    # =========================================================================
    def _on_canvas_edge_clicked(self, u: str, v: str) -> None:
        """Handle clicking directly on an edge on the Matplotlib canvas."""
        now_blocked = self.warehouse.toggle_edge_block(u, v)
        edge = canonical_edge(u, v)
        if edge in self.edge_check_vars:
            self.edge_check_vars[edge].set(now_blocked)

        state_str = "blocked" if now_blocked else "unblocked"
        self.update_status(f"Corridor {u} ↔ {v} is now {state_str}.", "warning" if now_blocked else "info")
        self._refresh_pathway_checkboxes()
        self._sync_visualization()

    def _on_canvas_node_clicked(self, node_id: str) -> None:
        """Handle clicking directly on a node: display in inspector and option to set dest."""
        self.inspect_node(node_id)
        self.visualizer.set_selected_node(node_id)
        self._sync_visualization()

    def inspect_node(self, node_id: str) -> None:
        """Display full metadata for a selected node in the inspector card."""
        if node_id not in self.warehouse.graph:
            return
        label = self.warehouse.get_node_label(node_id)
        ntype = self.warehouse.get_node_type(node_id)
        pos = self.warehouse.positions.get(node_id, (0.0, 0.0))
        neighbors = sorted(list(self.warehouse.graph.neighbors(node_id)))

        self.insp_name_lbl.config(text=f"{label} ({node_id})")
        self.insp_type_lbl.config(text=f"Type: {ntype}  •  Coord: ({pos[0]:.1f}, {pos[1]:.1f})")
        self.insp_degree_lbl.config(text=f"Aisles ({len(neighbors)}): {', '.join(neighbors)}")

    def _on_reset_view(self) -> None:
        """Reset canvas zoom to fit."""
        self.visualizer.reset_view()

    def _on_zoom_in(self) -> None:
        """Zoom in."""
        self.visualizer.zoom_in()

    def _on_zoom_out(self) -> None:
        """Zoom out."""
        self.visualizer.zoom_out()

    def _on_checkbox_toggled(self, edge: Tuple[str, str]) -> None:
        """Handle edge checkbox toggle."""
        var = self.edge_check_vars.get(edge)
        if var is None:
            return

        if var.get():
            self.warehouse.block_edge(edge[0], edge[1])
            self.update_status(f"Pathway blocked: {edge[0]} ↔ {edge[1]}", "warning")
        else:
            self.warehouse.unblock_edge(edge[0], edge[1])
            self.update_status(f"Pathway unblocked: {edge[0]} ↔ {edge[1]}", "info")

        self._refresh_pathway_checkboxes()
        self._sync_visualization()

    def unblock_all_pathways(self) -> None:
        """Clear all pathway blockages."""
        self.warehouse.reset_blockages()
        self._refresh_pathway_checkboxes()
        self._sync_visualization()
        self.update_status("All pathways unblocked.", "info")

    def _get_selected_source(self) -> Optional[str]:
        """Extract source node ID from combobox."""
        val = self.source_combo.get().strip()
        if not val:
            return None
        return val.split(":")[0].strip()

    def _get_selected_dest(self) -> Optional[str]:
        """Extract destination node ID from combobox."""
        val = self.dest_combo.get().strip()
        if not val:
            return None
        return val.split(":")[0].strip()

    def _on_endpoint_changed(self, event=None) -> None:
        """Handle endpoint change."""
        src = self._get_selected_source()
        if src:
            self.inspect_node(src)
        self._sync_visualization()

    def _on_algorithm_changed(self) -> None:
        """Handle algorithm change."""
        if self.current_result:
            self.update_status(f"Algorithm set to {self.algo_var.get()}. Press 'Run Navigation' to recompute.", "info")

    def _sync_visualization(self) -> None:
        """Redraw canvas with current source, dest, and result."""
        src = self._get_selected_source()
        dst = self._get_selected_dest()
        self.visualizer.draw(
            source=src,
            destination=dst,
            search_result=self.current_result,
        )

    def validate_inputs(self) -> Tuple[Optional[str], Optional[str]]:
        """Validate dropdown selections."""
        src = self._get_selected_source()
        dst = self._get_selected_dest()

        if not src:
            messagebox.showerror("Validation Error", "Please select a valid Source Location.")
            self.update_status("Invalid source location.", "error")
            return None, None

        if not dst:
            messagebox.showerror("Validation Error", "Please select a valid Destination Location.")
            self.update_status("Invalid destination location.", "error")
            return None, None

        if src not in self.warehouse.graph:
            messagebox.showerror("Validation Error", f"Source '{src}' does not exist in the warehouse.")
            return None, None

        if dst not in self.warehouse.graph:
            messagebox.showerror("Validation Error", f"Destination '{dst}' does not exist in the warehouse.")
            return None, None

        return src, dst

    # =========================================================================
    # SEARCH EXECUTION & RESULTS
    # =========================================================================
    def run_navigation_direct(self) -> None:
        """Execute search immediately and display complete results."""
        self._cancel_animation_if_running()
        src, dst = self.validate_inputs()
        if not src or not dst:
            return

        self.update_status("Searching for a route...", "busy")
        algo = self.algo_var.get()
        blocked = set(self.warehouse.get_blocked_edges())

        try:
            if algo == "BFS":
                result = bfs_search(self.warehouse.graph, src, dst, blocked_edges=blocked)
            else:
                result = dfs_search(self.warehouse.graph, src, dst, blocked_edges=blocked)
        except Exception as ex:
            messagebox.showerror("Search Error", str(ex))
            self.update_status(f"Error during search: {ex}", "error")
            return

        self.current_result = result
        self.display_results(result)
        self._sync_visualization()

        if result.found:
            self.update_status(
                f"Route found: {result.get_path_arrow_string()}  ({result.edge_count} edges in {result.execution_time_ms:.2f} ms)",
                "info",
            )
        else:
            self.update_status("No route available between the selected locations.", "error")

    def display_results(self, result: SearchResult) -> None:
        """Update results panel, metrics, and visited treeview."""
        labels = {nid: self.warehouse.get_node_label(nid) for nid in self.warehouse.get_node_ids()}

        # 1. Route badge & path text
        self.path_text.config(state="normal")
        self.path_text.delete("1.0", tk.END)

        if result.found:
            if result.edge_count == 0:
                self.route_badge.config(text="Source is Destination (0 Edges)", bg="#dcfce7", fg="#15803d")
            elif result.is_shortest:
                self.route_badge.config(text=f"Optimal Route Found ({result.edge_count} Edges)", bg="#dcfce7", fg="#15803d")
            else:
                self.route_badge.config(text=f"Route Found ({result.edge_count} Edges - Suboptimal)", bg="#fef3c7", fg="#b45309")

            self.path_text.insert(tk.END, result.get_path_display(labels))
        else:
            self.route_badge.config(text="No Route Available", bg="#fee2e2", fg="#b91c1c")
            self.path_text.insert(tk.END, "No route available between the selected locations.\nCheck if pathways are blocked.")

        self.path_text.config(state="disabled")

        # 2. Key Statistics (clean multi-line formatting without clipping)
        self.stat_algo_lbl.config(text=f"Algorithm: {result.algorithm_name}")
        self.stat_route_len_lbl.config(
            text=f"Path Length: {result.edge_count} edges ({len(result.path)} locations)" if result.found else "Path Length: None"
        )
        self.stat_visited_cnt_lbl.config(text=f"Nodes Visited: {result.visited_count}")
        self.stat_time_lbl.config(text=f"Search Time: {result.execution_time_ms:.2f} ms")

        if result.found:
            if result.algorithm_name.startswith("Breadth First"):
                opt_str = "Yes (BFS guarantees shortest path)"
            else:
                opt_str = "Yes (Matches shortest)" if result.is_shortest else "No (DFS does not guarantee shortest)"
        else:
            opt_str = "N/A"
        self.stat_optimal_lbl.config(text=f"Guaranteed Shortest: {opt_str}")

        blocked_names = [f"{u}-{v}" for u, v in result.blocked_edges]
        blocked_str = ", ".join(blocked_names) if blocked_names else "None"
        self.stat_blocked_lbl.config(text=f"Blocked Pathways: {blocked_str}")

        # 3. Visited Nodes Treeview
        for item in self.visited_tree.get_children():
            self.visited_tree.delete(item)

        path_set = set(result.path)
        for i, node_id in enumerate(result.visited_order, start=1):
            lbl = self.warehouse.get_node_label(node_id)
            ntype = self.warehouse.get_node_type(node_id)
            in_path = "✓ Yes" if node_id in path_set else "—"
            self.visited_tree.insert("", tk.END, values=(i, node_id, lbl, ntype, in_path))

    # =========================================================================
    # ANIMATION CONTROLLER
    # =========================================================================
    def start_animation(self) -> None:
        """Begin educational step-by-step search animation with queue/stack tracing."""
        self._cancel_animation_if_running()
        src, dst = self.validate_inputs()
        if not src or not dst:
            return

        algo = self.algo_var.get()
        blocked = set(self.warehouse.get_blocked_edges())

        try:
            if algo == "BFS":
                result = bfs_search(self.warehouse.graph, src, dst, blocked_edges=blocked)
            else:
                result = dfs_search(self.warehouse.graph, src, dst, blocked_edges=blocked)
        except Exception as ex:
            messagebox.showerror("Search Error", str(ex))
            return

        self.current_result = result
        self.display_results(result)

        self.is_animating = True
        self.animation_paused = False
        self.anim_stage = "visited"
        self.anim_index = 0
        self.animated_visited_nodes = []
        self.animated_path_nodes = []

        self.btn_animate.config(text="⏹ Stop", command=self.stop_animation)
        self.btn_pause.config(state="normal", text="⏸ Pause")
        self.btn_run.config(state="disabled")

        self.update_status(f"Starting {algo} animation...", "busy")
        self._schedule_next_frame()

    def toggle_pause_animation(self) -> None:
        """Pause or resume the active animation."""
        if not self.is_animating:
            return

        if self.animation_paused:
            self.animation_paused = False
            self.btn_pause.config(text="⏸ Pause")
            self.update_status("Animation resumed.", "busy")
            self._schedule_next_frame()
        else:
            self.animation_paused = True
            if self.anim_timer_id:
                self.root.after_cancel(self.anim_timer_id)
                self.anim_timer_id = None
            self.btn_pause.config(text="▶ Resume")
            self.update_status("Animation paused.", "warning")

    def stop_animation(self) -> None:
        """Halt animation and show final static state."""
        self._cancel_animation_if_running()
        self._sync_visualization()
        self.update_status("Animation stopped.", "info")

    def _cancel_animation_if_running(self) -> None:
        """Cancel any pending after() timer and reset control buttons."""
        if self.anim_timer_id:
            try:
                self.root.after_cancel(self.anim_timer_id)
            except Exception:
                pass
            self.anim_timer_id = None

        self.is_animating = False
        self.animation_paused = False
        self.btn_animate.config(text="▶ Start Animation", command=self.start_animation)
        self.btn_pause.config(state="disabled", text="⏸ Pause")
        self.btn_run.config(state="normal")

    def _schedule_next_frame(self) -> None:
        """Schedule next animation step using after()."""
        if not self.is_animating or self.animation_paused:
            return
        delay_ms = max(80, int(self.speed_var.get()))
        self.anim_timer_id = self.root.after(delay_ms, self._step_animation_frame)

    def _step_animation_frame(self) -> None:
        """Advance one frame of the search and robot traversal animation."""
        if not self.is_animating or not self.current_result:
            return

        src = self._get_selected_source()
        dst = self._get_selected_dest()

        if self.anim_stage == "visited":
            order = self.current_result.visited_order
            trace = self.current_result.trace

            if self.anim_index < len(order):
                curr_node = order[self.anim_index]
                self.animated_visited_nodes.append(curr_node)

                # Trace stats
                frontier_info = ""
                if self.anim_index < len(trace):
                    t_step = trace[self.anim_index]
                    f_name = "Queue" if self.algo_var.get() == "BFS" else "Stack"
                    frontier_info = f" • {f_name} size: {t_step.frontier_size}"

                self.anim_index += 1
                node_lbl = self.warehouse.get_node_label(curr_node)
                self.inspect_node(curr_node)

                self.update_status(
                    f"Exploring node {self.anim_index} of {len(order)}: {node_lbl} ({curr_node}){frontier_info}",
                    "busy",
                )

                self.visualizer.draw(
                    source=src,
                    destination=dst,
                    search_result=self.current_result,
                    animated_visited=self.animated_visited_nodes,
                    animated_path=[],
                    active_node=curr_node,
                )
                self._schedule_next_frame()
            else:
                # Finished visiting
                if self.current_result.found:
                    self.anim_stage = "path"
                    self.anim_index = 0
                    self.update_status("Target discovered! Tracing robot navigation route...", "busy")
                    self._schedule_next_frame()
                else:
                    self.update_status("Search complete: No route available.", "error")
                    self._cancel_animation_if_running()

        elif self.anim_stage == "path":
            path = self.current_result.path
            if self.anim_index < len(path):
                self.animated_path_nodes.append(path[self.anim_index])
                self.anim_index += 1
                curr_node = path[self.anim_index - 1]
                node_lbl = self.warehouse.get_node_label(curr_node)
                self.inspect_node(curr_node)

                self.update_status(
                    f"Robot navigating to: {node_lbl} ({curr_node}) [Step {self.anim_index} of {len(path)}]",
                    "busy",
                )

                self.visualizer.draw(
                    source=src,
                    destination=dst,
                    search_result=self.current_result,
                    animated_visited=self.animated_visited_nodes,
                    animated_path=self.animated_path_nodes,
                    active_node=curr_node,
                )
                self._schedule_next_frame()
            else:
                self.update_status(
                    f"Navigation complete! Robot reached destination in {self.current_result.edge_count} edges.",
                    "info",
                )
                self._cancel_animation_if_running()

    def clear_results(self) -> None:
        """Clear search results and reset view."""
        self._cancel_animation_if_running()
        self.current_result = None

        self.route_badge.config(text="No Search Run Yet", bg="#f1f5f9", fg="#475569")
        self.path_text.config(state="normal")
        self.path_text.delete("1.0", tk.END)
        self.path_text.insert(tk.END, "Select source & destination, then run navigation.")
        self.path_text.config(state="disabled")

        self.stat_algo_lbl.config(text="Algorithm: —")
        self.stat_route_len_lbl.config(text="Path Length: —")
        self.stat_visited_cnt_lbl.config(text="Nodes Visited: —")
        self.stat_time_lbl.config(text="Search Time: —")
        self.stat_optimal_lbl.config(text="Guaranteed Shortest: —")
        self.stat_blocked_lbl.config(text="Blocked Pathways: None")

        for item in self.visited_tree.get_children():
            self.visited_tree.delete(item)

        self._sync_visualization()
        self.update_status("Results cleared.", "info")

    def load_sample_warehouse(self) -> None:
        """Restore baseline starter map."""
        self.algo_var.set("BFS")
        self.load_selected_map("starter")

    def reset_all(self) -> None:
        """Reset entire application."""
        self.load_sample_warehouse()


def main() -> None:
    """Launch the Autonomous Warehouse Robot desktop application."""
    root = tk.Tk()
    app = AutonomousWarehouseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
