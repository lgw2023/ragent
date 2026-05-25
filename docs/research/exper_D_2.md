# 专家 D 修订方案 (v2)：聚焦 Resolution-Structure Circular Dependency 的收敛实现

基于 [`review_round_1.md`](review_round_1.md) 的综合评审，我对原方案做了以下关键调整：

1. **收敛 CRDT 的适用范围**：评审正确指出"实体合并不是天然 CRDT"，语义判断（两个实体是否应合并）不能被简化为集合 union。因此 CRDT 仅用于物化层的幂等字段（alias set、evidence set、mention count），不再声称解决语义冲突。
2. **放弃完整形式证明**：不再追求 serializability theorem 的完整证明，改为半形式化的不变量陈述 + 实验验证。避免项目过大。
3. **吸收 A 的 staging/log/writer 作为系统骨架**：不重复造轮子，直接把 mention log、append-only staging 作为工程底座。
4. **采纳 C 的评测体系和工程边界**：constraint-based evaluation 取代绝对 gold graph；不声称改进图数据库，明确定位为 ingestion layer。
5. **谨慎吸收 B 的语义冲突意识**：在 resolver 的 scoring 阶段引入 context embedding 区分同名异义，但不以 Semantic Lock Manager 为贡献点。

---

## 1. 核心问题不变：Resolution-Structure Circular Dependency

这是论文最有价值的差异化贡献，不做修改。

设 $M = \{m_1, m_2, \ldots, m_n\}$ 为 LLM 并发抽取的 mention 流，$G_t = (V_t, E_t)$ 为时刻 $t$ 的 canonical graph。实体解析函数：

$$\phi(m_i, G_t) \rightarrow v \in V_t \cup \{\bot\}$$

**核心矛盾**：$\phi$ 的输入包含 $G_t$（解析依赖图中已有实体的属性、别名、邻域），而 $G_t$ 又是之前所有 $\phi$ 决策的累积结果。并发执行下，多个 worker 同时读取 $G_t$，各自做出决策，导致：

- 重复实体：$m_j$ 看不到 $m_i$ 刚创建的 $v_{new}$，额外创建 $v_{new}'$
- 信息丢失：互相依赖的 mention（如 "OpenAI" 和 "Sam Altman"）并发解析时丧失关系消歧信号
- 不可重放：相同输入在不同调度下产生不同图

这个问题位于传统 ER（假设静态输入）、GraphRAG（关注建图后检索）、图数据库事务（处理结构事务不涉及语义歧义）三者的交叉缝隙中，尚未被形式化定义。

---

## 2. 修订后的形式化定义：精简版

原方案试图给出完整的 serializability theorem，评审认为风险过高。修订为以下 4 个核心定义 + 1 个非正式性质，足以支撑论文叙事，不需要完整证明。

**定义 1 (Mention Event)**：$m_i = (s_i, e_i, c_i, \text{ev}_i, R_i)$，包含 surface form、context embedding、confidence、evidence、关联 relation mention 集合。

**定义 2 (Canonical Graph State)**：$G = (V, E, A, P)$，其中 $A: V \rightarrow 2^{\mathcal{M}}$ 为别名映射，$P$ 为 provenance 图。

**定义 3 (Resolution Function)**：$\phi: \mathcal{M} \times G \rightarrow V \cup \{\bot\}$，将 mention 解析到已有 canonical entity 或返回 $\bot$（创建新实体 / defer）。

**定义 4 (Epoch)**：时间被划分为离散的 epoch $[e_1, e_2, \ldots]$。epoch $e_k$ 内所有 mention 基于同一 graph snapshot $G_{e_k}$ 做解析，决策先暂存为 tentative decision set $D_{e_k}$，在 epoch 边界统一提交后更新为 $G_{e_{k+1}}$。

**性质（非正式）**：如果 $\phi$ 对相同的 $(m_i, G)$ 输入产生相同输出（确定性），且物化操作满足幂等性，则：
- 同一 epoch 内的 mention 解析顺序不影响 tentative decision set
- 给定相同的 mention 流和 epoch 划分，replay 产生相同的最终图

不追求完整的 serializability 证明。这个性质通过实验验证（replay determinism 指标）。

---

## 3. 系统架构：三层分离

```text
Layer 1: Mention Ingestion
  LLM extraction workers → Mention Log (append-only)
  职责：结构化 LLM 输出为 MentionEvent，保留全部 provenance

Layer 2: Epoch-based Resolution
  Epoch Scheduler → Snapshot Reader → Resolver → Conflict Detector → Defer Queue
  职责：基于固定 snapshot 做 tentative resolution，检测 intra-epoch 冲突

Layer 3: Deterministic Materialization
  Decision Committer → CRDT-compatible Writer → Canonical Graph
  职责：将 resolution 决策原子提交到主图，保证幂等和可重放
```

### 3.1 Layer 1: Mention Ingestion（采纳自方案 A）

将 `chunk_results` 转化为结构化 `MentionEvent`，而非直接按 entity_name 聚合写入：

```python
@dataclass
class EntityMentionEvent:
    mention_id: str          # deterministic hash(surface_form + source_chunk_id + position)
    surface_form: str
    entity_type: str
    description: str
    confidence: float        # 通过 gleaning overlap 估算
    source_chunk_id: str
    source_doc_id: str
    context_embedding: list[float] | None
    created_at: str          # ISO format, deterministic (基于 source 而非 wall clock)

@dataclass
class RelationMentionEvent:
    mention_id: str
    src_surface: str
    tgt_surface: str
    predicate: str
    description: str
    weight: float
    confidence: float
    source_chunk_id: str
```

所有 mention 写入 append-only log（SQLite 或 JSONL），作为 single source of truth。当前 `merge_nodes_and_edges` 的输入不变，只是在其之前多了一层结构化。

### 3.2 Layer 2: Epoch-based Resolution（核心贡献）

**Epoch 划分**：最小实现以 source_group 为 epoch 边界（一组文档的全部 chunk 结果构成一个 epoch）。后续可扩展为时间窗口或 mention 数量阈值。

**Epoch 内流程**：

1. **Snapshot**：epoch 开始时，读取当前 canonical graph 的 entity list + embeddings，冻结为只读 $G_{e_k}$。
2. **Blocking**：对每个 mention，在 $G_{e_k}$ 上做 candidate blocking（surface similarity + type compatibility + embedding proximity）。这里吸收方案 B 的思路：用 context embedding 区分同名异义（如 "Apple" 公司 vs 水果），但不引入独立的 Semantic Lock Manager。
3. **Scoring**：对候选集打分，产生 tentative decision：merge to existing entity / create new / defer。
4. **Intra-epoch Conflict Detection**：检查本 epoch 内是否有矛盾决策（如两个 mention 分别想合并到不同实体，但它们自身应该被合并）。冲突的 mention 进入 defer queue。

**Epoch 边界**：

5. **Atomic Commit**：将无冲突的 tentative decisions 批量提交到主图。先写新实体节点，再写边，最后更新 vector DB。
6. **Defer 处理**：冲突 mention 留待下一 epoch，此时它们能看到更新后的 $G_{e_{k+1}}$，可能自然消解。

### 3.3 Layer 3: Deterministic Materialization（收敛 CRDT 范围）

原方案试图用 CRDT 覆盖整个实体合并过程，评审指出这不现实。修订后，CRDT 仅用于以下物化字段：

| 字段 | CRDT 类型 | 说明 |
|---|---|---|
| alias_set | G-Set (grow-only) | 实体的所有已知 surface form |
| evidence_set | G-Set | 支持该实体的所有 mention provenance |
| mention_count | G-Counter | 该实体被多少 mention 指向 |
| source_chunk_ids | G-Set | 来源追溯 |
| relation_evidence | OR-Set | 关系的支持/反对证据 |

**不用 CRDT 处理的字段**：
- `description`：语义摘要需要 LLM 介入，不是幂等操作。改为追加 description fragments，定期触发 LLM 重新摘要。
- `entity_type`：多数投票决定，非 CRDT。
- 合并/拆分决策：由 resolver 做语义判断，不能自动收敛。

这样既获得了物化层的幂等性和可重放性，又不夸大 CRDT 的能力边界。

---

## 4. 评测体系（采纳自方案 C + 原方案修订）

### 4.1 不构造绝对 gold graph，改用 constraint-based evaluation

评审和原方案都强调了 gold graph 构造的困难。采用相对约束：

- **Must-link pairs**：已知应合并的 mention 对（如 "OpenAI" 和 "OpenAI Inc."）
- **Must-not-link pairs**：已知不应合并的 mention 对（如 "Apple 公司" 和 "apple 水果"）
- **Must-exist relations**：关键关系必须存在
- **Must-not-exist relations**：幻觉关系必须不存在

评价指标基于 constraint satisfaction rate，而非完全图匹配。这在 ER 评测文献中有先例（pairwise F1）。

### 4.2 双层指标体系

| 类别 | 指标 | 说明 |
|---|---|---|
| 实体质量 | wrong merge rate | 违反 must-not-link 约束的比例 |
| 实体质量 | duplicate entity rate | 违反 must-link 约束的比例 |
| 实体质量 | constraint satisfaction F1 | must-link 和 must-not-link 的综合 F1 |
| 关系质量 | dangling edge rate | 边指向不存在实体的比例 |
| 关系质量 | contradictory relation rate | 互相矛盾的关系对数量 |
| 系统一致性 | replay determinism | 相同输入、不同调度下图是否一致 |
| 系统一致性 | idempotence under retry | 重复提交同一 mention 是否改变图 |
| 性能 | mentions/sec throughput | 不同并发度下的吞吐 |
| 性能 | P95/P99 latency | 尾延迟 |
| 性能 | hot-entity skew throughput | Zipf 分布下的热点实体吞吐 |
| 可运维 | provenance completeness | 每个 canonical entity 能否追溯到所有源 mention |
| 可运维 | defer/human-review ratio | 被 defer 的 mention 占比 |

### 4.3 实验设计

**关键原则**：固定 mention 流（用 `RawMergeUnit` 的 `chunk_results` 转化），只变化物化算法。

**对比方案**：

| 方案 | 说明 |
|---|---|
| B0: Direct-Write | 当前 `merge_nodes_and_edges`，按 entity_name 字符串合并 |
| B1: Staging-Only | 加 mention log + staging，但无 epoch 隔离，resolver 用当前最新图 |
| E1: Epoch-Snapshot | 本方案：epoch-based snapshot isolation + conflict detection |
| E2: Epoch-Snapshot + CRDT Materializer | E1 基础上加 CRDT 物化层 |

**可控变量**：

1. **并发度**：1（串行）→ 2 → 4 → 8 → 16 → 32 → 64，观察质量衰退曲线
2. **Entity skew**：Zipf 分布 $\alpha \in \{0, 0.5, 1.0, 1.5\}$，模拟热点实体（如高频出现的组织名）
3. **歧义度**：控制同名异义和异名同义的 mention 比例
4. **Epoch size**：展示 epoch size $\rightarrow \infty$ 退化为 offline batch ER，epoch size $\rightarrow 1$ 退化为 eager direct-write

**关键实验**：串行执行下所有方案应产生相同质量的图。并发实验的目标是证明 epoch 方案在提升吞吐的同时，质量衰退显著小于 baseline。

### 4.4 公平对待 Baseline

评审特别强调了这一点。确保：

1. Baseline 使用最优并发度配置（不故意用过粗的锁粒度）
2. Baseline 的 LLM summary 阈值与实验方案一致
3. Baseline 的 semaphore / keyed lock 机制保持最优状态
4. 不在 baseline 上施加任何人为劣化

---

## 5. 工程实施：收敛的模块结构

```text
ragent/ingest/
  __init__.py
  mention_event.py          # MentionEvent schema 定义
  mention_log.py            # Append-only mention log (SQLite)
  epoch_scheduler.py        # Epoch 划分与调度
  resolver.py               # Blocking + scoring + decision
  conflict_detector.py      # Intra-epoch 冲突检测
  materializer_crdt.py      # CRDT-compatible 物化（alias_set, evidence_set 等）
  materializer_direct.py    # Baseline wrapper: 当前 merge_nodes_and_edges
  metrics.py                # 实验指标采集
```

### 5.1 不替换 `merge_nodes_and_edges`

与方案 C 一致。保留现有函数作为 baseline，通过配置切换：

```python
# ragent.py 中根据配置选择 materializer
if config.materialization_strategy == "direct":
    await merge_nodes_and_edges(...)  # 现有 baseline
elif config.materialization_strategy == "epoch":
    await epoch_materializer.process(...)  # 新方案
```

### 5.2 Resolver 实现：从简单开始

最小 resolver 不需要是 SOTA ER 算法（评审明确说"不要声称发明了新 ER 算法"）：

1. **Blocking**：surface form 编辑距离 < 阈值 OR embedding cosine similarity > 阈值
2. **Scoring**：加权组合 surface similarity + type compatibility + context embedding similarity
3. **Decision**：score > merge_threshold → merge；score < reject_threshold → create new；中间 → defer

这个 resolver 足够简单，使得论文的对比实验清楚地归因于 epoch 机制而非 ER 算法本身。

### 5.3 置信度获取

复用现有 gleaning 机制（`entity_extract_max_gleaning`）：同一 chunk 多次抽取，计算结果 overlap 作为 confidence proxy。不需要额外 API 调用，有理论解释（bootstrap 估计量）。

---

## 6. 修订后的时间线

| 阶段 | 内容 | 时间 |
|---|---|---|
| W1-W2 | `MentionEvent` schema + mention log + `chunk_results` 转换层；冻结 baseline 配置；构造 must-link / must-not-link gold constraints（小规模，~200 对） | 2 周 |
| W3-W4 | Epoch scheduler + 最简 resolver（surface + embedding blocking）+ CRDT-compatible materializer（仅 alias_set, evidence_set, mention_count） | 2 周 |
| W5-W6 | 固定 mention 流上跑 B0 vs B1 vs E1 vs E2；收集 throughput / quality / conflict 数据 | 2 周 |
| W7-W8 | 变化并发度和 skew 分布的对比实验；撰写形式化定义（4 个定义 + 非正式性质） | 2 周 |
| W9-W10 | 补充实验：epoch size ablation、Neo4j 后端验证、defer ratio 分析 | 2 周 |
| W11-W14 | 论文写作 + 图表制作 + 审稿人预期问题准备 | 4 周 |

总计约 3.5 个月。比原方案多出 2 周，用于更充分的 ablation 和写作准备。

---

## 7. 投稿策略（维持原判断，微调表述）

首选 **VLDB / ICDE**。理由：

1. 这两个会议对 graph ingestion 和 data integration 有明确兴趣
2. 系统实验是第一优先级，形式化是加分项（符合我们"不追求完整证明"的收敛策略）
3. Ragent 提供真实系统实验，比纯理论论文更有说服力

**叙事定位**：不是"更好的 ER 算法"，不是"更好的图数据库"，而是"LLM mention 流的并发 ingestion 协议"。强调 resolution-structure circular dependency 是 ER 社区和图数据库社区都没有形式化的交叉问题。

**应对审稿人的潜在攻击**：

| 审稿人质疑 | 应对 |
|---|---|
| "这只是在图数据库上加了 ETL" | Epoch resolution 解决的是语义层面的 ER-graph 循环依赖，传统 ETL 不处理解析决策依赖目标结构的问题 |
| "Resolver 太简单" | 论文贡献在于 ingestion 协议而非 ER 算法本身；简单 resolver 反而证明架构的通用性 |
| "为什么不用现有 ER 工具" | 现有 ER 假设静态输入集，不处理被并发修改的目标图；实验中可在小规模 gold set 上与 ZeroER/Ditto 做质量对比 |
| "CRDT 的使用范围太窄" | 这是刻意的——语义判断不能用 CRDT 自动解决，我们只在保证幂等性的物化字段上使用 CRDT |
| "Epoch size 怎么选" | Ablation 实验展示 epoch size 从 1 到 ∞ 的 tradeoff 曲线，让用户根据场景选择 |

---

## 8. 与原方案 (v1) 的差异总结

| 维度 | v1 | v2 |
|---|---|---|
| CRDT 范围 | 覆盖整个实体模型（G-Counter + LWW-Register + OR-Set） | 仅物化层幂等字段（alias_set, evidence_set, mention_count） |
| 形式化深度 | 追求 serializability theorem 的完整证明 | 4 个核心定义 + 非正式性质 + 实验验证 |
| 系统骨架 | 自建全部模块 | 采纳方案 A 的 mention log / staging |
| 评测方法 | 提到 constraint-based 但未展开 | 完整的 constraint-based evaluation 体系（采纳自方案 C） |
| 语义冲突 | 未充分处理 | 在 resolver scoring 中吸收方案 B 的 context embedding 区分能力 |
| Description 合并 | 用 LWW-Register | 改为追加 fragments + 定期 LLM 重摘要（非 CRDT） |
| Baseline 对比 | 提到但不够详细 | 4 个对比方案（B0, B1, E1, E2）+ 公平性保证 |
| 时间线 | 3 个月 | 3.5 个月（多出 ablation 和写作时间） |

---

## 9. 最终立场

核心判断不变：**本论文最有价值的贡献是 Resolution-Structure Circular Dependency 这个问题定义本身**，以及 epoch-based snapshot isolation 作为解决框架。

修订的核心是**收敛**：
- 不做所有理论概念的完整实现
- 不声称 CRDT 能解决语义冲突
- 不追求完整形式证明
- 不替换现有工程代码，而是在其上构建可控的实验层

这是一篇"有理论框架、有形式化定义、有可控实验"的系统论文，不是一篇纯理论论文，也不是一篇系统 demo paper。Ragent 仓库的工程基础已经足够好，关键是把问题收窄、定义清楚、实验做干净。
