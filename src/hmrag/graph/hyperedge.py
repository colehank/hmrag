"""TypedHyperedge — the core relational unit of the typed hypergraph.

Formal definition (§3.1):
  τ: E → {T_sem, T_temp, T_causal, T_entity}
  ω: E × V → [0, 1]   (per-node membership weight within an edge)
  π: V ∪ E → M        (metadata including t_valid, t_invalid, confidence)

Design constraints from claim.md §7.1:
  - Type independence: same node set can belong to multiple edges of different types
  - Layer crossing: edges may span layers (only topic-anchored cross-layer edges allowed)
  - Size bound: |e| ≤ 16 (practical maximum, HyperMem observed all < 16)
  - Causal size: |e_causal| ≥ 3 (binary causality uses pairwise edges instead)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from hmrag.graph.types import HyperedgeType


@dataclass
class TypedHyperedge:
    """A typed hyperedge e ∈ E of the hypergraph H=(V,E,τ,ω,π).

    Attributes:
        id:         Unique edge identifier.
        edge_type:  τ(e) — one of the four type labels.
        node_ids:   Ordered list of node IDs in this edge (|e| ≥ 2).
        weights:    ω(e, v) for each node; defaults to uniform 1/|e|.
        t_valid:    Start of edge temporal validity.
        t_invalid:  End of edge temporal validity (None = still valid).
        confidence: Aggregate confidence score for the edge.
        source_session: Provenance session ID.
        metadata:   Arbitrary extra annotations (π mapping).
    """

    edge_type: HyperedgeType
    node_ids: list[str]

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    weights: dict[str, float] = field(default_factory=dict)

    t_valid: datetime | None = None
    t_invalid: datetime | None = None
    confidence: float = 1.0

    source_session: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.node_ids) < 2:
            raise ValueError(f"Hyperedge must contain at least 2 nodes; got {len(self.node_ids)}")
        if self.edge_type == HyperedgeType.CAUSAL and len(self.node_ids) < 3:
            raise ValueError(
                "Causal hyperedges require |e| ≥ 3; binary causality should use pairwise edges."
            )
        if len(self.node_ids) > 16:
            raise ValueError(f"Hyperedge size exceeds practical limit of 16; got {len(self.node_ids)}")
        # Normalize weights to uniform if not provided
        if not self.weights:
            w = 1.0 / len(self.node_ids)
            self.weights = {nid: w for nid in self.node_ids}

    def is_valid_at(self, t: datetime) -> bool:
        if self.t_valid is not None and t < self.t_valid:
            return False
        if self.t_invalid is not None and t >= self.t_invalid:
            return False
        return True

    def weight_of(self, node_id: str) -> float:
        return self.weights.get(node_id, 0.0)

    def overlaps_window(self, t_start: datetime, t_end: datetime) -> bool:
        """Return True if this edge's validity window overlaps [t_start, t_end]."""
        edge_start = self.t_valid or datetime.min
        edge_end = self.t_invalid or datetime.max
        return edge_start <= t_end and edge_end >= t_start
