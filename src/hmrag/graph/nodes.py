"""Node dataclasses for the Topic-Episode-Fact hierarchy."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from hmrag.graph.types import NodeLayer


@dataclass
class BaseNode:
    """Common fields shared by all node layers."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    layer: NodeLayer = field(init=False)
    text: str = ""
    embedding: list[float] | None = None

    # Temporal validity window (ISO 8601 strings or None for open range)
    t_valid: datetime | None = None
    t_invalid: datetime | None = None

    # Confidence score c_v ∈ [0, 1]
    confidence: float = 1.0

    # Source provenance
    source_session: str = ""
    source_turn: int = -1

    # Append-only revision history: list of {timestamp, action, old_confidence}
    history: list[dict[str, Any]] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def is_valid_at(self, t: datetime) -> bool:
        """Return True if this node is temporally valid at time t."""
        if self.t_valid is not None and t < self.t_valid:
            return False
        if self.t_invalid is not None and t >= self.t_invalid:
            return False
        return True

    def record_revision(self, action: str, old_confidence: float, ts: datetime | None = None) -> None:
        """Append a revision entry to the history (append-only, never delete)."""
        self.history.append(
            {
                "timestamp": (ts or datetime.utcnow()).isoformat(),
                "action": action,
                "old_confidence": old_confidence,
            }
        )


@dataclass
class TopicNode(BaseNode):
    """V^T — highest-level concept grouping multiple episodes."""

    layer: NodeLayer = field(default=NodeLayer.TOPIC, init=False)
    label: str = ""
    episode_ids: list[str] = field(default_factory=list)


@dataclass
class EpisodeNode(BaseNode):
    """V^E — a coherent event segment within a conversation session."""

    layer: NodeLayer = field(default=NodeLayer.EPISODE, init=False)
    topic_id: str = ""
    fact_ids: list[str] = field(default_factory=list)
    # Start/end turn indices within the source conversation
    turn_start: int = -1
    turn_end: int = -1


@dataclass
class FactNode(BaseNode):
    """V^F — atomic knowledge assertion extracted from a conversation turn.

    This is the leaf node in the hierarchy and the primary target of
    conflict-aware writes (§3.4 / RQ2).
    """

    layer: NodeLayer = field(default=NodeLayer.FACT, init=False)
    episode_id: str = ""
    subject: str = ""
    predicate: str = ""
    obj: str = ""

    # Conflict detection bookkeeping
    conflict_status: str = "clean"       # clean | pending_arbitration | invalidated
    conflicting_fact_ids: list[str] = field(default_factory=list)
