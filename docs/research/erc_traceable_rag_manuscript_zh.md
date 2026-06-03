# 面向专业 PDF 知识库的可追溯 ERC 异构证据图增强检索生成框架

作者：待补充

单位：待补充

版本：中文 Markdown 初稿，2026-06-03

英文题名：Provenance-Aware Entity-Relation-Chunk Evidence Graphs for Traceable Multi-Evidence Retrieval-Augmented Generation

## 摘要

专业 PDF 知识库问答常常需要同时定位定义、阈值、表格、跨章节描述和跨文档证据。传统 chunk-only RAG 在这类任务中容易出现局部命中、证据链缺失、数值或条件约束不完整，以及答案结论无法回溯到原文的问题。本文整理并评估一种面向可追溯多证据检索增强生成的 Entity-Relation-Chunk（ERC）异构证据图框架：系统将原始 chunk、抽取实体和抽取关系统一组织为带 provenance 的证据网络，并在查询阶段组合 chunk 语义召回、实体召回、关系召回、图邻域扩展、query variants、rerank 和 coverage-aware evidence selection。

本文第一版仅使用本仓库中可验证的实验材料和代码产物，不引入外部文献检索结果。主实验采用 DQE current gold 映射得到的 186 题数据集，共包含 331 条 required evidence，全部映射到真实 ragent project chunk，未引入伪 page、伪 chunk_id 或合成 source_ref。主 live artifact 为 `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014`，覆盖 B0-B7-Full 九种配置，`results.jsonl` 为 2232 行，`judge_results.jsonl` 为 1674 行且状态均为 `ok`。

实验结论应限定在 retrieval layer 和 provenance organization 层面。当前最佳端到端检索配置是 B7（B6 + rerank），其 `final_evidence_recall=0.4218`、`required_evidence_coverage=0.6123`，均高于 chunk-only B0 的 0.3315 和 0.4158。Full 配置在 evidence selection 修复后已明显缓解 selection drop，但仍略低于 B7（`final_evidence_recall=0.4164`、`required_evidence_coverage=0.6096`），因此不能写成最终成功版本。downstream correctness、faithfulness 和 unsupported claim rate 在本文中只作为答案生成链路诊断，不作为 retrieval module 的主 claim。工程层面，当前可支持 read-only replay isolation（`readonly_snapshot_unchanged=True`），但 fresh online build 与 raw replay 尚未等价（`online_vs_replay_match=False`），需要作为明确 limitation。

关键词：可追溯 RAG；异构证据图；实体关系检索；多证据问答；DQE-mapped benchmark；PDF 知识库

## 1. 引言

专业 PDF 知识库中的问答任务不同于开放域短事实检索。用户提出的问题往往不是询问单一事实，而是要求系统同时满足多项条件、综合多个来源、保留出处，并在必要时执行数值或阈值判断。例如，营养指南、慢病食养指南和食品标准文档中的问题通常包含人群条件、摄入限制、推荐模式、标准范围、表格数值和跨文档比较。若系统只依赖局部 chunk 相似度，可能命中一个相关段落，却遗漏同一答案所需的其他证据，从而生成看似流畅但无法完整追溯的回答。

本文关注的问题不是“最终回答是否写得足够好”，而是更基础的 retrieval contract：系统是否能把回答所需证据以真实 chunk、真实 page、真实 source_ref 和可审计组件路径组织出来。这个边界很重要。业务系统可以在检索层输出的证据基础上自行设计 prompt assembly、答案模板、引用格式和人工审核机制；因此，检索模块本身首先要证明它能提高 required evidence coverage、final evidence recall 和 provenance completeness。

ERC 框架的核心思想是把 Chunk、Entity 和 Relation 看作同一个证据网络中的不同节点或证据视角。chunk 提供原文语义片段，entity 提供概念锚点，relation 提供条件、比较和约束结构，三者均保留 source_chunk_ids、source_ref、page_numbers、section_path 和 file_path 等 provenance 字段。查询时，系统不只执行 chunk vector retrieval，而是通过实体/关系召回、图邻域扩展、query variants 和 rerank 逐步扩大候选证据，再通过 evidence selection 形成最终上下文。

本文的贡献可以概括为四点：

1. 提出并整理了面向专业 PDF 问答的 provenance-aware ERC 异构证据图建模方式，将 chunk、entity、relation 和 source metadata 组织为可回溯证据结构。
2. 构建了基于 DQE current gold 的 ERC live benchmark。186 个问题全部 answerable，331 条 required evidence 全部映射到真实 ragent chunk，且映射修复仅允许同文档 gold_evidence 校验。
3. 在同一 live project、同一 dataset 和同一 LLM judge 约束下完成 B0-B7-Full 全矩阵消融，显示 graph-aware retrieval components 对 required evidence coverage 和 final evidence recall 有可测收益。
4. 将代码和工程改进纳入论文叙述，包括 DQE 导入、live eval harness、断点续跑、judge 恢复、component attribution、follow-up diagnostics、cache control 和 build/replay/read-only audit。

相关工作与外部引用在本初稿中刻意保持占位。由于本次任务要求第一版只使用本仓库可验证证据，本文不虚构外部论文引用，也不把 DQE-Bench 历史系统分数写成 ERC live result。后续若进入投稿版本，应补充 KG-RAG、GraphRAG、RAG provenance、PDF document QA、benchmark construction 和 evidence attribution 相关文献。

## 2. 问题定义

给定一个由专业 PDF 文档构成的知识库，以及一个可能需要多段证据、多文档比较或表格数值判断的问题，系统需要返回两类输出：一是可用于生成答案的最终证据集合，二是基于证据生成的回答。本文将两者分开评估。

检索层目标是：在不伪造出处的前提下，最大化 required evidence 的覆盖。每个 required evidence 应尽量映射到真实 project chunk，并保留 source_ref、page_numbers、section_path、file_path 和 chunk_id。若证据无法映射，则必须显式标记 unmatched，而不能补造 chunk_id 或 page。

答案层目标是：在已检索证据的基础上生成正确、完整、相关、faithful 且数值准确的回答。本文保留 correctness、completeness、faithfulness、numerical_accuracy 和 unsupported_claim_rate，但这些指标被定位为 downstream diagnostic，因为最终答案还受到 prompt construction、context assembly、LLM model capability 和输出格式约束的影响。

据此，本文提出三个研究问题：

RQ1：provenance-aware ERC 异构证据图是否比 chunk-only retrieval 更能覆盖复杂问题所需的多源证据？

RQ2：在当前实现中，entity retrieval、relation retrieval、graph expansion、query variants、rerank 和 evidence selection 分别带来哪些收益或退化？

RQ3：当前工程路径是否支持可复现实验、只读推理隔离和实际缓存加速；哪些 build/replay 主张尚不能成立？

## 3. ERC 方法

### 3.1 ERC 异构证据图

ERC 框架将原始 chunk、抽取实体和抽取关系统一纳入一个带 provenance 的证据网络。chunk 是检索和引用的基本文本单元；entity 是从 chunk 中抽取出的概念、对象或术语；relation 描述实体之间的比较、条件、归属、限制和上下文关系。entity 和 relation 并不脱离原文存在，而是通过 source_chunk_ids、source_ref、page_numbers 和 section_path 反向连接到 chunk。

这种设计的意义在于，图检索结果不是抽象的知识图谱断言，而是可以回到原文证据的结构化候选。对于专业 PDF 问答，尤其是跨章节或跨文档问题，单个 chunk 的语义相似度可能不足以覆盖所有约束；实体和关系可以提供额外召回入口，图邻域则可以补充 query 中未显式写出的相关证据。

### 3.2 检索流程

本文实验中的系统配置按组件逐步加入：

| 配置 | 检索角色 | 解释 |
|---|---|---|
| B0 | Flat Chunk RAG | chunk-only baseline，仅使用扁平 chunk 向量检索 |
| B1 | Chunk + Rerank | 在 B0 候选上加入 rerank，控制 rerank 单独收益 |
| B2 | Graph-only | 使用 entity/relation graph retrieval 和 graph expansion，不使用 chunk fusion |
| B3 | Chunk + Entity | 在 chunk retrieval 基础上加入 entity retrieval |
| B4 | Chunk + Entity + Relation | 在 B3 基础上加入 relation retrieval |
| B5 | + Graph Expansion | 在 B4 基础上加入 graph neighborhood expansion |
| B6 | + Query Variants | 在 B5 基础上加入多约束 query variants |
| B7 | + Rerank | 在 B6 的融合候选后加入 rerank |
| Full | B7 + Evidence Selection | 在 B7 基础上执行 coverage-aware final evidence selection |

这个序列使消融具有可解释性：B3 观察 entity retrieval 是否提升 structured coverage，B4 观察 relation retrieval 的边际收益，B5 观察 graph expansion 对 candidate recall 的贡献，B6 观察 query variants 是否带来多约束覆盖或噪声，B7 观察 rerank 是否修复候选排序，Full 则专门检验 evidence selection 是否能在压缩 final context 的同时保留 required evidence。

### 3.3 代码实现对应关系

当前仓库中，ERC 论文主张对应到以下实现面：

| 研究组件 | 实现面 |
|---|---|
| DQE 数据导入与映射 | `tools/import_dqe_bench_to_erc_dataset.py` |
| live/gold_replay 评测 harness | `tools/erc_full_eval.py` |
| DQE slice 与组件归因 | `tools/analyze_dqe_erc_results.py` |
| 报告再生成 | `tools/erc_research_report.py` |
| query variants / rerank / selection 开关 | `ragent/base.py`、`ragent/operate.py`、`ragent/ragent.py` |
| offline replay / read-only audit | `ragent/offline_replay.py` 与 build_inference_separation artifacts |

这些代码改进不是手稿之外的工程背景，而是本文方法可复现性的组成部分。尤其是 live harness 的断点续跑、增量写入、judge 重试、状态字段读取和 attribution 输出，直接决定 186 题全矩阵实验是否可审计。

## 4. DQE-mapped 数据集

### 4.1 数据来源与总体统计

主实验数据集为 `benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl`，dataset id 为 `dqe_gold_mapped_full_186`。它来自 DQE current gold pool 的全量映射版本，而不是早期 20 题 pilot 或 40 题 balanced subset。

| 维度 | 数值 |
|---|---:|
| questions | 186 |
| answerable questions | 186 |
| empty gold evidence | 0 |
| empty answer key points | 0 |
| possibly over-general gold answers | 18 |
| duplicate question groups | 1 |
| source files | 42 |
| calculation-oriented questions | 16 |

题型分布如下：

| question_type | count |
|---|---:|
| fact_lookup | 13 |
| comparison | 15 |
| condition_filtering | 16 |
| aggregation_calculation | 16 |
| single_document_text_reasoning | 29 |
| single_document_multimodal_reasoning | 34 |
| multi_document_text_reasoning | 35 |
| multi_document_multimodal_reasoning | 28 |

难度分布为 easy 13、medium 53、hard 120；文档范围分布为 single_document 123、multi_document 63；模态分布为 text_document 124、multimodal_document 62。这个分布说明主实验不是只针对简单事实题，而包含大量 hard、多文档和多模态/表格压力题。

### 4.2 Provenance 映射规则

DQE 的 `source_unit_id` 不能直接当作 ragent live project 的 `chunk_id`。本实验通过 `tools/import_dqe_bench_to_erc_dataset.py` 将 DQE source unit 映射到 `example/qwen4b_diet_kg` 中真实 project chunk。映射过程遵守以下规则：

1. 先约束 DQE document id 或 source file，再做文本匹配。
2. 每个 evidence_source_id 先与配对 gold_evidence 文本复核。
3. 如果原 source id 与 gold text 不一致，只能在同一 DQE doc 内寻找更匹配 source unit，并记录 `repaired_from_gold_evidence`。
4. 匹配使用 exact substring、character n-gram recall、section overlap 和 numeric overlap。
5. page、source_ref、file_path、section_path 和 chunk_id 只来自真实 project chunk metadata。
6. unmatched source unit 必须保留在 `unmatched_evidence.jsonl`，不得写成 required live evidence。

映射审计结果如下：

| mapping check | value |
|---|---:|
| project chunks loaded | 1725 |
| required DQE evidence items | 331 |
| matched evidence items | 331 |
| unmatched evidence items | 0 |
| unique resolved source units | 144 |
| unique matched source units | 144 |
| source id repairs from gold evidence | 38 |
| low-confidence original source ids retained | 0 |
| questions with >=1 matched evidence | 186 / 186 |
| questions with >=2 matched evidence | 97 / 186 |
| source unit conflicts | 0 |
| evidence index conflicts | 0 |

这个 mapping contract 是本文可信度的底线。本文不使用伪 page、伪 chunk_id 或合成 source_ref，也不把 historical DQE system score 作为 ERC live performance。

### 4.3 DQE 能力切片

DQE 字段不仅用于扩大题量，还用于控制变量和失败归因。主实验保留以下 slices：

| slice | n | 用途 |
|---|---:|---|
| dqe_full_mapped | 186 | 全量 DQE-mapped 主集 |
| dqe_phase8_keep | 152 | DQE phase8 keep 子集 |
| dqe_phase8_replace_stress | 26 | 题目质量压力/错误分析 |
| dqe_multi_evidence_ge2 | 97 | 多证据覆盖实验 |
| dqe_multi_evidence_ge3 | 26 | 高强度多证据压力集 |
| dqe_multi_document | 63 | 跨文档证据聚合 |
| dqe_table_multimodal_stress | 128 | 表格/图片描述/多模态压力集 |
| dqe_repair_review_set | 15 | source unit repair 审计 |
| dqe_calculation | 16 | 数值计算问题 |
| dqe_hard | 120 | 难题集合 |
| dqe_selection_stress_candidates | 72 | evidence selection 压力候选 |

这些 slices 防止报告只给总体均分，也防止通过手工挑选有利题目制造结论。每个组件的收益都应检查是否集中在预期能力切片上。

## 5. 实验设计

主实验 artifact 为 `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014`。该 artifact 使用 `live` backend、`llm` judge mode、固定 dataset `dqe_gold_mapped_full_186`，并比较 B0、B1、B2、B3、B4、B5、B6、B7 和 Full。外部 LLM 约束为 `.env` 中的 `LLM_MODEL_URL=https://api.deepseek.com` 与 `LLM_MODEL=deepseek-v4-flash`；本文不允许通过切换到更强模型隐藏 retrieval layer 限制。

artifact 完整性如下：

| artifact | non-empty rows |
|---|---:|
| results.jsonl | 2232 |
| judge_results.jsonl | 1674 |
| metrics.tsv | 13 |
| dqe_slice_metrics.tsv | 100 |
| component_delta_by_slice.tsv | 78 |
| per_question_component_attribution.jsonl | 186 |
| annotated_dataset.jsonl | 186 |

最终 judge file 为 1674 行，`ok=1674`，duplicate keys 为 0。这个结果行数来自 186 题乘以 9 个 full_no_cache 主实验配置，以及 Full 的 cache phase 行。

主要 retrieval metrics 包括 Evidence Recall@K、Final Evidence Recall、Required Evidence Coverage 和 latency。Citation Precision/Recall 与 LLM-judged answer quality 作为 grounding 和 downstream answer generation 诊断。cache 实验只在 Full 配置上解释，不替代 B0-B7-Full 主消融。strict per-row cold control 使用 `benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636`，只用于补充缓存语义检查。

## 6. 主结果

### 6.1 Retrieval-layer 结果

| config | retrieval role | evidence recall@k | final evidence recall | required evidence coverage | latency p50 s |
|---|---|---:|---:|---:|---:|
| B0 | Flat Chunk RAG | 0.3315 | 0.3315 | 0.4158 | 10.2985 |
| B1 | Chunk + Rerank | 0.3315 | 0.3315 | 0.4158 | 12.1315 |
| B2 | Graph-only | 0.4581 | 0.3468 | 0.5739 | 15.7055 |
| B3 | Chunk + Entity | 0.3315 | 0.3315 | 0.5575 | 13.0380 |
| B4 | Chunk + Entity + Relation | 0.3315 | 0.3315 | 0.5667 | 10.9350 |
| B5 | + Graph Expansion | 0.5033 | 0.3889 | 0.5954 | 12.9890 |
| B6 | + Query Variants | 0.4565 | 0.3658 | 0.5843 | 14.9680 |
| B7 | + Rerank | 0.4565 | 0.4218 | 0.6123 | 16.8905 |
| Full | B7 + Evidence Selection | 0.4565 | 0.4164 | 0.6096 | 19.1345 |

B0 是 chunk-only baseline，其 required evidence coverage 为 0.4158。加入实体召回后，B3 的 required evidence coverage 提升到 0.5575，说明结构化 entity retrieval 对 required evidence coverage 有明显贡献。B4 进一步加入 relation retrieval，coverage 提升到 0.5667，收益较小但方向清晰。B5 加入 graph expansion 后，Evidence Recall@K 达到 0.5033，是所有配置中最高的 candidate recall，说明图邻域扩展能召回 chunk-only 和 entity/relation 直接召回之外的证据。

B6 的 query variants 在本 artifact 中产生回归：final evidence recall 从 B5 的 0.3889 降至 0.3658，required evidence coverage 从 0.5954 降至 0.5843。这说明 query expansion 不能被简单写成正结果，它需要更严格的过滤和候选合并策略。B7 的 post-fusion rerank 将 final evidence recall 提升到 0.4218，并将 required evidence coverage 提升到 0.6123，是当前最佳端到端检索配置。

Full 的 coverage-aware evidence selection 在修复后已明显缓解早期 selection drop，但相对 B7 仍有小幅下降：final evidence recall 从 0.4218 降至 0.4164，required evidence coverage 从 0.6123 降至 0.6096。因此，本文不把 Full 写成最终成功版本，而是把 evidence selection 写成已修复但仍需继续优化的负结果。

### 6.2 Downstream answer diagnostic

| config | correctness | completeness | faithfulness | numerical accuracy | unsupported claim rate |
|---|---:|---:|---:|---:|---:|
| B0 | 0.6879 | 0.7330 | 0.6832 | 0.8860 | 0.2856 |
| B5 | 0.7225 | 0.7664 | 0.7087 | 0.8607 | 0.2793 |
| B7 | 0.7456 | 0.7853 | 0.7062 | 0.8632 | 0.2776 |
| Full | 0.7404 | 0.7814 | 0.7036 | 0.8967 | 0.2831 |

B7 同时取得最高 downstream correctness（0.7456）和 completeness（0.7853）。Full correctness 为 0.7404，高于 B0 和 B5，但略低于 B7。numerical accuracy 在 Full 上最高（0.8967），这说明最终选择后的上下文在部分数值题上有帮助；但 unsupported claim rate 并未形成同等强的改进。因此，answer quality 结果支持“图检索链路能改善 downstream 诊断指标”的谨慎结论，但不能替代 retrieval-layer evidence coverage 的主 claim。

### 6.3 组件边际贡献

| comparison | delta final recall | delta required coverage | delta correctness | 解释 |
|---|---:|---:|---:|---|
| B0 -> B3 | 0.0000 | +0.1417 | +0.0388 | entity retrieval 显著提升 structured coverage |
| B3 -> B4 | 0.0000 | +0.0092 | +0.0008 | relation retrieval 贡献较小但为正 |
| B4 -> B5 | +0.0573 | +0.0287 | -0.0050 | graph expansion 是 final recall 关键跃升点 |
| B5 -> B6 | -0.0231 | -0.0111 | +0.0157 | query variants 带来 recall drift |
| B6 -> B7 | +0.0560 | +0.0280 | +0.0074 | rerank 修复 query variant 后的排序损失 |
| B7 -> Full | -0.0054 | -0.0027 | -0.0052 | evidence selection 仍略丢证据 |
| B0 -> Full | +0.0849 | +0.1938 | +0.0525 | 完整链路相对 chunk-only 仍有总体收益 |

这一结果支持本文的核心 retrieval claim：图相关组件对 required evidence coverage 和 final recall 有可测贡献，尤其是 entity retrieval、graph expansion 和 post-fusion rerank。但是，query variants 与 evidence selection 都不是已完全解决的正结果，而是当前算法继续改进的重点。

## 7. DQE 切片归因与失败分析

### 7.1 B7 主参考切片

由于 B7 是当前最佳端到端 retrieval setting，切片分析以 B7 为主要正向参照。

| DQE slice | n | correctness | final recall | required coverage | unsupported claim rate |
|---|---:|---:|---:|---:|---:|
| dqe_full_mapped | 186 | 0.7456 | 0.4218 | 0.6123 | 0.2776 |
| dqe_phase8_keep | 152 | 0.7778 | 0.4227 | 0.6142 | 0.2575 |
| dqe_phase8_replace_stress | 26 | 0.6137 | 0.4115 | 0.6012 | 0.3854 |
| dqe_multi_evidence_ge2 | 97 | 0.6587 | 0.3242 | 0.5618 | 0.3357 |
| dqe_multi_evidence_ge3 | 26 | 0.6468 | 0.1327 | 0.4588 | 0.3827 |
| dqe_multi_document | 63 | 0.5952 | 0.2796 | 0.5409 | 0.3681 |
| dqe_table_multimodal_stress | 128 | 0.7179 | 0.3655 | 0.5828 | 0.3190 |
| dqe_repair_review_set | 15 | 0.5933 | 0.4111 | 0.5910 | 0.3133 |
| dqe_calculation | 16 | 0.9000 | 0.6250 | 0.6897 | 0.1000 |
| dqe_hard | 120 | 0.6895 | 0.3767 | 0.5865 | 0.3104 |
| dqe_selection_stress_candidates | 72 | 0.6558 | 0.2609 | 0.5276 | 0.3325 |

calculation 切片表现最好，B7 correctness 为 0.9000，final recall 为 0.6250，required coverage 为 0.6897，unsupported claim rate 为 0.1000。这说明在证据命中后，当前回答链路对数值型问题可以较好利用证据。multi_document、multi_evidence_ge3 和 selection_stress_candidates 仍是短板，说明跨文档 evidence assembly 和最终 evidence preservation 是后续重点。

### 7.2 Failure taxonomy

当前 failure taxonomy 保留负结果，不做有利过滤：

| failure type | count |
|---|---:|
| no_primary_failure | 105 |
| no_required_coverage_gain | 11 |
| selection_drop | 2 |
| unsupported_claim_risk | 68 |

`unsupported_claim_risk` 集中在 table_or_multimodal（52）、hard（46）、multi_evidence_ge2（38）、selection_stress_candidate（32）和 multi_document（27）等标签。`selection_drop` 已从早期更严重状态降低到 2，但两个案例都落在 hard 与 table_or_multimodal 标签上，说明表格/多模态证据在 final selection 中仍需专门处理。

DQE slices 的价值在这里体现得很清楚：它不仅提供题目数量，还把失败位置映射到能力切片。后续算法迭代不应只追求总体平均分，而应针对 query variants、selection、跨文档 assembly 和表格证据表达做分层优化。

## 8. 代码与工程改进

### 8.1 DQE 导入与映射审计

`tools/import_dqe_bench_to_erc_dataset.py` 是从 DQE current gold 到 ERC live dataset 的稳定路径。该脚本解决了早期 ERC pilot 的关键问题：题量少、gold evidence 粒度不稳定、matched project chunk links 不足。新路径显式区分 DQE source_unit_id 与 ragent chunk_id，并通过同文档 gold_evidence 校验修复 stale source id。

代码贡献不仅是数据转换，还包括 dataset audit、mapping audit、source_unit_to_chunk_map、unmatched_evidence、dqe_capability_tags 和 dqe_slice_manifest 等可审计产物。这些产物构成本文 dataset 和 provenance section 的主要证据。

### 8.2 Live eval harness 与长任务恢复

`tools/erc_full_eval.py` 从早期 gold_replay sanity harness 扩展为支持 live backend、全矩阵配置、LLM judge、cache phase、annotated dataset 和 build/inference separation 的评测入口。为了完成 186 题乘以 9 配置的长任务，harness 增加了增量写入、`--resume-partial`、live query 和 judge timeout、重试与 retry sleep、并发控制以及 judge JSON 容错解析。

这些能力直接支撑了当前 artifact 的完整性：`results.jsonl=2232`、`judge_results.jsonl=1674`、`status=ok=1674`。手稿不能只报告最终表格，也应说明该结果来自可恢复、可审计的长任务执行路径。

### 8.3 Component attribution 与 follow-up diagnostics

`tools/analyze_dqe_erc_results.py` 将 full live output 转化为 `dqe_slice_metrics.tsv`、`component_delta_by_slice.tsv`、`per_question_component_attribution.jsonl` 和 `failure_taxonomy.md`。这些文件让本文能回答“哪个组件在哪类题上带来收益”，而不是只报告 B0 和 Full 的平均差。

follow-up diagnostics 进一步定位了两类问题：evidence selection 在部分题中丢掉 B7 已召回证据，query variants 在部分题中引入弱 split-only query 而导致 final recall 下降。针对 selection 的修复在 17-case subset 上使 Full final evidence recall 从 0.1373 提升到 0.4657，并将全量 rerun 中 `selection_drop` failure count 降到 2。query-variant 修复使 targeted subset 的 B6-B5 final-recall gap 从 -0.1408 收窄到 -0.0201，但全量中 B6 仍低于 B5，因此仍是后续目标。

### 8.4 Cache 与 read-only audit

主 live artifact 的 Full cache phases 显示 answer cache 对重复查询有显著加速：

| cache phase | p50 s | p95 s | mean s | caveat |
|---|---:|---:|---:|---|
| full_no_cache observed path | 19.1345 | 30.2838 | 19.7132 | 记录到 answer_cache_hit，不能视为严格冷启动 |
| retrieval_cache_warm | 8.5570 | 19.2100 | 9.6978 | 语义仍需进一步隔离验证 |
| answer_cache_warm | 0.0210 | 0.0600 | 0.0279 | 支持 repeated-query acceleration |
| keyword_candidate_cache_warm | 20.5190 | 43.8780 | 22.7958 | 本 run 没有 full-query latency win |

strict per-row cold control 进一步确认 Full cold path p50 为 20.2990s，answer-cache warm p50 为 0.0140s。它同时显示 retrieval-cache 和 keyword-candidate-cache 的语义仍需诊断，因此本文只把 answer cache acceleration 写成明确支持的工程结论。

fresh build/replay audit 来自 `benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json`。该 audit 完成 8 个 PDF 的 fresh online build 和 8 个 raw-unit files 的 offline replay；read-only replay inference 前后 digest 不变，`readonly_snapshot_unchanged=True`。但 online build digest 为 `33c855d175fbecc814b33dccd3daeb21`，offline replay digest 为 `0c5ec700ccd0e71662d7fade074b00b0`，`online_vs_replay_match=False`。因此本文只能主张 read-only isolation 已验证，不能主张 online/raw replay 等价。

## 9. 讨论

本文最稳健的结论是 retrieval-layer evidence coverage 的改善。B0 chunk-only baseline 在 required evidence coverage 上只有 0.4158，而 B3、B4、B5 和 B7 分别达到 0.5575、0.5667、0.5954 和 0.6123。这个趋势说明 ERC 图结构提供了 chunk-only 之外的证据定位能力。B5 的 highest Evidence Recall@K 进一步说明 graph expansion 对 candidate recall 有价值，而 B7 的 final recall 最高说明 rerank 对最终证据保留非常关键。

另一方面，本文也显示完整链路并不等于每个组件都有效。query variants 单独加入后导致 final recall 下降，Full evidence selection 修复后仍略低于 B7。这种负结果对论文反而有价值：它证明当前实验不是通过有利子集或合成 replay 选择性报告，而是把失败纳入 component attribution 和 failure taxonomy。对于一个面向真实专业文档的检索框架，知道收益在哪里、失败在哪里，比把 Full 包装成全胜更可信。

downstream answer quality 的解释也需要克制。B7 correctness 为 0.7456，Full correctness 为 0.7404，高于 B0 的 0.6879。这说明检索层改进有助于答案生成诊断，但 correctness 不是检索模块的唯一评价，也不能掩盖 citation precision 和 unsupported claim risk 的问题。本文建议把 retrieval layer 与 answer generation layer 作为两个可组合但可分离的评估对象：前者关注 evidence coverage 和 provenance，后者关注 prompt assembly、回答格式和 grounding。

工程层面的意义在于，本文不是单次 notebook 式实验，而是围绕可复现 artifact 构建了一套实验协议。dataset audit、mapping audit、commands、env snapshot、results、judge results、metrics、slice metrics、component delta、per-question attribution 和 failure taxonomy 都应成为后续论文和系统迭代的固定产物。当前 build/replay digest mismatch 也说明工程闭环尚未完成；把它写成 limitation 比提前声称等价更符合可审计研究原则。

## 10. 局限

第一，本文第一版没有引入外部文献综述和正式引用，因此尚不是完整投稿版本。Related Work 需要后续补充 KG-RAG、GraphRAG、RAG provenance、document QA、benchmark construction 和 evidence attribution 相关论文，并做引用完整性检查。

第二，当前主 live artifact 是 existing live project 上的 retrieval/QA ablation，不能支持 fresh online build 与 raw replay equivalence 的主张。fresh build/replay audit 虽然验证了 read-only replay isolation，但 `online_vs_replay_match=False` 仍需继续定位。

第三，Full evidence selection 仍略低于 B7。虽然 selection-drop failure count 已显著降低，但在全量结果中 Full 不是最强 retrieval setting，不能作为最终完整框架的成功结论。

第四，query variants 在全量结果中仍低于 B5。targeted subset 的修复缓解了回归，但没有完全消除，需要更强的 query filtering、variant scoring 或候选融合约束。

第五，citation precision、citation recall 和 unsupported claim rate 仍然暴露 grounding 问题。当前回答生成链路在最终证据使用和引用组织上还没有完全消化 retrieval layer 的收益。

第六，38 条 source-id repairs、表格证据映射、18 个 possibly over-general gold answers 和 duplicate question group 仍需要人工复核。机器映射结果支持当前 live benchmark，但投稿前应补充 manual review pass rate。

第七，cache 结果只能谨慎解释。answer cache acceleration 明确成立，但 retrieval-cache 与 keyword-candidate-cache 的语义和收益需要进一步隔离实验。

## 11. 结论

本文整理了一套面向专业 PDF 知识库的 provenance-aware ERC 异构证据图 RAG 框架，并在 DQE-mapped 186 题 live benchmark 上评估其 retrieval-layer 贡献。实验表明，相比 chunk-only B0，ERC 图相关组件能显著提高 required evidence coverage；B7 是当前最佳端到端检索配置，达到 `final_evidence_recall=0.4218` 和 `required_evidence_coverage=0.6123`。Full evidence selection 修复后仍略低于 B7，应作为后续算法目标，而不是被包装为最终成功版本。

从研究方法上看，本文的主要价值是把 dataset credibility、real chunk provenance、live ablation、component attribution、failure taxonomy 和 engineering reproducibility 组织成同一条证据链。它避免把 gold replay、历史 DQE 系统分数或弱 pilot 结果当成 live system performance，也避免伪造 page/chunk/source_ref。后续工作应围绕人工复核、query variants、evidence selection、跨文档 evidence assembly、table/multimodal grounding、cache semantics 和 build/replay digest mismatch 继续迭代。

## 附录 A：Evidence Map

| claim | 支持证据 | 可写入主文吗 | 边界 |
|---|---|---|---|
| DQE-mapped dataset 可作为当前主实验数据 | `benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl`、dataset audit、mapping audit | 是 | 需说明 18 个 over-general answer 和 1 组 duplicate |
| 331 条 required evidence 全部映射到真实 chunk | `benchmark/erc_dqe_mapping_20260601_000156/mapping_audit.md` | 是 | 38 条 repair 需人工复核 |
| B7 是当前最佳 retrieval setting | `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014/metrics.tsv` | 是 | 不等于 Full 成功 |
| Full 相比 B7 仍略低 | `metrics.tsv`、`component_delta_by_slice.tsv` | 是 | 写成修复后负结果 |
| answer cache 加速重复查询 | main latency summary 与 strict cold control | 是 | retrieval/keyword cache 不宜过度推广 |
| read-only replay isolation 已验证 | `separation_summary.json` | 是 | online/raw replay equivalence 未验证 |
| gold replay harness 可识别 injected gold evidence | `benchmark/erc_dqe_full_gold_replay_20260601_000156` | 仅附录 | 不能当 live performance |
| DQE old system score 说明题库区分度 | `/Volumes/SSD1/ragent_benchmark` 历史材料 | 暂不写或仅背景 | 不能当 ERC live result |

## 附录 B：复现命令

主 live ablation 命令模板：

```bash
uv run python tools/erc_full_eval.py \
  --backend live \
  --skip-live-build \
  --live-project-dir example/qwen4b_diet_kg \
  --dataset benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl \
  --configs B0 B1 B2 B3 B4 B5 B6 B7 Full \
  --judge-mode llm \
  --output-dir benchmark/erc_full_eval_<timestamp> \
  --skip-report \
  --resume-partial \
  --live-concurrency 4 \
  --live-max-attempts 5 \
  --live-retry-sleep 20 \
  --live-query-timeout 360 \
  --live-judge-timeout 180
```

strict per-row cold control 命令模板：

```bash
uv run python tools/erc_full_eval.py \
  --dataset benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl \
  --backend live \
  --skip-live-build \
  --live-project-dir benchmark/erc_full_eval_20260527_155656/build_inference_separation/offline_replay_project \
  --configs Full \
  --judge-mode llm \
  --live-concurrency 1 \
  --clear-cache-per-live-row \
  --output-dir benchmark/erc_full_eval_strict_cold_<timestamp> \
  --skip-report
```

报告再生成命令：

```bash
uv run python tools/erc_research_report.py \
  --dataset benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl \
  --full-eval-dir benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014 \
  --fresh-build-audit benchmark/erc_full_eval_20260527_155656/build_inference_separation/separation_summary.json \
  --strict-cold-eval-dir benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636 \
  --output docs/research/erc_traceable_rag_report.md
```

目标测试命令：

```bash
uv run pytest tests/test_erc_research_dataset.py tests/test_erc_full_eval.py tests/test_diversified_graph_retrieval.py
```

## 附录 C：投稿前多视角审稿问题清单

本节按 `academic-paper-reviewer` 的 full review 思路进行内部审稿式检查。结论不是正式外部评审，而是第一版手稿的质量门禁。

### C.1 Editor-in-Chief 视角

- 主要判断：手稿已有明确研究对象、数据集、实验结果和限制，适合作为 workshop 或系统论文初稿。
- 需修订项：投稿目标、作者信息、外部 related work 和引用格式仍为空，不能直接投稿。
- 当前处理：作者/单位/投稿 venue 保留占位；Related Work 明确标注为后续外部文献阶段补充。

### C.2 Methodology Reviewer 视角

- 主要判断：主实验使用真实 live artifact，行数、judge status、dataset mapping 和 slice attribution 可审计。
- 关键风险：fresh build/replay equivalence 未验证；strict cache control 只覆盖 Full；manual review pass rate 尚缺。
- 当前处理：将 `online_vs_replay_match=False`、cache caveat 和 manual review 需求写入 Limitations，不作为已解决结论。

### C.3 Domain Reviewer 视角

- 主要判断：手稿针对专业 PDF 问答、多证据覆盖和 provenance 组织，问题定义与数据集设计一致。
- 关键风险：相关工作缺失会削弱学术定位，尤其是 KG-RAG、GraphRAG 与 document-grounded QA 的比较。
- 当前处理：第一版不虚构外部引用；后续投稿版本必须增加外部文献综述。

### C.4 Cross-disciplinary Reviewer 视角

- 主要判断：将 DQE 作为能力切片和 failure attribution 控制层，是比单纯扩大题量更有价值的设计。
- 关键风险：如果后续只报告平均分，会削弱这条贡献。
- 当前处理：正文保留 DQE slices、component delta 和 failure taxonomy，并强调不能只看总体 correctness。

### C.5 Devil's Advocate 视角

- 可能的最强反驳：Full 并不是最优配置，是否还能称为完整框架？
- 回应：本文不把 Full 写成最终成功版本，而把 B7 写成当前 best retrieval setting；Full selection 是修复后仍需优化的负结果。
- 可能的最强反驳：answer correctness 提升不大，是否说明方法价值有限？
- 回应：本文主 claim 是 retrieval-layer evidence coverage，不是最终答案润色；downstream answer metrics 只作诊断。
- 可能的最强反驳：build/replay 没有等价，工程闭环是否不足？
- 回应：是。本文只声称 read-only replay isolation 已验证，online/raw replay equivalence 作为 limitation。

### C.6 审稿检查结论

当前没有必须阻断中文 Markdown 初稿交付的 critical issue；但存在三个投稿前必须解决的问题：外部文献综述、人工 evidence mapping review、build/replay digest mismatch 诊断。它们均已写入正文限制或后续工作，不在第一版中伪装成已完成。

