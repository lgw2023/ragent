# Expert B's Revised Vision (v2): Uncertainty-Aware Concurrent Entity Resolution & Deterministic Graph Materialization

Based on the synthesis in [`review_round_1.md`](file:///Volumes/SSD1/ragent/docs/research/review_round_1.md), I have refined my thoughts. The reviewer correctly identified a critical chicken-and-egg dilemma in my previous "Semantic Lock Manager" proposal: **to allocate a semantic lock, the system must first perform Entity Resolution (ER); however, to safely perform concurrent ER, the system requires locks to prevent race conditions on the graph structure.**

To resolve this circular dependency while keeping my emphasis on **semantic conflict awareness**, I present **MAGEv2 (Materialization & Alignment Graph Engine, Version 2)**. This revised design shifts the paradigm from *fine-grained semantic locking* to *epoch-based snapshot-isolated resolution with lazy conflict detection*.

---

## 1. Core Problem: The Resolution-Structure Circular Dependency

We formalize the core academic problem of the paper as the **Resolution-Structure Circular Dependency (RSCD)**:
* Let $G_t$ be the state of the Canonical Knowledge Graph at time $t$.
* Let $M = \{m_1, m_2, \dots\}$ be the concurrent stream of LLM-extracted mentions.
* The entity resolution decision for a mention $m_i$ depends on the surrounding graph context: $ER(m_i) = f(m_i, G_t)$.
* However, committing the resolution decision immediately updates the graph: $G_{t+1} = G_t \cup ER(m_i)$.
* Under high concurrency, multiple threads attempt to resolve different mentions simultaneously, reading and writing to $G$ in an uncoordinated manner, leading to semantic corruption (e.g., incorrect merges due to stale reads) or lock deadlocks.

```
       [Graph Context G_t]
             |      ^
  Reads G_t  |      | Writes G_{t+1} (updates structure)
             v      |
       [Entity Resolution ER(m_i)]
```

---

## 2. Refined Architecture: MAGEv2

MAGEv2 solves RSCD by replacing active run-time locking with **Epoch-based Snapshot Isolation (ESI)** and **Deterministic Materialization**, structured as follows:

```
+-----------------------------------------------------------------------------------+
|                            LLM Extraction Workers                                 |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               Mention Log / Staging Graph (Append-only Raw Mentions)              |
+-----------------------------------------------------------------------------------+
                                          |
                                          v  (Group into Epochs)
+===================================================================================+
|                              MAGEv2 INGESTION LAYER                               |
|                                                                                   |
|  1. Epoch-based Snapshot Resolver                                                 |
|     - Reads a static read-only snapshot G_epoch                                   |
|     - Resolves all mentions in current epoch concurrently against G_epoch         |
|     - Produces Tentative Merge Decisions (TMD)                                    |
|                                                                                   |
|  2. Semantic Conflict Detector & Defer Queue                                      |
|     - Detects overlapping TMDs (e.g., two threads resolving different mentions     |
|       to the same entity, or splitting homonyms)                                  |
|     - Resolves conflicts deterministically (e.g., based on confidence scores)     |
|     - Defers highly ambiguous conflicts to a Defer Queue for LLM/Human review     |
|                                                                                   |
|  3. Deterministic Materializer                                                    |
|     - Commits resolved decisions to the Canonical KG                              |
|     - Uses CRDTs for metadata updates (alias sets, evidence logs, mention counts) |
|                                                                                   |
+===================================================================================+
                                          |
                                          v  (Atomic, lock-free batch upserts)
+-----------------------------------------------------------------------------------+
|                            Canonical Knowledge Graph                              |
+-----------------------------------------------------------------------------------+
```

### Module 1: Epoch-based Snapshot Resolver
* **Mechanism**: Rather than resolving each mention individually and immediately locking the target database, we ingest mentions in batches (epochs). At the start of an epoch $E_k$, we capture a logical read-only snapshot of the canonical graph, $G_{snapshot}^k$.
* **Concurreny Benefit**: All extraction workers and resolver threads resolve mentions in $E_k$ concurrently against $G_{snapshot}^k$ without acquiring locks.
* **Output**: The resolver produces a list of **Tentative Merge Decisions (TMD)** (e.g., $m_a \to E_x$, $m_b \to E_y$).

### Module 2: Semantic Conflict Detector & Defer Queue
Because different threads might attempt to modify the same entities without coordination, we process the TMDs at the epoch boundary through a deterministic conflict detector:
* **Synonym Conflicts**: If $m_a$ and $m_b$ both resolve to the same canonical entity $E_x$, they do not block each other. They are merged.
* **Homonym Conflicts (Semantic Splitting)**: If the resolver maps a mention $m_c$ to $E_y$ (e.g., `"Apple"` $\to$ Company) but another maps $m_d$ to $E_y$ (e.g., `"Apple"` $\to$ Fruit), the conflict detector analyzes their semantic embeddings. Since their contexts clash, the detector splits the target into two distinct canonical nodes ($E_{y\_company}$ and $E_{y\_fruit}$).
* **Overlapping Updates**: If conflicts cannot be resolved deterministically, they are pushed to a **Defer Queue** to prevent pipeline blockages, while unambiguous writes are committed.

### Module 3: Deterministic Materializer
* **CRDT Integration**: We limit CRDTs strictly to commutative, associative, and idempotent graph properties. 
  - *Alias Sets*: Modeled as grow-only sets (G-Set) of strings.
  - *Evidence Logs & Provenance*: Append-only logs.
  - *Mention Counts / Weights*: Grow-only counters (PN-Counters).
* **Write Path**: Commits are applied to the Canonical KG in a single-threaded, partitioned batch writer, eliminating distributed database locks during materialization.

---

## 3. Concrete Implementation Plan in Ragent

We will leverage the Ragent codebase to implement and benchmark MAGEv2:

1. **Staging Modification**: Extend [`offline_replay.py`'s RawMergeUnit](file:///Volumes/SSD1/ragent/ragent/offline_replay.py#L22) to support epoch-level groupings. Instead of sequential document-by-document processing, group multiple `RawMergeUnit` items into an epoch batch.
2. **Snapshot Resolver Implementation**: In [`operate.py`](file:///Volumes/SSD1/ragent/ragent/operate.py), mock or extract a read-only snapshot of the active graph adapter ([`neo4j_impl.py`](file:///Volumes/SSD1/ragent/ragent/kg/neo4j_impl.py) or [`networkx_impl.py`](file:///Volumes/SSD1/ragent/ragent/kg/networkx_impl.py)) before executing the entity mapping.
3. **Conflict Detection Phase**: Replace the fine-grained locks in [`merge_nodes_and_edges` Line 3280](file:///Volumes/SSD1/ragent/ragent/operate.py#L3280) with a batch conflict resolution loop that runs in-memory before writing back to storage.
4. **Idempotence & Rollback Re-evaluation**: Leverage the existing snapshot backup/restore functions in [`offline_replay.py` Line 437](file:///Volumes/SSD1/ragent/ragent/offline_replay.py#L437) (`_snapshot_merge_state` and `_restore_merge_state`) to measure rollback costs when conflict detection triggers an epoch-level retry.

---

## 4. Academic Evaluation Matrix

To satisfy database-focused and AI-focused reviewers, our benchmark strategy is strictly defined:

| Metric Category | Metric Name | Definition | Hypothesis (Proposed vs Baseline Ragent) |
| :--- | :--- | :--- | :--- |
| **Semantic Quality** | **Wrong Merge Rate** | Ratio of contextually distinct entities incorrectly merged. | MAGEv2 decreases wrong merges by >80% due to context-aware homonym splitting. |
| | **Duplicate Entity Rate** | Ratio of redundant canonical nodes representing the same entity. | Decreased duplicate rate due to incremental synonym alignment. |
| **System Performance** | **Ingestion Throughput (TPS)** | Number of processed mentions per second. | MAGEv2 increases throughput by 2-4x under skewed load by removing key locks. |
| | **Conflict Rollback Cost** | CPU/IO overhead of resolving and retrying conflicting epoch commits. | Snapshot isolation reduces write retries to <5% of total transactions. |
| **Robustness** | **Replay Determinism** | Consistency of final graph states when replaying identical logs out-of-order. | 100% deterministic graph state achieved through CRDT-based metadata writes. |

This revised approach directly aligns with the reviewer's guidance: it grounds the paper in a sharp, formal academic problem (RSCD), leverages the strengths of staging and epoch-based updates, and ensures the engineering work remains focused and publishable.
