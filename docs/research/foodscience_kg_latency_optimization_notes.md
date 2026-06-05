# FoodScience KG 检索加速研究记录

日期：2026-06-05

本文档记录 FoodScience 大规模知识图谱检索加速工作的已知背景、已完成改造、已有单题测试结果、远程 HNSW/ANN 实验结果、远程实验提示词和后续文章写作边界。

## 1. 研究对象与初始问题

原始评估对象是服务器上的单项目知识图谱：

```text
/data/disk1/FoodScience_KG_final_sharded
```

后续远程实验使用的实际路径是：

```text
/data/disk3/FoodScience_KG_final_sharded
```

原始报告显示，`FoodScience_KG_final_sharded` 虽然目录名包含 `sharded`，但实际是合并后的扁平单项目目录，不是 `kg_000` 到 `kg_063` 这种联邦分片目录。

规模摘要：

| 项 | 数量 / 大小 |
| --- | ---: |
| 文档数 | 6,520 |
| text chunks | 58,184 |
| 图节点 | 228,259 |
| 图边 | 905,580 |
| entities vdb | 228,259，维度 2560 |
| relationships vdb | 905,580，维度 2560 |
| chunks vdb | 58,184，维度 2560 |
| `graph_chunk_entity_relation.graphml` | 3.9 GB |
| `vdb_entities.json` | 3.3 GB |
| `vdb_relationships.json` | 12 GB |
| `vdb_chunks.json` | 904 MB |
| 目录合计 | 约 21 GB |

原始热会话、冷缓存查询结果：

| 指标 | 值 |
| --- | ---: |
| HTTP 总耗时 | 84.4 s |
| `onehop_total` | 84.2 s |
| `hybrid_retrieval_total` | 84.01 s |
| `keyword_extraction` | 6.91 s |
| `graph_entity_vector_index_search` | 17.73 s |
| `graph_relation_vector_index_search` | 75.30 s |
| `rerank` | 0.75 s |
| 召回 chunk 数 | 10 |
| 缓存命中 | 0 |

原始冷启动结果：

| 指标 | 值 |
| --- | ---: |
| 总 wall time | 690.0 s |
| `rag_initialization_total` | 627.2 s |
| `rag_object_setup` | 625.0 s |
| 首次 `onehop_total` | 62.6 s |
| 首次 `hybrid_retrieval_total` | 62.43 s |
| 首次 `graph_relation_vector_index_search` | 56.93 s |
| 召回 chunk 数 | 10 |
| 缓存命中 | 0 |

初始瓶颈判断：

- 热会话检索阶段主要耗时来自 `graph_relation_vector_index_search`，即 90 万级 relationships 向量库的搜索。
- 冷启动主要耗时来自 GraphML 与三个 JSON 向量库加载，`rag_object_setup` 接近 625 s。
- `rerank`、图遍历、候选合并、final context selection 都不是主瓶颈。

## 2. 已完成的代码层改造

已完成的核心思路是：不重建 KG，不重新抽取实体关系，不重新嵌入；从现有 `vdb_chunks.json`、`vdb_entities.json`、`vdb_relationships.json` 构建只读 FAISS sidecar，把热查询中的 NanoVectorDB Python 侧全量扫描替换成 FAISS 索引搜索。

相关提交：

| 提交 | 用途 |
| --- | --- |
| `e2f3578 feat(vector): add FAISS sidecar runtime storage` | 引入 FAISS sidecar 运行时存储、构建工具、preload 和测试 |
| `2c13e06 chore: add FoodScience KG latency ANN remote task` | 新增远程 HNSW 实验任务文档 |

主要改造点：

| 模块 | 作用 |
| --- | --- |
| `ragent/kg/faiss_sidecar_impl.py` | 新增只读 `FaissSidecarVectorDBStorage`，通过 FAISS index + SQLite metadata 响应向量查询 |
| `tools/build_vector_sidecars.py` | 从现有 Nano vdb JSON 构建 sidecar，支持 `flat`、`hnsw`、`ivf_flat` |
| `ragent/ragent.py` | 支持通过 `RAG_VECTOR_RUNTIME_BACKEND=faiss_sidecar` 默认切换向量后端 |
| `ragent/kg/__init__.py` | 注册 `FaissSidecarVectorDBStorage` |
| `ragent/api/benchmark_service.py` | 支持 `RAG_PRELOAD_PROJECT_DIRS`，服务启动时预加载项目 |
| `docs/operations/faiss_sidecar_runtime.md` | 记录 sidecar 构建、服务启动、对比与回滚方法 |
| `tasks/foodscience_kg_latency_ann/` | 给远程服务器 AI 助手执行 HNSW 实验的任务目录 |

当前实现边界：

- exact FAISS `flat` 是精确搜索，能避免 Nano 的 JSON/Python 搜索路径，但仍是全量向量扫描。
- HNSW/IVF 已在构建工具中支持，但是否启用取决于 sidecar manifest；默认 exact runbook 仍是 `flat`。
- `RAG_PRELOAD_PROJECT_DIRS` 只能把首查初始化前移到服务启动阶段，不能消除初始化成本。
- 端到端是否达到 10 s 以内，必须依赖服务器上的真实 benchmark；本地没有图谱，不能证明。

### 2.1 技术原理：为什么 FAISS exact 与 HNSW 能大幅提速

原始 Nano 路径、FAISS exact 和 HNSW ef128 的核心差异如下：

| 路径 | 搜索类型 | 核心机制 | 性能收益来源 |
| --- | --- | --- | --- |
| NanoVectorDB | 精确搜索 | 对 JSON/内存中的 relationships 向量做 Python/NumPy 侧全量相似度扫描 | 无索引加速；在 90 万级、2560 维向量上开销很高 |
| FAISS exact (`flat`) | 精确搜索 | 将向量预处理为连续 `float32` 矩阵，L2 normalize 后写入 `IndexFlatIP`，查询时仍比较全部向量 | 同样全量扫描，但由 FAISS C++/SIMD 和缓存友好的矩阵布局执行 |
| HNSW ef128 | 近似搜索 | 将 relationships 向量组织成多层近邻图，查询时在图上导航，只访问小候选集 | 不再扫描全部 90 万 relationships 向量，算法层面减少访问量 |

原始 Nano 慢在两个层面：

- relationships vdb 约 905,580 条向量，每条 2560 维；一次关系检索近似需要执行 `905,580 x 2560` 维点积并取 top-k。
- JSON 形态和 Python 侧对象路径不适合高性能向量检索，数据布局、调度、候选排序都有额外开销。

FAISS exact 的收益不是因为少算了候选，而是因为把同样的精确全量扫描交给了高性能向量检索库：

- sidecar 构建时把 Nano vdb JSON 解码为连续 `float32` 矩阵；
- 向量和 query 都做 L2 normalization，用 inner product 近似 cosine similarity；
- `flat` index 使用 `IndexFlatIP`，仍返回 exact top-k；
- 元数据拆到 SQLite，向量搜索和记录读取解耦；
- 运行时通过 `faiss.read_index(...).search(...)` 搜索，并用 `asyncio.to_thread` 避免阻塞事件循环。

因此 FAISS exact 解决的是“工程实现慢”的问题：结果仍是精确搜索，但由 C++/SIMD、连续内存和高效 top-k 实现执行。

HNSW ef128 的收益来自算法层面。HNSW（Hierarchical Navigable Small World）会在构建 sidecar 时建立多层近邻图：

- 上层图更稀疏，用于快速跳到 query 附近的向量区域；
- 下层图更密，用于局部扩展和精细搜索；
- 查询时不再遍历全部向量，而是从入口点沿近邻图搜索有限候选。

`ef_search` 控制搜索时保留的候选宽度：

- `ef_search` 越大，召回通常更稳，但访问候选更多、速度可能下降；
- `ef_search` 越小，速度可能更快，但更容易漏掉 exact top-k；
- 本轮 ef64/ef128/ef256 sweep 显示三者关系索引耗时都极低，ef256 在部分 referenced-file alignment 上更接近 exact。

这解释了观测到的分段收益：

| 对比 | relation index median |
| --- | ---: |
| Nano | 54.15 s |
| FAISS exact | 7.76 s |
| HNSW ef128 | 0.04 s |

可解释为两段改进：

- Nano -> FAISS exact：同样精确全量扫描，但换成 FAISS 高性能实现，解决数据布局和 Python 路径开销。
- FAISS exact -> HNSW ef128：从全量扫描变成近似图搜索，避免访问绝大多数 relationships 向量。

质量上，HNSW 是近似检索，理论上可能漏掉 exact top-k。本轮 10-query smoke 中 HNSW ef128 与 exact FAISS 的 final chunk ID overlap 为 10/10，说明当前 `ef_search=128` 在最终证据 chunk 层面足够稳定；但 referenced files 仍有漂移，因此不能把 HNSW 写成与 exact 完全等价。

## 3. 已有 A/B 单题服务器测试结果

测试设置来自用户在 2026-06-04 回传的服务器结果。

| 项 | 值 |
| --- | --- |
| 接口 | `POST /v1/benchmark/query` |
| 项目 | `/data/disk3/FoodScience_KG_final_sharded` |
| 模式 | `hybrid`，`enable_rerank=true`，完整链路，含 LLM 作答 |
| 基础问题 | 乳制品保质期与防腐因素，英文，152 字符主体 |
| 防缓存扰动 | A：`#cb-A-8099-f7a2`；B：`#cb-B-8101-e91b`，带零宽/不同后缀 |
| 缓存 | 两次均为 `cache_hit_count: 0` |
| 原始 JSON | `/tmp/benchmark_query_compare.json` |
| 注意 | 两实例本次均为 `project_first_request: true`，包含 benchmark 会话内首条业务 query 路径 |

总体时延：

| 指标 | A：FAISS sidecar `:8099` | B：Nano `:8101` | B/A |
| --- | ---: | ---: | ---: |
| 客户端墙钟 | 22.77 s | 76.50 s | 3.36x |
| `request_processing_seconds` | 22.76 s | 76.49 s | 3.36x |
| `onehop_total` / `query_seconds` | 22.73 s | 76.45 s | 3.36x |
| `hybrid_retrieval_total` | 13.41 s | 63.10 s | 4.71x |
| `answer_generation` | 9.12 s | 13.11 s | 1.44x |

检索阶段分解：

| 阶段 | A：FAISS | B：Nano | 说明 |
| --- | ---: | ---: | --- |
| relationships 向量索引搜索 | 4.80 s | 47.98 s | 主要差距来源，约 10x |
| entities 向量索引搜索 | 2.95 s | 9.80 s | 约 3.3x |
| relationships query embedding | 1.84 s | 11.60 s | B 侧与 relation hits 重叠偏大，优先看 index search |
| entities query embedding | 1.93 s | 1.74 s | 接近 |
| chunks index search | 0.22 s | 0.65 s | 约 3x |
| chunk / 混合 vector_retrieval | 1.80 s | 2.06 s | 接近 |
| rerank | 0.96 s | 1.01 s | 几乎相同，走外网 API |
| keyword_extraction | 5.41 s | 2.20 s | A 更慢，属于 LLM/关键词路径波动，不是向量主因 |

结果规模：

| 项 | A：FAISS `:8099` | B：Nano `:8101` |
| --- | ---: | ---: |
| `reference_chunk_count` | 10 | 10 |
| `referenced_file_paths` | 17 | 17 |
| 答案长度 | 526 字 | 898 字 |

阶段性结论：

- FAISS sidecar 已经显著降低检索耗时：完整链路从 76.50 s 降到 22.77 s，检索段从 63.10 s 降到 13.41 s。
- 最大收益来自 relationships 向量索引搜索：约 47.98 s 降到 4.80 s。
- 这证明“替换 Nano 全量扫描路径”方向有效，但还不能证明完整链路已经达到 10 s。
- A 侧完整链路仍约 23 s，其中 `answer_generation` 约 9.12 s，`keyword_extraction` 约 5.41 s。即使进一步压低 relationships search，完整链路仍可能被 LLM 阶段限制。
- 当前 A 侧如果 manifest 中 `relationships=index_type=flat`，则还没有真正启用 ANN；HNSW 需要单独构建并验证质量。

## 4. 远程 HNSW 实验结果

结果文件：

```text
tasks/foodscience_kg_latency_ann/RESULTS_TEMPLATE.md
```

远程实验完成于 2026-06-04，补充实验完成于 2026-06-05。

### 4.1 环境与产物

| 项 | 值 |
| --- | --- |
| 服务器 | `DevServer-BMS-3d97cc99-0` |
| 远程仓库 | `/data/disk3/ragent-20260604_105639` |
| 远程 commit | `2c13e06686a356fcd050a93318bea025041b71d5` |
| Python | 3.10.20 (`uv run`) |
| uv | 0.11.14 |
| FAISS | 1.13.2 |
| KG project | `/data/disk3/FoodScience_KG_final_sharded` |
| 原始 JSON 目录 | `benchmark/foodscience_kg_latency_ann_20260604_2243/raw/`，远程 80 个文件 |
| 汇总文件 | `benchmark/foodscience_kg_latency_ann_20260604_2243/summary.json` |

本机当前没有远程 `benchmark/foodscience_kg_latency_ann_20260604_2243/` 原始目录；本记录依据远程助手回填的 `RESULTS_TEMPLATE.md` 汇总。

### 4.2 服务与 sidecar

| Variant | URL | Backend | Sidecar |
| --- | --- | --- | --- |
| Nano | `http://127.0.0.1:8101` | Nano JSON VDB | n/a |
| FAISS exact | `http://127.0.0.1:8099` | FAISS sidecar | `/data/disk3/FoodScience_KG_final_sharded_sidecar_exact` |
| FAISS HNSW ef128 | `http://127.0.0.1:8102` | FAISS sidecar | `/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef128` |
| FAISS HNSW ef64 | `http://127.0.0.1:8103` | FAISS sidecar | `/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef64` |
| FAISS HNSW ef256 | `http://127.0.0.1:8104` | FAISS sidecar | `/data/disk3/FoodScience_KG_final_sharded_sidecar_rel_hnsw_m16_ef256` |

Exact FAISS manifest：

| Namespace | Index type | Count | Search params |
| --- | --- | ---: | --- |
| chunks | flat | 58,184 | `{}` |
| entities | flat | 228,259 | `{}` |
| relationships | flat | 905,580 | `{}` |

HNSW manifest：

| Namespace | Index type | Count | Search params |
| --- | --- | ---: | --- |
| chunks | flat | 58,184 | `{}` |
| entities | flat | 228,259 | `{}` |
| relationships | hnsw | 905,580 | ef128: `{"ef_search":128}`；ef64: `{"ef_search":64}`；ef256: `{"ef_search":256}` |

HNSW ef128 构建耗时 593.12 s，约 9.9 min；输出目录约 13 GB。ef64/ef256 是基于相同 FAISS index 文件的 hardlink copy + manifest patch，主要用于调整 `ef_search`。

### 4.3 Retrieval-only 结果

设置：`retrieval_only=true`，`enable_rerank=true`，`include_trace=true`。10 queries x 3 baseline variants，共 30 requests，全部 `cache_hit_count=0`。

| Variant | Runs | Median request s | p95 request s | Median retrieval s | p95 retrieval s | Median relation index s | p95 relation index s | Median entity index s | p95 entity index s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nano | 10 | 75.76 | 105.11 | 75.64 | 104.95 | 54.15 | 81.32 | 15.16 | 18.88 |
| FAISS exact | 10 | 14.73 | 21.84 | 14.63 | 21.72 | 7.76 | 9.10 | 2.20 | 2.35 |
| FAISS HNSW ef128 | 10 | 9.09 | 12.79 | 8.99 | 12.63 | 0.04 | 0.08 | 2.10 | 2.30 |

关键结论：

- relationships index median：Nano 54.15 s，FAISS exact 7.76 s，HNSW ef128 0.04 s。
- HNSW ef128 相对 FAISS exact，retrieval median 从 14.63 s 降到 8.99 s，约 38.5% 更快。
- HNSW ef128 的关系索引 p95 为 0.08 s，远低于 1.5 s 目标。

### 4.4 Full-chain 结果

设置：`retrieval_only=false`，`enable_rerank=true`，`include_trace=true`。10 queries x 3 variants，共 30 requests，全部 `cache_hit_count=0`。

| Variant | Runs | Median request s | p95 request s | Median retrieval s | p95 retrieval s | Median answer_generation s | p95 answer_generation s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nano | 10 | 106.22 | 277.71 | 87.35 | 261.23 | 17.08 | 21.38 |
| FAISS exact | 10 | 29.93 | 37.98 | 13.60 | 15.42 | 16.50 | 22.96 |
| FAISS HNSW ef128 | 10 | 27.00 | 29.68 | 9.53 | 10.91 | 17.11 | 21.38 |

关键结论：

- HNSW ef128 相对 exact FAISS，full-chain median request 从 29.93 s 降到 27.00 s，约 10% 更快。
- full-chain median retrieval 从 13.60 s 降到 9.53 s，约 30% 更快。
- 完整链路仍主要受 `answer_generation` 约 17 s 限制；HNSW 不能单独把完整答案延迟压到 10 s 内。

### 4.5 Stage breakdown

Median seconds：

| Variant | relation index | entity index | chunks index | vector_retrieval | keyword_extraction | rerank | answer_generation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nano retrieval-only | 54.15 | 15.16 | 0.59 | 2.35 | 3.88 | 1.01 | n/a |
| FAISS exact retrieval-only | 7.76 | 2.20 | 0.49 | 2.01 | 3.37 | 1.00 | n/a |
| FAISS HNSW ef128 retrieval-only | 0.04 | 2.10 | 0.23 | 1.80 | 3.26 | 0.99 | n/a |
| Nano full-chain | 55.70 | 15.21 | 0.72 | 2.70 | 3.22 | 1.02 | 17.08 |
| FAISS exact full-chain | 7.28 | 2.26 | 0.40 | 2.14 | 3.30 | 0.97 | 16.50 |
| FAISS HNSW ef128 full-chain | 0.03 | 2.11 | 0.25 | 1.77 | 3.09 | 0.98 | 17.11 |

HNSW 之后，relationships 向量索引搜索不再是主瓶颈；剩余检索耗时主要来自 entity index、keyword extraction、vector retrieval 和 rerank，完整链路还叠加 LLM answer generation。

### 4.6 ef_search sweep

Retrieval-only，10 queries each，全部 `cache_hit_count=0`。

| Variant | Median request s | p95 request s | Median relation index s | p95 relation index s | Median retrieval s | p95 retrieval s | q07 ref files |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ef128 | 9.09 | 12.79 | 0.04 | 0.08 | 8.99 | 12.63 | 7 |
| ef64 | 9.27 | 14.09 | 0.03 | 0.07 | 9.15 | 13.98 | 12 |
| ef256 | 8.61 | 14.42 | 0.03 | 0.06 | 8.51 | 14.30 | 14 |

判断：

- 三个 `ef_search` 都满足关系索引 median <1.5 s。
- ef256 在 q07 的 referenced-file alignment 上比 ef128 更接近 exact，但 p95 retrieval 略高。
- 当前建议是 ef128 作为默认 profile，ef256 作为质量优先 profile。

### 4.7 质量观察

HNSW ef128 与 exact FAISS 的 retrieval-only 对比中，10 个查询的 final chunk ID overlap 均为 10/10。

| Query ID | Exact ref chunks | HNSW ref chunks | Chunk overlap | Exact referenced files | HNSW referenced files | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| q01_dairy_shelf_life | 10 | 10 | 10 | 13 | 14 | |
| q02_prepackaged_labeling | 10 | 10 | 10 | 15 | 16 | |
| q03_preservative_limits | 10 | 10 | 10 | 7 | 12 | |
| q04_water_activity_spoilage | 10 | 10 | 10 | 20 | 20 | |
| q05_haccp_meat_products | 10 | 10 | 10 | 16 | 15 | |
| q06_seafood_cold_chain | 10 | 10 | 10 | 12 | 14 | |
| q07_cereal_mycotoxins | 10 | 10 | 10 | 15 | 7 | chunk IDs match；ef256 gives 14/15 file-path alignment |
| q08_fermented_dairy | 10 | 10 | 10 | 10 | 10 | |
| q09_food_allergens | 10 | 10 | 10 | 10 | 10 | |
| q10_thermal_processing | 10 | 10 | 10 | 17 | 16 | |

质量边界：

- final chunk ID overlap 10/10 是强信号，说明 ef128 未破坏最终证据 chunk 集合。
- referenced files 有漂移，尤其 q07；不能仅凭 `referenced_file_paths` 声称完全等价。
- 这仍是 10-query smoke，不是全量质量评测。

### 4.8 当前决策

远程实验结论：promote relationships HNSW with `ef_search=128` as default；保留 `ef_search=256` 作为质量优先 profile。

理由：

- `relationships` manifest 已确认为 `hnsw`。
- relation-index median 约 0.03 到 0.04 s，p95 低于 0.08 s。
- retrieval-only median retrieval 从 exact 的 14.63 s 降到 8.99 s。
- full-chain median retrieval 从 exact 的 13.60 s 降到 9.53 s。
- final chunk ID overlap 在 10-query set 上为 10/10。
- 完整链路仍 LLM-bound，HNSW 是检索层优化，不是完整问答低于 10 s 的充分条件。

## 5. 给远程助手的提示词

下面是已给用户的远程执行提示词，可用于后续复现实验或让另一台服务器继续执行。

```text
请执行仓库中的远程实验任务：

tasks/foodscience_kg_latency_ann/README.md

要求：

1. 先完整阅读 README.md、queries.jsonl 和 RESULTS_TEMPLATE.md。
2. 知识图谱位于：
   /data/disk3/FoodScience_KG_final_sharded
3. 严格按照 README.md 执行检查、构建 relationships HNSW sidecar、启动独立服务并进行实验。
4. 不要重建知识图谱，不要覆盖或删除现有图谱、sidecar 和实验数据。
5. 保留现有 Nano :8101 和 FAISS exact :8099 服务；HNSW 使用新端口 :8102。
6. 优先完成 10 条查询的 retrieval_only 对比；资源允许时再完成完整链路对比。
7. 所有请求必须检查 cache_hit_count，冷缓存对比要求为 0。
8. 保存原始响应 JSON、服务日志、manifest 和执行命令。
9. 将实验结果完整回填到：
   tasks/foodscience_kg_latency_ann/RESULTS_TEMPLATE.md
10. 不要只给口头总结。完成后告诉我：
    - 修改了哪些文件
    - 原始实验结果保存路径
    - exact 与 HNSW 的 p50/p95
    - 检索质量变化
    - 是否建议启用 HNSW
    - 遇到的失败或未完成事项

开始前先确认当前仓库代码支持：
tools/build_vector_sidecars.py
ragent/kg/faiss_sidecar_impl.py

如果环境、服务端口、sidecar 路径与任务文档不一致，请根据服务器实际情况调整，并在 RESULTS_TEMPLATE.md 中记录调整原因。持续执行到实验完成；只有遇到可能破坏现有数据或无法自行解决的阻塞时才询问我。
```

## 6. 后续文章可用论述边界

可以写：

- 大规模 KG 的线上问答延迟并不只由 LLM 生成决定，关系向量库检索可能成为主导瓶颈。
- 在 90 万级 relationships、2560 维 embedding 场景下，NanoVectorDB 的全量扫描路径导致单次关系向量搜索达到几十秒。
- 将现有向量库离线转换为 FAISS sidecar，可在不重建 KG、不重跑 embedding 的条件下显著降低检索时延。
- 单题服务器 A/B 显示，FAISS sidecar 将完整链路从约 76.5 s 降至约 22.8 s，将检索段从约 63.1 s 降至约 13.4 s。
- 主要收益来自 relationship vector index search，从约 48 s 降至约 4.8 s。
- 10-query retrieval-only 实验显示，relationships HNSW ef128 将 relation index median 从 exact FAISS 的 7.76 s 降至 0.04 s，p95 从 9.10 s 降至 0.08 s。
- 10-query retrieval-only 实验显示，HNSW ef128 将 hybrid retrieval median 从 exact FAISS 的 14.63 s 降至 8.99 s。
- 10-query full-chain 实验显示，HNSW ef128 将 median retrieval 从 13.60 s 降至 9.53 s，但 median request 只从 29.93 s 降至 27.00 s，因为 answer generation 约 17 s。
- 在 10-query smoke set 上，HNSW ef128 与 exact FAISS 的 final context chunk ID overlap 为 10/10，未观察到 chunk 级证据集合退化。
- `ef_search=128` 可作为默认 HNSW profile；`ef_search=256` 可作为质量优先 profile，尤其用于改善部分 query 的 referenced-file alignment。

暂时不能写成定论：

- 不能声称完整链路已经稳定低于 10 s。
- 不能声称完整问答系统已解除所有性能瓶颈；HNSW 之后瓶颈转移到 answer generation、keyword extraction、entity index 等阶段。
- 不能声称质量完全不变；当前证据是 10-query final chunk ID overlap 10/10，但 referenced files 有漂移，且缺少人工答案质量评估。
- 不能把 10-query smoke 扩大表述成生产全量 p95；仍需要更大查询集、并发场景和长时间运行数据。
- 不能把 preload 说成消除初始化成本；它只是把初始化从首个用户请求转移到服务启动阶段。

待补充数据：

- 更大规模查询集上的 retrieval-only 与 full-chain p50/p95。
- HNSW under concurrency 的吞吐、排队和内存占用。
- answer generation 优化实验，例如更快模型、流式响应、回答长度控制或分阶段生成策略。
- entity index 是否需要 ANN 或进一步批量化优化。
- HNSW `ef_search=128/256` 在人工答案质量上的差异。

## 7. 下一阶段检索层计划

用户确认完整问答 LLM 推理时间不属于本项目范围，因此下一阶段只做 retrieval-only：

- 不再以 full-chain request latency 作为优化目标。
- 不再把 `answer_generation` 作为本项目瓶颈处理。
- 继续优化 entities 向量检索、search params、retrieval-only p95 和并发队列表现。

已新增远程任务：

```text
tasks/foodscience_kg_retrieval_scaleup/
```

任务内容：

| 文件 | 用途 |
| --- | --- |
| `README.md` | 远程执行说明，包含 entities HNSW sidecar 构建、服务启动、实验门槛 |
| `queries_50.jsonl` | 50 条 FoodScience retrieval-only 查询 |
| `run_retrieval_only_scaleup.py` | HTTP runner，支持多 variant、多并发、cache-buster、raw JSON 和 summary 输出 |
| `RESULTS_TEMPLATE.md` | 远程助手回填模板 |

同时已给 sidecar builder 增加 namespace 级别搜索配置：

```text
--entities-index-type
--entities-hnsw-ef-search
--relationships-hnsw-ef-search
--entities-ivf-nprobe
--relationships-ivf-nprobe
```

推荐下一轮候选：

| Variant | chunks | entities | relationships | 用途 |
| --- | --- | --- | --- | --- |
| `exact` | flat | flat | flat | 质量 oracle |
| `rel_hnsw_ef128` | flat | flat | hnsw ef128 | 当前默认 |
| `ent_hnsw_e128_rel_hnsw_r128` | flat | hnsw ef128 | hnsw ef128 | entities ANN 候选 |
| `ent_hnsw_e64_rel_hnsw_r128` | flat | hnsw ef64 | hnsw ef128 | 速度优先候选 |
| `ent_hnsw_e256_rel_hnsw_r128` | flat | hnsw ef256 | hnsw ef128 | 质量优先候选 |

下一轮成功标准：

- 与 `rel_hnsw_ef128` 相比，retrieval-only p50/p95 更低或至少 p95 不变且 median 更低。
- `graph_entity_vector_index_search` 明显低于当前约 2.1 s。
- final context chunk overlap 对 exact 没有系统性下降；低于 8/10 的 query 必须逐条解释。
- 并发 2/4/8 下没有系统性 5xx、timeout 或 cache 命中污染。
- 如果 entities HNSW 对 p95 没有贡献，就保持 entities flat，不为复杂度买单。
