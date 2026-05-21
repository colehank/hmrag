"""TypedHypergraph — the unified memory representation for HiMGA.

Formal 5-tuple definition (§7.1 of claim.md):
    H = (V, E, τ, ω, π)

where:
    V = V^T ∪ V^E ∪ V^F          — Topic, Episode, Fact nodes
    E ⊆ P(V) ∖ {∅, {v}}          — hyperedge set (|e| ≥ 2)
    τ: E → T                      — type mapping (4 types)
    ω: E × V → [0, 1]             — per-node membership weight
    π: V ∪ E → M                  — metadata (t_valid, t_invalid, confidence, source)

Two formal constraints:
    1. Type independence: ∃ e1, e2 s.t. V(e1)=V(e2) ∧ τ(e1)≠τ(e2)
    2. Layer crossing: V(e) may contain nodes from different layers,
       but cross-layer edges must be anchored at a Topic node.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Iterator

from hmrag.graph.hyperedge import TypedHyperedge
from hmrag.graph.nodes import BaseNode, EpisodeNode, FactNode, TopicNode
from hmrag.graph.types import HyperedgeType, NodeLayer


# Confidence score weighting constants (§7.2)
_ALPHA = 0.2   # extraction confidence weight
_BETA = 0.5    # degree-based weight
_GAMMA = 0.3   # time-decay weight
_D_REF = 10.0  # reference degree for normalization
_LAMBDA = 0.01  # time-decay rate (per day)


def _compute_confidence(
    c_extract: float,
    degree: int,
    t_valid: datetime | None,
    t_now: datetime | None = None,
) -> float:
    """Compute composite confidence score c_v = α·c^extract + β·c^degree + γ·c^time.

    Args:
        c_extract:  LLM-reported extraction confidence (unreliable; low weight α=0.2).
        degree:     Number of hyperedges containing this node.
        t_valid:    When the fact was asserted (for time-decay calculation).
        t_now:      Current time reference; defaults to utcnow().
    """
    t_now = t_now or datetime.utcnow()

    c_degree = min(1.0, degree / _D_REF)

    if t_valid is not None:
        delta_days = max(0.0, (t_now - t_valid).total_seconds() / 86400)
        c_time = math.exp(-_LAMBDA * delta_days)
    else:
        c_time = 1.0

    return _ALPHA * c_extract + _BETA * c_degree + _GAMMA * c_time


class TypedHypergraph:
    """The HiMGA typed hypergraph memory store.

    Provides O(1) node/edge lookup and maintains auxiliary indexes for:
        - per-layer node sets
        - per-type edge sets
        - per-node edge adjacency
        - entity → node mappings (for conflict detection)
    """

    def __init__(self) -> None:
        # Core collections
        self._nodes: dict[str, BaseNode] = {}
        self._edges: dict[str, TypedHyperedge] = {}

        # Auxiliary indexes
        self._nodes_by_layer: dict[NodeLayer, set[str]] = defaultdict(set)
        self._edges_by_type: dict[HyperedgeType, set[str]] = defaultdict(set)
        self._node_to_edges: dict[str, set[str]] = defaultdict(set)  # node_id → set[edge_id]

        # Entity index for conflict detection (§3.4): entity_key → set[fact_id]
        # entity_key = f"{subject}::{predicate}" (normalized)
        self._entity_index: dict[str, set[str]] = defaultdict(set)

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def add_node(self, node: BaseNode) -> str:
        """Add a node to the hypergraph; returns node id."""
        self._nodes[node.id] = node
        self._nodes_by_layer[node.layer].add(node.id)
        if isinstance(node, FactNode) and node.subject and node.predicate:
            key = f"{node.subject.lower()}::{node.predicate.lower()}"
            self._entity_index[key].add(node.id)
        return node.id

    def get_node(self, node_id: str) -> BaseNode | None:
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all edges containing it."""
        node = self._nodes.pop(node_id, None)
        if node is None:
            return
        self._nodes_by_layer[node.layer].discard(node_id)
        if isinstance(node, FactNode) and node.subject and node.predicate:
            key = f"{node.subject.lower()}::{node.predicate.lower()}"
            self._entity_index[key].discard(node_id)
        for edge_id in list(self._node_to_edges.get(node_id, [])):
            self.remove_edge(edge_id)
        self._node_to_edges.pop(node_id, None)

    def nodes_by_layer(self, layer: NodeLayer) -> list[BaseNode]:
        return [self._nodes[nid] for nid in self._nodes_by_layer[layer] if nid in self._nodes]

    @property
    def topics(self) -> list[TopicNode]:
        return [n for n in self.nodes_by_layer(NodeLayer.TOPIC) if isinstance(n, TopicNode)]

    @property
    def episodes(self) -> list[EpisodeNode]:
        return [n for n in self.nodes_by_layer(NodeLayer.EPISODE) if isinstance(n, EpisodeNode)]

    @property
    def facts(self) -> list[FactNode]:
        return [n for n in self.nodes_by_layer(NodeLayer.FACT) if isinstance(n, FactNode)]

    # ------------------------------------------------------------------
    # Hyperedge operations
    # ------------------------------------------------------------------

    def add_edge(self, edge: TypedHyperedge) -> str:
        """Add a typed hyperedge; validates constraints and updates indexes."""
        self._validate_edge(edge)
        self._edges[edge.id] = edge
        self._edges_by_type[edge.edge_type].add(edge.id)
        for node_id in edge.node_ids:
            self._node_to_edges[node_id].add(edge.id)
        return edge.id

    def get_edge(self, edge_id: str) -> TypedHyperedge | None:
        return self._edges.get(edge_id)

    def remove_edge(self, edge_id: str) -> None:
        edge = self._edges.pop(edge_id, None)
        if edge is None:
            return
        self._edges_by_type[edge.edge_type].discard(edge_id)
        for node_id in edge.node_ids:
            self._node_to_edges[node_id].discard(edge_id)

    def edges_by_type(self, edge_type: HyperedgeType) -> list[TypedHyperedge]:
        return [self._edges[eid] for eid in self._edges_by_type[edge_type] if eid in self._edges]

    def edges_of_node(self, node_id: str, edge_type: HyperedgeType | None = None) -> list[TypedHyperedge]:
        """Return all hyperedges containing node_id, optionally filtered by type."""
        edge_ids = self._node_to_edges.get(node_id, set())
        edges = [self._edges[eid] for eid in edge_ids if eid in self._edges]
        if edge_type is not None:
            edges = [e for e in edges if e.edge_type == edge_type]
        return edges

    def degree(self, node_id: str) -> int:
        """Number of hyperedges containing this node (used in confidence computation)."""
        return len(self._node_to_edges.get(node_id, set()))

    # ------------------------------------------------------------------
    # Confidence management
    # ------------------------------------------------------------------

    def recompute_confidence(self, node_id: str, c_extract: float = 0.5, t_now: datetime | None = None) -> float:
        """Recompute and update confidence score for a fact node."""
        node = self._nodes.get(node_id)
        if node is None:
            return 0.0
        new_c = _compute_confidence(
            c_extract=c_extract,
            degree=self.degree(node_id),
            t_valid=node.t_valid,
            t_now=t_now,
        )
        node.confidence = new_c
        return new_c

    def decay_confidence(self, node_id: str, decay_factor: float) -> None:
        """Apply an additional multiplicative decay to a node's confidence."""
        node = self._nodes.get(node_id)
        if node is not None:
            old = node.confidence
            node.confidence = max(0.0, node.confidence * decay_factor)
            node.record_revision(f"confidence_decay(factor={decay_factor:.3f})", old)

    # ------------------------------------------------------------------
    # Entity index (for conflict detection)
    # ------------------------------------------------------------------

    def facts_for_entity_predicate(self, subject: str, predicate: str) -> list[FactNode]:
        """Return all FactNodes with the same (subject, predicate) pair."""
        key = f"{subject.lower()}::{predicate.lower()}"
        return [
            self._nodes[nid]
            for nid in self._entity_index.get(key, set())
            if nid in self._nodes and isinstance(self._nodes[nid], FactNode)
        ]

    # ------------------------------------------------------------------
    # Filtered views
    # ------------------------------------------------------------------

    def valid_edges_at(self, t: datetime, edge_type: HyperedgeType | None = None) -> list[TypedHyperedge]:
        """Return edges that are temporally valid at time t."""
        edges = self.edges_by_type(edge_type) if edge_type else list(self._edges.values())
        return [e for e in edges if e.is_valid_at(t)]

    def valid_edges_in_window(
        self,
        t_start: datetime,
        t_end: datetime,
        edge_type: HyperedgeType | None = None,
    ) -> list[TypedHyperedge]:
        """Return edges whose validity window overlaps [t_start, t_end]."""
        edges = self.edges_by_type(edge_type) if edge_type else list(self._edges.values())
        return [e for e in edges if e.overlaps_window(t_start, t_end)]

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------

    def iter_nodes(self) -> Iterator[BaseNode]:
        return iter(self._nodes.values())

    def iter_edges(self) -> Iterator[TypedHyperedge]:
        return iter(self._edges.values())

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        return {
            "total_nodes": len(self._nodes),
            "topics": len(self._nodes_by_layer[NodeLayer.TOPIC]),
            "episodes": len(self._nodes_by_layer[NodeLayer.EPISODE]),
            "facts": len(self._nodes_by_layer[NodeLayer.FACT]),
            "total_edges": len(self._edges),
            **{f"edges_{et.value}": len(self._edges_by_type[et]) for et in HyperedgeType},
        }

    # ------------------------------------------------------------------
    # Internal validation
    # ------------------------------------------------------------------

    def _validate_edge(self, edge: TypedHyperedge) -> None:
        """Validate hyperedge against formal constraints."""
        # All node IDs must exist
        missing = [nid for nid in edge.node_ids if nid not in self._nodes]
        if missing:
            raise ValueError(f"Hyperedge references unknown node IDs: {missing}")

        # Cross-layer edges must be anchored at a Topic node
        layers = {self._nodes[nid].layer for nid in edge.node_ids}
        if len(layers) > 1 and NodeLayer.TOPIC not in layers:
            raise ValueError(
                "Cross-layer hyperedges must include at least one Topic-layer node as anchor."
            )
