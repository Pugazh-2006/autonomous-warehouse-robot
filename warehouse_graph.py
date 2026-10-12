"""Warehouse Graph Module for Autonomous Warehouse Robot.

This module models the warehouse layout as an undirected graph using NetworkX.
It stores node metadata (labels, types), fixed geometric positions, and
manages blocked and active pathways across any selected warehouse map.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple, Any
import networkx as nx

from map_manager import WarehouseMap, _build_starter_map


def canonical_edge(u: str, v: str) -> Tuple[str, str]:
    """Return a canonical sorted tuple representation of an undirected edge.

    Args:
        u: First node identifier.
        v: Second node identifier.

    Returns:
        A 2-tuple with node IDs sorted alphabetically.
    """
    return (u, v) if u <= v else (v, u)


class WarehouseGraph:
    """Manages the warehouse topology, node metadata, and pathway blockages.

    Attributes:
        graph: Underlying NetworkX undirected Graph.
        positions: Fixed 2D coordinates for rendering each node.
        blocked_edges: Set of canonical edge tuples that are currently blocked.
        current_map: Currently loaded WarehouseMap metadata.
    """

    DEFAULT_NODES: Dict[str, Dict[str, str]] = {
        "S": {"label": "Storage Area", "type": "Storage"},
        "A": {"label": "Rack A", "type": "Rack"},
        "B": {"label": "Rack B", "type": "Rack"},
        "C": {"label": "Packing Station", "type": "Packing Station"},
        "D": {"label": "Exit", "type": "Exit"},
    }

    DEFAULT_EDGES: List[Tuple[str, str]] = [
        ("S", "A"),
        ("S", "B"),
        ("A", "C"),
        ("B", "D"),
        ("C", "D"),
    ]

    # Fixed 2D planar coordinates for baseline warehouse schematic
    DEFAULT_POSITIONS: Dict[str, Tuple[float, float]] = {
        "S": (1.0, 2.0),
        "A": (3.0, 3.1),
        "B": (3.0, 0.9),
        "C": (5.0, 3.1),
        "D": (5.0, 0.9),
    }

    def __init__(self, warehouse_map: Optional[WarehouseMap] = None) -> None:
        """Initialize the warehouse graph with default or provided map.

        Args:
            warehouse_map: Optional WarehouseMap to load upon initialization.
        """
        self.graph: nx.Graph = nx.Graph()
        self.positions: Dict[str, Tuple[float, float]] = dict(self.DEFAULT_POSITIONS)
        self.blocked_edges: Set[Tuple[str, str]] = set()
        self.current_map: WarehouseMap = warehouse_map or _build_starter_map()

        if warehouse_map is not None:
            self.load_map(warehouse_map)
        else:
            self.load_default_warehouse()

    def load_map(self, warehouse_map: WarehouseMap) -> None:
        """Load an arbitrary warehouse map definition.

        Args:
            warehouse_map: The WarehouseMap specification to populate into graph.
        """
        self.current_map = warehouse_map
        self.graph.clear()
        self.blocked_edges.clear()
        self.positions = dict(warehouse_map.positions)

        # Add nodes with metadata
        for node_id, data in warehouse_map.nodes.items():
            pos = self.positions.get(node_id, (0.0, 0.0))
            self.graph.add_node(
                node_id,
                label=data["label"],
                type=data["type"],
                pos=pos,
            )

        # Add undirected edges
        for u, v in warehouse_map.edges:
            self.graph.add_edge(u, v)

    def load_default_warehouse(self) -> None:
        """Populate the graph with the baseline 5-node Starter Map."""
        starter = _build_starter_map()
        self.load_map(starter)

    def block_edge(self, u: str, v: str) -> bool:
        """Mark a pathway between u and v as blocked.

        Args:
            u: First endpoint.
            v: Second endpoint.

        Returns:
            True if edge exists and is newly blocked, False otherwise.
        """
        edge = canonical_edge(u, v)
        if self.graph.has_edge(edge[0], edge[1]):
            self.blocked_edges.add(edge)
            return True
        return False

    def unblock_edge(self, u: str, v: str) -> bool:
        """Unblock a pathway between u and v.

        Args:
            u: First endpoint.
            v: Second endpoint.

        Returns:
            True if edge was previously blocked and is now unblocked.
        """
        edge = canonical_edge(u, v)
        if edge in self.blocked_edges:
            self.blocked_edges.remove(edge)
            return True
        return False

    def toggle_edge_block(self, u: str, v: str) -> bool:
        """Toggle the blocked state of a pathway.

        Args:
            u: First endpoint.
            v: Second endpoint.

        Returns:
            The new blocked status (True if now blocked, False if unblocked).
        """
        edge = canonical_edge(u, v)
        if edge in self.blocked_edges:
            self.blocked_edges.remove(edge)
            return False
        else:
            if self.graph.has_edge(edge[0], edge[1]):
                self.blocked_edges.add(edge)
                return True
            return False

    def is_edge_blocked(self, u: str, v: str) -> bool:
        """Check if an edge is currently blocked.

        Args:
            u: First endpoint.
            v: Second endpoint.

        Returns:
            True if pathway is blocked, False otherwise.
        """
        return canonical_edge(u, v) in self.blocked_edges

    def get_all_edges(self) -> List[Tuple[str, str]]:
        """Return all edges in deterministic canonical order."""
        edges = [canonical_edge(u, v) for u, v in self.graph.edges()]
        return sorted(list(set(edges)))

    def get_blocked_edges(self) -> List[Tuple[str, str]]:
        """Return list of currently blocked canonical edges in sorted order."""
        return sorted(list(self.blocked_edges))

    def get_active_edges(self) -> List[Tuple[str, str]]:
        """Return list of unblocked canonical edges in sorted order."""
        return [edge for edge in self.get_all_edges() if edge not in self.blocked_edges]

    def get_active_neighbors(self, node: str) -> List[str]:
        """Return active (unblocked) neighbors of a node in deterministic order.

        Args:
            node: The node identifier.

        Returns:
            Sorted list of neighbor node IDs reachable without traversing blocked edges.
        """
        if node not in self.graph:
            return []
        active = []
        for nbr in self.graph.neighbors(node):
            if not self.is_edge_blocked(node, nbr):
                active.append(nbr)
        return sorted(active)

    def get_node_label(self, node: str) -> str:
        """Return the friendly label for a node, or the node ID if not found."""
        if node in self.graph.nodes:
            return self.graph.nodes[node].get("label", node)
        return node

    def get_node_type(self, node: str) -> str:
        """Return the warehouse type for a node, or 'Unknown'."""
        if node in self.graph.nodes:
            return self.graph.nodes[node].get("type", "Unknown")
        return "Unknown"

    def get_node_display(self, node: str) -> str:
        """Return a formatted string such as 'S: Storage Area'."""
        label = self.get_node_label(node)
        return f"{node}: {label}"

    def get_node_ids(self) -> List[str]:
        """Return sorted list of all node identifiers."""
        return sorted(list(self.graph.nodes.keys()))

    def reset_blockages(self) -> None:
        """Clear all pathway blockages without modifying graph topology."""
        self.blocked_edges.clear()

    def get_node_count(self) -> int:
        """Return total number of nodes in graph."""
        return self.graph.number_of_nodes()

    def get_edge_count(self) -> int:
        """Return total number of edges in graph."""
        return self.graph.number_of_edges()

    def get_map_name(self) -> str:
        """Return friendly name of current map."""
        return self.current_map.name
