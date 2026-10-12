"""Random Warehouse Map Generator Module.

Generates realistic, connected, grid- and aisle-aligned warehouse maps
with customizable or randomized node counts (8 to 60) and full seed reproducibility.
"""

from __future__ import annotations
import math
import random
from typing import Dict, List, Optional, Set, Tuple, Union
import networkx as nx

from map_manager import WarehouseMap
from warehouse_graph import canonical_edge


class RandomMapGenerator:
    """Generates procedurally connected warehouse maps structured around aisles."""

    @staticmethod
    def generate(
        node_count: Optional[int] = None,
        seed: Optional[Union[int, str]] = None,
        map_name: Optional[str] = None,
    ) -> Tuple[WarehouseMap, int]:
        """Generate a reproducible, connected warehouse map.

        Args:
            node_count: Desired node count between 8 and 60. If None, chosen randomly.
            seed: Seed value for reproducibility (int or string). If None, random seed is used.
            map_name: Optional custom map display name.

        Returns:
            Tuple of (WarehouseMap, actual_seed_integer_used).
        """
        # Resolve integer seed
        if seed is None or str(seed).strip() == "":
            actual_seed = random.randint(1000, 999999)
        elif isinstance(seed, str):
            try:
                actual_seed = int(seed.strip())
            except ValueError:
                actual_seed = abs(hash(seed.strip())) % (2**31 - 1)
        else:
            actual_seed = int(seed)

        rng = random.Random(actual_seed)

        # Resolve node count
        if node_count is None:
            target_n = rng.randint(10, 45)
        else:
            target_n = max(8, min(60, int(node_count)))

        # Determine grid dimensions (cols C, rows R) to form realistic aisles
        # Provide extra grid capacity so different seeds generate distinct layout clusters
        rows = max(3, min(6, int(round(math.sqrt(target_n * 0.65)))))
        cols = max(math.ceil(target_n / rows) + 1, math.ceil((target_n * 1.35) / rows))

        # Generate a connected subset of grid coordinates
        # Start at center and grow outward using a breadth-first expansion
        all_coords: List[Tuple[int, int]] = []
        for c in range(cols):
            for r in range(rows):
                all_coords.append((c, r))

        # We select target_n coordinates that are guaranteed to form a connected grid subgraph
        selected_coords: Set[Tuple[int, int]] = set()
        start_coord = (0, rows // 2)
        selected_coords.add(start_coord)
        frontier = [start_coord]

        while len(selected_coords) < target_n and frontier:
            curr = rng.choice(frontier)
            c, r = curr
            neighbors = []
            for dc, dr in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nc, nr = c + dc, r + dr
                if 0 <= nc < cols and 0 <= nr < rows and (nc, nr) not in selected_coords:
                    neighbors.append((nc, nr))

            if neighbors:
                next_c = rng.choice(neighbors)
                selected_coords.add(next_c)
                frontier.append(next_c)
            else:
                frontier.remove(curr)

        # Fallback if frontier exhausted early: fill in sorted proximity
        if len(selected_coords) < target_n:
            for c, r in all_coords:
                if (c, r) not in selected_coords:
                    selected_coords.add((c, r))
                    if len(selected_coords) >= target_n:
                        break

        sorted_coords = sorted(list(selected_coords), key=lambda pt: (pt[0], pt[1]))

        # Assign node IDs, facility types, and readable labels
        nodes: Dict[str, Dict[str, str]] = {}
        positions: Dict[str, Tuple[float, float]] = {}
        coord_to_id: Dict[Tuple[int, int], str] = {}

        min_c = min(pt[0] for pt in sorted_coords)
        max_c = max(pt[0] for pt in sorted_coords)
        column_x = {}
        current_x = 1.0
        for c in range(cols):
            column_x[c] = current_x
            current_x += rng.uniform(1.05, 1.45)
        row_y = {r: 0.9 + r * 1.15 + rng.uniform(-0.12, 0.12) for r in range(rows)}

        storage_count = 0
        rack_count = 0
        intersection_count = 0
        packing_count = 0
        exit_count = 0
        charging_count = 0

        for i, (c, r) in enumerate(sorted_coords, start=1):
            x = round(column_x[c] + rng.uniform(-0.10, 0.10), 2)
            y = round(row_y[r] + rng.uniform(-0.08, 0.08), 2)

            # Determine facility type based on warehouse logistics zones
            if c == min_c:
                storage_count += 1
                node_id = f"S{storage_count}"
                label = f"Inbound Storage {storage_count}"
                ntype = "Storage"
            elif c == max_c:
                if r == rows - 1 and charging_count == 0:
                    charging_count += 1
                    node_id = f"CH{charging_count}"
                    label = f"Charging Dock {charging_count}"
                    ntype = "Charging Station"
                elif r % 2 == 1:
                    packing_count += 1
                    node_id = f"P{packing_count}"
                    label = f"Packing Station {packing_count}"
                    ntype = "Packing Station"
                else:
                    exit_count += 1
                    node_id = f"D{exit_count}"
                    label = f"Dispatch Exit {exit_count}"
                    ntype = "Exit"
            elif r == 0 or r == rows - 1:
                intersection_count += 1
                node_id = f"X{intersection_count:02d}"
                label = f"Aisle Crossway {c}-{r}"
                ntype = "Intersection"
            else:
                rack_count += 1
                node_id = f"R{rack_count:02d}"
                label = f"Storage Rack C{c}R{r}"
                ntype = "Rack"

            coord_to_id[(c, r)] = node_id
            nodes[node_id] = {
                "label": label,
                "type": ntype,
                "short_label": label.replace("Storage ", "").replace("Inbound ", ""),
            }
            positions[node_id] = (x, y)

        # Build grid-aligned pathways
        edges_set: Set[Tuple[str, str]] = set()

        for c, r in sorted_coords:
            u_id = coord_to_id[(c, r)]
            # Horizontal connection
            if (c + 1, r) in coord_to_id:
                v_id = coord_to_id[(c + 1, r)]
                edges_set.add(canonical_edge(u_id, v_id))
            # Vertical connection
            if (c, r + 1) in coord_to_id:
                v_id = coord_to_id[(c, r + 1)]
                edges_set.add(canonical_edge(u_id, v_id))

            # Add occasional express links so generated maps do not all look
            # like the same plain lattice while keeping the warehouse geometry.
            if (c + 2, r) in coord_to_id and rng.random() < 0.22:
                edges_set.add(canonical_edge(u_id, coord_to_id[(c + 2, r)]))
            if (c, r + 2) in coord_to_id and rng.random() < 0.12:
                edges_set.add(canonical_edge(u_id, coord_to_id[(c, r + 2)]))

        # Build temporary NetworkX graph to guarantee connectivity
        G = nx.Graph()
        for nid in nodes:
            G.add_node(nid)
        for u, v in edges_set:
            G.add_edge(u, v)

        # If not connected, connect components by adding closest aisle segments
        if not nx.is_connected(G):
            components = list(nx.connected_components(G))
            while len(components) > 1:
                comp_a = list(components[0])
                comp_b = list(components[1])
                # Find pair with minimum Euclidean distance
                best_pair = None
                best_dist = float("inf")
                for u in comp_a:
                    for v in comp_b:
                        pu, pv = positions[u], positions[v]
                        dist = math.hypot(pu[0] - pv[0], pu[1] - pv[1])
                        if dist < best_dist:
                            best_dist = dist
                            best_pair = (u, v)

                if best_pair:
                    edge = canonical_edge(best_pair[0], best_pair[1])
                    edges_set.add(edge)
                    G.add_edge(edge[0], edge[1])

                components = list(nx.connected_components(G))

        # Final edge list sorted canonically
        edges = sorted(list(edges_set))

        # Select meaningful default source and destination
        # Choose a Storage node as source, and Packing or Exit node as destination
        storage_nodes = [nid for nid, d in nodes.items() if d["type"] == "Storage"]
        dest_candidates = [
            nid for nid, d in nodes.items() if d["type"] in ("Packing Station", "Exit")
        ]

        if storage_nodes:
            default_source = storage_nodes[0]
        else:
            default_source = sorted_coords[0]
            default_source = coord_to_id[default_source]

        if dest_candidates:
            default_dest = dest_candidates[0]
        else:
            default_dest = sorted_coords[-1]
            default_dest = coord_to_id[default_dest]

        if default_source == default_dest and len(nodes) > 1:
            all_ids = list(nodes.keys())
            default_dest = all_ids[-1] if all_ids[0] == default_source else all_ids[0]

        name = map_name or f"Random Warehouse ({len(nodes)} nodes)"

        generated_map = WarehouseMap(
            key=f"random_{actual_seed}",
            name=name,
            node_count_label=f"{len(nodes)} nodes",
            description=f"Procedurally generated connected warehouse with seed {actual_seed} and {len(edges)} pathways.",
            nodes=nodes,
            edges=edges,
            positions=positions,
            default_source=default_source,
            default_destination=default_dest,
        )

        return generated_map, actual_seed
