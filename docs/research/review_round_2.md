# Review Round 2：面向大模型抽取知识图谱的不确定性感知并发实体解析与图物化方案评审与收敛版设计

> 本文基于第一轮评审、专家 A/B/C/D 的第二轮修订方案，以及后续关于 defer queue、幂等写入、provisional entity、新增实体与合并实体并存场景的讨论，形成第二轮综合评审与最新版方案建议。

---

## 0. 结论摘要

第二轮之后，四位专家的方案已经从彼此竞争转向明显收敛。最值得保留的不是某一个专家的完整方案，而是以下融合路线：

```text
以 D 的 Resolution-Structure Circular Dependency 作为论文核心问题；
以 C 的边界控制、评测体系和论文收敛策略作为主执行路线；
以 A 的 Mention Log / Epoch / Partitioned Writer 作为工程骨架；
谨慎吸收 B 的语义冲突检测、defer queue 和同名异义意识。
```

最终建议采用的方案可以概括为：

```text
LLM 抽取结果不直接写入 canonical KG，
而是先形成 mention/event log；
每个 epoch 冻结一个 graph snapshot；
resolver 基于固定 snapshot 和 batch 内局部 mention graph 产生 tentative decisions；
materializer 对 merge / create / provisional / defer 四类决策做确定性、幂等物化；
下一轮 epoch 再基于更新后的图继续解析。
```

推荐论文题目：

**Uncertainty-aware Epoch Resolution and Deterministic Graph Materialization for LLM-extracted Knowledge Graphs**

中文题目：

**面向大模型抽取知识图谱的不确定性感知 Epoch 实体解析与确定性图物化方法**

或：

**面向大模型抽取知识图谱的不确定性感知并发实体解析与确定性图物化算法**

---

## 1. 第二轮总体判断

### 1.1 排名与采用建议

| 排名 | 专家方案 | 综合判断 | 建议采用方式 |
|---|---|---|---|
| 1 | C_2 | 最适合作为最终执行路线。它吸收了 D 的理论问题，同时控制了工程边界和实验规模。 | 作为主方案框架 |
| 2 | D_2 | 理论创新最强，问题定义最有论文价值，但单独执行略偏抽象。 | 作为论文核心问题与形式化定义来源 |
| 3 | A_2 | 工程骨架最清楚，可直接指导系统实现，但学术叙事需借助 C/D。 | 作为系统实现骨架 |
| 4 | B_2 | 比第一版稳健，放弃 semantic lock 后价值主要在语义冲突检测和 defer queue。 | 只吸收局部机制 |

### 1.2 第二轮最关键的共识

第一轮时，四个专家方案的重心差异较大：

- A 强调 staging log 与 partitioned writer；
- B 强调 semantic lock / MAGE；
- C 强调最小可发表路线、边界控制和评测体系；
- D 强调实体解析与动态图结构之间的循环依赖。

第二轮后，四个方案基本都承认：本项目的核心不是普通的 LLM 建图，也不是普通的图数据库事务，而是：

> 实体解析需要依赖当前图结构，而当前图结构又由实体解析结果不断更新。在并发 LLM mention 流下，这种解析—结构循环依赖会导致不可重放、错误合并、重复实体、重试不幂等和图结构污染。

这就是本文建议保留的核心学术命题：

**Resolution-Structure Circular Dependency，简称 RSCD。**

---

## 2. 核心问题：Resolution-Structure Circular Dependency

设 LLM 从文档中抽取出 mention 流：

```text
M = {m1, m2, ..., mn}
```

设 canonical knowledge graph 在时刻 t 的状态为：

```text
G_t = (V_t, E_t)
```

实体解析函数可以抽象为：

```text
φ(m_i, G_t) -> v ∈ V_t ∪ {new, defer}
```

即，一个 mention 应该合并到已有实体、新建实体，还是暂缓，需要依赖当前图中的别名、属性、邻居、关系上下文和 provenance。

但一旦实体解析决策被提交，它又会改变图：

```text
G_{t+1} = materialize(G_t, φ(m_i, G_t))
```

因此形成循环：

```text
实体解析依赖图结构
        ↑        ↓
图结构又由实体解析结果更新
```

在串行、低并发或静态数据集上，这个问题通常被隐藏。但在 LLM 并发抽取场景下，它会变得非常严重。

### 2.1 直接写图会导致的问题

如果每个 worker 抽取后立即查图、解析、合并、写图，会产生以下问题：

1. **不可重放**：同一批文档，因 worker 调度顺序不同，最终 canonical graph 不同。
2. **重复实体**：两个 worker 同时看不到对方刚创建的新实体，于是创建重复节点。
3. **错误合并传播**：一个错误合并会立即改变图结构，后续 worker 又基于被污染的图继续做错误决策。
4. **重试不幂等**：任务失败重试可能重复创建节点、重复创建边、重复累加 mention count。
5. **热点实体长尾阻塞**：大量 mention 指向同一高频实体时，锁竞争严重。
6. **新实体漏识别或乱创建**：系统要么过度保守、拒绝新增，要么把低置信 mention 直接变成永久实体。

### 2.2 为什么现有方向不能完整覆盖

传统实体解析通常假设输入记录集合相对静态，关注两条记录是否同一；图数据库事务关注结构写入一致性，但不处理语义歧义；GraphRAG 和 LLM-KG 构建多关注抽取质量和下游问答效果，而较少研究大规模并发 ingestion 过程中 canonical graph 如何稳定物化。

本项目的空白点在于：

> LLM mention 流本身带有不确定性、重复性和语义歧义；而这些 mention 又需要并发、高吞吐地进入一个持续演化的 canonical KG。如何在这种场景下保证稳定增长、低错误合并、可重放和可恢复，是一个独立且清晰的问题。

---

## 3. 核心解决思路

本方案不是消灭“实体解析依赖图”这个事实，而是把不可控的实时循环改造成可控的跨 epoch 迭代。

一句话概括：

> 不让实体解析直接读写正在变化的主图；而是让它读取固定图快照，在一个 epoch 内产生 tentative decisions，再由确定性 materializer 统一处理 merge、create、provisional 和 defer 决策。

整体流程：

```text
Raw Documents / Chunks
        ↓
LLM Extraction Workers
        ↓
MentionEvent / RelationMentionEvent
        ↓
Append-only Mention Log
        ↓
Epoch Builder
        ↓
Snapshot-based Tentative Resolver
        ↓
Intra-epoch Mention Clustering
        ↓
Decision Classifier
        ├── merge_existing
        ├── create_canonical
        ├── create_provisional
        └── defer
        ↓
Conflict Detector
        ↓
Deterministic Idempotent Materializer
        ↓
Canonical KG + Working/Candidate Layer
        ↓
Next Epoch Snapshot
```

---

## 4. 关键设计一：Epoch-based Snapshot Resolution

### 4.1 固定图快照

在 epoch k 开始时，系统冻结图快照：

```text
G_k_snapshot
```

本 epoch 中所有 resolver worker 都只能基于这个只读快照做实体解析，而不能读取其他 worker 在同一 epoch 中刚写入的结果。

这样可以把原来的副作用过程：

```text
resolve_and_write(m_i, live_graph)
```

改造成近似纯函数：

```text
tentative_decision_i = resolve(m_i, G_k_snapshot, batch_context)
```

### 4.2 Tentative decision 而非立即提交

resolver 输出的是暂定决策，而不是直接改图操作。例如：

```text
mention: "Apple"
context: "Apple released a new iPhone."
decision:
  type: merge_existing
  target: Entity#AppleInc
  confidence: 0.91
  evidence: {doc_id, chunk_id, span}
```

或：

```text
mention: "Apple Bank"
decision:
  type: create_canonical
  entity_type: FinancialInstitution
  confidence: 0.88
  evidence: {...}
```

或：

```text
mention: "Apple Studios"
decision:
  type: create_provisional
  possible_related_to: Entity#AppleInc
  confidence: 0.62
  evidence: {...}
```

这些决策先进入 decision set，不直接写主图。

---

## 5. 关键设计二：四分决策机制

前一版方案容易被理解为“为了稳定主图，所以倾向于不新增实体”。第二轮讨论后，需要明确修正：本方案的目标不是保持主图不变，而是让新增、合并、暂定和延迟都显式化。

最终建议采用四分决策：

```text
1. merge_existing      合并到已有 canonical entity
2. create_canonical    创建确定的新 canonical entity
3. create_provisional  创建暂定实体，放入 candidate/working layer
4. defer               暂缓，不写实体节点，等待更多证据或人工/强模型复判
```

### 5.1 merge_existing

当 mention 与已有实体匹配分数高、类型兼容、关系上下文一致、冲突分数低时，执行合并。

示例：

```text
m1: Apple released a new iPhone.
→ merge_existing(Entity#AppleInc)
```

### 5.2 create_canonical

当系统高置信判断该 mention cluster 确实不是已有实体，并且 batch 内有足够支持证据时，直接创建新 canonical entity。

示例：

```text
m4: Apple Bank opened a new branch in New York.
```

如果已有图中只有 Apple Inc. 和 Apple fruit，而该 mention 的类型为 FinancialInstitution，且上下文包含 branch、savings account、New York 等信息，则可以新建：

```text
Entity#AppleBank
status = canonical
type = FinancialInstitution
```

### 5.3 create_provisional

当系统基本确定这里有一个实体，但不确定它是否应该成为新的 canonical entity，或是否应合并到已有实体时，创建 provisional entity。

示例：

```text
m3: Apple Studios acquired the film rights.
```

可能情况包括：

```text
Apple Inc. 的业务部门
独立公司
LLM 抽取错误或名称不规范
```

此时不应直接合并，也不应直接成为永久实体，而是创建：

```text
ProvisionalEntity#P_AppleStudios
status = provisional
possible_related_to = Entity#AppleInc
evidence = {m3}
```

后续 epoch 中，P_AppleStudios 可以被：

```text
promote to canonical
merge into existing canonical
merge with another provisional
reject as extraction error
keep unresolved
```

### 5.4 defer

defer 表示当前证据不足以安全地形成实体决策。它适用于抽取本身可疑、候选实体差距过小、上下文冲突严重或需要外部知识/人工审核的情形。

示例：

```text
mention: "Jordan"
context 同时出现 NBA、country、capital、Amman 等线索
→ defer
```

注意：

```text
defer ≠ provisional
```

区别是：

| 类型 | 含义 |
|---|---|
| provisional | 基本确定有一个实体，但身份或 canonical 归属未定 |
| defer | 目前连是否应形成实体决策都不可靠，先不写图 |

---

## 6. 关键设计三：Epoch 内部 mention clustering

新增实体不应以单个 mention 为单位盲目创建，而应以 mention cluster 为单位。

在每个 epoch 内，resolver 不仅比较 mention 与已有 canonical entity，还应比较 mention 与 mention 之间的关系。

可构建一个局部图：

```text
mention-candidate bipartite graph
+ mention-mention similarity graph
+ relation-neighborhood compatibility graph
```

考虑因素包括：

```text
surface form similarity
context embedding similarity
entity type compatibility
relation pattern compatibility
source/document locality
negative constraints / must-not-link
positive constraints / must-link
```

示例：

```text
m4: Apple Bank opened a new branch in New York.
m6: Apple Bank offers savings accounts.
m7: Apple Bank is headquartered in Manhasset.
```

三者可先聚成：

```text
C_new_1 = {m4, m6, m7}
surface = Apple Bank
type = FinancialInstitution
evidence_count = 3
```

若该 cluster 与 Apple Inc.、Apple fruit 均类型不兼容，且内部证据一致，则创建 canonical entity：

```text
create_canonical(Entity#AppleBank)
```

这样可以避免两种错误：

1. 单 mention 新建导致大量碎片实体；
2. 过度保守导致真正新实体长期进不了图。

---

## 7. 关键设计四：defer queue 的后续处理

defer queue 不是垃圾桶，也不是永久搁置，而是一个延迟解析机制。

每个 defer item 应保存：

```text
defer_item = {
  mention_id,
  mention_text,
  source_chunk,
  candidate_entities,
  confidence_scores,
  conflict_reason,
  required_evidence,
  epoch_id,
  retry_count
}
```

### 7.1 处理路径

进入 defer queue 后，可采用以下路径：

1. **下一个 epoch 重新解析**：等待图结构或上下文证据变得更充分后再进入 resolver。
2. **扩大上下文**：从 sentence 扩展到 paragraph、document title、neighboring chunks、source provenance 和 relation mentions。
3. **强模型复判**：对高价值或高冲突 mention 使用更高成本模型。
4. **人工审核**：用于法律主体、金融机构、药物、客户名、关键人物等高风险实体。
5. **转 provisional**：如果后续证据显示“确实有实体但身份不清”，则创建 provisional entity。
6. **保留 unresolved**：超过 retry 或 epoch 上限仍无法判断时，不强行写入 canonical KG。

### 7.2 必须报告 defer 指标

论文实验中不能只说“困难样本进入 defer”，否则评审会质疑系统回避难题。必须报告：

```text
defer_rate
resolved_after_defer_rate
promoted_to_canonical_rate
merged_after_defer_rate
manual_review_rate
unresolved_rate
wrong_merge_reduction
```

尤其要避免靠无限 defer 换取高精度。

---

## 8. 关键设计五：确定性幂等物化

### 8.1 什么是幂等写入

幂等写入指：同一个写入操作执行一次和执行多次，最终图状态完全一样。

形式化地说：

```text
apply(G, Δ) = apply(apply(G, Δ), Δ)
```

这对 LLM-KG ingestion 非常重要，因为实际系统中经常发生：

```text
任务失败重试
worker 崩溃恢复
网络超时重发
同一个 chunk 被重复处理
同一批 decision 被重复提交
```

如果没有幂等性，会出现重复节点、重复边、重复 evidence、mention_count 重复累加等问题。

### 8.2 稳定 ID 设计

建议为各类对象生成稳定 ID：

```text
mention_id  = hash(doc_id + chunk_id + span_start + span_end + surface)
decision_id = hash(epoch_id + mention_id + snapshot_version + resolver_version)
entity_id   = hash(entity_cluster_id or canonical_key)
edge_id     = hash(subject_entity_id + predicate + object_entity_id + evidence_id)
evidence_id = hash(doc_id + chunk_id + span_start + span_end)
```

写入时使用：

```text
upsert node
upsert edge
add evidence_id to set
add source_id to set
add mention_id to set
```

而不是盲目 insert 或 `count += 1`。

### 8.3 哪些字段适合幂等合并

适合集合式合并的字段：

```text
aliases
source_ids
evidence_ids
mention_ids
provenance_records
observed_surface_forms
supporting_chunks
```

适合 min/max 的字段：

```text
first_seen_time = min(old, new)
last_seen_time  = max(old, new)
confidence      = max(old, new) 或重新聚合
```

不适合直接累加的字段：

```text
mention_count += 1
edge_weight += score
frequency += 1
```

应改为：

```text
mention_count = count(unique mention_ids)
edge_weight   = aggregate(unique evidence_ids)
```

### 8.4 CRDT 的边界

可以使用 CRDT-like 思路处理 alias set、evidence set、source_ids、mention_ids 等单调字段，但不能声称“CRDT 解决实体合并”。

实体合并是语义决策，不是集合 union。

正确表述：

> CRDT-like merge 只用于物化层的幂等字段；实体是否合并仍由 snapshot-based resolver 和 conflict detector 决定。

---

## 9. Apple 场景下的完整示例

假设当前 canonical KG 中已有：

```text
E1: Apple Inc.
  type: Company
  aliases: {Apple, Apple Inc., AAPL}
  relations:
    CEO -> Tim Cook
    headquartered_in -> Cupertino

E2: Apple
  type: Fruit
  aliases: {apple}
  relations:
    contains -> Vitamin C
```

某个 epoch 中来了以下 mention：

```text
m1: Apple released a new iPhone.
m2: Apple contains vitamin C.
m3: Apple Studios acquired the film rights.
m4: Apple Bank opened a new branch in New York.
m5: Green Apple is a cultivar popular in Japan.
m6: Apple Bank offers savings accounts.
m7: Apple Bank is headquartered in Manhasset.
```

基于固定快照和 epoch 内部聚类，系统应输出：

| mention/cluster | 决策 | 说明 |
|---|---|---|
| m1 | merge_existing(E1) | iPhone 上下文强指向 Apple Inc. |
| m2 | merge_existing(E2) | vitamin C 上下文强指向水果 |
| m3 | create_provisional(P1: Apple Studios) | 实体性较强，但可能是 Apple Inc. 部门或独立主体 |
| {m4,m6,m7} | create_canonical(E3: Apple Bank) | 多证据支持、类型为金融机构、与已有 Apple 实体不兼容 |
| m5 | create_provisional(P2: Green Apple cultivar) | 可能是植物品种/子类，需后续证据确认 |

最终不是简单地“保持主图不变”，而是：

```text
确定能合并的合并；
确定是新实体的新增；
实体性强但归属不明的进入 provisional layer；
抽取或身份都不可靠的进入 defer queue。
```

---

## 10. 系统架构建议

### 10.1 三层架构

```text
Layer 1: Mention Ingestion
  - LLM extraction workers
  - MentionEvent / RelationMentionEvent
  - Append-only Mention Log
  - 保留 surface、context、confidence、span、source、provenance

Layer 2: Epoch-based Resolution
  - Epoch Scheduler
  - Snapshot Reader
  - Candidate Retriever
  - Mention Clustering
  - Tentative Resolver
  - Conflict Detector
  - Defer Queue

Layer 3: Deterministic Materialization
  - Decision Sorter
  - Idempotent Upsert Writer
  - Canonical KG
  - Working/Candidate Layer
  - Provenance Store
```

### 10.2 主图与候选层分离

建议将图分为：

```text
Canonical KG
  高置信实体、关系和属性

Working / Candidate Layer
  provisional entities
  low-confidence edges
  unresolved clusters
  defer metadata
```

默认下游 RAG / QA 使用 Canonical KG。下一轮 resolver 可以参考 Working Layer，但应降低权重，避免 provisional 结构过早污染主图。

### 10.3 决策状态机

实体或 mention cluster 可采用如下状态机：

```text
candidate
   ↓
provisional
   ├── promote_to_canonical
   ├── merge_into_existing
   ├── merge_with_provisional
   ├── reject
   └── keep_unresolved
```

更完整的决策生命周期：

```text
MentionEvent
   ↓
TentativeDecision
   ↓
merge_existing / create_canonical / create_provisional / defer
   ↓
MaterializedCanonical / ProvisionalLayer / DeferQueue
   ↓
Next Epoch Re-evaluation
```

---

## 11. 冲突检测机制

冲突检测不应被包装成万能语义判断器，而应定位为 materialization 前的安全闸门。

建议检测以下冲突：

1. **同名异义冲突**：同 surface 指向类型或上下文不兼容的实体。
2. **一 mention 多候选冲突**：最高候选与次高候选分数接近。
3. **类型冲突**：Company / Fruit / FinancialInstitution / Person 等类型不兼容。
4. **关系模式冲突**：`released_iPhone` 与 `contains_vitamin_C` 明显属于不同语义邻域。
5. **已有图约束冲突**：违反 must-not-link 或 schema constraint。
6. **epoch 内新实体重复冲突**：多个新建 cluster 可能表示同一个新实体。
7. **provisional 与 canonical 冲突**：暂定实体与已有实体越来越相似或越来越矛盾。

冲突处理优先级：

```text
低冲突高置信 → commit
中冲突实体性强 → provisional
高冲突低置信 → defer
高价值高风险 → human / strong model review
```

---

## 12. 实验与评测设计

### 12.1 Baselines

建议至少包含：

| Baseline | 描述 |
|---|---|
| B0 Direct Write | 当前 Ragent 式直接写图 / keyed lock / eager merge |
| B1 Serial Resolution | 单线程串行解析与写入，作为稳定但低吞吐参考 |
| B2 Batch ER without Epoch | 批处理实体解析，但没有 snapshot 与确定性物化 |
| B3 Epoch without Provisional | 有 epoch，但只有 merge/create/defer，无 provisional layer |
| B4 Full System | 本文完整方案：epoch + clustering + four-way decision + idempotent materialization |

### 12.2 Workloads

建议构造四类 workload：

```text
normal workload
synonym-heavy workload
homonym-heavy workload
skew/hot-entity workload
retry/failure workload
```

同时至少加入一个真实语料案例，避免完全依赖合成数据。

### 12.3 指标

语义质量指标：

```text
pairwise precision / recall / F1
must-link violation rate
must-not-link violation rate
wrong merge rate
duplicate entity rate
provisional promotion accuracy
```

图物化稳定性指标：

```text
replay determinism
idempotence under retry
dangling edge rate
provenance completeness
```

系统指标：

```text
throughput
latency per epoch
hot entity skew performance
lock/contention reduction
memory/storage overhead
```

延迟与暂定机制指标：

```text
defer_rate
resolved_after_defer_rate
provisional_rate
promote_rate
merge_after_provisional_rate
reject_rate
unresolved_rate
```

### 12.4 关键消融实验

建议消融：

```text
without snapshot
without deterministic ordering
without mention clustering
without provisional layer
without defer queue
without idempotent IDs
without conflict detector
```

其中最重要的是证明：

1. snapshot 提升 replay determinism；
2. idempotent materialization 解决 retry 重复写；
3. provisional layer 在不显著增加 wrong merge 的情况下提升新实体召回；
4. defer queue 降低错误合并，但不能无限增大 unresolved rate；
5. mention clustering 减少新实体碎片化。

---

## 13. 论文贡献建议写法

建议写成四条贡献：

### Contribution 1：问题定义

提出并形式化 LLM-extracted KG ingestion 中的 Resolution-Structure Circular Dependency，指出实体解析依赖动态图结构，而图结构又由并发解析决策持续更新，从而导致不可重放、错误合并和重试不幂等。

### Contribution 2：Epoch-based uncertainty-aware resolution

提出基于固定 graph snapshot 的 epoch 实体解析机制，使同一 epoch 内的 mention 基于一致上下文产生 tentative decisions，并结合 epoch 内 mention clustering 同时处理已有实体合并与新实体发现。

### Contribution 3：Four-way decision and deterministic materialization

设计 merge_existing、create_canonical、create_provisional、defer 四分决策机制，以及确定性、幂等的图物化协议，在保证 canonical KG 稳定性的同时支持新实体受控增长。

### Contribution 4：Benchmark and evaluation

构建面向 LLM-KG ingestion 的评测框架，在 synonym-heavy、homonym-heavy、skew、retry/failure 等场景下联合评估实体解析质量、图稳定性、幂等性和系统吞吐。

---

## 14. 与四位专家方案的对应关系

| 设计点 | 主要来源 | 说明 |
|---|---|---|
| RSCD 问题定义 | D_2 | 最重要的学术创新点 |
| 论文边界与评测体系 | C_2 | 保证项目可发表、可实现 |
| Mention Log / Staging | A_2 | 工程入口，切断直接写图 |
| Epoch / Snapshot | A_2 + C_2 + D_2 | 核心隔离机制 |
| Partitioned Writer | A_2 | 作为物化层优化，不作为主贡献 |
| Conflict Detector | B_2 | 吸收语义冲突意识，但不做 semantic lock |
| Defer Queue | B_2 + 后续讨论 | 用于高冲突、低置信决策 |
| Provisional Entity | 后续讨论新增 | 用于平衡稳定性与新实体召回 |
| Idempotent Materialization | C_2 + D_2 + 后续讨论 | 保证重试和恢复不写坏图 |
| CRDT-like fields | D_2 | 仅限 alias/evidence/source/mention set |

---

## 15. 需要避免的表述风险

### 15.1 不要说“我们提出新的图数据库事务协议”

本项目定位是 LLM-KG ingestion/materialization layer，不是图数据库内核。

推荐表述：

```text
We design an ingestion-layer protocol for deterministic and idempotent materialization of LLM-extracted mentions into a canonical KG.
```

### 15.2 不要说“CRDT 解决实体合并”

实体合并是语义判断，CRDT 只能用于物化字段集合的幂等合并。

### 15.3 不要说“epoch 提升实体解析准确率”

epoch 的主要作用是 snapshot consistency、replay determinism 和并发稳定性。准确率提升来自更好的上下文、mention clustering、conflict detection 和 provisional/defer 机制。

### 15.4 不要让 defer 成为逃避难题的工具

必须报告 defer rate、resolved rate、unresolved rate 和人工复核比例。

### 15.5 不要让 provisional 污染主图

provisional entity 应放在 candidate/working layer，下游默认不直接使用，或使用时带置信权重。

### 15.6 不要只用合成数据

合成数据适合制造同名异义、重试、热点 skew，但至少要有真实语料案例分析。

---

## 16. 可落地实现建议

### 16.1 第一阶段：切断直接写图

目标：把 LLM 抽取与 canonical graph 写入解耦。

任务：

```text
实现 MentionEvent 数据结构
实现 RelationMentionEvent 数据结构
实现 append-only MentionLogStorage
让 extraction workers 只写 mention log，不直接 merge KG
```

### 16.2 第二阶段：实现 epoch coordinator

目标：按时间窗或 batch size 形成 epoch。

任务：

```text
EpochBuilder
SnapshotManager
SnapshotReader
Epoch metadata store
```

### 16.3 第三阶段：实现 tentative resolver

目标：基于固定 snapshot 做候选召回、mention clustering 和 tentative decision。

任务：

```text
CandidateRetriever
MentionClusterer
ResolutionScorer
DecisionClassifier
```

### 16.4 第四阶段：实现 materializer

目标：确定性排序、冲突检测、幂等写入。

任务：

```text
DecisionSorter
ConflictDetector
IdempotentGraphWriter
Stable ID generator
ProvenanceStore
```

### 16.5 第五阶段：实现 defer/provisional 生命周期

目标：管理不确定实体与延迟解析。

任务：

```text
DeferQueue
ProvisionalEntityStore
Promotion/Merge/Reject workflow
Retry policy
Manual/strong-model review hook
```

### 16.6 第六阶段：实验与论文评测

目标：验证本方案相对 baseline 的收益。

任务：

```text
构造 workloads
实现 replay determinism 测试
实现 retry idempotence 测试
实现 entity resolution constraints 评测
实现 skew throughput 测试
实现 ablation study
```

---

## 17. 最终建议

第二轮后，项目应从“哪个专家方案最优”转为“如何把已经收敛的共识组织成一个清晰、可发表、可实现的系统论文”。

最终推荐路线：

```text
C_2 作为主执行路线；
D_2 作为理论核心；
A_2 作为工程骨架；
B_2 只吸收冲突检测和 defer queue；
再加入本轮讨论形成的 provisional entity 与四分决策机制。
```

一句话总结：

> 本项目不应被包装成普通的 LLM 知识图谱构建系统，而应聚焦于 LLM mention 流并发进入 canonical KG 时的解析—结构循环依赖问题。通过 epoch snapshot resolution、mention clustering、merge/create/provisional/defer 四分决策和 deterministic idempotent materialization，可以在支持知识图谱持续增长的同时，降低错误合并、重复实体和不可重放风险。

---

## 18. 最简版方案描述

如果需要在摘要或 proposal 中压缩成一段，可以使用：

> 本项目研究 LLM 抽取 mention 流在并发物化为 canonical knowledge graph 时的 Resolution-Structure Circular Dependency：实体解析依赖当前图结构，而图结构又由解析决策不断更新，导致不可重放、错误合并和重试不幂等。我们提出一种不确定性感知的 epoch-based 图物化框架：抽取阶段仅写入 append-only mention log；每个 epoch 基于固定图快照执行实体解析和 batch 内 mention clustering；解析结果被划分为 merge_existing、create_canonical、create_provisional 和 defer 四类决策；物化阶段通过确定性排序、冲突检测、稳定 ID 与集合式 upsert 实现幂等写入。该框架将实时循环依赖转化为跨 epoch 的受控迭代，在保证 canonical KG 稳定性和可重放性的同时支持新实体的受控增长。
