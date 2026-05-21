"""Graph subpackage: typed hypergraph data structures and construction for HiMGA."""

from hmrag.graph.builder import ConversationTurn, LLMExtractor, MemoryBuilder
from hmrag.graph.conflict import ConflictDetector, ConflictRecord, TemporalPruner
from hmrag.graph.hyperedge import TypedHyperedge
from hmrag.graph.nodes import BaseNode, EpisodeNode, FactNode, TopicNode
from hmrag.graph.typed_hypergraph import TypedHypergraph
from hmrag.graph.types import (
    ConflictResolution,
    ConflictType,
    HyperedgeType,
    NodeLayer,
)

__all__ = [
    "TypedHypergraph",
    "TypedHyperedge",
    "BaseNode",
    "TopicNode",
    "EpisodeNode",
    "FactNode",
    "NodeLayer",
    "HyperedgeType",
    "ConflictType",
    "ConflictResolution",
]
