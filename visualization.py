"""Visualization Module for Autonomous Warehouse Robot.

Renders warehouse graphs across small (5 nodes) to large (60 nodes) layouts
with dynamic scaling, automated bounding box fitting, zoom & pan controls,
interactive edge click-to-block, and node inspection.
"""

from __future__ import annotations
import math
from typing import Callable, Dict, List, Optional, Set, Tuple
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
import matplotlib.patches as patches

from warehouse_graph import WarehouseGraph, canonical_edge
from algorithms import SearchResult


class WarehouseVisualizer:
    """Manages the Matplotlib figure, dynamic scaling, and multi-scale rendering."""

    # zoom_factor is the visible viewport as a fraction of the fitted map.
    # Keeping it within these limits prevents nodes and labels from being
    # pushed beyond the canvas while still allowing useful inspection.
    MIN_ZOOM_FACTOR = 0.80
    MAX_ZOOM_FACTOR = 1.80

    # Color Palette: Professional, restrained, accessible
    COLOR_BG = "#f8fafc"            # Slate-50 background
    COLOR_NODE_DEFAULT = "#94a3b8"  # Slate-400
    COLOR_NODE_SOURCE = "#0d9488"   # Teal-600
    COLOR_NODE_DEST = "#e11d48"     # Rose-600
    COLOR_NODE_ROUTE = "#2563eb"    # Royal Blue-600
    COLOR_NODE_VISITED = "#f59e0b"  # Amber-500
    COLOR_NODE_ACTIVE = "#8b5cf6"   # Purple-500 (animated exploration)
    COLOR_NODE_SELECTED = "#0284c7" # Sky-600 (user inspection)

    COLOR_EDGE_OPEN = "#64748b"     # Slate-500
    COLOR_EDGE_BLOCKED = "#dc2626"  # Red-600
    COLOR_EDGE_ROUTE = "#2563eb"    # Royal Blue-600

    def __init__(
        self,
        master_widget: any,
        warehouse: WarehouseGraph,
        on_edge_toggle_cb: Optional[Callable[[str, str], None]] = None,
        on_node_click_cb: Optional[Callable[[str], None]] = None,
        on_zoom_change_cb: Optional[Callable[[float], None]] = None,
    ) -> None:
        """Initialize visualizer with parent widget and interaction callbacks.

        Args:
            master_widget: Parent Tkinter widget.
            warehouse: WarehouseGraph instance.
            on_edge_toggle_cb: Callback when an edge is clicked (u, v).
            on_node_click_cb: Callback when a node is clicked (node_id).
            on_zoom_change_cb: Callback when the visible zoom changes.
        """
        self.warehouse = warehouse
        self.on_edge_toggle_cb = on_edge_toggle_cb
        self.on_node_click_cb = on_node_click_cb
        self.on_zoom_change_cb = on_zoom_change_cb

        # Setup Matplotlib Figure
        self.fig = Figure(figsize=(6.8, 5.2), dpi=100, facecolor=self.COLOR_BG)
        self.ax = self.fig.add_subplot(111)
        # Let the fitted-map boundary use almost the whole canvas. The default
        # Matplotlib subplot margins made the safe area look detached from the
        # rest of the workspace.
        self.fig.subplots_adjust(left=0.035, right=0.965, bottom=0.035, top=0.965)
        self.ax.set_facecolor(self.COLOR_BG)

        # Zoom & Pan State
        self.zoom_factor: float = 1.0
        self.base_xlim: Tuple[float, float] = (0.0, 6.0)
        self.base_ylim: Tuple[float, float] = (0.0, 4.0)
        self.selected_node: Optional[str] = None
        self.dark_mode: bool = True
        self._viewport_border: Optional[patches.Rectangle] = None
        self._pan_active = False
        self._pan_start_pixel: Optional[Tuple[float, float]] = None
        self._pan_start_xlim: Tuple[float, float] = self.base_xlim
        self._pan_start_ylim: Tuple[float, float] = self.base_ylim

        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=master_widget)
        self.canvas_widget = self.canvas.get_tk_widget()

        # Connect mouse events
        self.canvas.mpl_connect("button_press_event", self._handle_button_press)
        self.canvas.mpl_connect("button_release_event", self._handle_button_release)
        self.canvas.mpl_connect("motion_notify_event", self._handle_motion)
        self.canvas.mpl_connect("scroll_event", self._handle_scroll)

        # Initial render
        self.draw()

    def set_theme(self, dark_mode: bool) -> None:
        """Update graph colors to match the application's light/dark theme."""
        self.dark_mode = dark_mode
        if dark_mode:
            self.COLOR_BG = "#0b1627"
            self.COLOR_NODE_DEFAULT = "#344a66"
            self.COLOR_NODE_SOURCE = "#19bda8"
            self.COLOR_NODE_DEST = "#ef6680"
            self.COLOR_NODE_ROUTE = "#4f8cff"
            self.COLOR_NODE_VISITED = "#d99a3f"
            self.COLOR_NODE_ACTIVE = "#9c7bff"
            self.COLOR_NODE_SELECTED = "#35b9ec"
            self.COLOR_EDGE_OPEN = "#57708f"
            self.COLOR_EDGE_BLOCKED = "#f05d75"
            self.COLOR_EDGE_ROUTE = "#4f8cff"
        else:
            self.COLOR_BG = "#f8fafc"
            self.COLOR_NODE_DEFAULT = "#94a3b8"
            self.COLOR_NODE_SOURCE = "#0d9488"
            self.COLOR_NODE_DEST = "#e11d48"
            self.COLOR_NODE_ROUTE = "#2563eb"
            self.COLOR_NODE_VISITED = "#f59e0b"
            self.COLOR_NODE_ACTIVE = "#8b5cf6"
            self.COLOR_NODE_SELECTED = "#0284c7"
            self.COLOR_EDGE_OPEN = "#64748b"
            self.COLOR_EDGE_BLOCKED = "#dc2626"
            self.COLOR_EDGE_ROUTE = "#2563eb"
        self.fig.set_facecolor(self.COLOR_BG)
        self.ax.set_facecolor(self.COLOR_BG)
        self.draw()

    def get_widget(self):
        """Return Tkinter canvas widget."""
        return self.canvas_widget

    def set_selected_node(self, node_id: Optional[str]) -> None:
        """Set or clear the highlighted inspected node."""
        self.selected_node = node_id

    def reset_view(self) -> None:
        """Reset zoom factor to auto-fit."""
        self.zoom_factor = 1.0
        self._notify_zoom_changed()
        self.draw()

    def zoom_in(self) -> None:
        """Zoom in by 20%."""
        self.zoom_factor = max(self.MIN_ZOOM_FACTOR, self.zoom_factor * 0.8)
        self._notify_zoom_changed()
        self._apply_zoom()

    def zoom_out(self) -> None:
        """Zoom out by 25%."""
        self.zoom_factor = min(self.MAX_ZOOM_FACTOR, self.zoom_factor * 1.25)
        self._notify_zoom_changed()
        self._apply_zoom()

    def _notify_zoom_changed(self) -> None:
        """Notify the application so it can show the current zoom limit."""
        if self.on_zoom_change_cb:
            self.on_zoom_change_cb(self.zoom_factor)

    def _apply_zoom(self) -> None:
        """Apply current zoom factor to axis limits."""
        current_xlim = self.ax.get_xlim()
        current_ylim = self.ax.get_ylim()
        cx = (current_xlim[0] + current_xlim[1]) / 2.0
        cy = (current_ylim[0] + current_ylim[1]) / 2.0
        dx = (self.base_xlim[1] - self.base_xlim[0]) * self.zoom_factor / 2.0
        dy = (self.base_ylim[1] - self.base_ylim[0]) * self.zoom_factor / 2.0

        xlim = self._clamp_pan_axis(cx - dx, cx + dx, self.base_xlim)
        ylim = self._clamp_pan_axis(cy - dy, cy + dy, self.base_ylim)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self._draw_viewport_border()
        self.canvas.draw_idle()

    @staticmethod
    def _clamp_pan_axis(
        proposed_low: float,
        proposed_high: float,
        base_limits: Tuple[float, float],
    ) -> Tuple[float, float]:
        """Keep a panned viewport aligned with the fitted map bounds."""
        view_size = proposed_high - proposed_low
        base_low, base_high = base_limits
        base_size = base_high - base_low
        if view_size >= base_size:
            center = (base_low + base_high) / 2.0
            return center - view_size / 2.0, center + view_size / 2.0

        low_limit = base_low
        high_limit = base_high - view_size
        clamped_low = min(max(proposed_low, low_limit), high_limit)
        return clamped_low, clamped_low + view_size

    def _draw_viewport_border(self) -> None:
        """Show the current visible map area as a subtle dashed boundary."""
        if self._viewport_border is not None:
            try:
                self._viewport_border.remove()
            except ValueError:
                # The axes may have been cleared since the last draw.
                pass

        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        border_color = "#607a9d" if self.dark_mode else "#9aaabd"
        self._viewport_border = patches.Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            fill=False,
            edgecolor=border_color,
            linewidth=1.0,
            linestyle=(0, (5, 4)),
            alpha=0.85,
            zorder=0,
            clip_on=False,
        )
        self.ax.add_patch(self._viewport_border)

    def draw(
        self,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        search_result: Optional[SearchResult] = None,
        animated_visited: Optional[List[str]] = None,
        animated_path: Optional[List[str]] = None,
        active_node: Optional[str] = None,
    ) -> None:
        """Render the complete warehouse graph with current states.

        Args:
            source: Selected source node ID.
            destination: Selected destination node ID.
            search_result: Completed search result (if any).
            animated_visited: Subset of visited nodes to show during animation.
            animated_path: Subset of path nodes to show during animation.
            active_node: Currently active node being evaluated during animation.
        """
        self.ax.clear()
        self._viewport_border = None
        self.ax.set_facecolor(self.COLOR_BG)
        self.ax.axis("off")

        positions = self.warehouse.positions
        node_count = self.warehouse.get_node_count()

        if not positions:
            self.canvas.draw_idle()
            return

        # 1. Compute dynamic bounding box
        xs = [pos[0] for pos in positions.values()]
        ys = [pos[1] for pos in positions.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)

        # Scale node radius and styling dynamically according to map size
        if node_count <= 8:
            node_radius = 0.32
            font_size = 11.0
            lw_edge = 2.6
            lw_route = 5.0
            label_mode = "full"
        elif node_count <= 18:
            node_radius = 0.26
            font_size = 9.0
            lw_edge = 2.2
            lw_route = 4.2
            label_mode = "compact"
        elif node_count <= 35:
            node_radius = 0.22
            font_size = 7.2
            lw_edge = 1.8
            lw_route = 3.6
            label_mode = "compact"
        else:
            node_radius = 0.19
            font_size = 6.4
            lw_edge = 1.5
            lw_route = 3.2
            label_mode = "compact"

        pad_x = max(1.05, span_x * 0.14)
        pad_y = max(0.95, span_y * 0.16)
        legend_space = pad_y * 1.25

        self.base_xlim = (min_x - pad_x, max_x + pad_x)
        self.base_ylim = (min_y - pad_y - legend_space, max_y + pad_y)

        # Apply bounds respecting zoom factor
        cx = (self.base_xlim[0] + self.base_xlim[1]) / 2.0
        cy = (self.base_ylim[0] + self.base_ylim[1]) / 2.0
        dx = (self.base_xlim[1] - self.base_xlim[0]) * self.zoom_factor / 2.0
        dy = (self.base_ylim[1] - self.base_ylim[0]) * self.zoom_factor / 2.0
        self.ax.set_xlim(cx - dx, cx + dx)
        self.ax.set_ylim(cy - dy, cy + dy)
        # A strict equal aspect makes a wide warehouse occupy only a small
        # strip of a tall Tk panel. Larger maps use the available canvas while
        # small educational maps retain their true geometric proportions.
        self.ax.set_aspect("equal" if node_count <= 18 else "auto")
        self._draw_viewport_border()

        # Determine effective path and visited sets
        effective_path: List[str] = []
        if animated_path is not None:
            effective_path = animated_path
        elif search_result and search_result.found:
            effective_path = search_result.path

        effective_visited: Set[str] = set()
        if animated_visited is not None:
            effective_visited = set(animated_visited)
        elif search_result:
            effective_visited = set(search_result.visited_order)

        # Set of canonical edges in the active path
        path_edge_set: Set[Tuple[str, str]] = set()
        for i in range(len(effective_path) - 1):
            path_edge_set.add(canonical_edge(effective_path[i], effective_path[i + 1]))

        # 2. Draw Edges
        self._draw_edges(path_edge_set, lw_edge, lw_route, node_radius)

        # 3. Draw Route Direction Arrows
        if len(effective_path) > 1:
            self._draw_route_arrows(effective_path, node_radius)

        # 4. Draw Nodes
        self._draw_nodes(
            source,
            destination,
            effective_path,
            effective_visited,
            active_node,
            node_radius,
            font_size,
            label_mode,
        )

        # 5. Draw Legend
        self._draw_legend()

        self.canvas.draw_idle()

    def _draw_edges(
        self,
        path_edge_set: Set[Tuple[str, str]],
        lw_edge: float,
        lw_route: float,
        node_radius: float,
    ) -> None:
        """Draw open, blocked, and route edges."""
        all_edges = self.warehouse.get_all_edges()
        positions = self.warehouse.positions

        for u, v in all_edges:
            pos_u = positions[u]
            pos_v = positions[v]
            edge = canonical_edge(u, v)
            is_blocked = self.warehouse.is_edge_blocked(u, v)
            is_route = edge in path_edge_set

            if is_blocked:
                # Red dashed line
                self.ax.plot(
                    [pos_u[0], pos_v[0]],
                    [pos_u[1], pos_v[1]],
                    color=self.COLOR_EDGE_BLOCKED,
                    linestyle="--",
                    linewidth=max(2.0, lw_edge * 1.3),
                    alpha=0.75,
                    zorder=2,
                )
                # Obstacle marker at midpoint
                mid_x = (pos_u[0] + pos_v[0]) / 2.0
                mid_y = (pos_u[1] + pos_v[1]) / 2.0
                marker_size = max(7, int(node_radius * 30))
                self.ax.plot(
                    mid_x,
                    mid_y,
                    marker="X",
                    markersize=marker_size,
                    color=self.COLOR_EDGE_BLOCKED,
                    markeredgecolor="white",
                    markeredgewidth=1.2,
                    zorder=3,
                )
            elif is_route:
                # Highlighted route line
                self.ax.plot(
                    [pos_u[0], pos_v[0]],
                    [pos_u[1], pos_v[1]],
                    color=self.COLOR_EDGE_ROUTE,
                    linestyle="-",
                    linewidth=lw_route,
                    alpha=0.92,
                    zorder=3,
                )
            else:
                # Open pathway
                self.ax.plot(
                    [pos_u[0], pos_v[0]],
                    [pos_u[1], pos_v[1]],
                    color=self.COLOR_EDGE_OPEN,
                    linestyle="-",
                    linewidth=lw_edge,
                    alpha=0.75,
                    zorder=1,
                )

    def _draw_route_arrows(self, path: List[str], node_radius: float) -> None:
        """Draw directional navigation arrows along the active robot path."""
        positions = self.warehouse.positions
        head_w = max(6.0, node_radius * 28.0)
        head_l = max(7.0, node_radius * 34.0)

        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            p1 = positions[u]
            p2 = positions[v]

            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dist = math.hypot(dx, dy)
            if dist < 0.001:
                continue

            # Position arrow centered between node boundaries
            t_start = 0.40
            t_end = 0.64
            arrow = patches.FancyArrowPatch(
                (p1[0] + t_start * dx, p1[1] + t_start * dy),
                (p1[0] + t_end * dx, p1[1] + t_end * dy),
                arrowstyle=f"Simple,tail_width=2.0,head_width={head_w:.1f},head_length={head_l:.1f}",
                facecolor="#e8f0fb" if self.dark_mode else "#ffffff",
                edgecolor="#1e3a8a",
                linewidth=1.1,
                zorder=4,
            )
            self.ax.add_patch(arrow)

    def _draw_nodes(
        self,
        source: Optional[str],
        destination: Optional[str],
        path: List[str],
        visited: Set[str],
        active_node: Optional[str],
        node_radius: float,
        font_size: float,
        label_mode: str,
    ) -> None:
        """Render nodes with color hierarchy and scaling."""
        positions = self.warehouse.positions
        path_set = set(path)

        for node_id in self.warehouse.get_node_ids():
            x, y = positions[node_id]
            label = self.warehouse.get_node_label(node_id)
            node_type = self.warehouse.get_node_type(node_id)

            is_src = (node_id == source)
            is_dst = (node_id == destination)
            is_active = (node_id == active_node)
            is_in_path = (node_id in path_set)
            is_vis = (node_id in visited)
            is_selected = (node_id == self.selected_node)

            # Color hierarchy
            if is_active:
                fill_color = self.COLOR_NODE_ACTIVE
                border_color = "#5b21b6"
                border_width = 2.5
            elif is_src:
                fill_color = self.COLOR_NODE_SOURCE
                border_color = "#0f766e"
                border_width = 2.5
            elif is_dst:
                fill_color = self.COLOR_NODE_DEST
                border_color = "#be123c"
                border_width = 2.5
            elif is_in_path:
                fill_color = self.COLOR_NODE_ROUTE
                border_color = "#1d4ed8"
                border_width = 2.5
            elif is_vis:
                fill_color = self.COLOR_NODE_VISITED
                border_color = "#b45309"
                border_width = 2.0
            elif is_selected:
                fill_color = self.COLOR_NODE_SELECTED
                border_color = "#0369a1"
                border_width = 2.5
            else:
                fill_color = self.COLOR_NODE_DEFAULT
                border_color = "#475569"
                border_width = 1.5

            # Outer ring glow for selected, active, or path nodes
            if is_selected or is_in_path or is_active:
                glow_color = "#38bdf8" if is_selected else ("#60a5fa" if is_in_path else "#c084fc")
                glow = patches.Circle(
                    (x, y),
                    radius=node_radius * 1.28,
                    facecolor="none",
                    edgecolor=glow_color,
                    linewidth=1.8,
                    linestyle=":",
                    zorder=4,
                )
                self.ax.add_patch(glow)

            # Main circle
            circle = patches.Circle(
                (x, y),
                radius=node_radius,
                facecolor=fill_color,
                edgecolor=border_color,
                linewidth=border_width,
                zorder=5,
            )
            self.ax.add_patch(circle)

            # Node ID text inside
            display_id = node_id
            self.ax.text(
                x, y,
                display_id,
                ha="center",
                va="center",
                color="white",
                fontsize=font_size,
                fontweight="bold",
                zorder=6,
            )

            # Every node keeps a visible human-readable label. Larger maps use
            # short labels so the warehouse remains legible instead of hiding
            # all names and leaving only opaque IDs on the canvas.
            if label_mode == "full":
                external_label = f"{label}\n({node_type})"
                external_size = 8.0
                pad = 0.22
            else:
                external_label = self._compact_node_label(node_id, node_type, label)
                external_size = 6.0 if len(self.warehouse.get_node_ids()) > 35 else 7.0
                pad = 0.12

            if label_mode in ("full", "compact"):
                offset_y = (node_radius + 0.16) if y >= 2.0 else -(node_radius + 0.16)
                self.ax.text(
                    x, y + offset_y,
                    external_label,
                    ha="center",
                    va="center",
                    fontsize=external_size,
                    fontweight="semibold",
                    color="#e8f0fb" if self.dark_mode else "#0f172a",
                    bbox=dict(
                        boxstyle=f"round,pad={pad}",
                        facecolor="#172840" if self.dark_mode else "white",
                        edgecolor="#385574" if self.dark_mode else "#cbd5e1",
                        linewidth=0.55,
                        alpha=0.86,
                    ),
                    zorder=6,
                )

    @staticmethod
    def _compact_node_label(node_id: str, node_type: str, label: str) -> str:
        """Create a readable one-line label for medium and large maps."""
        digits = "".join(ch for ch in node_id if ch.isdigit())
        suffix = digits[-2:] if digits else node_id[-2:]
        if node_type == "Rack":
            return f"Rack {suffix}"
        if node_type == "Storage":
            return f"In {suffix}"
        if node_type == "Intersection":
            return f"J-{suffix}"
        if node_type == "Packing Station":
            return f"Pack {suffix}"
        if node_type == "Charging Station":
            return "Charge"
        if node_type == "Exit":
            return f"Exit {suffix}"
        return label[:14]

    def _draw_legend(self) -> None:
        """Render a clean custom legend for graph colors."""
        legend_elements = [
            Line2D([0], [0], marker="o", color="w", label="Source (Start)",
                   markerfacecolor=self.COLOR_NODE_SOURCE, markersize=8),
            Line2D([0], [0], marker="o", color="w", label="Destination (End)",
                   markerfacecolor=self.COLOR_NODE_DEST, markersize=8),
            Line2D([0], [0], marker="o", color="w", label="Route Node",
                   markerfacecolor=self.COLOR_NODE_ROUTE, markersize=8),
            Line2D([0], [0], marker="o", color="w", label="Visited Node",
                   markerfacecolor=self.COLOR_NODE_VISITED, markersize=8),
            Line2D([0], [0], color=self.COLOR_EDGE_OPEN, lw=2.0, label="Open Pathway"),
            Line2D([0], [0], color=self.COLOR_EDGE_ROUTE, lw=3.8, label="Robot Route"),
            Line2D([0], [0], color=self.COLOR_EDGE_BLOCKED, lw=2.0, linestyle="--", label="Blocked Pathway"),
            Line2D([0], [0], marker=">", color=self.COLOR_EDGE_ROUTE, markerfacecolor="#e8f0fb" if self.dark_mode else "white",
                   markeredgecolor="#1e3a8a", markeredgewidth=1.1, label="Route Direction", markersize=8),
        ]
        legend = self.ax.legend(
            handles=legend_elements,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.0),
            ncol=4,
            fontsize=7.5,
            frameon=True,
            facecolor="#14243a" if self.dark_mode else "white",
            edgecolor="#385574" if self.dark_mode else "#cbd5e1",
            framealpha=0.96,
        )
        for legend_text in legend.get_texts():
            legend_text.set_color("#e8f0fb" if self.dark_mode else "#243447")

    def _handle_scroll(self, event) -> None:
        """Handle mouse wheel zooming."""
        if event.button == "up":
            self.zoom_in()
        elif event.button == "down":
            self.zoom_out()

    def _handle_button_press(self, event) -> None:
        """Start middle-button panning or route left-click interactions."""
        if event.button == 2:
            self._pan_active = True
            self._pan_start_pixel = (float(event.x), float(event.y))
            self._pan_start_xlim = self.ax.get_xlim()
            self._pan_start_ylim = self.ax.get_ylim()
            self.canvas_widget.configure(cursor="hand2")
            return

        if event.button == 1:
            self._handle_click(event)

    def _handle_button_release(self, event) -> None:
        """Stop middle-button panning and restore the normal cursor."""
        if event.button == 2:
            self._pan_active = False
            self._pan_start_pixel = None
            self.canvas_widget.configure(cursor="arrow")

    def _handle_motion(self, event) -> None:
        """Move the visible map while the middle mouse button is held."""
        if not self._pan_active or self._pan_start_pixel is None:
            return
        if event.x is None or event.y is None:
            return

        bbox = self.ax.get_window_extent()
        if bbox.width <= 0 or bbox.height <= 0:
            return

        start_x, start_y = self._pan_start_pixel
        delta_x = (float(event.x) - start_x) / bbox.width
        delta_y = (float(event.y) - start_y) / bbox.height
        x_span = self._pan_start_xlim[1] - self._pan_start_xlim[0]
        y_span = self._pan_start_ylim[1] - self._pan_start_ylim[0]

        proposed_xlim = (
            self._pan_start_xlim[0] - delta_x * x_span,
            self._pan_start_xlim[1] - delta_x * x_span,
        )
        proposed_ylim = (
            self._pan_start_ylim[0] - delta_y * y_span,
            self._pan_start_ylim[1] - delta_y * y_span,
        )
        xlim = self._clamp_pan_axis(*proposed_xlim, self.base_xlim)
        ylim = self._clamp_pan_axis(*proposed_ylim, self.base_ylim)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self._draw_viewport_border()
        self.canvas.draw_idle()

    def _handle_click(self, event) -> None:
        """Handle canvas click for edge blocking and node inspection."""
        if event.xdata is None or event.ydata is None:
            return

        click_x, click_y = float(event.xdata), float(event.ydata)
        positions = self.warehouse.positions
        node_count = self.warehouse.get_node_count()

        # Dynamic hit threshold based on node count
        node_threshold = 0.35 if node_count <= 10 else (0.28 if node_count <= 25 else 0.22)
        edge_threshold = 0.28 if node_count <= 10 else (0.22 if node_count <= 25 else 0.16)

        # 1. Check if user clicked a node
        closest_node = None
        min_node_dist = float("inf")
        for node_id, (nx_val, ny_val) in positions.items():
            dist = math.hypot(click_x - nx_val, click_y - ny_val)
            if dist < min_node_dist:
                min_node_dist = dist
                closest_node = node_id

        if closest_node is not None and min_node_dist <= node_threshold:
            self.selected_node = closest_node
            if self.on_node_click_cb:
                self.on_node_click_cb(closest_node)
            return

        # 2. Check if user clicked near an edge
        if self.on_edge_toggle_cb:
            closest_edge: Optional[Tuple[str, str]] = None
            min_edge_dist = float("inf")

            for u, v in self.warehouse.get_all_edges():
                dist = self._point_to_segment_distance(
                    click_x, click_y,
                    positions[u][0], positions[u][1],
                    positions[v][0], positions[v][1],
                )
                if dist < min_edge_dist:
                    min_edge_dist = dist
                    closest_edge = (u, v)

            if closest_edge is not None and min_edge_dist <= edge_threshold:
                self.on_edge_toggle_cb(closest_edge[0], closest_edge[1])

    @staticmethod
    def _point_to_segment_distance(
        px: float, py: float, x1: float, y1: float, x2: float, y2: float
    ) -> float:
        """Compute Euclidean distance from point (px, py) to line segment (x1, y1)-(x2, y2)."""
        dx = x2 - x1
        dy = y2 - y1
        l2 = dx * dx + dy * dy
        if l2 == 0:
            return math.hypot(px - x1, py - y1)

        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)
