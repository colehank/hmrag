"""Intent-driven typed retrieval module (§3.3 / M3).

Implements the five-step retrieval pipeline:
    1. Intent analysis: q → (r, [t_s, t_e], q_key, q_dense)
       where r ∈ Δ^|T| is the type activation weight vector
    2. Type gating: retain edges where Σ_T r_T · 1[τ(e)=T] > θ
    3. Temporal filtering: retain edges where [t_s,t_e] ∩ [t_valid(e), t_invalid(e)] ≠ ∅
    4. Coarse-to-fine hierarchy traversal: Topic → Episode → Fact
       (adapted from HyperMem §3.3, Yue et al., 2026)
    5. Confidence-weighted scoring: S(e) = w_e · c_e · sim(q, e)

Intent-to-type mapping (typical):
    WHY  queries → high r_causal
    WHEN queries → high r_temporal
    WHO  queries → high r_entity
    WHERE queries → high r_entity
    General info → high r_semantic
    Compound     → multiple types simultaneously activated

Primary routing: lightweight intent classifier
Fallback:        LLM zero-shot classification (when classifier confidence < threshold)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol

from hmrag.graph.hyperedge import TypedHyperedge
from hmrag.graph.nodes import BaseNode, EpisodeNode, FactNode, TopicNode
from hmrag.graph.typed_hypergraph import TypedHypergraph
from hmrag.graph.types import HyperedgeType, NodeLayer


# ---------------------------------------------------------------------------
# Type activation weight vector
# ---------------------------------------------------------------------------

@dataclass
class TypeActivationWeights:
    """r ∈ Δ^|T| — probability simplex over the four hyperedge types.

    Allows compound queries to activate multiple types simultaneously.
    """

    semantic: float = 0.25
    temporal: float = 0.25
    causal: float = 0.25
    entity: float = 0.25

    def __post_init__(self) -> None:
        self._normalize()

    def _normalize(self) -> None:
        total = self.semantic + self.temporal + self.causal + self.entity
        if total > 0:
            self.semantic /= total
            self.temporal /= total
            self.causal /= total
            self.entity /= total

    def weight_for(self, edge_type: HyperedgeType) -> float:
        return {
            HyperedgeType.SEMANTIC: self.semantic,
            HyperedgeType.TEMPORAL: self.temporal,
            HyperedgeType.CAUSAL: self.causal,
            HyperedgeType.ENTITY: self.entity,
        }[edge_type]

    @classmethod
    def for_intent(cls, intent: "QueryIntent") -> "TypeActivationWeights":
        """Return canonical activation weights for known intent types."""
        presets = {
            QueryIntent.WHY: cls(semantic=0.1, temporal=0.1, causal=0.7, entity=0.1),
            QueryIntent.WHEN: cls(semantic=0.1, temporal=0.7, causal=0.1, entity=0.1),
            QueryIntent.WHO: cls(semantic=0.1, temporal=0.1, causal=0.1, entity=0.7),
            QueryIntent.WHERE: cls(semantic=0.1, temporal=0.1, causal=0.1, entity=0.7),
            QueryIntent.GENERAL: cls(semantic=0.7, temporal=0.1, causal=0.1, entity=0.1),
            QueryIntent.COMPOUND: cls(semantic=0.25, temporal=0.25, causal=0.25, entity=0.25),
        }
        return presets.get(intent, cls())


class QueryIntent(str, Enum):
    WHY = "why"
    WHEN = "when"
    WHO = "who"
    WHERE = "where"
    GENERAL = "general"
    COMPOUND = "compound"


# ---------------------------------------------------------------------------
# Query representation
# ---------------------------------------------------------------------------

@dataclass
class RetrievalQuery:
    """Parsed retrieval query after intent analysis step."""

    raw: str
    intent: QueryIntent
    type_weights: TypeActivationWeights
    t_start: datetime | None = None
    t_end: datetime | None = None
    keywords: list[str] = field(default_factory=list)
    dense_vector: list[float] | None = None


# ---------------------------------------------------------------------------
# Protocols for injectable components
# ---------------------------------------------------------------------------

class EmbeddingModel(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class LLMClassifier(Protocol):
    """LLM-backed intent classifier (fallback when lightweight classifier is uncertain)."""
    def classify_intent(self, query: str) -> tuple[QueryIntent, float]: ...


# ---------------------------------------------------------------------------
# Lightweight rule-based intent classifier (primary path)
# ---------------------------------------------------------------------------

_WHY_PATTERNS = re.compile(r"\b(why|because|reason|cause|explain)\b", re.I)
_WHEN_PATTERNS = re.compile(r"\b(when|date|time|how long|ago|before|after|since)\b", re.I)
_WHO_PATTERNS = re.compile(r"\b(who|whose|person|people|named|mention)\b", re.I)
_WHERE_PATTERNS = re.compile(r"\b(where|location|place|city|country)\b", re.I)


class LightweightIntentClassifier:
    """Rule-based intent classifier.

    Used as the primary path; falls back to LLMClassifier when confidence < threshold.
    """

    def classify(self, query: str) -> tuple[QueryIntent, float]:
        scores: dict[QueryIntent, int] = {
            QueryIntent.WHY: len(_WHY_PATTERNS.findall(query)),
            QueryIntent.WHEN: len(_WHEN_PATTERNS.findall(query)),
            QueryIntent.WHO: len(_WHO_PATTERNS.findall(query)),
            QueryIntent.WHERE: len(_WHERE_PATTERNS.findall(query)),
        }
        top_intent, top_count = max(scores.items(), key=lambda x: x[1])
        if top_count == 0:
            return QueryIntent.GENERAL, 0.5
        active_types = sum(1 for v in scores.values() if v > 0)
        if active_types >= 3:
            return QueryIntent.COMPOUND, 0.6
        confidence = min(0.95, 0.6 + top_count * 0.1)
        return top_intent, confidence


# ---------------------------------------------------------------------------
# Scoring utilities
# ---------------------------------------------------------------------------

def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Core retriever
# ---------------------------------------------------------------------------

@dataclass
class RetrievalResult:
    """A single retrieved node with its score."""

    node: BaseNode
    score: float
    contributing_edges: list[TypedHyperedge] = field(default_factory=list)


class TypedHypergraphRetriever:
    """Full five-step retrieval pipeline for HiMGA.

    Args:
        embedding_model: Used to encode query + node texts for dense similarity.
        llm_classifier:  Optional LLM fallback for intent classification.
        type_gate_threshold: θ — minimum activation score for an edge to pass gating.
        top_k_topic: Number of top Topic nodes to retain after coarse retrieval.
        top_k_episode: Number of Episode nodes per topic.
        top_k_fact: Number of Fact nodes per episode.
    """

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        llm_classifier: LLMClassifier | None = None,
        type_gate_threshold: float = 0.15,
        top_k_topic: int = 10,
        top_k_episode: int = 10,
        top_k_fact: int = 30,
    ) -> None:
        self.embedding_model = embedding_model
        self.llm_classifier = llm_classifier
        self.type_gate_threshold = type_gate_threshold
        self.top_k_topic = top_k_topic
        self.top_k_episode = top_k_episode
        self.top_k_fact = top_k_fact
        self._intent_clf = LightweightIntentClassifier()

    def retrieve(
        self,
        graph: TypedHypergraph,
        query: str,
        t_now: datetime | None = None,
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        """Main retrieval entry point.

        Args:
            graph:   The typed hypergraph memory store.
            query:   Natural language query.
            t_now:   Reference time for temporal validity (defaults to utcnow).
            top_k:   Override the default top_k_fact limit.

        Returns:
            Ranked list of RetrievalResult, each containing a FactNode and its score.
        """
        t_now = t_now or datetime.utcnow()

        # Step 1: Intent analysis
        parsed_query = self._analyze_intent(query)
        if parsed_query.dense_vector is None:
            parsed_query.dense_vector = self.embedding_model.encode([query])[0]

        # Step 2 + 3: Type gating + temporal filtering → candidate edges
        candidate_edges = self._gate_and_filter(graph, parsed_query, t_now)

        # Step 4: Coarse-to-fine hierarchy traversal
        fact_nodes = self._hierarchical_traversal(graph, parsed_query, candidate_edges, top_k)

        # Step 5: Confidence-weighted scoring
        results = self._score_and_rank(graph, fact_nodes, parsed_query, candidate_edges)
        k = top_k or self.top_k_fact
        return results[:k]

    # ------------------------------------------------------------------
    # Step 1: Intent analysis
    # ------------------------------------------------------------------

    def _analyze_intent(self, query: str) -> RetrievalQuery:
        intent, confidence = self._intent_clf.classify(query)

        # Fall back to LLM if confidence below threshold
        if confidence < 0.65 and self.llm_classifier is not None:
            intent, confidence = self.llm_classifier.classify_intent(query)

        type_weights = TypeActivationWeights.for_intent(intent)
        keywords = [w for w in re.findall(r"\b\w{3,}\b", query.lower()) if w not in _STOPWORDS]

        return RetrievalQuery(
            raw=query,
            intent=intent,
            type_weights=type_weights,
            keywords=keywords,
        )

    # ------------------------------------------------------------------
    # Step 2 + 3: Type gating + temporal filtering
    # ------------------------------------------------------------------

    def _gate_and_filter(
        self,
        graph: TypedHypergraph,
        query: RetrievalQuery,
        t_now: datetime,
    ) -> list[TypedHyperedge]:
        passed: list[TypedHyperedge] = []
        for edge in graph.iter_edges():
            # Type gate: Σ_T r_T · 1[τ(e)=T] > θ
            activation = query.type_weights.weight_for(edge.edge_type)
            if activation < self.type_gate_threshold:
                continue

            # Temporal filter: validity window overlap
            t_start = query.t_start or datetime.min
            t_end = query.t_end or t_now
            if not edge.overlaps_window(t_start, t_end):
                continue

            passed.append(edge)

        return passed

    # ------------------------------------------------------------------
    # Step 4: Coarse-to-fine hierarchy traversal (Topic → Episode → Fact)
    # ------------------------------------------------------------------

    def _hierarchical_traversal(
        self,
        graph: TypedHypergraph,
        query: RetrievalQuery,
        candidate_edges: list[TypedHyperedge],
        top_k: int | None,
    ) -> list[FactNode]:
        # Build candidate node set from gated edges
        candidate_node_ids: set[str] = set()
        for edge in candidate_edges:
            candidate_node_ids.update(edge.node_ids)

        # -- Topic level: rank by similarity, retain top_k_topic --
        topic_scores: dict[str, float] = {}
        for topic in graph.topics:
            if topic.id in candidate_node_ids or not candidate_node_ids:
                score = self._node_similarity(topic, query)
                topic_scores[topic.id] = score

        top_topic_ids = sorted(topic_scores, key=lambda x: topic_scores[x], reverse=True)[: self.top_k_topic]

        # -- Episode level: traverse from selected topics --
        episode_scores: dict[str, float] = {}
        for topic_id in top_topic_ids:
            topic = graph.get_node(topic_id)
            if not isinstance(topic, TopicNode):
                continue
            for ep_id in topic.episode_ids:
                episode = graph.get_node(ep_id)
                if not isinstance(episode, EpisodeNode):
                    continue
                if ep_id in candidate_node_ids or not candidate_node_ids:
                    episode_scores[ep_id] = self._node_similarity(episode, query)

        top_episode_ids = sorted(episode_scores, key=lambda x: episode_scores[x], reverse=True)[: self.top_k_episode]

        # -- Fact level: collect from selected episodes --
        fact_candidates: list[FactNode] = []
        for ep_id in top_episode_ids:
            episode = graph.get_node(ep_id)
            if not isinstance(episode, EpisodeNode):
                continue
            for fact_id in episode.fact_ids:
                fact = graph.get_node(fact_id)
                if isinstance(fact, FactNode) and fact.conflict_status != "invalidated":
                    fact_candidates.append(fact)

        return fact_candidates

    # ------------------------------------------------------------------
    # Step 5: Confidence-weighted scoring
    # ------------------------------------------------------------------

    def _score_and_rank(
        self,
        graph: TypedHypergraph,
        facts: list[FactNode],
        query: RetrievalQuery,
        candidate_edges: list[TypedHyperedge],
    ) -> list[RetrievalResult]:
        # Index contributing edges per fact for scoring
        edge_by_node: dict[str, list[TypedHyperedge]] = {}
        for edge in candidate_edges:
            for nid in edge.node_ids:
                edge_by_node.setdefault(nid, []).append(edge)

        results: list[RetrievalResult] = []
        for fact in facts:
            sim = self._node_similarity(fact, query)
            contributing = edge_by_node.get(fact.id, [])
            # w_e = max weight of fact across contributing edges
            w_e = max((e.weight_of(fact.id) for e in contributing), default=1.0)
            c_e = fact.confidence
            score = w_e * c_e * sim
            results.append(RetrievalResult(node=fact, score=score, contributing_edges=contributing))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _node_similarity(self, node: BaseNode, query: RetrievalQuery) -> float:
        if query.dense_vector and node.embedding:
            return cosine_similarity(query.dense_vector, node.embedding)
        # Keyword fallback
        if query.keywords and node.text:
            tokens = set(node.text.lower().split())
            hit = sum(1 for kw in query.keywords if kw in tokens)
            return hit / max(len(query.keywords), 1)
        return 0.0


# ---------------------------------------------------------------------------
# Common stopwords (lightweight)
# ---------------------------------------------------------------------------
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "this", "that", "these", "those",
    "and", "but", "or", "nor", "for", "yet", "so", "about", "with",
    "in", "on", "at", "by", "from", "to", "of", "not", "what",
}
