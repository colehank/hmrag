"""HiMGA — Hierarchical Multigraph RAG for Conversational Memory.

Core package exposing the typed hypergraph memory system:

    from hmrag.graph import TypedHypergraph, TypedHyperedge, MemoryBuilder
    from hmrag.retrieval import TypedHypergraphRetriever
"""

from hmrag.graph import (
    ConflictDetector,
    ConflictRecord,
    ConflictResolution,
    ConflictType,
    ConversationTurn,
    EpisodeNode,
    FactNode,
    HyperedgeType,
    LLMExtractor,
    MemoryBuilder,
    NodeLayer,
    TemporalPruner,
    TopicNode,
    TypedHyperedge,
    TypedHypergraph,
)
from hmrag.retrieval import (
    QueryIntent,
    RetrievalQuery,
    RetrievalResult,
    TypeActivationWeights,
    TypedHypergraphRetriever,
)

__all__ = [
    # Graph
    "TypedHypergraph",
    "TypedHyperedge",
    "TopicNode",
    "EpisodeNode",
    "FactNode",
    "NodeLayer",
    "HyperedgeType",
    # Construction
    "MemoryBuilder",
    "ConversationTurn",
    "LLMExtractor",
    # Conflict
    "ConflictDetector",
    "ConflictRecord",
    "ConflictType",
    "ConflictResolution",
    "TemporalPruner",
    # Retrieval
    "TypedHypergraphRetriever",
    "RetrievalQuery",
    "RetrievalResult",
    "TypeActivationWeights",
    "QueryIntent",
]
