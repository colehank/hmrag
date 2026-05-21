"""Tests for hmrag.graph — TypedHypergraph, nodes, edges, and conflict detection."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from hmrag.graph import (
    ConflictDetector,
    ConflictResolution,
    ConflictType,
    EpisodeNode,
    FactNode,
    HyperedgeType,
    NodeLayer,
    TemporalPruner,
    TopicNode,
    TypedHyperedge,
    TypedHypergraph,
)


# ---------------------------------------------------------------------------
# TypedHyperedge constraints
# ---------------------------------------------------------------------------


def test_hyperedge_requires_at_least_two_nodes():
    with pytest.raises(ValueError, match="at least 2 nodes"):
        TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["n1"])


def test_causal_hyperedge_requires_at_least_three_nodes():
    with pytest.raises(ValueError, match="require |e| ≥ 3"):
        TypedHyperedge(edge_type=HyperedgeType.CAUSAL, node_ids=["n1", "n2"])


def test_causal_hyperedge_accepts_three_nodes():
    edge = TypedHyperedge(edge_type=HyperedgeType.CAUSAL, node_ids=["n1", "n2", "n3"])
    assert len(edge.node_ids) == 3


def test_hyperedge_exceeds_size_limit():
    with pytest.raises(ValueError, match="exceeds practical limit"):
        TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=[f"n{i}" for i in range(17)])


def test_hyperedge_uniform_weights_default():
    edge = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["n1", "n2", "n3"])
    assert abs(edge.weight_of("n1") - 1 / 3) < 1e-9
    assert abs(sum(edge.weights.values()) - 1.0) < 1e-9


def test_hyperedge_temporal_validity():
    now = datetime(2026, 1, 1)
    edge = TypedHyperedge(
        edge_type=HyperedgeType.TEMPORAL,
        node_ids=["n1", "n2"],
        t_valid=now,
        t_invalid=datetime(2026, 6, 1),
    )
    assert edge.is_valid_at(datetime(2026, 3, 1))
    assert not edge.is_valid_at(datetime(2025, 12, 31))
    assert not edge.is_valid_at(datetime(2026, 6, 2))


def test_hyperedge_window_overlap():
    edge = TypedHyperedge(
        edge_type=HyperedgeType.TEMPORAL,
        node_ids=["n1", "n2"],
        t_valid=datetime(2026, 3, 1),
        t_invalid=datetime(2026, 6, 1),
    )
    assert edge.overlaps_window(datetime(2026, 1, 1), datetime(2026, 4, 1))
    assert not edge.overlaps_window(datetime(2025, 1, 1), datetime(2025, 12, 31))


# ---------------------------------------------------------------------------
# TypedHypergraph: node management
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_graph() -> TypedHypergraph:
    return TypedHypergraph()


@pytest.fixture
def graph_with_nodes() -> TypedHypergraph:
    g = TypedHypergraph()
    topic = TopicNode(id="t1", text="Marathon training", label="marathon")
    ep = EpisodeNode(id="e1", text="Week 3 training session", topic_id="t1")
    f1 = FactNode(id="f1", text="Alice runs 10km", episode_id="e1",
                  subject="Alice", predicate="runs", obj="10km")
    f2 = FactNode(id="f2", text="Alice trains daily", episode_id="e1",
                  subject="Alice", predicate="trains", obj="daily")
    for n in [topic, ep, f1, f2]:
        g.add_node(n)
    return g


def test_add_and_get_node(empty_graph: TypedHypergraph):
    node = TopicNode(id="t1", text="Hello")
    empty_graph.add_node(node)
    assert empty_graph.get_node("t1") is node


def test_nodes_by_layer(graph_with_nodes: TypedHypergraph):
    assert len(graph_with_nodes.topics) == 1
    assert len(graph_with_nodes.episodes) == 1
    assert len(graph_with_nodes.facts) == 2


def test_remove_node_cascades_to_edges(graph_with_nodes: TypedHypergraph):
    edge = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["f1", "f2"])
    graph_with_nodes.add_edge(edge)
    assert graph_with_nodes.get_edge(edge.id) is not None
    graph_with_nodes.remove_node("f1")
    # Edge should be removed because f1 was in it
    assert graph_with_nodes.get_edge(edge.id) is None


# ---------------------------------------------------------------------------
# TypedHypergraph: edge management
# ---------------------------------------------------------------------------


def test_add_valid_edge(graph_with_nodes: TypedHypergraph):
    edge = TypedHyperedge(edge_type=HyperedgeType.ENTITY, node_ids=["f1", "f2"])
    graph_with_nodes.add_edge(edge)
    assert graph_with_nodes.get_edge(edge.id) is edge


def test_edge_validates_unknown_nodes(graph_with_nodes: TypedHypergraph):
    edge = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["f1", "unknown_node"])
    with pytest.raises(ValueError, match="unknown node IDs"):
        graph_with_nodes.add_edge(edge)


def test_cross_layer_edge_requires_topic_anchor(graph_with_nodes: TypedHypergraph):
    # episode + fact (no topic) → should raise
    edge = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["e1", "f1"])
    with pytest.raises(ValueError, match="Topic-layer node"):
        graph_with_nodes.add_edge(edge)


def test_cross_layer_edge_with_topic_anchor(graph_with_nodes: TypedHypergraph):
    # topic + fact → valid (topic anchor present)
    edge = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["t1", "f1"])
    graph_with_nodes.add_edge(edge)
    assert graph_with_nodes.get_edge(edge.id) is not None


def test_type_independence(graph_with_nodes: TypedHypergraph):
    # Same node set, two different edge types → both should be valid
    sem = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["f1", "f2"])
    ent = TypedHyperedge(edge_type=HyperedgeType.ENTITY, node_ids=["f1", "f2"])
    graph_with_nodes.add_edge(sem)
    graph_with_nodes.add_edge(ent)
    assert graph_with_nodes.get_edge(sem.id) is not None
    assert graph_with_nodes.get_edge(ent.id) is not None


def test_edges_by_type(graph_with_nodes: TypedHypergraph):
    sem = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["f1", "f2"])
    temp = TypedHyperedge(edge_type=HyperedgeType.TEMPORAL, node_ids=["f1", "f2"])
    graph_with_nodes.add_edge(sem)
    graph_with_nodes.add_edge(temp)
    assert len(graph_with_nodes.edges_by_type(HyperedgeType.SEMANTIC)) == 1
    assert len(graph_with_nodes.edges_by_type(HyperedgeType.TEMPORAL)) == 1


def test_degree(graph_with_nodes: TypedHypergraph):
    edge = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["f1", "f2"])
    graph_with_nodes.add_edge(edge)
    assert graph_with_nodes.degree("f1") == 1
    assert graph_with_nodes.degree("f2") == 1
    assert graph_with_nodes.degree("t1") == 0


# ---------------------------------------------------------------------------
# Confidence management
# ---------------------------------------------------------------------------


def test_confidence_decay(graph_with_nodes: TypedHypergraph):
    f1 = graph_with_nodes.get_node("f1")
    assert f1 is not None
    original = f1.confidence
    graph_with_nodes.decay_confidence("f1", 0.5)
    assert f1.confidence == pytest.approx(original * 0.5)
    assert len(f1.history) == 1  # revision recorded


def test_recompute_confidence_after_adding_edges(graph_with_nodes: TypedHypergraph):
    edge = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["f1", "f2"])
    graph_with_nodes.add_edge(edge)
    new_c = graph_with_nodes.recompute_confidence("f1", c_extract=0.8)
    assert 0.0 <= new_c <= 1.0


# ---------------------------------------------------------------------------
# ConflictDetector
# ---------------------------------------------------------------------------


@pytest.fixture
def conflict_graph() -> TypedHypergraph:
    g = TypedHypergraph()
    g.add_node(TopicNode(id="t1", text="Alice facts"))
    ep = EpisodeNode(id="e1", topic_id="t1")
    g.add_node(ep)

    old = FactNode(
        id="old",
        episode_id="e1",
        subject="Alice",
        predicate="lives_in",
        obj="Beijing",
        t_valid=datetime(2026, 1, 1),
        t_invalid=None,
    )
    new = FactNode(
        id="new",
        episode_id="e1",
        subject="Alice",
        predicate="lives_in",
        obj="Shanghai",
        t_valid=datetime(2026, 5, 1),
        t_invalid=None,
    )
    g.add_node(old)
    g.add_node(new)
    return g


def test_contradiction_detected(conflict_graph: TypedHypergraph):
    detector = ConflictDetector()
    new_fact = conflict_graph.get_node("new")
    assert isinstance(new_fact, FactNode)
    records = detector.check(conflict_graph, new_fact)
    # Should detect a contradiction (same predicate, different object)
    assert len(records) > 0
    types = {r.conflict_type for r in records}
    assert ConflictType.CONTRADICTION in types


def test_contradiction_resolution_marks_arbitration(conflict_graph: TypedHypergraph):
    detector = ConflictDetector()
    new_fact = conflict_graph.get_node("new")
    assert isinstance(new_fact, FactNode)
    records = detector.check(conflict_graph, new_fact)
    for rec in records:
        if rec.conflict_type == ConflictType.CONTRADICTION:
            detector.resolve(conflict_graph, rec)
    old_fact = conflict_graph.get_node("old")
    assert isinstance(old_fact, FactNode)
    assert old_fact.conflict_status == "pending_arbitration"
    assert old_fact.confidence < 1.0  # confidence was decayed


def test_orthogonal_facts_coexist(graph_with_nodes: TypedHypergraph):
    detector = ConflictDetector()
    f3 = FactNode(
        id="f3",
        episode_id="e1",
        subject="Alice",
        predicate="likes",  # different predicate from existing facts
        obj="running",
        t_valid=datetime(2026, 1, 1),
    )
    graph_with_nodes.add_node(f3)
    records = detector.check(graph_with_nodes, f3)
    # All should be ORTHOGONAL (no other facts share "likes" predicate)
    for rec in records:
        assert rec.resolution == ConflictResolution.NO_ACTION


def test_temporal_conflict_invalidates_old_fact(empty_graph: TypedHypergraph):
    g = empty_graph
    g.add_node(TopicNode(id="t1"))
    g.add_node(EpisodeNode(id="e1", topic_id="t1"))

    t1 = datetime(2026, 1, 1)
    t2 = datetime(2026, 3, 1)

    old = FactNode(
        id="old",
        episode_id="e1",
        subject="Bob",
        predicate="role",
        obj="intern",
        t_valid=t1,
        t_invalid=datetime(2026, 6, 1),  # overlaps with new
    )
    new = FactNode(
        id="new",
        episode_id="e1",
        subject="Bob",
        predicate="role",
        obj="intern",  # same object, so no contradiction
        t_valid=t2,
        t_invalid=None,
    )
    g.add_node(old)
    g.add_node(new)

    detector = ConflictDetector()
    records = detector.check(g, new)
    temporal_records = [r for r in records if r.conflict_type == ConflictType.TEMPORAL_CONFLICT]
    assert len(temporal_records) > 0

    for rec in temporal_records:
        detector.resolve(g, rec)

    old_node = g.get_node("old")
    assert isinstance(old_node, FactNode)
    assert old_node.t_invalid == t2  # invalidated at new fact's t_valid


# ---------------------------------------------------------------------------
# TemporalPruner
# ---------------------------------------------------------------------------


def test_pruner_identifies_stale_low_confidence_nodes(empty_graph: TypedHypergraph):
    g = empty_graph
    g.add_node(TopicNode(id="t1"))
    g.add_node(EpisodeNode(id="e1", topic_id="t1"))

    stale = FactNode(
        id="stale",
        episode_id="e1",
        subject="X",
        predicate="y",
        obj="z",
        confidence=0.05,  # below threshold
        t_invalid=datetime(2020, 1, 1),  # expired long ago
    )
    fresh = FactNode(
        id="fresh",
        episode_id="e1",
        subject="A",
        predicate="b",
        obj="c",
        confidence=0.9,  # above threshold
    )
    g.add_node(stale)
    g.add_node(fresh)

    pruner = TemporalPruner(min_confidence=0.1, retention_days=30)
    prunable = pruner.prune(g)
    assert "stale" in prunable
    assert "fresh" not in prunable


# ---------------------------------------------------------------------------
# Graph statistics
# ---------------------------------------------------------------------------


def test_stats(graph_with_nodes: TypedHypergraph):
    edge = TypedHyperedge(edge_type=HyperedgeType.SEMANTIC, node_ids=["f1", "f2"])
    graph_with_nodes.add_edge(edge)
    stats = graph_with_nodes.stats()
    assert stats["total_nodes"] == 4
    assert stats["topics"] == 1
    assert stats["episodes"] == 1
    assert stats["facts"] == 2
    assert stats["total_edges"] == 1
    assert stats["edges_semantic"] == 1
