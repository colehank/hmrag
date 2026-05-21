"""Core type definitions for the typed hypergraph."""

from __future__ import annotations

from enum import Enum, auto


class NodeLayer(str, Enum):
    """Three-layer node hierarchy: Topic → Episode → Fact."""

    TOPIC = "topic"
    EPISODE = "episode"
    FACT = "fact"


class HyperedgeType(str, Enum):
    """Four mutually non-exclusive hyperedge types (τ mapping in the formal definition).

    Each type captures a distinct relational dimension that cannot be reduced
    to the others — empirically supported by MAGMA ablation experiments
    (Jiang et al., 2026) where removing any single graph type causes
    independent performance degradation.
    """

    SEMANTIC = "semantic"    # T_sem: binds semantically related fragments under the same topic
    TEMPORAL = "temporal"    # T_temp: binds events in the same time window
    CAUSAL = "causal"        # T_causal: binds causal convergence/divergence structures (|e|≥3)
    ENTITY = "entity"        # T_entity: binds cross-time events involving the same entity


class ConflictType(str, Enum):
    """Four conflict categories for type-aware conflict detection (§3.4 / RQ2)."""

    TEMPORAL_CONFLICT = "temporal_conflict"   # same entity + same predicate + overlapping time window
    CONTRADICTION = "contradiction"           # same entity + opposing predicate + semantic co-occurrence
    VERSION_UPDATE = "version_update"         # same entity + same predicate type + more recent
    ORTHOGONAL = "orthogonal"                 # same entity + different attribute type → coexist


class ConflictResolution(str, Enum):
    """Resolution actions produced by conflict detection."""

    INVALIDATE_OLD = "invalidate_old"         # set t_invalid on the old assertion
    MARK_FOR_ARBITRATION = "mark_for_arb"    # both versions kept, LLM arbitration pending
    DECAY_CONFIDENCE = "decay_confidence"     # reduce old assertion's confidence weight
    NO_ACTION = "no_action"                   # orthogonal; coexist
