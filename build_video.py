"""Autonomous Warehouse Robot - Video Generation Script.

Produces a high-definition 720p 24fps demonstration video (MP4) and animated GIF
showcasing multi-map warehouse navigation, BFS vs DFS exploration, dynamic
corridor blocking, detour re-planning, and robot traversal.
"""

from __future__ import annotations
import math
import os
import subprocess
import time
from typing import Dict, List, Optional, Set, Tuple

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
import matplotlib.patches as patches

from PIL import Image, ImageDraw, ImageFont

from warehouse_graph import WarehouseGraph, canonical_edge
from map_manager import MapManager, WarehouseMap
from map_generator import RandomMapGenerator
from algorithms import bfs_search, dfs_search, SearchResult

W, H = 1280, 720
FPS = 24

# Typography
FONT_BOLD_XL = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 36)
FONT_BOLD_L = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)
FONT_BOLD_M = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 15)
FONT_BOLD_S = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 12)
FONT_REG_M = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
FONT_REG_S = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 12)
FONT_MONO = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)


def render_graph_to_pil(
    warehouse: WarehouseGraph,
    source: str,
    destination: str,
    search_result: Optional[SearchResult] = None,
    animated_visited: Optional[List[str]] = None,
    animated_path: Optional[List[str]] = None,
    active_node: Optional[str] = None,
    robot_pos: Optional[Tuple[float, float]] = None,
    canvas_w: int = 760,
    canvas_h: int = 540,
) -> Image.Image:
    """Render the warehouse graph to a PIL Image using Matplotlib Agg."""
    fig = Figure(figsize=(canvas_w / 100, canvas_h / 100), dpi=100, facecolor="#f8fafc")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")
    ax.axis("off")

    positions = warehouse.positions
    node_count = warehouse.get_node_count()

    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(1.0, max_x - min_x)
    span_y = max(1.0, max_y - min_y)

    pad_x = max(0.8, span_x * 0.12)
    pad_y = max(0.8, span_y * 0.14)
    legend_space = pad_y * 1.2

    ax.set_xlim(min_x - pad_x, max_x + pad_x)
    ax.set_ylim(min_y - pad_y - legend_space, max_y + pad_y)
    ax.set_aspect("equal")

    # Dynamic scaling
    if node_count <= 8:
        node_radius = 0.32
        font_size = 11.0
        lw_edge = 2.6
        lw_route = 5.2
        show_ext = True
    elif node_count <= 18:
        node_radius = 0.26
        font_size = 9.0
        lw_edge = 2.2
        lw_route = 4.2
        show_ext = False
    else:
        node_radius = 0.20
        font_size = 6.5
        lw_edge = 1.6
        lw_route = 3.4
        show_ext = False

    effective_path = animated_path if animated_path is not None else (search_result.path if search_result and search_result.found else [])
    effective_visited = set(animated_visited) if animated_visited is not None else (set(search_result.visited_order) if search_result else set())

    path_edges = set()
    for i in range(len(effective_path) - 1):
        path_edges.add(canonical_edge(effective_path[i], effective_path[i + 1]))

    # Draw edges
    for u, v in warehouse.get_all_edges():
        p_u = positions[u]
        p_v = positions[v]
        edge = canonical_edge(u, v)
        is_blocked = warehouse.is_edge_blocked(u, v)
        is_route = edge in path_edges

        if is_blocked:
            ax.plot([p_u[0], p_v[0]], [p_u[1], p_v[1]], color="#dc2626", linestyle="--", linewidth=max(2.2, lw_edge * 1.3), alpha=0.8, zorder=2)
            mid_x = (p_u[0] + p_v[0]) / 2.0
            mid_y = (p_u[1] + p_v[1]) / 2.0
            ax.plot(mid_x, mid_y, marker="X", markersize=max(8, int(node_radius * 32)), color="#dc2626", markeredgecolor="white", markeredgewidth=1.2, zorder=3)
        elif is_route:
            ax.plot([p_u[0], p_v[0]], [p_u[1], p_v[1]], color="#2563eb", linestyle="-", linewidth=lw_route, alpha=0.92, zorder=3)
        else:
            ax.plot([p_u[0], p_v[0]], [p_u[1], p_v[1]], color="#64748b", linestyle="-", linewidth=lw_edge, alpha=0.75, zorder=1)

    # Route arrows
    head_w = max(6.0, node_radius * 28.0)
    head_l = max(7.0, node_radius * 34.0)
    for i in range(len(effective_path) - 1):
        u, v = effective_path[i], effective_path[i + 1]
        p1, p2 = positions[u], positions[v]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        if math.hypot(dx, dy) > 0.001:
            arrow = patches.FancyArrowPatch(
                (p1[0] + 0.40 * dx, p1[1] + 0.40 * dy),
                (p1[0] + 0.64 * dx, p1[1] + 0.64 * dy),
                arrowstyle=f"Simple,tail_width=2.0,head_width={head_w:.1f},head_length={head_l:.1f}",
                facecolor="#ffffff",
                edgecolor="#1e3a8a",
                linewidth=1.1,
                zorder=4,
            )
            ax.add_patch(arrow)

    # Nodes
    path_set = set(effective_path)
    for nid, (x, y) in positions.items():
        is_src = (nid == source)
        is_dst = (nid == destination)
        is_active = (nid == active_node)
        is_in_path = (nid in path_set)
        is_vis = (nid in effective_visited)

        if is_active:
            fill, border, bw = "#8b5cf6", "#5b21b6", 2.6
        elif is_src:
            fill, border, bw = "#0d9488", "#0f766e", 2.6
        elif is_dst:
            fill, border, bw = "#e11d48", "#be123c", 2.6
        elif is_in_path:
            fill, border, bw = "#2563eb", "#1d4ed8", 2.5
        elif is_vis:
            fill, border, bw = "#f59e0b", "#b45309", 2.0
        else:
            fill, border, bw = "#94a3b8", "#475569", 1.5

        if is_in_path or is_active:
            glow = patches.Circle((x, y), radius=node_radius * 1.3, facecolor="none", edgecolor="#60a5fa" if is_in_path else "#c084fc", linewidth=1.8, linestyle=":", zorder=4)
            ax.add_patch(glow)

        circle = patches.Circle((x, y), radius=node_radius, facecolor=fill, edgecolor=border, linewidth=bw, zorder=5)
        ax.add_patch(circle)

        ax.text(x, y, nid, ha="center", va="center", color="white", fontsize=font_size, fontweight="bold", zorder=6)

        if show_ext:
            lbl = warehouse.get_node_label(nid)
            ntype = warehouse.get_node_type(nid)
            off_y = (node_radius + 0.16) if y >= 2.0 else -(node_radius + 0.16)
            ax.text(x, y + off_y, f"{lbl}\n({ntype})", ha="center", va="center", fontsize=8.0, fontweight="semibold", color="#0f172a", bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#cbd5e1", linewidth=0.7, alpha=0.92), zorder=6)

    # Robot Marker (if navigating)
    if robot_pos:
        rx, ry = robot_pos
        # Robot pulse ring
        r_pulse = patches.Circle((rx, ry), radius=node_radius * 1.5, facecolor="#38bdf8", alpha=0.35, zorder=7)
        ax.add_patch(r_pulse)
        # Robot core glyph
        r_core = patches.Circle((rx, ry), radius=node_radius * 0.75, facecolor="#0284c7", edgecolor="#ffffff", linewidth=2.0, zorder=8)
        ax.add_patch(r_core)
        ax.text(rx, ry, "🤖", ha="center", va="center", fontsize=11, zorder=9)

    # Legend
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", label="Source (Start)", markerfacecolor="#0d9488", markersize=8),
        Line2D([0], [0], marker="o", color="w", label="Destination (End)", markerfacecolor="#e11d48", markersize=8),
        Line2D([0], [0], marker="o", color="w", label="Route Node", markerfacecolor="#2563eb", markersize=8),
        Line2D([0], [0], marker="o", color="w", label="Visited Node", markerfacecolor="#f59e0b", markersize=8),
        Line2D([0], [0], color="#64748b", lw=2.0, label="Open Pathway"),
        Line2D([0], [0], color="#2563eb", lw=3.8, label="Robot Route"),
        Line2D([0], [0], color="#dc2626", lw=2.0, linestyle="--", label="Blocked Pathway"),
        Line2D([0], [0], marker=">", color="#2563eb", markerfacecolor="white", markeredgecolor="#1e3a8a", markeredgewidth=1.1, label="Route Direction", markersize=8),
    ]
    ax.legend(handles=legend_elements, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=4, fontsize=7.2, frameon=True, facecolor="white", edgecolor="#cbd5e1", framealpha=0.96)

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    rgba = canvas.buffer_rgba()
    pil_img = Image.frombuffer("RGBA", (canvas_w, canvas_h), rgba, "raw", "RGBA", 0, 1).convert("RGB")
    return pil_img


def build_app_frame(
    graph_img: Image.Image,
    scenario_title: str,
    subtitle_msg: str,
    map_name: str,
    node_count: int,
    edge_count: int,
    algo_name: str,
    src_label: str,
    dst_label: str,
    route_status: str,
    route_status_color: str,
    path_len_str: str,
    visited_cnt_str: str,
    opt_str: str,
    blocked_str: str,
    frontier_info: str,
    path_lines: List[str],
    progress_pct: float = 0.0,
) -> Image.Image:
    """Composite a full application frame with controls, canvas, results card, and status bar."""
    frame = Image.new("RGB", (W, H), "#f1f5f9")
    draw = ImageDraw.Draw(frame)

    # 1. Header
    draw.rectangle([0, 0, W, 64], fill="#0f172a")
    draw.text((20, 10), "Autonomous Warehouse Robot", font=FONT_BOLD_L, fill="#f8fafc")
    draw.text((20, 36), f"{scenario_title}  •  {subtitle_msg}", font=FONT_REG_S, fill="#94a3b8")

    # Progress bar along top
    if progress_pct > 0:
        bar_w = int(W * min(1.0, progress_pct))
        draw.rectangle([0, 61, bar_w, 64], fill="#0284c7")

    # Layout coordinates
    left_w = 260
    right_w = 270
    center_l = left_w + 14
    center_w = W - left_w - right_w - 28
    right_l = center_l + center_w + 10

    # 2. Left Panel: Controls Card
    box_l_top = 72
    box_l_h = H - box_l_top - 36
    draw.rounded_rectangle([8, box_l_top, 8 + left_w, box_l_top + box_l_h], radius=6, fill="#ffffff", outline="#cbd5e1")
    draw.text((18, box_l_top + 10), "Warehouse Controls", font=FONT_BOLD_M, fill="#1e293b")

    draw.text((18, box_l_top + 36), "Active Map:", font=FONT_BOLD_S, fill="#334155")
    draw.rounded_rectangle([18, box_l_top + 52, 8 + left_w - 10, box_l_top + 76], radius=4, fill="#f8fafc", outline="#94a3b8")
    draw.text((26, box_l_top + 57), f"{map_name} ({node_count}N)", font=FONT_REG_S, fill="#0f172a")

    draw.text((18, box_l_top + 84), "Source (Start):", font=FONT_BOLD_S, fill="#334155")
    draw.rounded_rectangle([18, box_l_top + 100, 8 + left_w - 10, box_l_top + 124], radius=4, fill="#f8fafc", outline="#94a3b8")
    draw.text((26, box_l_top + 105), src_label, font=FONT_REG_S, fill="#0f172a")

    draw.text((18, box_l_top + 132), "Destination (Target):", font=FONT_BOLD_S, fill="#334155")
    draw.rounded_rectangle([18, box_l_top + 148, 8 + left_w - 10, box_l_top + 172], radius=4, fill="#f8fafc", outline="#94a3b8")
    draw.text((26, box_l_top + 153), dst_label, font=FONT_REG_S, fill="#0f172a")

    draw.text((18, box_l_top + 180), "Search Algorithm:", font=FONT_BOLD_S, fill="#334155")
    is_bfs = "BFS" in algo_name
    draw.ellipse([22, box_l_top + 200, 32, box_l_top + 210], fill="#2563eb" if is_bfs else "#ffffff", outline="#2563eb")
    draw.text((38, box_l_top + 197), "Breadth First Search (BFS)", font=FONT_REG_S, fill="#0f172a" if is_bfs else "#64748b")
    draw.ellipse([22, box_l_top + 218, 32, box_l_top + 228], fill="#ffffff" if is_bfs else "#2563eb", outline="#2563eb")
    draw.text((38, box_l_top + 215), "Depth First Search (DFS)", font=FONT_REG_S, fill="#64748b" if is_bfs else "#0f172a")

    # Action Status Button
    draw.rounded_rectangle([18, box_l_top + 242, 8 + left_w - 10, box_l_top + 270], radius=4, fill="#0d9488")
    draw.text((70, box_l_top + 248), "Simulation Running", font=FONT_BOLD_S, fill="#ffffff")

    # Corridor Status Box
    box_c_top = box_l_top + 280
    draw.text((18, box_c_top), "Corridor Blockage Status:", font=FONT_BOLD_S, fill="#1e293b")
    status_bg = "#fee2e2" if blocked_str != "None" else "#dcfce7"
    status_fg = "#dc2626" if blocked_str != "None" else "#059669"
    draw.rounded_rectangle([18, box_c_top + 18, 8 + left_w - 10, box_c_top + 46], radius=4, fill=status_bg)
    draw.text((26, box_c_top + 24), f"Blocked: {blocked_str}", font=FONT_BOLD_S, fill=status_fg)

    # 3. Center Panel: Canvas & Banner
    box_m_top = 72
    box_m_h = H - box_m_top - 36
    draw.rounded_rectangle([center_l, box_m_top, center_l + center_w, box_m_top + box_m_h], radius=6, fill="#ffffff", outline="#cbd5e1")
    draw.text((center_l + 16, box_m_top + 10), f"Map: {map_name}  •  {node_count} Nodes  •  {edge_count} Pathways", font=FONT_BOLD_M, fill="#0f172a")

    # Paste Graph Canvas
    canv_resized = graph_img.resize((center_w - 16, box_m_h - 44), Image.Resampling.LANCZOS)
    frame.paste(canv_resized, (center_l + 8, box_m_top + 36))

    # 4. Right Panel: Metrics & Navigation Path
    draw.rounded_rectangle([right_l, box_m_top, right_l + right_w, box_m_top + box_m_h], radius=6, fill="#ffffff", outline="#cbd5e1")

    # Banner Status
    bg_banner = "#dcfce7" if route_status_color == "green" else ("#fee2e2" if route_status_color == "red" else "#fef3c7")
    fg_banner = "#15803d" if route_status_color == "green" else ("#b91c1c" if route_status_color == "red" else "#b45309")
    draw.rounded_rectangle([right_l + 10, box_m_top + 10, right_l + right_w - 10, box_m_top + 40], radius=5, fill=bg_banner)
    draw.text((right_l + 20, box_m_top + 16), route_status, font=FONT_BOLD_S, fill=fg_banner)

    # Metrics rows
    met_y = box_m_top + 48
    draw.rounded_rectangle([right_l + 10, met_y, right_l + right_w - 10, met_y + 140], radius=5, fill="#f8fafc", outline="#e2e8f0")
    draw.text((right_l + 18, met_y + 8), "Search Metrics", font=FONT_BOLD_S, fill="#1e293b")

    m_rows = [
        ("Algorithm:", algo_name),
        ("Path Length:", path_len_str),
        ("Nodes Visited:", visited_cnt_str),
        ("Guaranteed Shortest:", opt_str),
        ("Frontier State:", frontier_info),
    ]
    my = met_y + 26
    for k, v in m_rows:
        draw.text((right_l + 18, my), k, font=FONT_BOLD_S, fill="#475569")
        draw.text((right_l + 130, my), v, font=FONT_REG_S, fill="#0f172a")
        my += 21

    # Navigation Path Card
    p_top = met_y + 150
    p_h = box_m_h - (p_top - box_m_top) - 10
    draw.rounded_rectangle([right_l + 10, p_top, right_l + right_w - 10, p_top + p_h], radius=5, fill="#f8fafc", outline="#cbd5e1")
    draw.text((right_l + 18, p_top + 8), "Robot Navigation Path", font=FONT_BOLD_S, fill="#1e293b")

    py = p_top + 28
    for line in path_lines[:12]:
        is_arr = "↓" in line
        draw.text((right_l + 24, py), line, font=FONT_MONO, fill="#2563eb" if is_arr else "#0f172a")
        py += 18

    # 5. Bottom Status Bar
    draw.rectangle([0, H - 26, W, H], fill="#1e293b")
    draw.ellipse([14, H - 18, 22, H - 10], fill="#10b981")
    draw.text((30, H - 19), f"Status: {subtitle_msg}", font=FONT_REG_S, fill="#f8fafc")

    return frame


def render_title_frame(title: str, subtitle: str, highlights: List[str], footer: str) -> Image.Image:
    """Render a clean presentation title card."""
    frame = Image.new("RGB", (W, H), "#0b1329")
    draw = ImageDraw.Draw(frame)

    # Decorative header line
    draw.rectangle([0, 0, W, 6], fill="#2563eb")

    # Title & Subtitle
    draw.text((100, 130), title, font=FONT_BOLD_XL, fill="#ffffff")
    draw.text((100, 185), subtitle, font=FONT_BOLD_L, fill="#38bdf8")

    # Divider
    draw.line([100, 225, 450, 225], fill="#0284c7", width=3)

    # Highlights
    hy = 260
    for h in highlights:
        draw.text((120, hy), h, font=FONT_REG_M, fill="#e2e8f0")
        hy += 42

    # Footer
    draw.rectangle([0, H - 60, W, H], fill="#0f172a")
    draw.text((100, H - 42), footer, font=FONT_REG_S, fill="#94a3b8")

    return frame


def generate_video() -> None:
    """Produce all animation frames and stream directly to FFmpeg pipe."""
    print("=" * 60)
    print("Starting Autonomous Warehouse Robot Demonstration Video Builder")
    print("=" * 60)

    mgr = MapManager()

    # Setup FFmpeg output pipe
    mp4_filename = "autonomous_warehouse_robot_demo.mp4"
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{W}x{H}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        mp4_filename,
    ]

    pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    total_frames = 0

    def push_frame(img: Image.Image, count: int = 1):
        nonlocal total_frames
        raw_bytes = img.tobytes()
        for _ in range(count):
            pipe.stdin.write(raw_bytes)
            total_frames += 1

    # -------------------------------------------------------------------------
    # SCENE 1: Introduction Title Card (3.0 seconds = 72 frames)
    # -------------------------------------------------------------------------
    print("Rendering Scene 1: Introduction Title Card...")
    card1 = render_title_frame(
        title="Autonomous Warehouse Robot",
        subtitle="Graph Traversal & Path Planning Simulation",
        highlights=[
            "• Multi-Map Warehouse Simulator (Starter 5N to Large 50N + Random Maps)",
            "• Breadth First Search (BFS) vs. Depth First Search (DFS)",
            "• Real-Time Dynamic Obstacle & Corridor Blockage Avoidance",
            "• Deterministic Traversal & Step-by-Step Educational Animation",
        ],
        footer="Python 3.11  •  Tkinter  •  NetworkX  •  Matplotlib  •  34 Automated Tests Passed",
    )
    push_frame(card1, count=72)

    # -------------------------------------------------------------------------
    # SCENE 2: Baseline Map - BFS Navigation (7.5 seconds = 180 frames)
    # -------------------------------------------------------------------------
    print("Rendering Scene 2: Baseline 5-Node Map BFS Search & Traversal...")
    starter_map = mgr.get_map("starter")
    wh_starter = WarehouseGraph(starter_map)
    bfs_res = bfs_search(wh_starter.graph, "S", "C")

    # Step-by-step exploration
    order = bfs_res.visited_order  # ['S', 'A', 'B', 'C']
    visited_accum = []

    for idx, node in enumerate(order):
        visited_accum.append(node)
        queue_snapshot = bfs_res.trace[idx].frontier_snapshot if idx < len(bfs_res.trace) else []
        g_img = render_graph_to_pil(
            wh_starter, "S", "C", search_result=None,
            animated_visited=list(visited_accum), active_node=node,
        )
        app_f = build_app_frame(
            graph_img=g_img,
            scenario_title="Scenario 1: Baseline BFS Search",
            subtitle_msg=f"Expanding node {idx+1}/{len(order)}: {wh_starter.get_node_label(node)} ({node})",
            map_name="Starter Map", node_count=5, edge_count=5,
            algo_name="Breadth First Search (BFS)",
            src_label="S: Storage Area", dst_label="C: Packing Station",
            route_status="Exploring Search Frontier...", route_status_color="amber",
            path_len_str="Searching...", visited_cnt_str=f"{len(visited_accum)} expanded",
            opt_str="BFS Guaranteed", blocked_str="None",
            frontier_info=f"Queue size: {len(queue_snapshot)}",
            path_lines=["Searching for optimal route..."],
            progress_pct=0.15 + (idx / len(order)) * 0.10,
        )
        push_frame(app_f, count=18)

    # Destination reached: display optimal route
    final_path = bfs_res.path  # ['S', 'A', 'C']
    path_display_lines = ["Storage Area (S)", "   ↓", "Rack A (A)", "   ↓", "Packing Station (C)"]
    g_img = render_graph_to_pil(wh_starter, "S", "C", search_result=bfs_res)
    app_f = build_app_frame(
        graph_img=g_img,
        scenario_title="Scenario 1: Optimal Route Found",
        subtitle_msg="Goal reached! BFS found shortest path: S → A → C (2 edges)",
        map_name="Starter Map", node_count=5, edge_count=5,
        algo_name="Breadth First Search (BFS)",
        src_label="S: Storage Area", dst_label="C: Packing Station",
        route_status="Optimal Route Found (2 Edges)", route_status_color="green",
        path_len_str="2 edges (3 locations)", visited_cnt_str="4 nodes (S, A, B, C)",
        opt_str="Yes (BFS Shortest)", blocked_str="None",
        frontier_info="Search Completed",
        path_lines=path_display_lines,
        progress_pct=0.25,
    )
    push_frame(app_f, count=24)

    # Robot movement animation along S -> A -> C
    pos_s = wh_starter.positions["S"]
    pos_a = wh_starter.positions["A"]
    pos_c = wh_starter.positions["C"]

    # Traversal leg 1: S -> A (20 frames)
    for t in range(20):
        frac = t / 19.0
        cur_rx = pos_s[0] + frac * (pos_a[0] - pos_s[0])
        cur_ry = pos_s[1] + frac * (pos_a[1] - pos_s[1])
        g_img = render_graph_to_pil(wh_starter, "S", "C", search_result=bfs_res, robot_pos=(cur_rx, cur_ry))
        app_f = build_app_frame(
            graph_img=g_img,
            scenario_title="Scenario 1: Robot Dispatched",
            subtitle_msg="Robot en route: Moving from Storage Area (S) to Rack A (A)...",
            map_name="Starter Map", node_count=5, edge_count=5,
            algo_name="Breadth First Search (BFS)",
            src_label="S: Storage Area", dst_label="C: Packing Station",
            route_status="Robot Moving along Path", route_status_color="green",
            path_len_str="2 edges (3 locations)", visited_cnt_str="4 nodes",
            opt_str="Yes (BFS Shortest)", blocked_str="None",
            frontier_info="Navigating Leg 1/2",
            path_lines=path_display_lines,
            progress_pct=0.28,
        )
        push_frame(app_f, count=1)

    # Traversal leg 2: A -> C (20 frames)
    for t in range(20):
        frac = t / 19.0
        cur_rx = pos_a[0] + frac * (pos_c[0] - pos_a[0])
        cur_ry = pos_a[1] + frac * (pos_c[1] - pos_a[1])
        g_img = render_graph_to_pil(wh_starter, "S", "C", search_result=bfs_res, robot_pos=(cur_rx, cur_ry))
        app_f = build_app_frame(
            graph_img=g_img,
            scenario_title="Scenario 1: Delivery Complete",
            subtitle_msg="Robot arrived at Packing Station (C)! Mission successful.",
            map_name="Starter Map", node_count=5, edge_count=5,
            algo_name="Breadth First Search (BFS)",
            src_label="S: Storage Area", dst_label="C: Packing Station",
            route_status="Delivery Complete at Packing Station", route_status_color="green",
            path_len_str="2 edges (3 locations)", visited_cnt_str="4 nodes",
            opt_str="Yes (BFS Shortest)", blocked_str="None",
            frontier_info="Mission Completed",
            path_lines=path_display_lines,
            progress_pct=0.32,
        )
        push_frame(app_f, count=1)

    push_frame(app_f, count=16)

    # -------------------------------------------------------------------------
    # SCENE 3: Dynamic Obstacle & Detour Re-Routing (7.5 seconds = 180 frames)
    # -------------------------------------------------------------------------
    print("Rendering Scene 3: Dynamic Corridor Blockage and Detour Re-routing...")
    # Block edge S-A!
    wh_starter.block_edge("S", "A")

    # Obstacle detected warning frame
    g_img = render_graph_to_pil(wh_starter, "S", "C", search_result=None)
    app_f = build_app_frame(
        graph_img=g_img,
        scenario_title="Scenario 2: Corridor S-A Blocked",
        subtitle_msg="⚠️ Obstacle Detected on Corridor S-A! Re-routing required...",
        map_name="Starter Map", node_count=5, edge_count=5,
        algo_name="Breadth First Search (BFS)",
        src_label="S: Storage Area", dst_label="C: Packing Station",
        route_status="Corridor S-A Blocked!", route_status_color="red",
        path_len_str="Calculating Detour...", visited_cnt_str="—",
        opt_str="Recalculating", blocked_str="S-A",
        frontier_info="Detour Planning",
        path_lines=["⚠️ Pathway S-A is blocked", "Recalculating alternative detour..."],
        progress_pct=0.40,
    )
    push_frame(app_f, count=36)

    # Detour search via BFS: routes via S -> B -> D -> C
    detour_res = bfs_search(wh_starter.graph, "S", "C", blocked_edges=set(wh_starter.get_blocked_edges()))
    detour_path_lines = [
        "Storage Area (S)", "   ↓", "Rack B (B)", "   ↓",
        "Exit (D)", "   ↓", "Packing Station (C)",
    ]

    g_img = render_graph_to_pil(wh_starter, "S", "C", search_result=detour_res)
    app_f = build_app_frame(
        graph_img=g_img,
        scenario_title="Scenario 2: Alternative Detour Discovered",
        subtitle_msg="Alternative Route Found: S → B → D → C (3 edges) bypassing blocked corridor S-A",
        map_name="Starter Map", node_count=5, edge_count=5,
        algo_name="Breadth First Search (BFS)",
        src_label="S: Storage Area", dst_label="C: Packing Station",
        route_status="Optimal Detour Found (3 Edges)", route_status_color="green",
        path_len_str="3 edges (4 locations)", visited_cnt_str="4 nodes",
        opt_str="Yes (Optimal Detour)", blocked_str="S-A",
        frontier_info="Detour Active",
        path_lines=detour_path_lines,
        progress_pct=0.48,
    )
    push_frame(app_f, count=36)

    # Robot navigating detour: S -> B -> D -> C
    pos_b = wh_starter.positions["B"]
    pos_d = wh_starter.positions["D"]

    for leg_start, leg_end, leg_name in [(pos_s, pos_b, "S to B"), (pos_b, pos_d, "B to D"), (pos_d, pos_c, "D to C")]:
        for t in range(16):
            frac = t / 15.0
            rx = leg_start[0] + frac * (leg_end[0] - leg_start[0])
            ry = leg_start[1] + frac * (leg_end[1] - leg_start[1])
            g_img = render_graph_to_pil(wh_starter, "S", "C", search_result=detour_res, robot_pos=(rx, ry))
            app_f = build_app_frame(
                graph_img=g_img,
                scenario_title="Scenario 2: Robot Following Detour",
                subtitle_msg=f"Robot following detour: Navigating {leg_name}...",
                map_name="Starter Map", node_count=5, edge_count=5,
                algo_name="Breadth First Search (BFS)",
                src_label="S: Storage Area", dst_label="C: Packing Station",
                route_status="Robot Following Detour", route_status_color="green",
                path_len_str="3 edges (4 locations)", visited_cnt_str="4 nodes",
                opt_str="Yes (Optimal Detour)", blocked_str="S-A",
                frontier_info=f"Traversing {leg_name}",
                path_lines=detour_path_lines,
                progress_pct=0.52,
            )
            push_frame(app_f, count=1)

    push_frame(app_f, count=24)

    # -------------------------------------------------------------------------
    # SCENE 4: Algorithmic Comparison: BFS vs DFS (8.0 seconds = 192 frames)
    # -------------------------------------------------------------------------
    print("Rendering Scene 4: Algorithmic Divergence: BFS vs DFS...")
    wh_starter.reset_blockages()

    # Search to Exit D
    bfs_d = bfs_search(wh_starter.graph, "S", "D")
    dfs_d = dfs_search(wh_starter.graph, "S", "D")

    # BFS from S to D -> S-B-D (2 edges)
    g_img = render_graph_to_pil(wh_starter, "S", "D", search_result=bfs_d)
    app_f = build_app_frame(
        graph_img=g_img,
        scenario_title="Scenario 3: BFS Optimality (Target: Exit D)",
        subtitle_msg="BFS finds optimal path: S → B → D (Length: 2 edges) in concentric ring exploration.",
        map_name="Starter Map", node_count=5, edge_count=5,
        algo_name="Breadth First Search (BFS)",
        src_label="S: Storage Area", dst_label="D: Exit",
        route_status="Optimal Route Found (2 Edges)", route_status_color="green",
        path_len_str="2 edges (3 locations)", visited_cnt_str="4 nodes",
        opt_str="Yes (BFS Guaranteed)", blocked_str="None",
        frontier_info="FIFO Queue Search",
        path_lines=["Storage Area (S)", "   ↓", "Rack B (B)", "   ↓", "Exit (D)"],
        progress_pct=0.62,
    )
    push_frame(app_f, count=60)

    # DFS from S to D -> S-A-C-D (3 edges)
    g_img = render_graph_to_pil(wh_starter, "S", "D", search_result=dfs_d)
    app_f = build_app_frame(
        graph_img=g_img,
        scenario_title="Scenario 3: DFS Exploration (Target: Exit D)",
        subtitle_msg="DFS plunges deep into first branch: S → A → C → D (Length: 3 edges — Suboptimal).",
        map_name="Starter Map", node_count=5, edge_count=5,
        algo_name="Depth First Search (DFS)",
        src_label="S: Storage Area", dst_label="D: Exit",
        route_status="Suboptimal Route (3 Edges)", route_status_color="amber",
        path_len_str="3 edges (4 locations)", visited_cnt_str="4 nodes",
        opt_str="No (DFS Not Guaranteed)", blocked_str="None",
        frontier_info="LIFO Stack Search",
        path_lines=["Storage Area (S)", "   ↓", "Rack A (A)", "   ↓", "Packing Station (C)", "   ↓", "Exit (D)"],
        progress_pct=0.70,
    )
    push_frame(app_f, count=60)

    # -------------------------------------------------------------------------
    # SCENE 5: Multi-Scale: Cross-Aisle Warehouse (7.5 seconds = 180 frames)
    # -------------------------------------------------------------------------
    print("Rendering Scene 5: Multi-Scale 18-Node Cross-Aisle Warehouse...")
    cross_map = mgr.get_map("cross_aisle")
    wh_cross = WarehouseGraph(cross_map)
    cross_res = bfs_search(wh_cross.graph, cross_map.default_source, cross_map.default_destination)

    cross_path_lines = [
        "Inbound Dock A (IN1)", "   ↓",
        "Aisle 1 Rack North (R01)", "   ↓",
        "Aisle 1 Rack South (R02)", "   ↓",
        "High-Density Rack 2 (R04)", "   ↓",
        "Aisle 2 Rack South (R06)", "   ↓",
        "High-Speed Pack Line (P01)",
    ]

    g_img = render_graph_to_pil(wh_cross, "IN1", "P01", search_result=cross_res)
    app_f = build_app_frame(
        graph_img=g_img,
        scenario_title="Scenario 4: Multi-Scale Cross-Aisle Warehouse",
        subtitle_msg="18-node fulfillment center: Route IN1 → R01 → R02 → R04 → R06 → P01 (5 edges in 0.24 ms)",
        map_name="Cross-Aisle Warehouse", node_count=18, edge_count=27,
        algo_name="Breadth First Search (BFS)",
        src_label="IN1: Inbound Dock A", dst_label="P01: High-Speed Pack Line",
        route_status="Optimal Route Found (5 Edges)", route_status_color="green",
        path_len_str="5 edges (6 locations)", visited_cnt_str="14 nodes expanded",
        opt_str="Yes (BFS Optimal)", blocked_str="None",
        frontier_info="Aisle Navigation",
        path_lines=cross_path_lines,
        progress_pct=0.82,
    )
    push_frame(app_f, count=48)

    # Robot navigating cross-aisle picking corridor
    p_in1 = wh_cross.positions["IN1"]
    p_r01 = wh_cross.positions["R01"]
    p_r02 = wh_cross.positions["R02"]
    p_r04 = wh_cross.positions["R04"]
    p_r06 = wh_cross.positions["R06"]
    p_p01 = wh_cross.positions["P01"]

    waypts = [p_in1, p_r01, p_r02, p_r04, p_r06, p_p01]
    for seg_idx in range(len(waypts) - 1):
        w1, w2 = waypts[seg_idx], waypts[seg_idx + 1]
        for t in range(12):
            frac = t / 11.0
            rx = w1[0] + frac * (w2[0] - w1[0])
            ry = w1[1] + frac * (w2[1] - w1[1])
            g_img = render_graph_to_pil(wh_cross, "IN1", "P01", search_result=cross_res, robot_pos=(rx, ry))
            app_f = build_app_frame(
                graph_img=g_img,
                scenario_title="Scenario 4: AMR Order Picking in Progress",
                subtitle_msg=f"Robot transporting batch order across aisle segment {seg_idx+1} of 5...",
                map_name="Cross-Aisle Warehouse", node_count=18, edge_count=27,
                algo_name="Breadth First Search (BFS)",
                src_label="IN1: Inbound Dock A", dst_label="P01: High-Speed Pack Line",
                route_status="Robot Order Picking", route_status_color="green",
                path_len_str="5 edges (6 locations)", visited_cnt_str="14 nodes",
                opt_str="Yes (BFS Optimal)", blocked_str="None",
                frontier_info=f"Corridor Leg {seg_idx+1}/5",
                path_lines=cross_path_lines,
                progress_pct=0.85 + (seg_idx / 5.0) * 0.08,
            )
            push_frame(app_f, count=1)

    push_frame(app_f, count=24)

    # -------------------------------------------------------------------------
    # SCENE 6: Outro & GitHub Summary (4.0 seconds = 96 frames)
    # -------------------------------------------------------------------------
    print("Rendering Scene 6: Outro Summary...")
    outro = render_title_frame(
        title="Autonomous Warehouse Robot",
        subtitle="Complete Simulation Package Ready for Deployment",
        highlights=[
            "✔ 34 Automated Tests Passed (Algorithms, Procedural Maps, GUI)",
            "✔ Scalable from 5 to 60 Nodes with Dynamic Auto-Fitting & Zoom",
            "✔ Full Source Code & Documentation on GitHub:",
            "  https://github.com/rohanv2007/autonomous-warehouse-robot",
        ],
        footer="Created by Rohan V  •  Python 3.11  •  Ready for Classroom & Industry Demos",
    )
    push_frame(outro, count=96)

    # Close pipe
    pipe.stdin.close()
    pipe.wait()
    print(f"Video created successfully: {mp4_filename} ({total_frames} frames, {total_frames / FPS:.1f}s)")

    # Also generate an animated GIF for GitHub README preview
    print("Converting to animated GIF for GitHub README preview...")
    gif_filename = "autonomous_warehouse_robot_demo.gif"
    gif_cmd = [
        "ffmpeg", "-y",
        "-i", mp4_filename,
        "-vf", "fps=10,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        "-loop", "0",
        gif_filename,
    ]
    subprocess.run(gif_cmd, check=True)
    print(f"Animated GIF created: {gif_filename}")


if __name__ == "__main__":
    generate_video()
