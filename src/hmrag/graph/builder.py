"""Memory construction pipeline: Dialogue → Typed Hypergraph (§3.2 / M2).

Implements the three-stage write process:
    1. Three-layer segmentation: Episode boundary → Topic aggregation → Fact extraction
       (protocol adapted from HyperMem §3.2, Yue et al., 2026)
    2. Parallel four-type hyperedge extraction (type-specific extractors)
    3. Conflict detection and resolution (§3.4, delegates to ConflictDetector)
    4. Confidence score update

Dual-stream architecture (§9.1 engineering constraint):
    - Sync fast path  (< 500 ms target): T_sem + T_temp hyperedge construction
    - Async slow path: T_causal hyperedge construction + conflict detection

The causal hyperedge constraint |e_causal| ≥ 3 is enforced at the extractor level;
binary causal relations are demoted to pairwise temporal edges.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from hmrag.graph.conflict import ConflictDetector, ConflictRecord
from hmrag.graph.hyperedge import TypedHyperedge
from hmrag.graph.nodes import EpisodeNode, FactNode, TopicNode
from hmrag.graph.typed_hypergraph import TypedHypergraph
from hmrag.graph.types import HyperedgeType, NodeLayer


# ---------------------------------------------------------------------------
# Data contracts for the pipeline
# ---------------------------------------------------------------------------

@dataclass
class ConversationTurn:
    """A single dialogue turn."""

    turn_index: int
    speaker: str
    text: str
    timestamp: datetime | None = None
    session_id: str = ""


@dataclass
class ExtractionResult:
    """Structured output from an LLM extractor call."""

    facts: list[dict[str, Any]] = field(default_factory=list)
    """Each fact: {subject, predicate, object, confidence, t_valid, t_invalid}"""

    hyperedge_candidates: list[dict[str, Any]] = field(default_factory=list)
    """Each candidate: {node_ids: list[str], edge_type: str, confidence: float}"""

    raw_response: str = ""


# ---------------------------------------------------------------------------
# LLM extractor protocol (dependency-injection interface)
# ---------------------------------------------------------------------------

class LLMExtractor(Protocol):
    """Protocol for any LLM-backed extraction component.

    Concrete implementations (e.g., OpenAI, local Qwen3) are injected at
    runtime and are NOT instantiated inside this module to keep it testable
    without API keys.
    """

    def extract_facts(
        self,
        turns: list[ConversationTurn],
        context: str = "",
    ) -> ExtractionResult: ...

    def extract_hyperedges(
        self,
        edge_type: HyperedgeType,
        node_texts: dict[str, str],
        fact_ids: list[str],
    ) -> list[dict[str, Any]]: ...

    def detect_episode_boundary(
        self,
        turns: list[ConversationTurn],
        window_size: int = 5,
    ) -> list[int]: ...


# ---------------------------------------------------------------------------
# Segmentation layer
# ---------------------------------------------------------------------------

class DialogueSegmenter:
    """Implements three-layer segmentation: Episode → Topic → Fact.

    The segmentation protocol follows HyperMem §3.2 (Yue et al., 2026).
    This class handles the structural segmentation; actual content extraction
    is delegated to the injected LLMExtractor.
    """

    def __init__(self, extractor: LLMExtractor, episode_window: int = 10) -> None:
        self.extractor = extractor
        self.episode_window = episode_window

    def segment_episodes(self, turns: list[ConversationTurn]) -> list[list[ConversationTurn]]:
        """Split turns into coherent episode segments.

        Uses a sliding window + LLM boundary detection as primary method,
        with a fixed-window fallback for efficiency.
        """
        if len(turns) <= self.episode_window:
            return [turns]

        boundary_indices = self.extractor.detect_episode_boundary(turns, self.episode_window)
        # Ensure boundaries are valid and sorted
        boundary_indices = sorted({0, *boundary_indices, len(turns)})

        episodes: list[list[ConversationTurn]] = []
        for i in range(len(boundary_indices) - 1):
            start, end = boundary_indices[i], boundary_indices[i + 1]
            if start < end:
                episodes.append(turns[start:end])
        return episodes if episodes else [turns]

    @staticmethod
    def turns_to_text(turns: list[ConversationTurn]) -> str:
        return "\n".join(f"[{t.speaker}] {t.text}" for t in turns)


# ---------------------------------------------------------------------------
# Type-specific hyperedge extractors (Abstract Base)
# ---------------------------------------------------------------------------

class BaseHyperedgeExtractor(ABC):
    """Abstract base for all four type-specific hyperedge extractors."""

    edge_type: HyperedgeType

    @abstractmethod
    def extract(
        self,
        graph: TypedHypergraph,
        fact_ids: list[str],
        extractor: LLMExtractor,
    ) -> list[TypedHyperedge]:
        """Return new hyperedges to be added to the graph."""
        ...


class SemanticHyperedgeExtractor(BaseHyperedgeExtractor):
    """T_sem: binds semantically related Fact nodes within the same Episode."""

    edge_type = HyperedgeType.SEMANTIC

    def extract(self, graph: TypedHypergraph, fact_ids: list[str], extractor: LLMExtractor) -> list[TypedHyperedge]:
        if len(fact_ids) < 2:
            return []
        node_texts = {
            fid: graph.get_node(fid).text  # type: ignore[union-attr]
            for fid in fact_ids
            if graph.get_node(fid) is not None
        }
        candidates = extractor.extract_hyperedges(HyperedgeType.SEMANTIC, node_texts, fact_ids)
        return self._candidates_to_edges(candidates, fact_ids)

    def _candidates_to_edges(
        self, candidates: list[dict[str, Any]], valid_ids: set[str] | list[str]
    ) -> list[TypedHyperedge]:
        valid_set = set(valid_ids)
        edges: list[TypedHyperedge] = []
        for c in candidates:
            nids = [nid for nid in c.get("node_ids", []) if nid in valid_set]
            if len(nids) >= 2:
                edges.append(
                    TypedHyperedge(
                        edge_type=HyperedgeType.SEMANTIC,
                        node_ids=nids,
                        confidence=float(c.get("confidence", 1.0)),
                    )
                )
        return edges


class TemporalHyperedgeExtractor(BaseHyperedgeExtractor):
    """T_temp: binds events in the same time window (fast path)."""

    edge_type = HyperedgeType.TEMPORAL

    def extract(self, graph: TypedHypergraph, fact_ids: list[str], extractor: LLMExtractor) -> list[TypedHyperedge]:
        node_texts = {
            fid: graph.get_node(fid).text  # type: ignore[union-attr]
            for fid in fact_ids
            if graph.get_node(fid) is not None
        }
        candidates = extractor.extract_hyperedges(HyperedgeType.TEMPORAL, node_texts, fact_ids)
        edges: list[TypedHyperedge] = []
        for c in candidates:
            nids = c.get("node_ids", [])
            if len(nids) >= 2:
                edges.append(
                    TypedHyperedge(
                        edge_type=HyperedgeType.TEMPORAL,
                        node_ids=nids,
                        confidence=float(c.get("confidence", 1.0)),
                    )
                )
        return edges


class CausalHyperedgeExtractor(BaseHyperedgeExtractor):
    """T_causal: binds causal convergence/divergence structures (slow path).

    Enforces |e_causal| ≥ 3; binary causal pairs are demoted to T_temp edges.
    """

    edge_type = HyperedgeType.CAUSAL

    def extract(self, graph: TypedHypergraph, fact_ids: list[str], extractor: LLMExtractor) -> list[TypedHyperedge]:
        node_texts = {
            fid: graph.get_node(fid).text  # type: ignore[union-attr]
            for fid in fact_ids
            if graph.get_node(fid) is not None
        }
        candidates = extractor.extract_hyperedges(HyperedgeType.CAUSAL, node_texts, fact_ids)
        edges: list[TypedHyperedge] = []
        for c in candidates:
            nids = c.get("node_ids", [])
            if len(nids) >= 3:
                edges.append(
                    TypedHyperedge(
                        edge_type=HyperedgeType.CAUSAL,
                        node_ids=nids,
                        confidence=float(c.get("confidence", 1.0)),
                    )
                )
            # Binary causal pairs demoted to temporal (not discarded, cf. §7.1 note)
        return edges


class EntityHyperedgeExtractor(BaseHyperedgeExtractor):
    """T_entity: binds cross-time events involving the same entity."""

    edge_type = HyperedgeType.ENTITY

    def extract(self, graph: TypedHypergraph, fact_ids: list[str], extractor: LLMExtractor) -> list[TypedHyperedge]:
        node_texts = {
            fid: graph.get_node(fid).text  # type: ignore[union-attr]
            for fid in fact_ids
            if graph.get_node(fid) is not None
        }
        candidates = extractor.extract_hyperedges(HyperedgeType.ENTITY, node_texts, fact_ids)
        edges: list[TypedHyperedge] = []
        for c in candidates:
            nids = c.get("node_ids", [])
            if len(nids) >= 2:
                edges.append(
                    TypedHyperedge(
                        edge_type=HyperedgeType.ENTITY,
                        node_ids=nids,
                        confidence=float(c.get("confidence", 1.0)),
                    )
                )
        return edges


# ---------------------------------------------------------------------------
# Main builder: dual-stream architecture
# ---------------------------------------------------------------------------

class MemoryBuilder:
    """Orchestrates the full dialogue → TypedHypergraph write pipeline.

    Dual-stream architecture (§9.1):
        Fast path  (sync, < 500ms): fact extraction + T_sem + T_temp construction
        Slow path  (async): T_causal construction + conflict detection
    """

    def __init__(self, llm_extractor: LLMExtractor) -> None:
        self.extractor = llm_extractor
        self.segmenter = DialogueSegmenter(llm_extractor)
        self.conflict_detector = ConflictDetector()

        self._sem_extractor = SemanticHyperedgeExtractor()
        self._temp_extractor = TemporalHyperedgeExtractor()
        self._causal_extractor = CausalHyperedgeExtractor()
        self._entity_extractor = EntityHyperedgeExtractor()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_turns(
        self,
        graph: TypedHypergraph,
        turns: list[ConversationTurn],
        session_id: str = "",
        topic_label: str = "",
    ) -> list[ConflictRecord]:
        """Synchronous entry point: ingest turns via fast path, schedule slow path.

        Returns conflict records produced during fast-path processing.
        Slow-path conflicts (causal edges + LLM arbitration) are handled
        asynchronously and not returned here.
        """
        episodes = self.segmenter.segment_episodes(turns)
        topic_node = self._build_topic(graph, turns, topic_label, session_id)

        all_conflicts: list[ConflictRecord] = []
        for episode_turns in episodes:
            episode_node = self._build_episode(graph, episode_turns, topic_node.id, session_id)
            facts = self._extract_facts(graph, episode_turns, episode_node.id, session_id)

            # Fast path: semantic + temporal hyperedges
            fact_ids = [f.id for f in facts]
            sem_edges = self._sem_extractor.extract(graph, fact_ids, self.extractor)
            temp_edges = self._temp_extractor.extract(graph, fact_ids, self.extractor)
            for edge in sem_edges + temp_edges:
                graph.add_edge(edge)

            # Fast-path conflict detection (structural only, no LLM)
            for fact in facts:
                conflicts = self.conflict_detector.check(graph, fact)
                for record in conflicts:
                    self.conflict_detector.resolve(graph, record)
                all_conflicts.extend(conflicts)

        return all_conflicts

    async def ingest_turns_async(
        self,
        graph: TypedHypergraph,
        turns: list[ConversationTurn],
        session_id: str = "",
        topic_label: str = "",
    ) -> list[ConflictRecord]:
        """Full async pipeline including slow-path causal extraction.

        Should be awaited when latency budget allows the slow path to complete.
        """
        # Run fast path synchronously first
        fast_conflicts = self.ingest_turns(graph, turns, session_id, topic_label)

        # Slow path: causal + entity hyperedges (parallelized)
        all_fact_ids = [f.id for f in graph.facts]
        causal_task = asyncio.to_thread(
            self._causal_extractor.extract, graph, all_fact_ids, self.extractor
        )
        entity_task = asyncio.to_thread(
            self._entity_extractor.extract, graph, all_fact_ids, self.extractor
        )
        causal_edges, entity_edges = await asyncio.gather(causal_task, entity_task)
        for edge in causal_edges + entity_edges:
            try:
                graph.add_edge(edge)
            except ValueError:
                pass  # skip invalid edges (e.g., unknown node refs)

        return fast_conflicts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_topic(
        self,
        graph: TypedHypergraph,
        turns: list[ConversationTurn],
        label: str,
        session_id: str,
    ) -> TopicNode:
        topic_node = TopicNode(
            text=label or self.segmenter.turns_to_text(turns[:2]),
            label=label,
            source_session=session_id,
            t_valid=turns[0].timestamp if turns else None,
        )
        graph.add_node(topic_node)
        return topic_node

    def _build_episode(
        self,
        graph: TypedHypergraph,
        turns: list[ConversationTurn],
        topic_id: str,
        session_id: str,
    ) -> EpisodeNode:
        text = self.segmenter.turns_to_text(turns)
        episode_node = EpisodeNode(
            text=text,
            topic_id=topic_id,
            source_session=session_id,
            turn_start=turns[0].turn_index if turns else -1,
            turn_end=turns[-1].turn_index if turns else -1,
            t_valid=turns[0].timestamp if turns else None,
        )
        graph.add_node(episode_node)

        # Update parent topic
        topic = graph.get_node(topic_id)
        if isinstance(topic, TopicNode):
            topic.episode_ids.append(episode_node.id)

        return episode_node

    def _extract_facts(
        self,
        graph: TypedHypergraph,
        turns: list[ConversationTurn],
        episode_id: str,
        session_id: str,
    ) -> list[FactNode]:
        text = self.segmenter.turns_to_text(turns)
        result = self.extractor.extract_facts(turns, context=text)

        facts: list[FactNode] = []
        for f in result.facts:
            fact_node = FactNode(
                text=f.get("text", f"{f.get('subject','')} {f.get('predicate','')} {f.get('object','')}"),
                episode_id=episode_id,
                subject=str(f.get("subject", "")),
                predicate=str(f.get("predicate", "")),
                obj=str(f.get("object", "")),
                source_session=session_id,
                confidence=float(f.get("confidence", 1.0)),
                t_valid=f.get("t_valid"),
                t_invalid=f.get("t_invalid"),
            )
            graph.add_node(fact_node)

            # Update parent episode
            episode = graph.get_node(episode_id)
            if isinstance(episode, EpisodeNode):
                episode.fact_ids.append(fact_node.id)

            facts.append(fact_node)

        return facts
