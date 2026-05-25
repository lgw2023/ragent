# 专家 C 第二轮建议：以“解析-结构循环依赖”为核心，收敛到可实现的 epoch-based KG 物化论文

读完 `review_round_1.md` 后，我对第一版专家 C 意见做一次修订。第一版 C 的判断基本方向是对的：不要把课题包装成普通 LLM 建图系统，也不要声称改造图数据库事务内核，而应落在 LLM-KG ingestion/materialization layer。但评审指出的问题也成立：**第一版 C 更像稳健工程路线，还缺少一句足够锋利的学术命题。**

因此，第二轮我建议把论文主问题从：

```text
如何把 noisy LLM mentions 稳定物化为 canonical graph
```

进一步收窄和强化为：

```text
在并发 LLM mention 流中，实体解析决策依赖当前 canonical graph；
而 canonical graph 又由并发实体解析决策持续更新。
如何在这种解析-结构循环依赖下，实现可重放、幂等、低错误合并的图物化？
```

这个命题比“加 staging layer”更像研究问题，也比“semantic lock manager”更稳，因为它直接解释了为什么传统 ER、GraphRAG 工具和图数据库并发控制都没有完整覆盖这个场景。

---

## 1. 我对第一轮评审的接受与修正

### 1.1 我接受的判断

评审中最关键的判断是：

**本项目最有价值的创新点不是某个具体模块，而是 LLM mention 流在并发写入 canonical KG 时，实体解析与图结构动态更新之间的循环依赖。**

我认同这个判断。第一版 C 已经提出 mention log、resolver、deterministic materializer 和双层评测，但这些还只是系统骨架。若没有“解析依赖图、图又被解析改变”的理论定义，论文容易被评为工程组合。

所以第二版 C 的核心变化是：

1. 将 **Resolution-Structure Circular Dependency** 作为论文主问题。
2. 将 **epoch/snapshot-based resolution** 作为主方法。
3. 将第一版 C 的 mention log、resolver、materializer、benchmark 降级为实现该方法的工程支撑。
4. 将 CRDT 和 semantic lock 限定在合适边界，避免理论过度承诺。

### 1.2 我保留的边界

虽然吸收 D 的理论核心，但我仍坚持第一版 C 的几个边界：

1. 不声称改造图数据库事务。
2. 不把 staging-first 当主创新。
3. 不把 LLM prompt engineering 当主贡献。
4. 不把 CRDT 包装成实体消歧的解法。
5. 不依赖完整 gold graph，而优先使用 pairwise/entity constraints 评价。

这几个边界会保护论文不被审稿人从数据库、ER、GraphRAG 三个方向同时攻击。

---

## 2. 修订后的论文定位

推荐题目：

**Uncertainty-aware Epoch Resolution and Deterministic Graph Materialization for LLM-extracted Knowledge Graphs**

中文题目：

**面向大模型抽取 mention 流的不确定性感知 epoch 实体解析与确定性图物化方法**

如果希望更贴近原始题目，可以写成：

**面向大模型抽取知识图谱的不确定性感知并发实体解析与确定性图物化方法**

但正文中必须强调：这里的“并发”不是泛泛的多线程加速，而是 **多个 mention 在不同图快照上做解析决策时产生的语义一致性问题**。

---

## 3. 修订后的核心问题定义

当前 Ragent 的 direct-write baseline 可以抽象为：

```text
chunk_results
  -> group by entity_name
  -> keyed lock
  -> merge descriptions/source ids
  -> upsert canonical graph
```

其隐含假设是：

```text
entity_name == canonical entity id
```

这个假设在 LLM 抽取场景中不成立。LLM 输出的是 mention，不是 canonical entity。更重要的是，一个 mention 应该解析到哪个 canonical entity，往往依赖当前图中已有的别名、类型、邻居、关系和证据。

形式化地说：

```text
resolve(m, G_t) -> canonical_entity_id | new_entity | defer
```

但 `G_t` 又是历史 mention 解析决策物化后的结果：

```text
G_t = materialize(resolve(m_1, G_0), ..., resolve(m_k, G_{k-1}))
```

并发条件下，多个 resolver 可能基于同一个旧图快照同时决策，导致：

1. 应该合并的 mention 被并发创建成重复实体。
2. 应该拆分的同名 mention 被抢先合并。
3. 边在端点尚未稳定时被物化，产生悬空或错误边。
4. 重试和乱序 replay 后得到不同 canonical graph。

因此，论文问题应定义为：

**给定固定的 noisy LLM mention stream，设计一种解析与物化机制，使其在并发、乱序和重试条件下产生满足语义约束和系统约束的 canonical graph，并尽量保持高吞吐。**

---

## 4. 修订后的方法主线：Epoch-based Resolution with Deterministic Materialization

### 4.1 总体结构

建议系统结构如下：

```text
LLM extraction workers
        ↓
Mention Log / Staging Events
        ↓
Epoch Builder
        ↓
Snapshot-based Resolver
        ↓
Conflict Detector + Defer Queue
        ↓
Deterministic Materializer
        ↓
Canonical Knowledge Graph
```

这个结构吸收 A 的 mention log，保留 C 的 deterministic materializer，吸收 D 的 epoch/snapshot 核心，谨慎吸收 B 的语义冲突意识。

### 4.2 Epoch 的定义

一个 epoch 是一段有限 mention event 的集合：

```text
Epoch_k = {
  mention_events: M_k,
  base_graph_snapshot: G_k,
  resolver_config: R_k,
  extractor_versions: X_k
}
```

epoch 内部：

1. 所有 mention 基于同一个 `G_k` 做 tentative resolution。
2. tentative decision 不直接修改 canonical graph。
3. 关系 mention 先绑定 mention endpoints，而不是立即绑定 canonical endpoints。

epoch 边界：

1. 汇总 tentative decisions。
2. 做 conflict detection。
3. 将可提交的 decisions 编译成 deterministic materialization ops。
4. 按稳定顺序提交到 canonical graph。
5. 生成 `G_{k+1}`，供下一个 epoch 使用。

这样可以把并发写图问题转换为：

```text
epoch 内并行解析
epoch 边界确定性提交
```

### 4.3 Resolver 的输出

每个 mention 不应只输出一个实体 id，而应输出一个带置信度和证据的决策：

```text
ResolutionDecision {
  decision_id
  epoch_id
  mention_id
  base_snapshot_id
  candidates: [(entity_id, score, evidence)]
  decision_type: MATCH | CREATE | DEFER | CONFLICT
  chosen_entity_id
  confidence
  reasons
}
```

这能回应评审对“不确定性”的要求：不确定性不是抽象口号，而是进入决策记录、冲突检测和物化边界。

### 4.4 Conflict Detector 的职责

冲突检测不需要一开始做成复杂逻辑。最小可发表版本可以包含四类：

```text
must-not-link violation
type incompatibility
relation endpoint instability
duplicate create candidates
```

输出：

```text
COMMIT: 高置信且无冲突
DEFER: 低置信或冲突未解决
REVIEW: 必须人工或离线 resolver 处理
```

重要的是，不要把所有冲突都强行解决。**显式 defer 比错误物化更符合不确定性感知。**

### 4.5 Deterministic Materializer 的职责

materializer 不负责“判断两个实体是否相同”。它只负责把 resolver 已经产生的 decision 稳定写入图。

它应保证：

1. 同一 `decision_id` 重复提交不会改变结果。
2. 同一 epoch 内 ops 有稳定排序。
3. alias set、evidence set、mention count 等字段采用幂等合并。
4. relation 只有在 endpoints 已提交时才物化。
5. 所有 op 都有 provenance 和 checkpoint。

这一步可以吸收 CRDT 思想，但边界要清楚：

```text
CRDT-like/idempotent merge 用于 alias/evidence/provenance/relation evidence；
实体是否合并仍由 resolver 和 conflict detector 决定。
```

---

## 5. 对 Semantic Lock 的修正立场

第一轮评审指出 B 的 semantic lock 有鸡蛋问题：锁划分依赖 ER，而 ER 又是待解决问题。我同意。

因此第二版 C 不建议把 **Semantic Lock Manager** 作为主贡献。可替代做法是：

```text
不要在解析前分配语义锁；
而是在 epoch 决策之后，按 chosen canonical entity / tentative cluster 分区提交。
```

也就是说：

```text
semantic lock before ER  -> 不建议
cluster partition after tentative ER -> 建议
```

这样可以避免理论漏洞。并发控制发生在 materialization 阶段，而不是试图在 resolver 之前预测语义锁。

---

## 6. 对 CRDT 的修正立场

CRDT 只能作为物化字段的收敛工具，不能作为语义解析工具。

可以使用 CRDT-like 思想的字段：

```text
alias set
mention id set
evidence id set
source chunk id set
relation evidence set
mention counter
```

不应声称 CRDT 自动解决：

```text
同名异义
异名同义
实体拆分
矛盾事实判断
ontology 粒度选择
```

论文可以写成：

**Our materialization operations are idempotent and CRDT-inspired for monotonic evidence fields, while semantic merge/split decisions remain explicit resolution decisions.**

这比“CRDT 解决并发实体解析”更准确，也更容易被接受。

---

## 7. 修订后的实验设计

### 7.1 Baselines

保留并强化第一版 C 的 baseline 设计：

```text
B0: Ragent direct-write exact-string merge
B1: Mention log + sequential deterministic materializer
B2: Mention log + direct incremental resolver + keyed materializer
B3: Epoch resolver + deterministic materializer
B4: Epoch resolver + conflict defer + partitioned materializer
```

B0 是当前仓库的 `merge_nodes_and_edges`，不能被削弱。B1 用来证明 staging/replay 本身的收益有限。B3/B4 才体现论文主贡献。

### 7.2 Workloads

至少需要四组 workload：

```text
W1 normal: 普通文档抽取
W2 synonym-heavy: 异名同义高比例
W3 homonym-heavy: 同名异义高比例
W4 skew+retry: 热点实体 + 并发重试 + 乱序提交
```

关键是 W4。没有 skew、retry、乱序，论文的“并发实体解析”就缺少说服力。

### 7.3 Gold labels 不做完整 gold graph

我接受评审关于 gold graph 难构造的提醒。建议采用 constraint-based evaluation：

```text
must-link pair satisfaction
must-not-link pair satisfaction
must-exist relation satisfaction
must-not-exist relation violation
evidence coverage
```

这样可以避免“canonical graph 正确答案本身取决于 schema 粒度”的争议。

### 7.4 指标

语义指标：

```text
must-link recall
must-not-link precision
wrong merge rate
duplicate entity rate
dangling edge rate
contradictory relation rate
defer rate
evidence coverage
```

系统指标：

```text
mentions/sec
materialization ops/sec
p95/p99 latency
queue wait time
replay determinism
idempotence under retry
snapshot consistency violation
throughput under Zipf skew
```

一个特别重要的图表应是：

```text
并发度提升时，不同方法的 semantic quality degradation curve
```

如果 B0 在并发或乱序下 duplicate/wrong merge 上升，而 B3/B4 更稳定，这就是论文最有力结果。

---

## 8. 面向当前仓库的落地路线

### 8.1 第一步：冻结 direct-write baseline

不要改坏 `merge_nodes_and_edges`。应将其作为 baseline 固化，并增加最小 instrumentation：

```text
entity_name
edge_key
lock_wait_ms
merge_ms
source_chunk_count
created_or_updated
```

同时固定实验条件：

```text
禁用或固定 LLM merge summary
忽略或固定 created_at
固定 raw units
固定并发度
```

### 8.2 第二步：从 RawMergeUnit 生成 MentionEvent

新增转换层：

```text
RawMergeUnit.chunk_results -> EntityMentionEvent / RelationMentionEvent
```

先不要求 source span，因为现有抽取结果未必有 char offset。最小 event id 可以由以下字段生成：

```text
hash(doc_id, chunk_id, record_index, surface, event_type)
```

这样可先打通 replay 和 idempotence。

### 8.3 第三步：实现 epoch runner

建议新增模块：

```text
ragent/ingest/events.py
ragent/ingest/mention_log.py
ragent/ingest/epoch.py
ragent/ingest/resolver.py
ragent/ingest/conflicts.py
ragent/ingest/materializer.py
ragent/ingest/metrics.py
```

最小 epoch runner：

```text
load mention events
chunk into epochs by size or source_group_key
snapshot current graph state
parallel tentative resolve
detect conflicts
apply deterministic ops
write metrics
```

### 8.4 第四步：保守 resolver

先实现可解释多信号 resolver：

```text
surface similarity
entity type compatibility
context embedding similarity
neighbor relation support
must-link/must-not-link constraint check
```

不要先做复杂 LLM-as-judge。LLM-as-judge 可以作为后续 hard-case ablation。

### 8.5 第五步：并发实验与消融

消融应至少包含：

```text
no epoch vs epoch
no conflict defer vs conflict defer
exact string vs surface+type vs surface+type+embedding+neighbor
sequential materialization vs partitioned materialization
retry off vs retry on
uniform vs Zipf skew
```

---

## 9. 论文贡献应如何写

我建议最终贡献列表写成四条：

1. **Problem formulation**：首次形式化 LLM-extracted KG ingestion 中的 resolution-structure circular dependency，指出实体解析依赖动态图快照，而图快照又由并发解析决策更新。
2. **Method**：提出 epoch-based uncertainty-aware resolution，将并发 mention 解析限定在一致图快照上，并在 epoch 边界执行冲突检测与确定性提交。
3. **Materialization protocol**：设计幂等、可重放、provenance-preserving 的 graph materialization ops，使 alias/evidence/relation provenance 等字段可稳定合并。
4. **Benchmark/evaluation**：基于 Ragent 构建 fixed mention stream benchmark，联合评价语义约束满足率、replay determinism、retry idempotence 和 skew 下吞吐。

这四条比“我们加了一个 staging graph”和“我们用了 semantic lock”更稳。

---

## 10. 需要避免的论文风险

### 10.1 不要把 epoch 说成万能

epoch-based resolution 解决的是 snapshot consistency 和 replay determinism，不自动保证 entity resolution 质量。ER 质量仍取决于 resolver。

### 10.2 不要承诺严格 serializability

如果没有完整形式证明，不建议声称 serializable。可以说：

```text
deterministic replay under fixed mention events and fixed resolver configuration
snapshot-consistent resolution within each epoch
idempotent materialization under retry
```

这些更容易证明和测试。

### 10.3 不要让 defer rate 过高

如果大量 ambiguous mentions 都 defer，图质量可能看起来很安全但不可用。实验必须报告 defer rate，并展示质量-覆盖率 tradeoff。

### 10.4 不要只在合成数据上做实验

合成数据可以控制冲突，但必须有一个真实小语料或当前食品/标准文档语料上的案例分析，否则会被认为 workload 人造。

---

## 11. 我的第二轮最终建议

第一版 C 的路线可以保留，但要改主心骨：

```text
旧 C：
  fixed raw units -> mention log -> uncertainty resolver -> deterministic materializer

新 C_2：
  fixed raw units -> mention events
  -> epoch/snapshot-based tentative resolution
  -> conflict/defer
  -> deterministic idempotent materialization
```

也就是说，**mention log 是基础设施，epoch-based resolution 才是方法。**

最终项目应采用这样的主张：

**LLM-KG construction 的难点不是抽取一批三元组，也不是简单提高写入吞吐，而是在并发 mention 流中处理实体解析决策与动态图结构之间的循环依赖。通过 epoch/snapshot-based resolution 和确定性物化，可以在不修改底层图数据库的前提下，让 canonical KG 构建过程具备可重放、幂等、可审计和更低语义污染的性质。**

这个主张既吸收了评审对 D 的肯定，也保留了 C 的可落地性。我认为这是当前最稳的 paper 路线。
