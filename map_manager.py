"""Map Manager Module for Autonomous Warehouse Robot.

Defines the WarehouseMap data structure and provides predefined realistic
warehouse maps of various scales (Starter 5 nodes, Compact 12 nodes,
Cross-Aisle 18 nodes, Medium 28 nodes, Large 50 nodes).
"""

from __future__ import annotations
from dataclasses import dataclass, field
import random
from typing import Dict, List, Optional, Tuple


@dataclass
class WarehouseMap:
    """Encapsulates a complete warehouse map specification."""

    key: str
    name: str
    node_count_label: str
    description: str
    nodes: Dict[str, Dict[str, str]]  # node_id -> {"label": str, "type": str}
    edges: List[Tuple[str, str]]
    positions: Dict[str, Tuple[float, float]]
    default_source: str
    default_destination: str

    @property
    def node_count(self) -> int:
        """Return total number of nodes in map."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Return total number of pathways in map."""
        return len(self.edges)


def _build_starter_map() -> WarehouseMap:
    """Build the baseline 5-node Starter Map."""
    nodes = {
        "S": {"label": "Storage Area", "type": "Storage"},
        "A": {"label": "Rack A", "type": "Rack"},
        "B": {"label": "Rack B", "type": "Rack"},
        "C": {"label": "Packing Station", "type": "Packing Station"},
        "D": {"label": "Exit", "type": "Exit"},
    }
    edges = [
        ("S", "A"),
        ("S", "B"),
        ("A", "C"),
        ("B", "D"),
        ("C", "D"),
    ]
    positions = {
        "S": (1.0, 2.0),
        "A": (3.0, 3.1),
        "B": (3.0, 0.9),
        "C": (5.0, 3.1),
        "D": (5.0, 0.9),
    }
    return WarehouseMap(
        key="starter",
        name="Starter Map",
        node_count_label="5 nodes",
        description="Classic 5-node educational layout connecting Storage Area to Packing Station and Exit.",
        nodes=nodes,
        edges=edges,
        positions=positions,
        default_source="S",
        default_destination="C",
    )


def _build_compact_map() -> WarehouseMap:
    """Build the 12-node Compact Warehouse layout."""
    nodes = {
        "S1": {"label": "Inbound Receiving", "type": "Storage"},
        "S2": {"label": "Bulk Staging", "type": "Storage"},
        "X1": {"label": "West Junction North", "type": "Intersection"},
        "A1": {"label": "Storage Rack A1", "type": "Rack"},
        "X2": {"label": "West Junction South", "type": "Intersection"},
        "X3": {"label": "East Junction North", "type": "Intersection"},
        "B1": {"label": "Storage Rack B1", "type": "Rack"},
        "X4": {"label": "East Junction South", "type": "Intersection"},
        "CH1": {"label": "Charging Dock", "type": "Charging Station"},
        "P1": {"label": "Main Packing Station", "type": "Packing Station"},
        "D1": {"label": "Outbound Exit 1", "type": "Exit"},
        "D2": {"label": "Secondary Exit", "type": "Exit"},
    }
    positions = {
        "S1": (1.0, 3.0),
        "S2": (1.0, 1.0),
        "X1": (2.6, 3.0),
        "A1": (2.6, 2.0),
        "X2": (2.6, 1.0),
        "X3": (4.4, 3.0),
        "B1": (4.4, 2.0),
        "X4": (4.4, 1.0),
        "CH1": (6.0, 3.0),
        "P1": (6.0, 2.0),
        "D1": (6.0, 1.0),
        "D2": (4.4, 0.0),
    }
    edges = [
        # Inbound spine
        ("S1", "S2"),
        ("S1", "X1"),
        ("S2", "X2"),
        # West Aisle
        ("X1", "A1"),
        ("A1", "X2"),
        # Cross corridors
        ("X1", "X3"),
        ("A1", "B1"),
        ("X2", "X4"),
        # East Aisle
        ("X3", "B1"),
        ("B1", "X4"),
        # Outbound spine & stations
        ("X3", "CH1"),
        ("B1", "P1"),
        ("X4", "D1"),
        ("CH1", "P1"),
        ("P1", "D1"),
        ("X4", "D2"),
    ]
    return WarehouseMap(
        key="compact",
        name="Compact Warehouse",
        node_count_label="12 nodes",
        description="Dual-aisle facility with inbound storage, picking racks, charging bay, and packing line.",
        nodes=nodes,
        edges=edges,
        positions=positions,
        default_source="S1",
        default_destination="P1",
    )


def _build_cross_aisle_map() -> WarehouseMap:
    """Build the 18-node Cross-Aisle Warehouse layout."""
    nodes = {
        # Column 1: Receiving
        "IN1": {"label": "Inbound Dock A", "type": "Storage"},
        "IN2": {"label": "Inbound Dock B", "type": "Storage"},
        # Column 2: West Rack Bay
        "X01": {"label": "North-West Intersection", "type": "Intersection"},
        "R01": {"label": "Aisle 1 Rack North", "type": "Rack"},
        "R02": {"label": "Aisle 1 Rack South", "type": "Rack"},
        "X02": {"label": "South-West Intersection", "type": "Intersection"},
        # Column 3: Central Cross-Aisle Hub
        "X03": {"label": "Central Crossway North", "type": "Intersection"},
        "R03": {"label": "High-Density Rack 1", "type": "Rack"},
        "R04": {"label": "High-Density Rack 2", "type": "Rack"},
        "X04": {"label": "Central Crossway South", "type": "Intersection"},
        # Column 4: East Rack Bay
        "X05": {"label": "North-East Intersection", "type": "Intersection"},
        "R05": {"label": "Aisle 2 Rack North", "type": "Rack"},
        "R06": {"label": "Aisle 2 Rack South", "type": "Rack"},
        "X06": {"label": "South-East Intersection", "type": "Intersection"},
        # Column 5: Operational Utilities
        "CH1": {"label": "Rapid Charging Bay", "type": "Charging Station"},
        "QC1": {"label": "Quality Control Station", "type": "Packing Station"},
        "P01": {"label": "High-Speed Pack Line", "type": "Packing Station"},
        "EX1": {"label": "Dispatch Gate 1", "type": "Exit"},
    }
    positions = {
        "IN1": (1.0, 3.2),
        "IN2": (1.0, 1.2),
        "X01": (2.8, 3.8),
        "R01": (2.8, 2.6),
        "R02": (2.8, 1.8),
        "X02": (2.8, 0.6),
        "X03": (4.6, 3.8),
        "R03": (4.6, 2.6),
        "R04": (4.6, 1.8),
        "X04": (4.6, 0.6),
        "X05": (6.4, 3.8),
        "R05": (6.4, 2.6),
        "R06": (6.4, 1.8),
        "X06": (6.4, 0.6),
        "CH1": (8.0, 3.8),
        "QC1": (8.0, 2.6),
        "P01": (8.0, 1.8),
        "EX1": (8.0, 0.6),
    }
    edges = [
        # Inbound links
        ("IN1", "X01"),
        ("IN1", "R01"),
        ("IN2", "R02"),
        ("IN2", "X02"),
        # West column
        ("X01", "R01"),
        ("R01", "R02"),
        ("R02", "X02"),
        # North arterial highway
        ("X01", "X03"),
        ("X03", "X05"),
        ("X05", "CH1"),
        # Central cross aisle
        ("R01", "R03"),
        ("R03", "R05"),
        ("R05", "QC1"),
        ("R02", "R04"),
        ("R04", "R06"),
        ("R06", "P01"),
        # South arterial highway
        ("X02", "X04"),
        ("X04", "X06"),
        ("X06", "EX1"),
        # Middle column
        ("X03", "R03"),
        ("R03", "R04"),
        ("R04", "X04"),
        # East column
        ("X05", "R05"),
        ("R05", "R06"),
        ("R06", "X06"),
        # Outbound spine
        ("CH1", "QC1"),
        ("QC1", "P01"),
        ("P01", "EX1"),
    ]
    return WarehouseMap(
        key="cross_aisle",
        name="Cross-Aisle Warehouse",
        node_count_label="18 nodes",
        description="Standard fulfillment layout featuring a central cross-aisle dividing picking aisles.",
        nodes=nodes,
        edges=edges,
        positions=positions,
        default_source="IN1",
        default_destination="P01",
    )


def _build_aisle_map(
    key: str,
    name: str,
    node_prefix: str,
    cols: int,
    rows: int,
    seed: int,
    description: str,
    default_source: str,
    default_destination: str,
) -> WarehouseMap:
    """Build a connected warehouse with staggered aisles and varied corridors.

    The previous implementation rendered medium and large maps as perfect grids.
    This keeps the useful aisle structure while adding stable variation to aisle
    spacing, node positions, and cross-corridor connections.
    """
    rng = random.Random(seed)
    nodes: Dict[str, Dict[str, str]] = {}
    positions: Dict[str, Tuple[float, float]] = {}
    edges: List[Tuple[str, str]] = []

    x_values: List[float] = []
    x = 1.0
    for _ in range(cols):
        x_values.append(round(x, 2))
        x += rng.uniform(1.05, 1.45)

    y_values = [round(0.9 + row * 1.05 + rng.uniform(-0.12, 0.12), 2) for row in range(rows)]
    column_wave = {c: rng.uniform(-0.28, 0.28) for c in range(cols)}
    cross_rows = {0, rows // 2, rows - 1}

    for c in range(cols):
        for r in range(rows):
            node_id = f"{node_prefix}{c}{r}"
            x_pos = x_values[c] + rng.uniform(-0.10, 0.10)
            y_pos = y_values[r] + column_wave[c] + rng.uniform(-0.08, 0.08)
            positions[node_id] = (round(x_pos, 2), round(y_pos, 2))

            if c == 0:
                label = f"Inbound Dock {r + 1}"
                ntype = "Storage"
            elif c == cols - 1:
                if r == rows - 1:
                    label, ntype = "Charging Hub", "Charging Station"
                elif r in (rows // 2, max(1, rows // 2 - 1)):
                    label, ntype = f"Packing Hub {r + 1}", "Packing Station"
                else:
                    label, ntype = f"Dispatch Gate {r + 1}", "Exit"
            elif r in cross_rows:
                label, ntype = f"Cross Aisle {c + 1}-{r + 1}", "Intersection"
            else:
                zone = chr(64 + ((c - 1) % 6) + 1)
                label, ntype = f"Rack Zone {zone}{r}", "Rack"

            nodes[node_id] = {
                "label": label,
                "type": ntype,
                "short_label": label.replace("Storage ", "").replace("Inbound ", ""),
            }

    def add_edge(u: str, v: str) -> None:
        edge = tuple(sorted((u, v)))
        if edge not in edges:
            edges.append(edge)

    # Every aisle remains vertically connected.
    for c in range(cols):
        for r in range(rows - 1):
            add_edge(f"{node_prefix}{c}{r}", f"{node_prefix}{c}{r + 1}")

    # Three main cross aisles plus a few varied secondary links.
    for r in sorted(cross_rows):
        for c in range(cols - 1):
            add_edge(f"{node_prefix}{c}{r}", f"{node_prefix}{c + 1}{r}")
    for r in range(rows):
        if r in cross_rows:
            continue
        for c in range(cols - 1):
            if rng.random() < 0.42:
                add_edge(f"{node_prefix}{c}{r}", f"{node_prefix}{c + 1}{r}")

    return WarehouseMap(
        key=key,
        name=name,
        node_count_label=f"{cols * rows} nodes",
        description=description,
        nodes=nodes,
        edges=edges,
        positions=positions,
        default_source=default_source,
        default_destination=default_destination,
    )


def _build_medium_map() -> WarehouseMap:
    """Build a 28-node staggered multi-aisle warehouse."""
    return _build_aisle_map(
        key="medium",
        name="Medium Warehouse",
        node_prefix="M",
        cols=7,
        rows=4,
        seed=731,
        description="Staggered multi-aisle facility with rack zones, cross aisles, charging, and dual dispatch.",
        default_source="M02",
        default_destination="M61",
    )


def _build_large_map() -> WarehouseMap:
    """Build a 50-node large warehouse with varied aisle geometry."""
    return _build_aisle_map(
        key="large",
        name="Large Warehouse",
        node_prefix="N",
        cols=10,
        rows=5,
        seed=1947,
        description="Fulfillment megahub with staggered rack aisles, cross-aisle highways, and operational work cells.",
        default_source="N02",
        default_destination="N92",
    )


class MapManager:
    """Manages map registry, selection, and caching."""

    def __init__(self) -> None:
        """Initialize and register all standard warehouse maps."""
        self._maps: Dict[str, WarehouseMap] = {}
        self._register_default_maps()
        self._current_map_key: str = "starter"

    def _register_default_maps(self) -> None:
        """Instantiate and register baseline maps."""
        starter = _build_starter_map()
        compact = _build_compact_map()
        cross = _build_cross_aisle_map()
        medium = _build_medium_map()
        large = _build_large_map()

        self.register_map(starter)
        self.register_map(compact)
        self.register_map(cross)
        self.register_map(medium)
        self.register_map(large)

    def register_map(self, warehouse_map: WarehouseMap) -> None:
        """Register a new map definition."""
        self._maps[warehouse_map.key] = warehouse_map

    def get_map(self, key: str) -> Optional[WarehouseMap]:
        """Retrieve a map by its key."""
        return self._maps.get(key)

    def get_all_maps(self) -> List[WarehouseMap]:
        """Return list of all registered maps in presentation order."""
        order = ["starter", "compact", "cross_aisle", "medium", "large"]
        result = []
        for key in order:
            if key in self._maps:
                result.append(self._maps[key])
        # Add any custom / random maps
        for key, m in self._maps.items():
            if key not in order:
                result.append(m)
        return result

    def get_current_map(self) -> WarehouseMap:
        """Return the currently selected map."""
        return self._maps.get(self._current_map_key, self._maps["starter"])

    def set_current_map(self, key: str) -> bool:
        """Set current active map key."""
        if key in self._maps:
            self._current_map_key = key
            return True
        return False
