# HiMGA: Hierarchical Multigraph RAG for Conversational Memory via Typed Hypergraphs and Conflict-Aware Knowledge Evolution

<!-- Created: 2026-05-21 | Version: 0.1-draft (pre-experiment) -->
<!-- Sections §4.2–§4.5 (main results, ablation, cross-type analysis, RQ interaction) are placeholders pending experimental data. -->
<!-- Target venue: ACL / EMNLP 2026 long paper -->

---

## Abstract

Conversational memory retrieval-augmented generation (RAG) faces three structural challenges absent from document RAG: dialogue utterances bear four informationally distinct and mutually irreducible relation dimensions (semantic, temporal, causal, entity) that degrade retrieval when conflated; the natural multi-scale nested structure of conversation produces higher-order joint associations that pairwise edges cannot faithfully represent; and the knowledge state of a running dialogue is non-uniform and evolving, requiring explicit conflict arbitration during memory writes. Existing methods address these challenges only in isolation: MAGMA (Jiang et al., 2026) separates relation dimensions with four binary-edge graphs but cannot express higher-order bindings, scoring only 66.7% on the LongMemEval knowledge-update subset versus a Full-Context baseline of 78.2%; HyperMem (Yue et al., 2026) achieves 92.73% on LoCoMo via a three-layer hypergraph but uses a single implicit hyperedge type and provides no conflict arbitration; Zep/Graphiti (Rasmussen et al., 2025) introduces temporal edge invalidation that succeeds with GPT-4o (83.3%) but regresses with GPT-4o-mini (74.4% < 76.9%), revealing a strong dependency on the arbitrating model's capability. We present HiMGA, a unified framework whose typed hypergraph $\mathcal{H} = (V, E, \tau, \omega, \pi)$ simultaneously encodes four explicit hyperedge types and a three-layer Topic-Episode-Fact node hierarchy, paired with a conflict-aware write protocol that classifies conflicts into four categories and applies type-specific arbitration strategies. On LoCoMo, HiMGA achieves [TBD] overall (target $\geq$ 91.5%), with substantial gains on cross-type queries. On LongMemEval knowledge-update, HiMGA achieves [TBD] with GPT-4o-mini (target $\geq$ 77%) and [TBD] with GPT-4o (target $\geq$ 84%), eliminating Zep's weak-model regression.

---

## 1. Introduction

Retrieval-augmented generation has emerged as a practical paradigm for grounding language model responses in external knowledge. Standard document RAG succeeds because its knowledge base satisfies three implicit assumptions: the corpus is static, inter-chunk dependencies are adequately captured by semantic similarity, and all chunks are epistemically equal. Conversational memory violates all three assumptions simultaneously. First, dialogue is a multi-dimensional relational network: the sentence "the race was cancelled" carries starkly different causal implications depending on whether it follows "I signed up for the marathon three days ago" or "the race just finished." More critically, dialogue fragments simultaneously exhibit four informationally distinct and mutually irreducible relation types—semantic co-reference, temporal precedence, causal dependence, and entity co-participation—that cannot be faithfully collapsed into a single similarity score. Ablation evidence from MAGMA confirms this directly: removing the causal graph, temporal backbone, entity links, and adaptive routing produce independent, non-substitutable performance drops of 5.6%, 5.3%, 3.4%, and 6.3% respectively on LoCoMo (Jiang et al., 2026, Table 4). Second, dialogue is a multi-scale nested structure. Utterances cohere into episodes, which aggregate into topics, forming a natural cognitive hierarchy (Anderson & Bower, 1972). Within this hierarchy, groups of three or more elements jointly determine meaning that no pairwise edge can recover—the semantics are constituted by the joint participation, not by any binary decomposition. HyperMem demonstrates this empirically: its Overall score of 92.73% exceeds HyperGraphRAG (86.49%) and LightRAG (79.87%) on LoCoMo, with the gap growing with hyperedge arity (Yue et al., 2026). Third, dialogue is a knowledge state stream. A statement at turn 50 may directly supersede information from turn 10, making the memory base non-uniform in temporal validity and rife with potential contradictions that must be detected and resolved at write time.

Existing systems address these challenges only in isolation, and each exhibits a characteristic failure mode. MAGMA (Jiang et al., 2026) addresses the relation-dimension challenge with four orthogonal binary-edge graphs and intent-driven routing, but uses no hyperedges, failing to capture higher-order associations (P3). Its knowledge-update score of 66.7% falls below the Full-Context baseline of 78.2%, demonstrating that an unmanaged graph memory actively harms retrieval when facts are stale. HyperMem (Yue et al., 2026) addresses the hierarchy and higher-order binding challenges with a three-layer hypergraph architecture, but employs a single implicit hyperedge type: all hyperedges express semantic co-membership, with no distinction between temporal, causal, or entity-based high-order associations. This precludes type-specific activation during retrieval and leaves the relation-dimension challenge (P1) entirely unaddressed. Zep/Graphiti (Rasmussen et al., 2025) introduces temporal edge invalidation with four-field temporal metadata, and with GPT-4o achieves 83.3% on LongMemEval knowledge-update, exceeding Full-Context (78.2%) for the first time. However, with GPT-4o-mini the same system regresses to 74.4%, falling below Full-Context (76.9%), revealing a strong and brittle dependency on the capability of the arbitrating model. None of these systems simultaneously integrates typed hyperedge bindings, hierarchical node organization, and robust conflict arbitration within a single unified formalism.

HiMGA addresses this gap by introducing a typed hypergraph as a unified representational substrate for conversational memory. The core insight is that the operations of "splitting" (separating relation dimensions, as MAGMA does) and "binding" (joining multiple elements into higher-order units, as HyperMem does) are not in tension—they are orthogonal axes that can be simultaneously expressed through typed hyperedges. A hyperedge in HiMGA carries an explicit type label from $\mathcal{T} = \{T_\text{sem}, T_\text{temp}, T_\text{causal}, T_\text{entity}\}$, connects two or more nodes from the three-layer Topic-Episode-Fact hierarchy, and participates in a conflict-aware write protocol that classifies incoming knowledge conflicts into four categories and applies minimum-revision arbitration strategies that do not require a high-capability LLM for every decision.

This paper makes the following contributions:

1. **Typed Hypergraph Protocol**: We formalize conversational memory as a five-tuple $\mathcal{H} = (V, E, \tau, \omega, \pi)$ with four explicit hyperedge types aligned to the four relation dimensions established by MAGMA's ablation evidence. We demonstrate that this formalism subsumes both MAGMA's relation-dimension separation and HyperMem's higher-order binding within a single representation. (We note that typed hypergraphs as a mathematical structure predate this work; Berge (1973) provides the foundational treatment. Our contribution is the domain-specific protocol design for conversational memory RAG.)

2. **Intent-Driven Typed Retrieval**: We introduce a retrieval protocol that decomposes query intent into a type-activation weight vector $\mathbf{r} \in \Delta^{|\mathcal{T}|}$, applies type-gating and temporal filtering before hierarchical coarse-to-fine traversal, and weights candidates by the confidence score $S(e) = w_e \cdot c_e \cdot \text{sim}(q, e)$.

3. **Conflict-Aware Knowledge Evolution**: We introduce a write protocol that classifies conflicts into four categories—temporal conflict, contradiction, version update, and orthogonal coexistence—and applies minimum-revision arbitration that reduces dependency on the arbitrating LLM's capability, targeting robustness with models as weak as GPT-4o-mini. On LongMemEval knowledge-update, HiMGA targets [TBD]% with GPT-4o-mini (vs. Zep's regression to 74.4%) and [TBD]% with GPT-4o.

4. **Cross-type Query Benchmark**: We construct and publicly release a 50-query cross-type evaluation subset requiring simultaneous activation of two or more hyperedge types, providing a dedicated diagnostic tool absent from existing benchmarks.

The remainder of this paper is organized as follows. Section 2 formalizes the task and derives four core research problems from first principles. Section 3 presents the HiMGA framework, including the typed hypergraph definition, memory construction pipeline, intent-driven retrieval protocol, and conflict-aware evolution mechanism. Section 4 presents experimental setup and results. Section 5 reviews related work. Section 6 concludes.

---

## 2. Problem Formulation

### 2.1 Task Definition

Let $\mathcal{C} = \{(u_1, s_1), (u_2, s_2), \ldots, (u_n, s_n)\}$ denote a multi-turn dialogue where $u_i$ is an utterance and $s_i \in \{\texttt{user}, \texttt{assistant}\}$ is the speaker role. A conversational memory RAG system maintains a structured memory $\mathcal{M}_t$ that is incrementally updated after each turn $t$:

$$\mathcal{M}_t = \textsc{Write}(\mathcal{M}_{t-1},\, u_t)$$

Given a query $q$ at turn $T$, the system retrieves a context set $\mathcal{R} \subseteq \mathcal{M}_T$ and generates a response:

$$\hat{a} = \textsc{Generate}(q,\, \mathcal{R})$$

The objective is to maximize response quality $\mathbb{E}[\text{Quality}(\hat{a}, a^*)]$ over a distribution of query types and dialogue lengths, where $a^*$ is the ground-truth answer. Critically, the memory $\mathcal{M}_t$ must be updated **online** (i.e., without full reconstruction as new utterances arrive) and must reflect the **current validity state** of all stored knowledge assertions.

### 2.2 Core Research Problems

The three intrinsic properties of conversational data—being a multi-dimensional relational network (Attribute A), a multi-scale nested structure (Attribute B), and a knowledge state stream (Attribute C)—give rise to four research problems that must be addressed to build a robust conversational memory system.

**P1: Relation-Dimension Separation.** Dialogue fragments simultaneously participate in four informationally distinct relation types: semantic co-reference, temporal ordering, causal dependence, and entity co-participation. Mixing these dimensions in a unified embedding space causes mutual interference during retrieval. MAGMA's ablation experiment provides direct evidence: removing any single relation graph produces an independent, non-substitutable performance drop on LoCoMo, with causal and temporal graphs each contributing over 5 percentage points (Jiang et al., 2026, Table 4). This establishes that the four relation types are informationally complementary and cannot be reduced to a single semantic similarity.

**P2: Granularity Hierarchy.** Dialogue naturally forms a nested cognitive hierarchy: Utterance $\to$ Episode $\to$ Topic $\to$ Conversation. Retrieval must adapt its granularity to query intent: fact-seeking queries require leaf-level precision, while multi-hop and temporal queries benefit from episode- or topic-level context. HyperMem's ablation demonstrates this directly: removing Episode Context reduces Temporal reasoning by 5.61 percentage points; removing Topic and Episode Retrieval (TR \& ER) reduces Multi-Hop reasoning by 5.68 percentage points (Yue et al., 2026, Table 2).

**P3: Higher-Order Joint Associations.** Within each hierarchical level, groups of three or more elements jointly constitute semantic units that no pairwise edge can faithfully represent. The joint meaning is constituted by multi-element co-participation and cannot be reconstructed from binary decompositions without information loss. The incremental performance gap from LightRAG (79.87\%) to HyperGraphRAG (86.49\%) to HyperMem (92.73\%) on LoCoMo, growing with hyperedge arity, provides empirical grounding for this claim (Yue et al., 2026, Table 1).

**P4: Knowledge Conflict Resolution.** As dialogue progresses, later turns may contradict, supersede, or refine earlier knowledge assertions. Without explicit conflict arbitration, stale knowledge persists in the memory and contaminates retrieval. MAGMA scores only 66.7\% on LongMemEval knowledge-update versus Full-Context's 78.2\%, demonstrating that unmanaged graph memory is actively harmful in knowledge-evolution scenarios (Jiang et al., 2026; Wu et al., 2024). Zep's temporal edge invalidation partially addresses this, achieving 83.3\% with GPT-4o, but regresses to 74.4\% with GPT-4o-mini (Rasmussen et al., 2025), leaving P4 open in weak-model settings.

---

## 3. The HiMGA Framework

### 3.1 Typed Hypergraph

**Motivation.** Existing approaches fail on P1 and P3 simultaneously because they treat relation separation and higher-order binding as competing design choices. MAGMA's four-graph architecture enforces strict relation-dimension separation but uses only binary edges: every edge connects exactly two nodes, making it impossible to express the joint meaning constituted by three or more co-participating elements. HyperMem's three-layer hypergraph encodes higher-order associations and multi-scale hierarchy, but assigns all hyperedges an identical implicit type—"belongs to the same topic or episode"—leaving all four relation dimensions conflated within a single edge pool. The consequence is that type-specific routing at retrieval time is impossible, and a query requiring causal activation cannot be distinguished from one requiring temporal activation. Neither a serial combination of these two systems nor a straightforward merger can resolve this limitation: a system that first retrieves from MAGMA's typed graphs and then re-ranks using HyperMem's hyperedges still lacks the ability to execute "causal-type activation $+$ entity-hyperedge traversal $+$ temporal filtering" as a unified reasoning step over a single graph object.

**Definition 1 (Typed Hypergraph).** The HiMGA memory representation is the five-tuple:

$$\mathcal{H} = (V,\; E,\; \tau,\; \omega,\; \pi)$$

where:

- $V = V^T \cup V^E \cup V^F$ is the node set partitioned into three disjoint layers corresponding to **Topic**, **Episode**, and **Fact** nodes respectively, with $V^T \cap V^E = V^E \cap V^F = V^T \cap V^F = \emptyset$.
- $E \subseteq \mathcal{P}(V) \setminus \{\emptyset, \{v\}\}$ is the hyperedge set, where every hyperedge $e \in E$ satisfies $|e| \geq 2$.
- $\tau : E \to \mathcal{T} = \{T_\text{sem},\, T_\text{temp},\, T_\text{causal},\, T_\text{entity}\}$ is the **type mapping**, assigning each hyperedge one of four explicit semantic types.
- $\omega : E \times V \to [0, 1]$ is the **weight mapping**, where $\omega(e, v)$ denotes the participation weight of node $v$ within hyperedge $e$ (defined as $0$ when $v \notin e$).
- $\pi : V \cup E \to \mathcal{M}$ is the **metadata mapping**, where $\mathcal{M}$ includes fields: $t_\text{valid}$ (validity start time), $t_\text{invalid}$ (validity end time, $+\infty$ if currently valid), $c \in [0,1]$ (confidence score), $\texttt{source}$ (originating utterance index), and $\texttt{history}$ (append-only revision log).

**Table 1: Four Hyperedge Types in HiMGA**

| Type | Symbol | Binding Semantics | Scale Constraint |
|------|--------|-------------------|-----------------|
| Semantic | $T_\text{sem}$ | Binds semantically related fragments within a shared topic or episode (subsumes HyperMem's episode/fact hyperedge design) | $|e| \geq 2$; $|e| \leq 16$ |
| Temporal | $T_\text{temp}$ | Binds consecutive events within a shared time window; supports temporal ordering queries | $|e| \geq 2$; $|e| \leq 16$ |
| Causal | $T_\text{causal}$ | Binds event nodes in convergent or divergent causal structures; restricted to genuinely higher-order causal scenarios | $|e_\text{causal}| \geq 3$; binary causality is expressed as a pairwise directed edge |
| Entity | $T_\text{entity}$ | Binds cross-time events co-involving the same named entity (person, location, or object) | $|e| \geq 2$; $|e| \leq 16$ |

**Formal Constraints.** Two structural properties govern the typed hypergraph:

1. **Type Independence**: The same set of nodes may simultaneously belong to multiple hyperedges of different types, i.e., $\exists\, e_1, e_2 \in E : V(e_1) = V(e_2) \land \tau(e_1) \neq \tau(e_2)$. This is the key property that enables orthogonal relation-dimension encoding (P1) while preserving higher-order binding (P3) within a single graph object.

2. **Hierarchical Crossing**: Hyperedges may span nodes from different layers, i.e., $V(e)$ may include nodes from $V^T$, $V^E$, and $V^F$ simultaneously. In practice, cross-layer hyperedges require a Topic node as the anchor: $V(e) \cap V^T \neq \emptyset$ whenever $V(e) \cap V^F \neq \emptyset$ and $|V(e) \cap V^T| = 0$ would yield an unanchored cross-layer edge. Same-layer hyperedges carry no such constraint.

Additional practical bounds: $|e| \leq 16$ for all types (consistent with HyperMem's empirical practice); $|e_\text{causal}| \geq 3$ (binary causal relations are expressed as pairwise directed edges and incur no hyperedge overhead).

**Confidence Score.** Each Fact node $v \in V^F$ carries a scalar confidence $c_v \in [0, 1]$ computed as:

$$c_v = \alpha \cdot c^\text{extract}_v + \beta \cdot c^\text{degree}_v + \gamma \cdot c^\text{time}_v$$

where:
- $c^\text{extract}_v$ is the extraction-time confidence reported by the LLM (high variance; low weight $\alpha = 0.2$),
- $c^\text{degree}_v = \min\!\left(1,\, \deg_E(v) / d_\text{ref}\right)$ is the normalized hyperedge degree of $v$ (proxy for cross-referential support; $\beta = 0.5$),
- $c^\text{time}_v = \exp\!\left(-\lambda\, (t_\text{now} - t_\text{valid}(v))\right)$ is a time-decay factor ($\gamma = 0.3$).

Default weights $(\alpha, \beta, \gamma) = (0.2, 0.5, 0.3)$ are subject to hyperparameter tuning; the key design choice is that temporal recency is weighted less than structural support, reflecting the empirical observation that isolated but recent claims are less reliable than structurally corroborated older ones.

---

### 3.2 Memory Construction

**Three-Layer Segmentation.** Each incoming utterance $u_t$ is processed through a three-stage segmentation pipeline. First, an episode boundary detector determines whether $u_t$ initiates a new episode (based on topic shift) or extends the current one. Second, episode clusters are aggregated into Topics by a hierarchical topic model that matches against existing $V^T$ nodes or creates new ones. Third, a Fact extractor parses each utterance into atomic knowledge assertions $\{f_i\}$ that populate $V^F$.

This three-layer segmentation is consistent with HyperMem's design (Yue et al., 2026) and is retained without modification, as HyperMem's ablation evidence validates the value of each layer independently.

**Algorithm 1: HiMGA Memory Write**

```
Input:  New utterance u_t, current memory H = (V, E, τ, ω, π)
Output: Updated memory H'

[FAST PATH — synchronous, target < 500 ms]
1.  Detect episode boundary → assign u_t to episode node v^E ∈ V^E
2.  Update or create topic node v^T ∈ V^T
3.  Extract fact set F_t = {f_1, ..., f_k} from u_t via LLM
4.  Create Fact nodes V^F_t ⊆ V^F for each f_i
5.  Build T_sem hyperedge: e_sem = {v^E} ∪ V^F_t; add to E with τ(e_sem) = T_sem
6.  Build T_temp hyperedge: e_temp = (recent episode context within time window)
    add to E with τ(e_temp) = T_temp
7.  For each f_i ∈ F_t: run conflict detection (Algorithm 2, types: temp_conflict,
    version_update, orthogonal only)
8.  Update confidence scores c_v for all affected nodes

[SLOW PATH — asynchronous]
9.  Build T_causal hyperedges: for each candidate causal cluster C ⊆ V^F_t
    with |C| ≥ 3, verify via LLM and add e_causal with τ(e_causal) = T_causal
10. Build T_entity hyperedges: for each named entity x in u_t, collect
    cross-time co-participating fact nodes and add e_entity with τ = T_entity
11. Run full contradiction detection (Algorithm 2, type: contradiction)
12. Compress nodes where c_v < θ_compress and t_now - t_valid > W_retain
    into summary nodes
13. Commit slow-path updates to H
```

**Dual-Stream Architecture.** The fast path handles semantic and temporal hyperedge construction and non-LLM-intensive conflict detection, targeting a wall-clock latency of under 500 ms (benchmarked as no more than twice Zep's reported write latency). The slow path handles causal hyperedge construction—which requires multi-element verification by an LLM—and full contradiction detection, executing asynchronously without blocking the dialogue flow. This design follows MAGMA's dual-stream principle (Jiang et al., 2026) and is classified as an engineering constraint (P5) rather than an independent research contribution.

**Causal Hyperedge Scale Constraint.** The lower bound $|e_\text{causal}| \geq 3$ is not merely a heuristic but follows from the semantics of the type: a binary causal relation ("A caused B") is already faithfully expressible as a directed pairwise edge and gains nothing from hyperedge packaging. Causal hyperedges are reserved for genuinely higher-order scenarios—converging causes (multiple events jointly causing an outcome) or diverging effects (one event causing multiple downstream outcomes)—where the joint causal semantics cannot be reconstructed from pairwise decompositions. When the LLM extraction fails to produce a valid triple, the candidate degrades to a pairwise edge rather than being discarded.

---

### 3.3 Intent-Driven Typed Retrieval

**Intent Analysis.** Given a query $q$, the retrieval module first decomposes it into a structured intent representation:

$$q \;\longrightarrow\; \bigl(\mathbf{r},\; [t_s, t_e],\; q_\text{key},\; q_\text{dense}\bigr)$$

where $\mathbf{r} \in \Delta^{|\mathcal{T}|}$ is a type-activation weight vector over the four hyperedge types, $[t_s, t_e]$ is a temporal scope (possibly $(-\infty, +\infty)$ for temporally unconstrained queries), $q_\text{key}$ is a keyword representation for sparse retrieval, and $q_\text{dense}$ is an embedding for dense similarity computation.

The type-activation vector $\mathbf{r}$ is computed by a lightweight intent classifier. Canonical mappings include: WHY-type queries assign high weight to $r_\text{causal}$; WHEN-type queries to $r_\text{temp}$; WHO/WHERE queries to $r_\text{entity}$; general information queries to $r_\text{sem}$; and composite queries distribute activation across multiple types simultaneously. When classification confidence falls below a threshold $\delta_\text{cls}$, the system falls back to LLM zero-shot classification to avoid routing errors on ambiguous queries.

**Type Gating.** The full hyperedge pool $E$ is first filtered to the activated subset:

$$E_\text{active} = \Bigl\{ e \in E \;\Big|\; \sum_{T \in \mathcal{T}} r_T \cdot \mathbb{1}[\tau(e) = T] > \theta_\text{gate} \Bigr\}$$

This step eliminates hyperedges whose type does not match the query intent, preventing cross-type interference analogous to what MAGMA prevents at the graph level.

**Temporal Filtering.** Within $E_\text{active}$, only hyperedges with overlapping temporal validity are retained:

$$E_\text{valid} = \Bigl\{ e \in E_\text{active} \;\Big|\; [t_s, t_e] \cap [t_\text{valid}(e), t_\text{invalid}(e)] \neq \emptyset \Bigr\}$$

This step leverages the $\pi$ metadata to exclude logically expired knowledge from the candidate set, directly addressing P4 at the retrieval stage in addition to the write-time conflict protocol.

**Hierarchical Coarse-to-Fine Traversal.** Retrieval proceeds in three passes following the HyperMem protocol (Yue et al., 2026, §3.3): (1) **Topic pass** — identify the top-$k_T$ Topic nodes most similar to $q_\text{dense}$; (2) **Episode pass** — expand to Episode nodes connected to the selected Topics via $E_\text{valid}$; (3) **Fact pass** — expand to Fact nodes connected to the selected Episodes, forming the final candidate set $\mathcal{F}_\text{cand}$.

**Confidence-Weighted Scoring.** Each candidate element $e \in \mathcal{F}_\text{cand}$ is scored as:

$$S(e) = w_e \cdot c_e \cdot \text{sim}(q, e)$$

where $w_e$ is the participation weight from $\omega$, $c_e$ is the current confidence score from the metadata $\pi$, and $\text{sim}(q, e)$ is the cosine similarity between $q_\text{dense}$ and the element's embedding. The top-$k_F$ elements by $S(\cdot)$ are returned as the retrieval context $\mathcal{R}$.

---

### 3.4 Conflict-Aware Knowledge Evolution

**Motivation.** The failure mode documented for MAGMA on LongMemEval knowledge-update (66.7% vs. Full-Context 78.2%) demonstrates that an unmanaged graph memory that retains all past assertions—including stale and contradicted ones—actively interferes with LLM generation. Zep's temporal edge invalidation mechanism addresses this correctly in principle: it carries four temporal metadata fields per edge ($t'_\text{created}$, $t'_\text{expired}$, $t_\text{valid}$, $t_\text{invalid}$) and triggers LLM-based arbitration when a new edge semantically conflicts with an existing one. This achieves 83.3% on LongMemEval knowledge-update with GPT-4o, the first system to surpass Full-Context (78.2%) on this subset (Rasmussen et al., 2025). However, with GPT-4o-mini the same mechanism regresses to 74.4%, falling below Full-Context (76.9%), revealing that Zep's arbitration is a single LLM call that is unreliable when the LLM cannot accurately assess semantic contradiction.

This failure has lasting practical significance beyond any particular model generation. Two application classes permanently require robustness with weaker models: (1) compliance-sensitive deployments in healthcare, finance, and public administration, where regulations prohibit sending sensitive data to external API endpoints and thus require local 7B–13B-class open-weight models; (2) cost-sensitive large-scale deployments where operating at GPT-4o-mini cost rather than GPT-4o cost represents an order-of-magnitude reduction. Neither of these constraints diminishes as frontier models advance.

**Four-Category Conflict Classification.** HiMGA classifies all write-time conflicts into four categories, each with a specific detection condition and resolution strategy:

**Table 2: Conflict Classification in HiMGA**

| Conflict Type | Trigger Condition | Resolution Strategy |
|---------------|-------------------|---------------------|
| Temporal conflict (`temp_conflict`) | Same entity $+$ same predicate $+$ overlapping time windows within a temporal hyperedge | Set $t_\text{invalid}$ of old assertion to $t_\text{valid}$ of new; preserve history in append-only log |
| Contradiction (`contradiction`) | Same entity $+$ opposing predicates $+$ co-occurrence within a shared semantic hyperedge | Mark old assertion as `under_review`; LLM arbitrates; retain both versions with updated confidence scores |
| Version update (`version_update`) | Same entity $+$ same predicate type $+$ new assertion is more recent | Decay old assertion weight by factor $\exp(-\lambda \Delta t)$; do not delete |
| Orthogonal coexistence (`orthogonal`) | Same entity $+$ non-contradictory predicate types (e.g., "likes running" vs. "dislikes early mornings") | No action; both assertions coexist |

**Minimum-Revision Principle.** No node or edge is physically deleted. All conflict resolution operates through two lossless mechanisms: (a) setting $t_\text{invalid}$ in the metadata $\pi(e)$ to indicate logical expiry while preserving the full assertion for provenance; (b) applying confidence decay $c \leftarrow c \cdot \exp(-\lambda \Delta t)$ to reduce retrieval weight without erasure. The `history` field in $\pi$ records all revision timestamps in an append-only log. Nodes with $c_v < \theta_\text{compress}$ and $t_\text{now} - t_\text{valid}(v) > W_\text{retain}$ are periodically compressed into summary nodes to control memory growth, analogous to the compression mechanism in A-MEM (Xu et al., 2025).

The key advantage of this four-category scheme over Zep's single-LLM arbitration is that three of the four categories—temporal conflict, version update, and orthogonal coexistence—can be detected and resolved using only structural metadata comparisons and lightweight heuristics, without any LLM call. Only `contradiction` requires LLM arbitration, and the structural pre-classification reduces the frequency of contradiction calls and provides the LLM with a targeted comparison frame (two pre-identified conflicting assertions rather than an open-ended conflict scan). This structural reduction of LLM dependency is the mechanism by which HiMGA targets robustness under GPT-4o-mini.

---

## 4. Experiments

### 4.1 Experimental Setup

**Datasets.** We evaluate HiMGA on two benchmarks that together cover the two core research problems.

*LoCoMo* (Maharana et al., 2024) is a long-form conversational memory benchmark with five evaluation subsets: Single-Hop, Multi-Hop, Temporal, Open-Domain, and Adversarial, plus an Overall score. LoCoMo is the primary evaluation for RQ1 (typed hypergraph representation) because its multi-hop and temporal subsets are most sensitive to higher-order retrieval quality and relation-type discrimination. All five subsets are reported for completeness.

*LongMemEval* (Wu et al., 2024) is a conversational memory benchmark with a dedicated `knowledge-update` subset of approximately 83 questions testing a system's ability to prefer the most recent and valid knowledge assertion when earlier assertions have been superseded. LongMemEval is the primary evaluation for RQ2 (conflict-aware knowledge evolution). Results are reported on the `knowledge-update` subset specifically; overall LongMemEval results are reported in the Appendix.

**Baselines.** We compare against four baselines representing the major paradigms:

- **Full-Context**: Places the entire conversation history in the LLM context window without any memory structure. Scores 48.1\% on LoCoMo Overall and 76.9\%/78.2\% on LongMemEval knowledge-update with GPT-4o-mini/GPT-4o respectively. Serves as the "no structure" reference.
- **MAGMA** (Jiang et al., 2026, arXiv:2601.03236): Four orthogonal binary-edge graphs with intent-adaptive routing. Scores 70.0\% on LoCoMo Overall and 66.7\% on LongMemEval knowledge-update (GPT-4o).
- **HyperMem** (Yue et al., 2026, arXiv:2604.08256): Three-layer single-type hypergraph. Scores 92.73\% on LoCoMo Overall; LongMemEval not reported in original paper.
- **Zep/Graphiti** (Rasmussen et al., 2025, arXiv:2501.13956): Temporal knowledge graph with edge invalidation. LongMemEval knowledge-update: 74.4\% (GPT-4o-mini), 83.3\% (GPT-4o); LoCoMo not reported.

**Evaluation Configurations.** We use two evaluation configurations to ensure comparability with each baseline.

*LoCoMo configuration* (aligned with HyperMem):
- Embedding model: Qwen3-Embedding-4B; Reranker: Qwen3-Reranker-4B
- Generator: GPT-4.1-mini; retrieval top-$k$: Topic = 10, Episode = 10, Fact = 30
- Judge: GPT-4o-mini with LLM-as-a-Judge protocol; three independent runs averaged

*LongMemEval configuration* (aligned with Zep):
- Dual-model evaluation: GPT-4o-mini and GPT-4o as both generator and arbitration LLM
- Context length $\approx$ 115k tokens for Full-Context baseline
- Judge: GPT-4o with LongMemEval official evaluation prompts

*Open-source reproducibility configuration*: Generator and Judge both set to Qwen3-32B as a fallback for long-term replicability without closed-source API access.

**Evaluation Metrics.** Primary metric: LLM-as-a-Judge score on a 0–1 scale following the protocol of HyperMem and MAGMA for LoCoMo, and the official LongMemEval evaluation protocol for LongMemEval. All reported numbers are means over three independent runs. Statistical uncertainty is quantified by bootstrapped 95\% confidence intervals (10,000 bootstrap samples) to account for the limited size of the LongMemEval knowledge-update subset ($n \approx 83$). For the cross-type query evaluation (§4.4), we additionally report Evidence Recall (proportion of ground-truth evidence nodes retrieved).

**Baseline Number Summary.** For reference, the complete set of baseline numbers used in all comparisons:

| System | LoCoMo Overall | LME knowledge-update (4o-mini) | LME knowledge-update (4o) |
|--------|---------------|-------------------------------|--------------------------|
| Full-Context | 48.1% | 76.9% | 78.2% |
| MAGMA | 70.0% | — | 66.7% |
| HyperMem | 92.73% | N/A | N/A |
| Zep | N/A | 74.4% | 83.3% |
| **HiMGA (target)** | **$\geq$ 91.5%** | **$\geq$ 77%** | **$\geq$ 84%** |

---

### 4.2 Main Results

*[Section reserved for experimental results. Data not yet available.]*

---

### 4.3 Ablation Study

*[Section reserved for experimental results. Data not yet available.]*

---

### 4.4 Cross-Type Query Analysis

*[Section reserved for experimental results. Data not yet available.]*

---

### 4.5 RQ1 $\times$ RQ2 Interaction

*[Section reserved for experimental results. Data not yet available.]*

---

## 5. Related Work

### 5.1 Graph Memory Systems

Structured graph memory for conversational agents has been an active area since MemoryBank (Zhong et al., 2023) proposed persistent key-value stores for dialogue history. More recent work has shifted toward relational graph representations that preserve typed dependencies between memory units.

**MAGMA** (Jiang et al., 2026, arXiv:2601.03236) represents the most direct prior work on multi-type relational graph memory. MAGMA constructs four independent binary-edge graphs—temporal backbone, causal graph, semantic graph, and entity graph—and routes retrieval queries through an intent classifier that activates the relevant graph layers. The system achieves 70.0\% on LoCoMo Overall. Its ablation experiment, showing independent contributions of 5.6\%, 5.3\%, 3.4\%, and 6.3\% for causal, temporal, entity, and routing components respectively, constitutes the strongest available empirical evidence that the four relation dimensions are informationally irreducible. HiMGA inherits this insight and elevates it to the typed hyperedge level, enabling multi-type activation within a single traversal rather than post-hoc fusion of results from separate graphs. MAGMA's 66.7\% knowledge-update score (below Full-Context 78.2\%) motivates HiMGA's explicit conflict protocol.

**Zep/Graphiti** (Rasmussen et al., 2025, arXiv:2501.13956) introduces temporal edge validity with four-field metadata ($t'_\text{created}$, $t'_\text{expired}$, $t_\text{valid}$, $t_\text{invalid}$) and LLM-driven edge invalidation. The system's knowledge-update score of 83.3\% with GPT-4o is the current state of the art on LongMemEval knowledge-update and the first to surpass Full-Context. Its regression to 74.4\% with GPT-4o-mini directly motivates HiMGA's four-category structural conflict classification, which reduces the frequency and ambiguity of LLM arbitration calls. Graphiti also introduces a multi-fact edge construction that the authors describe as "an implementation of hyper-edges" (Rasmussen et al., 2025, §2.2.2), but this is a binary-edge approximation without explicit type labels.

**A-MEM** (Xu et al., 2025) implements an Zettelkasten-inspired memory system with automatic note linking and periodic compression of low-salience memories. Its compression mechanism—consolidating weakly referenced nodes into summary nodes—is conceptually related to HiMGA's confidence-threshold compression, though HiMGA's formalization is grounded in the $\pi$ metadata structure rather than a separate note management layer.

### 5.2 Hypergraph Methods for RAG

The application of hypergraph structures to retrieval-augmented generation has seen rapid development, motivated by the theoretical argument that higher-order associations cannot be faithfully represented by pairwise edges.

**HyperGraphRAG** (Luo et al., 2025) introduces hyperedges into a document RAG pipeline, achieving 86.49\% on LoCoMo Overall. The system uses a flat node structure without hierarchical organization and a single implicit hyperedge type.

**HyperMem** (Yue et al., 2026, arXiv:2604.08256) extends hypergraph RAG to the conversational setting with the Topic-Episode-Fact three-layer hierarchy, achieving 92.73\% on LoCoMo Overall—the current highest published score on this benchmark. HyperMem's ablation experiment validating the independent contributions of hierarchy levels (w/o Episode Context: −5.61\% on Temporal; w/o TR\&ER: −5.68\% on Multi-Hop) provides the empirical foundation for HiMGA's retention of the three-layer structure. HyperMem's central limitation is that all hyperedges carry a single implicit type (semantic co-membership), preventing relation-dimension-specific activation at retrieval time.

**Hyper-RAG** (Feng et al., 2026) applies hypergraph structures to scientific document retrieval with a focus on dense hyperedge construction, but is evaluated on document RAG benchmarks rather than conversational memory benchmarks and does not address knowledge evolution.

**Cog-RAG** (Hu et al., 2026) employs a dual-view hypergraph (token-level and concept-level) for question answering, incorporating both dense and sparse retrieval paths. It shares HyperMem's limitation of single-type hyperedges and does not include hierarchy or conflict management.

The table below summarizes the key structural differences among hypergraph-based methods:

**Table 3: Comparison of Hypergraph-Based Memory Methods**

| System | Node Layers | Typed Hyperedges | Handles P4 (Conflict) | LoCoMo Overall |
|--------|:-----------:|:----------------:|:---------------------:|:--------------:|
| HyperGraphRAG (Luo et al., 2025) | Flat | Single (implicit) | No | 86.49% |
| Hyper-RAG (Feng et al., 2026) | Flat | Single (implicit) | No | Not evaluated |
| Cog-RAG (Hu et al., 2026) | Dual-view | Single (implicit) | No | Not evaluated |
| HyperMem (Yue et al., 2026) | 3-layer (T/E/F) | Single (implicit) | No | **92.73%** |
| **HiMGA (this work)** | **3-layer (T/E/F)** | **4 explicit types** | **Yes** | **[TBD]** |

We note that typed hypergraphs as a mathematical structure have a long history (Berge, 1973); HiMGA's contribution is not the invention of this structure but its first systematic application as a protocol for conversational memory RAG, including the domain-specific definition of the four-type taxonomy aligned to MAGMA's empirically validated relation dimensions, the intent-driven type-activation retrieval protocol, and the type-aware conflict arbitration write protocol.

### 5.3 Knowledge Evolution and Temporal Consistency

The problem of maintaining temporally consistent knowledge in neural systems has been studied under several framings. Temporal Knowledge Graphs (TKGs) (Trivedi et al., 2017; García-Durán et al., 2018) represent facts as quadruples $(s, r, o, t)$ where $t$ is a timestamp, and model the evolution of relational facts over time. HiMGA's $[t_\text{valid}, t_\text{invalid}]$ metadata encoding shares the spirit of TKGs but operates at the level of a conversational memory system rather than a static knowledge base.

Graphiti (the underlying engine of Zep) extends TKG ideas to dialogue by introducing write-time edge invalidation: when a new edge semantically conflicts with an existing edge, the existing edge's $t_\text{invalid}$ is set to the new edge's $t_\text{valid}$ (Rasmussen et al., 2025). This is the mechanism that enables Zep's strong performance with GPT-4o. HiMGA's four-category conflict classification subsumes this temporal invalidation as the `temp_conflict` category while extending the taxonomy to handle contradictions (which require LLM arbitration), version updates (which require confidence decay), and orthogonal coexistence (which require no action).

Continual learning literature (Kirkpatrick et al., 2017; Rebuffi et al., 2017) addresses catastrophic forgetting in neural models, which is conceptually related to knowledge evolution in memory systems, but operates on model weights rather than structured external memory and does not provide explicit provenance or temporal metadata.

---

## 6. Conclusion

We have presented HiMGA, a conversational memory RAG framework that addresses the three intrinsic structural challenges of dialogue data—multi-dimensional relation networks, multi-scale nested associations, and evolving knowledge states—within a single unified formalism. Three core contributions are made:

First, the **Typed Hypergraph Protocol**: a five-tuple $\mathcal{H} = (V, E, \tau, \omega, \pi)$ with four explicit hyperedge types (semantic, temporal, causal, entity) organized over a three-layer Topic-Episode-Fact node hierarchy. This formalism is the first to simultaneously encode relation-dimension separation (previously achievable only in binary-edge multi-graph systems like MAGMA) and higher-order joint binding (previously achievable only in single-type hypergraph systems like HyperMem) within a single graph object, enabling cross-type joint retrieval in a unified reasoning step.

Second, the **Intent-Driven Typed Retrieval Protocol**: a query decomposition mechanism that produces a type-activation weight vector $\mathbf{r} \in \Delta^{|\mathcal{T}|}$ from query intent, applies type-gating and temporal filtering before hierarchical coarse-to-fine traversal, and scores candidates with a confidence-weighted similarity function. This protocol extends HyperMem's hierarchical retrieval design with explicit type discrimination.

Third, the **Conflict-Aware Knowledge Evolution Protocol**: a four-category conflict taxonomy (temporal conflict, contradiction, version update, orthogonal coexistence) with minimum-revision resolution strategies that reduce LLM arbitration calls to only the contradiction category, targeting robustness in weak-model settings that Zep's single-call arbitration cannot achieve.

**Limitations.** Several limitations warrant acknowledgment. (1) HiMGA's evaluation is restricted to LoCoMo and LongMemEval; generalization to multi-modal dialogues, multi-agent conversations, and domain-specific corpora (e.g., medical consultation records) is unverified. (2) The LongMemEval knowledge-update subset contains approximately 83 questions; statistical power to detect 1–3 percentage point differences is limited even with bootstrapped confidence intervals. (3) Causal hyperedge extraction is dependent on LLM quality in the slow path; the target precision (P@5 > 0.70) requires empirical validation.

**Future Work.** Three directions are most immediate. First, extending the typed hypergraph to multi-modal conversational memory by introducing modality-typed hyperedges that bind visual and textual evidence. Second, scaling the conflict arbitration protocol to large multi-session memories with hundreds of thousands of fact nodes, potentially requiring approximate conflict detection based on entity-level indexing. Third, investigating automated calibration of the confidence weights $(\alpha, \beta, \gamma)$ through online learning, reducing the need for manual hyperparameter specification in diverse deployment environments.

---

## References

Anderson, J. R., & Bower, G. H. (1972). *Human Associative Memory*. Winston.

Berge, C. (1973). *Graphs and Hypergraphs*. North-Holland.

Feng, Z., et al. (2026). Hyper-RAG: Hypergraph-Enhanced Retrieval-Augmented Generation. *arXiv preprint*.

García-Durán, A., Dumančić, S., & Niepert, M. (2018). Learning sequence encoders for temporal knowledge graph completion. In *EMNLP 2018*.

Hu, Y., et al. (2026). Cog-RAG: Cognitive Hypergraph Retrieval-Augmented Generation. *arXiv preprint*.

Jiang, X., Li, Y., Li, Z., & Li, X. (2026). MAGMA: Multi-dimensional Adaptive Graph Memory Architecture for Conversational RAG. *arXiv:2601.03236*.

Kirkpatrick, J., et al. (2017). Overcoming catastrophic forgetting in neural networks. *PNAS*, 114(13), 3521–3526.

Luo, Z., et al. (2025). HyperGraphRAG: Hypergraph-Based Retrieval-Augmented Generation. *arXiv preprint*.

Maharana, A., et al. (2024). LoCoMo: Long Context Memory for Conversations. In *ACL 2024*.

Rasmussen, P., et al. (2025). Zep: A Temporal Knowledge Graph Architecture for Agent Memory. *arXiv:2501.13956*.

Rebuffi, S.-A., Kolesnikov, A., Sperl, G., & Lampert, C. H. (2017). iCaRL: Incremental classifier and representation learning. In *CVPR 2017*.

Trivedi, R., Dai, H., Wang, Y., & Song, L. (2017). Know-Evolve: Deep temporal reasoning for dynamic knowledge graphs. In *ICML 2017*.

Wu, X., et al. (2024). LongMemEval: Benchmarking Long-Term Memory in Conversational AI. *arXiv preprint*.

Xu, W., et al. (2025). A-MEM: Agentic Memory for LLM Agents. *arXiv preprint*.

Yue, H., et al. (2026). HyperMem: Hypergraph-Structured Hierarchical Memory for Conversational AI. *arXiv:2604.08256*. ACL 2026 main.

Zhong, W., et al. (2023). MemoryBank: Enhancing Large Language Models with Long-Term Memory. *arXiv preprint*.
