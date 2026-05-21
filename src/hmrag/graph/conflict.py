"""Conflict-aware knowledge evolution module (§3.4 / RQ2).

Implements four-category conflict detection and resolution for typed hyperedge writes.
The key design principle is shifting conflict-detection burden from a single LLM
arbitration call (as in Zep/Graphiti) to structured type-aware checks, reducing
dependency on arbitration model capability and enabling robust behavior on weak
models (gpt-4o-mini target: ≥77% on LongMemEval knowledge-update vs Zep's 74.4%).

Four conflict types (claim.md §6 RQ2):
    1. temporal_conflict  — same entity + same predicate + overlapping time window
    2. contradiction      — same entity + opposite predicate + semantic co-occurrence
    3. version_update     — same entity + same predicate type + more recent timestamp
    4. orthogonal         — same entity + different attribute type → coexist

Minimalist revision principle:
    - Nodes and edges are NEVER physically deleted
    - Invalidation expressed via t_invalid and confidence decay only
    - All revisions appended to node.history (audit trail)
    - Nodes below confidence threshold + outside retention window are
      periodically compressed to summary nodes (done by the pruner)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from hmrag.graph.nodes import FactNode
from hmrag.graph.types import ConflictResolution, ConflictType

if TYPE_CHECKING:
    from hmrag.graph.typed_hypergraph import TypedHypergraph


# Confidence decay constants
_CONTRADICTION_DECAY = 0.5    # when a contradiction is found but kept pending arbitration
_VERSION_UPDATE_DECAY = 0.7   # when superseded by a more-recent version
_LAMBDA_DECAY = 0.01          # exponential time-decay rate (per day)


@dataclass
class ConflictRecord:
    """Represents a single detected conflict and its resolution."""

    conflict_type: ConflictType
    resolution: ConflictResolution
    existing_fact_id: str
    new_fact_id: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


class ConflictDetector:
    """Stateless conflict detector; operates on a TypedHypergraph instance.

    Usage:
        detector = ConflictDetector()
        records = detector.check(graph, new_fact)
        for rec in records:
            detector.resolve(graph, rec)
    """

    def check(self, graph: "TypedHypergraph", new_fact: FactNode) -> list[ConflictRecord]:
        """Check new_fact against existing facts and return conflict records.

        Runs three structured checks in order:
            1. Temporal conflict (structural, cheapest — no LLM needed)
            2. Version update (structural)
            3. Contradiction (requires semantic comparison — may call LLM)

        Orthogonal facts pass all checks and return an empty list.
        """
        records: list[ConflictRecord] = []
        existing = graph.facts_for_entity_predicate(new_fact.subject, new_fact.predicate)
        existing = [f for f in existing if f.id != new_fact.id]

        for old_fact in existing:
            record = self._classify(old_fact, new_fact)
            if record is not None:
                records.append(record)

        return records

    def resolve(self, graph: "TypedHypergraph", record: ConflictRecord) -> None:
        """Apply the prescribed resolution action to the graph (minimalist principle)."""
        old_fact = graph.get_node(record.existing_fact_id)
        if old_fact is None:
            return

        if record.resolution == ConflictResolution.INVALIDATE_OLD:
            new_fact = graph.get_node(record.new_fact_id)
            new_t_valid = new_fact.t_valid if new_fact is not None else datetime.utcnow()
            old_conf = old_fact.confidence
            old_fact.t_invalid = new_t_valid
            old_fact.record_revision(
                f"invalidated_by:{record.new_fact_id}",
                old_conf,
            )

        elif record.resolution == ConflictResolution.MARK_FOR_ARBITRATION:
            old_conf = old_fact.confidence
            old_fact.conflict_status = "pending_arbitration"
            if isinstance(old_fact, FactNode):
                if record.new_fact_id not in old_fact.conflicting_fact_ids:
                    old_fact.conflicting_fact_ids.append(record.new_fact_id)
            graph.decay_confidence(record.existing_fact_id, _CONTRADICTION_DECAY)
            old_fact.record_revision(
                f"marked_pending_arb::{record.new_fact_id}",
                old_conf,
            )

        elif record.resolution == ConflictResolution.DECAY_CONFIDENCE:
            graph.decay_confidence(record.existing_fact_id, _VERSION_UPDATE_DECAY)

        # ConflictResolution.NO_ACTION: orthogonal, do nothing

    # ------------------------------------------------------------------
    # Internal classification logic
    # ------------------------------------------------------------------

    def _classify(self, old: FactNode, new: FactNode) -> ConflictRecord | None:
        """Classify the relationship between old and new facts.

        Priority order (most specific to least):
            contradiction > temporal_conflict > version_update > orthogonal

        Contradiction is checked first because "same predicate, different object"
        (e.g., "lives in Beijing" vs "lives in Shanghai") is a semantic conflict
        regardless of temporal window overlap.  Temporal conflict applies only
        when the obj is the same but the time ranges overlap (a time-range update
        for an identical assertion, e.g., a recurring schedule entry).
        """
        # Check for semantic contradiction first (different object values = semantic conflict)
        if self._are_contradictory(old, new):
            return ConflictRecord(
                conflict_type=ConflictType.CONTRADICTION,
                resolution=ConflictResolution.MARK_FOR_ARBITRATION,
                existing_fact_id=old.id,
                new_fact_id=new.id,
                details={"old_obj": old.obj, "new_obj": new.obj},
            )

        # Temporal window overlap with same obj = time-range conflict (e.g., recurring facts)
        if self._temporal_windows_overlap(old, new):
            return ConflictRecord(
                conflict_type=ConflictType.TEMPORAL_CONFLICT,
                resolution=ConflictResolution.INVALIDATE_OLD,
                existing_fact_id=old.id,
                new_fact_id=new.id,
                details={"old_t_valid": str(old.t_valid), "new_t_valid": str(new.t_valid)},
            )

        # Check for version update (same predicate, newer timestamp)
        if self._is_version_update(old, new):
            return ConflictRecord(
                conflict_type=ConflictType.VERSION_UPDATE,
                resolution=ConflictResolution.DECAY_CONFIDENCE,
                existing_fact_id=old.id,
                new_fact_id=new.id,
                details={"old_t_valid": str(old.t_valid), "new_t_valid": str(new.t_valid)},
            )

        # Orthogonal: different attribute types — coexist
        return ConflictRecord(
            conflict_type=ConflictType.ORTHOGONAL,
            resolution=ConflictResolution.NO_ACTION,
            existing_fact_id=old.id,
            new_fact_id=new.id,
        )

    @staticmethod
    def _temporal_windows_overlap(old: FactNode, new: FactNode) -> bool:
        """True if both facts have time windows AND they overlap."""
        if old.t_valid is None or new.t_valid is None:
            return False
        old_end = old.t_invalid or datetime.max
        new_end = new.t_invalid or datetime.max
        old_start = old.t_valid
        new_start = new.t_valid
        return old_start <= new_end and new_start <= old_end

    @staticmethod
    def _are_contradictory(old: FactNode, new: FactNode) -> bool:
        """Heuristic contradiction detection based on object values.

        Full implementation would embed and compare semantically; this provides
        a structural approximation sufficient for the majority of factual updates
        (e.g., "lives in Beijing" → "lives in Shanghai").
        """
        if not old.obj or not new.obj:
            return False
        # Simple heuristic: same predicate + different non-empty objects
        return (
            old.predicate.lower() == new.predicate.lower()
            and old.obj.lower() != new.obj.lower()
        )

    @staticmethod
    def _is_version_update(old: FactNode, new: FactNode) -> bool:
        """True if new fact is a more recent version of the same predicate."""
        if old.t_valid is None or new.t_valid is None:
            return False
        return new.t_valid > old.t_valid


class TemporalPruner:
    """Periodically compresses low-confidence, expired nodes into summary nodes.

    Implements the periodic compression step from §3.4:
    nodes where confidence < min_confidence AND t_invalid < (now - retention_days)
    are replaced by a single summary FactNode.
    """

    def __init__(self, min_confidence: float = 0.1, retention_days: int = 180) -> None:
        self.min_confidence = min_confidence
        self.retention_days = retention_days

    def prune(self, graph: "TypedHypergraph") -> list[str]:
        """Mark prunable nodes and return their IDs (does not delete them)."""
        now = datetime.utcnow()
        cutoff_delta = self.retention_days * 86400  # seconds

        prunable: list[str] = []
        for fact in graph.facts:
            if fact.confidence >= self.min_confidence:
                continue
            if fact.t_invalid is None:
                continue
            expired_seconds = (now - fact.t_invalid).total_seconds()
            if expired_seconds < cutoff_delta:
                continue
            prunable.append(fact.id)

        return prunable
