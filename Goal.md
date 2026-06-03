面向专业 PDF 知识库的可追溯异构证据图增强检索生成框架

当前状态（2026-06-03）：

- 本文档早期出现的“最小闭环”“40 题 balanced subset”“先不跑全矩阵”等内容只保留为历史规划和 fallback，不再是当前执行目标。
- 当前主线已经切换为 DQE current gold 全量 mapped dataset：186 题、331 条真实 ragent chunk evidence 映射、B0-B7-Full 全矩阵 live ablation。
- 当前统一结果入口是 `docs/research/erc_traceable_rag_total_results.md`。论文式可再生成技术报告是 `docs/research/erc_traceable_rag_report.md`。
- 当前主 live 结果使用 `benchmark/erc_full_eval_dqe_full_flash_followup_20260603_1014`。该目录是 2026-06-03 在 selection/query-variant 修复后完成的 186 题 B0-B7-Full 全量 live rerun，结果 2232 行、judge 1674 行且全为 `ok`。
- `benchmark/erc_full_eval_20260527_155656` 现在只作为修复前对照和 fresh build/raw replay/read-only audit 来源；其 `build_inference_separation/separation_summary.json` 记录 `readonly_snapshot_unchanged=True`、`online_vs_replay_match=False`。
- `benchmark/erc_full_eval_dqe_full_20260601_1233_retry1` 是更早一版 186 题 DQE live artifact，保留用于过程审计，不再作为当前统一入口。
- 严格逐行冷缓存补充控制使用 `benchmark/erc_full_eval_dqe_full_strict_cold_20260602_151636`。它只用于校验 Full 延迟和缓存命中口径，不替代 B0-B7-Full 主消融表。
- gold replay、20 题 pilot、40 题 balanced subset 只能作为开发过程和 sanity evidence。
- 当前最强 retrieval 配置是 B7：`final_evidence_recall=0.4218`、`required_evidence_coverage=0.6123`。Full evidence selection 已被修复显著缓解，但全量复跑中仍略低于 B7：`final_evidence_recall=0.4164`、`required_evidence_coverage=0.6096`，不能写成最终成功版本。
- Query variant 过滤已缓解原先回归，但 B6 仍低于 B5：`final_evidence_recall 0.3658 vs 0.3889`，仍是后续算法目标。
- build/replay 仅支持“read-only replay isolation 已验证”；`online_vs_replay_match=False`，不能声称 online build 与 raw replay 等价。
- 后续所有 ERC live 实验、LLM judge、rerun 和报告刷新中调用外部 LLM 的步骤只能使用 `.env` 中的 `LLM_MODEL_URL=https://api.deepseek.com` 与 `LLM_MODEL=deepseek-v4-flash`；不得替换为 `deepseek-v4-pro`、Claude Opus 或其他 LLM。若模型能力限制影响结果，只能作为 limitation 报告。



英文可写成：



Provenance-Aware Entity-Relation-Chunk Evidence Graphs for Traceable Multi-Evidence Retrieval-Augmented Generation



一、核心研究问题



专业 PDF 问答中，复杂问题往往需要同时聚合多个证据片段、实体概念、数值表格和跨章节关系。传统 chunk-only RAG 容易出现证据缺失、局部命中、计算链不完整和引用不可追溯。当前框架通过将 Entity、Relation 与原始 Chunk 统一建模为带 provenance 的 ERC 异构证据网络，并在查询阶段联合 chunk 召回、实体召回、关系召回、图邻域扩展、query variant、rerank 和证据选择，提升复杂问题的多证据聚合与可追溯回答能力。



二、拟提出的贡献



ERC 异构证据图建模

将原始 chunk、抽取实体、抽取关系统一纳入一个带 provenance 的证据网络。每个实体和关系保留 source_chunk_ids、source_ref、页码、章节路径、文件来源，从而支持从答案回溯到原文证据。



混合证据检索算法

查询阶段不只做 chunk 向量召回，而是融合：

chunk semantic retrieval、entity retrieval、relation retrieval、graph neighborhood expansion、query variants、candidate fusion、rerank、coverage-aware evidence selection。



面向复杂问题的证据覆盖机制

对多约束问题，例如“含糖饮料 + 中速步行 + 爬楼 + 成年男性”，通过 query variant 和覆盖导向选择，避免只命中其中一个局部主题。



构建态与推理态分离的工程闭环

将知识库构建、raw unit 离线重放、证据图物化、只读推理运行时、缓存加速解耦，形成：

Build-time separation -> Evidence graph materialization -> Read-only inference -> Cache acceleration。



实证评测

用真实中文专业 PDF 文档构造复杂问答集，评估答案质量、证据召回、引用可追溯性、延迟和缓存收益。



三、实验数据集设计

实验文档数量不要作为硬性门槛。优先完成一套真实、可复现、证据标注可靠的最小闭环；当前可以直接使用 `/Volumes/SSD1/ragent/example/qwen4b_diet_kg` 及 `/Volumes/SSD1/ragent/example/qwen4b_diet_kg_raw_units` 对应的 5 个来源 PDF。若时间和算力允许，再扩展到更多 PDF，例如补齐到原先设想的 8 个 PDF 数据集。



Dataset A：健康营养指南问答集（核心数据集）

使用：



/Volumes/SSD1/ragent/example/成人肥胖食养指南_2024.pdf

/Volumes/SSD1/ragent/example/成人高血压食养指南_2022.pdf

/Volumes/SSD1/ragent/example/中国居民膳食指南_2022.pdf

重点测试复杂多跳、数值计算、饮食建议、阈值判断、跨文档联合推理。



建议参考 /Volumes/SSD1/ragent/script/query.sh 构造约 8-10 个高质量问题：



单文档事实题：20%

跨章节多跳题：25%

跨文档联合判断题：25%

表格/数值计算题：20%

需要解释证据来源的追溯题：10%

Dataset B：食品标准法规问答集（可选扩展）

最小闭环可先使用 qwen4b_diet_kg 已覆盖的 2 个标准 PDF：



/Volumes/SSD1/ragent/example/GBT1354-2018bz.pdf

/Volumes/SSD1/ragent/example/GBT22106-2008dz.pdf

重点测试标准条款、适用范围、指标限值、术语定义、跨标准对照。建议参考 /Volumes/SSD1/ragent/script/query.sh 构造约 4-6 个高质量问题。

如需要扩大食品标准覆盖面，再追加以下 3 个 PDF 作为扩展集；它们不是最小实验闭环的前置条件：

/Volumes/SSD1/ragent/example/GB-31607-2021.pdf

/Volumes/SSD1/ragent/example/GB29938-2020.pdf

/Volumes/SSD1/ragent/example/GB31647-2018.pdf



每个问题建议标注：



question

gold_answer

required_source_refs

required_chunk_ids，如果可得

required_entities

required_relations

question_type

difficulty

requires_calculation: true/false

四、对比系统与消融实验

建议至少做这些配置：



编号	配置	目的

B0	Flat Chunk RAG	传统 chunk 向量检索基线

B1	Chunk + Rerank	检验 rerank 本身收益

B2	Graph-only	只用实体/关系/图邻域

B3	Chunk + Entity	检验实体召回增益

B4	Chunk + Entity + Relation	检验关系召回增益

B5	Chunk + Entity + Relation + Graph Expansion	检验图邻域扩展

B6	B5 + Query Variants	检验多约束覆盖

B7	B6 + Rerank	检验重排增益

Full	B7 + Evidence Selection	当前完整框架

缓存实验单独做：



Full no cache

Full retrieval cache warm

Full answer cache warm

Full keyword candidate cache warm

五、评价指标

答案质量：



Correctness

Completeness

Relevance

Faithfulness

Numerical accuracy

Pairwise win rate

证据质量：



Evidence Recall@K

Final Evidence Recall

Citation Precision

Citation Recall

Required Evidence Coverage

Unsupported Claim Rate

可追溯性：



是否返回 source_ref

是否返回页码/章节

答案中的关键结论是否能映射到最终证据 chunk

entity/relation 是否能追溯到 source_chunk_ids

系统效率：



first request latency

steady cold latency

retrieval warm latency

answer warm latency

p50 / p95 / mean

cache hit stages

graph/entity/relation/vector/rerank/answer generation 分阶段耗时

构建态分离：



online build 与 offline replay 的 graph/vector/doc status 是否一致

raw JSONL replay 是否可复现

replay 失败是否 rollback

只读推理时 snapshot 是否不被修改

六、补充实验计划



质量主实验

在当前可用的 5-PDF 最小闭环数据集上跑 B0、B1、B2、B5、Full。先不跑全矩阵，快速得到主结论；扩展到更多 PDF 后再补充完整 Dataset A/B 对比。



组件消融实验

对 Dataset A 中复杂题子集跑完整消融，尤其关注：

query variants、relation retrieval、graph expansion、evidence selection。



多证据覆盖实验

单独挑出需要 2 个以上证据才能回答的问题，统计 required evidence coverage。这个实验最能体现 ERC 图的价值。



可追溯性实验

随机抽样回答，检查答案关键结论是否能回溯到最终证据。输出 citation precision/recall。



缓存与延迟实验

基于现有 benchmark/latency_test.sh 和 benchmark/keyword_cache_benefit.py 、/Volumes/SSD1/ragent/script/query.sh 扩展多个查询，不再只用单题 smoke test。报告冷启动、冷查询、retrieval warm、answer warm 的延迟差异。



离线重放与只读推理实验

用选定来源文档构建 raw merge units，然后：

online build 一份；

offline replay 一份；

对比 graph nodes、edges、entity vdb、relationship vdb、chunk vdb、doc status。

再把 replay 后的 snapshot 作为只读推理输入，验证查询结果一致且运行时不污染构建产物。



七、推荐的论文结果表

建议最终至少准备 6 张表/图：



数据集统计表：PDF 数量、chunk 数、entity 数、relation 数、问题数。

主质量结果表：各方法 correctness/completeness/faithfulness/win rate。

消融实验表：逐项加入 entity、relation、graph expansion、query variants、rerank、selection。

证据覆盖表：Evidence Recall@K、Final Evidence Recall、Citation Precision。

延迟与缓存表：steady cold vs retrieval warm vs answer warm。

案例分析图：一个复杂问题的 ERC 检索路径，从 query variants 到最终 evidence chunks。

八、优先级

建议先做最小闭环：



/Volumes/SSD1/ragent/script/query.sh及项目中/Volumes/SSD1/ragent/benchmark的金标准结果作为高质量 gold 问题。

跑 Flat Chunk、Chunk+Rerank、Graph-only、Full 四组。

产出质量分数、证据覆盖和延迟三张核心表。

确认 Full 明显优于 baseline 后，再扩展到剩余食品标准 PDF 和完整消融。

九、当前实验产物审计结论

截至 2026-05-27，当前仓库中已经新增了完整评测框架和研究报告雏形：

/Volumes/SSD1/ragent/tools/erc_full_eval.py

/Volumes/SSD1/ragent/tools/erc_research_report.py

/Volumes/SSD1/ragent/tests/test_erc_full_eval.py

/Volumes/SSD1/ragent/docs/research/erc_traceable_rag_report.md

/Volumes/SSD1/ragent/benchmark/erc_full_eval_20260527_125240

这些产物可以作为实验框架、报告模板和 sanity check 的起点，但不能直接作为论文中的真实实验结果。当前审计发现如下。

第一，当前 full eval 主要是确定性的 gold_replay 后端，而不是真实的在线检索、真实证据召回、真实 rerank 和真实模型回答评测。/Volumes/SSD1/ragent/tools/erc_full_eval.py 中 `--backend` 目前只支持 `gold_replay`，完整框架的答案和证据主要由 gold 标注字段派生。Full 配置在覆盖率达到 1 时会直接返回 gold_answer。因此，现有 `metrics.tsv` 和 `summary.md` 更适合作为评测管线自检结果，不能作为“ERC 框架优于 baseline”的论文证据。

第二，当前 build/replay separation 和 read-only inference 检查仍偏合成化。代码中 online snapshot、offline replay snapshot、readonly before/after snapshot 存在直接复制或同源派生，尚未真实验证项目已有构建流程、离线重放流程和只读推理运行时之间的一致性。因此，论文中的“构建态分离、证据图物化、只读推理”必须通过真实构建产物、真实 replay 产物和真实查询运行时来重新测量。

第三，当前 provenance 页码和 chunk 追溯信息仍不够真实。部分 page 字段由 source_ref 的 hash 伪造，required_chunk_ids 也可能为空。后续必须从 MinerU 输出、PDF 解析产物或项目真实索引中读取真实 page、section、chunk_id、source_chunk_ids、source_ref 和文件路径；如果无法获得真实页码，就应在论文结果中明确标注缺失，而不能用伪页码替代。

第四，当前消融结果存在由预设比例和取整逻辑导致的指标饱和。B6、B7、Full 在部分指标上容易同时达到 1.0，无法有效区分 query variants、rerank、evidence selection 的独立贡献。后续需要改成真实检索输出上的消融实验，按配置真正启用/禁用 chunk retrieval、entity retrieval、relation retrieval、graph expansion、query variants、rerank 和 evidence selection。

第五，当前 `--configs` 子集运行存在健壮性问题。例如只运行 B0 时，latency/cache summary 会假定 Full cache phase 一定存在，导致 KeyError。后续应修复该问题，使评测脚本可以独立运行任意配置组合，便于分批补跑和复现实验。

这些问题不否定当前工作的价值：当前产物已经搭好了数据集 schema、结果目录结构、聚合指标、报告渲染和测试入口。但下一阶段的科研目标必须从“评测管线可运行”推进到“真实、可复现、无偏的系统实证评估”。

十、下一阶段任务目的

下一阶段的核心目的，是把当前 ERC Traceable RAG 的研究从框架叙述和 gold_replay dry-run，推进为可以写入论文的真实实验闭环。具体来说，需要在真实 PDF/MinerU 文档、真实索引、真实检索、真实 rerank、真实推理运行时和真实缓存机制上，客观评估以下主张：

1. 将 entity、relation 与原始 chunk 统一建模为带 provenance 的 Entity-Relation-Chunk 异构证据网络，是否比 chunk-only RAG 更能覆盖复杂问题所需的多源证据。

2. 查询阶段融合 chunk 语义召回、实体召回、关系召回、图邻域扩展、query variant 覆盖、rerank 与证据选择，是否能提升复杂问题的答案正确性、完整性、faithfulness 和证据可追溯性。

3. 工程上将知识库构建、离线重放、推理运行时和平台部署解耦，形成“构建态分离、证据图物化、只读推理、缓存加速”的闭环，是否能带来可复现构建、只读推理安全性和实际延迟收益。

十一、下一阶段行动计划

第一步：修复评测框架边界。

保留 gold_replay 作为 harness sanity check，但在报告中明确命名为 Gold Replay Sanity Evaluation。新增或接入 live backend，使评测脚本真正调用当前项目的知识库、检索器、reranker、证据选择器和推理运行时。修复 `--configs` 子集运行 KeyError，确保 B0、B1、B2、B5、Full 可以独立运行。

第二步：构造真实 gold 数据集。

基于 `/Volumes/SSD1/ragent/example` 下的 PDF、MinerU 解析目录，以及现有 `/Volumes/SSD1/ragent/example/qwen4b_diet_kg` 和 raw units，先整理一批高质量问题作为最小论文闭环。最小闭环可以使用 qwen4b_diet_kg 来源的 5 个 PDF，建议约 12-16 道题；若扩展到更多 PDF，再补到约 20 道题。每题必须尽量标注真实 `required_source_refs`、`required_chunk_ids`、`required_entities`、`required_relations`、`gold_answer`、`question_type`、`difficulty` 和 `requires_calculation`。无法标注的字段必须留空并说明原因，不得合成伪证据。

第三步：实现真实对比与消融。

最小必跑配置为 B0 Flat Chunk、B1 Chunk+Rerank、B2 Graph-only、B5 Chunk+Entity+Relation+Graph Expansion、Full。若时间允许，再补 B3、B4、B6、B7。每个配置必须使用同一批问题、同一运行环境、同一 judge 标准和同一日志格式。

第四步：实现真实证据指标。

从实际 retrieved contexts 和 final evidence 中计算 Evidence Recall@K、Final Evidence Recall、Citation Precision、Citation Recall、Required Evidence Coverage、Unsupported Claim Rate。不要从 gold 字段直接派生模型表现。引用中的 page、source_ref、chunk_id 和 source_chunk_ids 必须来自真实索引或解析产物。

第五步：实现真实构建/重放/只读验证。

用同一批来源文档真实构建一份在线索引，再用对应 raw units 真实 replay 一份离线索引。最小闭环可先使用 qwen4b_diet_kg 的 5 个来源 PDF；扩展集再追加剩余 PDF。对比 graph nodes、edges、entity vector store、relation vector store、chunk vector store、doc status、digest。随后用 replay snapshot 进行只读查询，验证查询前后 snapshot digest 不变，并记录所有写入尝试或缓存写入是否被隔离。

第六步：实现真实缓存与延迟实验。

在 Full 配置下至少测量 no cache、retrieval warm、answer warm、keyword candidate warm 或当前系统实际支持的缓存阶段。记录每题的 total latency、retrieval latency、rerank latency、answer latency、cache hit/miss 和 p50/p95/mean。缓存实验必须区分构建缓存、检索缓存、答案缓存和运行时临时缓存。

第七步：更新研究报告。

`/Volumes/SSD1/ragent/docs/research/erc_traceable_rag_report.md` 应明确区分 synthetic/gold_replay 结果和 live 结果。论文主表只使用 live 结果；gold_replay 只能放在附录或工程自检说明中。若某项实验未完成，应作为 limitation，而不是用合成结果替代。

十二、2026-05-31 DQE-Bench Gold 数据集可信度修复进展

本轮工作的重点不是继续包装 20 题 pilot 结果，而是先修复 ERC Traceable RAG 的评测题集可信度问题。上一轮 `benchmark/erc_evidence_questions.jsonl` 只有 20 题，gold evidence 标注粒度不稳定，真实 matched project chunk links 不足，不能支撑最终论文主实验。现在已经基于 DQE-Bench current gold 样本完成了第一版审计、source unit 到 ragent chunk 映射、balanced subset 导入和 smoke 验证。

新增脚本和测试：

- `/Volumes/SSD1/ragent/tools/import_dqe_bench_to_erc_dataset.py`
- `/Volumes/SSD1/ragent/tests/test_import_dqe_bench_to_erc_dataset.py`

输入来源：

- `/Volumes/SSD1/ragent_benchmark/tmp/docs/current_report.md`
- `/Volumes/SSD1/ragent_benchmark/benchmark_catalog/current_gold_samples.json`
- `/Volumes/SSD1/ragent_benchmark/.artifacts/current_gold_score_detail_20260413/question_detail.csv`
- `/Volumes/SSD1/ragent_benchmark/.artifacts/benchmark_runs/*/01_source_preparation/source_units.jsonl`
- `/Volumes/SSD1/ragent_benchmark/.artifacts/benchmark_runs/*/01_source_preparation/evidence_index.jsonl`
- `/Volumes/SSD1/ragent/example/qwen4b_diet_kg`

已生成的本地 artifact：

- 数据集审计目录：`/Volumes/SSD1/ragent/benchmark/erc_dqe_dataset_audit_20260531_221654`
- 映射审计目录：`/Volumes/SSD1/ragent/benchmark/erc_dqe_mapping_20260531_221654`
- ERC 兼容 40 题 balanced subset：`/Volumes/SSD1/ragent/benchmark/erc_evidence_questions_dqe_20260531_221654.jsonl`
- Gold replay smoke：`/Volumes/SSD1/ragent/benchmark/erc_dqe_gold_replay_smoke_20260531_221654`

DQE current gold 审计结论：

- current gold 样本总数：186。
- question_type 分布：fact_lookup 13、comparison 15、condition_filtering 16、aggregation_calculation 16、single_document_text_reasoning 29、single_document_multimodal_reasoning 34、multi_document_text_reasoning 35、multi_document_multimodal_reasoning 28。
- difficulty 分布：easy 13、medium 53、hard 120。
- document_scope 分布：single_document 123、multi_document 63。
- modality 分布：text_document 124、multimodal_document 62。
- 186 题全部 answerable，全部有 `gold_evidence` 和 `answer_key_points`。
- 审计发现 1 组重复题文本：`g005, g170`。
- 审计标记 18 题 gold answer 可能偏泛化，需要后续人工抽检。
- DQE phase 8 replacement decision：keep 152、replace 26、no_decision 8。新版 ERC balanced subset 选题时默认排除 replace 题。

source_unit 到 ragent chunk 映射结论：

- ragent project：`/Volumes/SSD1/ragent/example/qwen4b_diet_kg`。
- project chunks loaded：1725。
- DQE source units：2227。
- DQE evidence index rows：2227。
- DQE evidence item 总数：331。
- matched evidence items：331。
- unmatched evidence items：0。
- unique resolved source units：144。
- unique matched source units：144。
- 发现并修复 38 条 `evidence_source_id` 与配对 `gold_evidence` 文本不一致的问题。
- 修复策略：先按原始 `evidence_source_id` 取 source unit，再用配对 `gold_evidence` 做文本复核；若重合度过低，则只在同一 DQE doc_id 内寻找更匹配的 source unit，并在映射结果中记录 `repaired_from_gold_evidence`。不得跨文档修复，不得伪造 page、chunk_id 或 source_ref。
- page、source_ref、file_path、section_path、chunk_id 全部来自真实 ragent chunk metadata。
- 表格 evidence 的映射单独允许 `doc_constrained_table_section_ngram`，前提是同文档、同章节、table-like 内容且保留 match method，避免普通段落被低阈值误匹配。

新版 ERC 40 题 balanced subset：

- dataset id：`dqe_gold_mapped_balanced_40`。
- 每个 question_type 选 5 题，共 40 题。
- question_type 分布：8 类各 5 题。
- difficulty 分布：easy 5、medium 17、hard 18。
- document_scope 分布：single_document 30、multi_document 10。
- modality 分布：text_document 30、multimodal_document 10。
- annotation_status：`dqe_mapped_complete` 33 题，`dqe_mapped_complete_with_source_unit_repairs` 7 题。
- 每题 required evidence 数量分布：1 条 6 题、2 条 23 题、3 条 2 题、4 条 7 题、5 条 1 题、6 条 1 题。
- 所有题都有真实 `required_chunk_ids`、`required_source_refs`、`required_source_unit_ids`、`required_evidence`、`page_numbers`。
- `required_relations` 暂时保留为空，并标记 `relation_annotation_status=not_available_in_dqe_gold`。这意味着新版题集当前可用于真实 chunk/evidence recall 和 answer grounding，不应夸大为完整 entity-relation gold。

验证结果：

- `python3 -m py_compile tools/import_dqe_bench_to_erc_dataset.py` 通过。
- `uv run pytest tests/test_import_dqe_bench_to_erc_dataset.py -q`：7 passed。
- 新数据集 schema 检查：40 records ok。
- `python3 tools/erc_full_eval.py --dataset benchmark/erc_evidence_questions_dqe_20260531_221654.jsonl --output-dir benchmark/erc_dqe_gold_replay_smoke_20260531_221654 --backend gold_replay --configs B0 --skip-report` 通过。
- B0 gold replay smoke 只作为 harness sanity：question_count 40，evidence_recall_at_k 0.7358，final_evidence_recall 0.7192，required_evidence_coverage 0.6096。
- 目标测试通过：`uv run pytest tests/test_erc_research_dataset.py tests/test_erc_full_eval.py tests/test_diversified_graph_retrieval.py tests/test_bulk_raw_units_tools.py tests/test_offline_replay_matches_online.py::test_doc_already_seen_only_skips_processed_records tests/test_offline_replay_matches_online.py::test_vector_snapshot_uses_client_storage_vectors_without_reembedding -q`，39 passed。
- `git diff --check` 通过。

重要边界：

- DQE 旧系统得分不能写成 ERC live result，只能作为题目质量背景。
- `erc_dqe_gold_replay_smoke_20260531_221654` 不是论文主实验结果，只能证明新版题集兼容现有 ERC evaluation harness。
- 40 题 balanced subset 还需要人工抽样复核，尤其是 7 题 source unit repair、表格 evidence 映射和 18 个可能泛化 gold answer 中进入候选集的题。
- 下一步 live ablation 必须使用真实 live backend、真实 project chunk、真实 retrieval traces 和真实 judge results；不能从 gold fields 派生模型表现。

十三、课题文档设计补全版

当前课题文档需要从“想法 + pilot 结果”收敛为“可审计的研究设计 + 可复现实验记录 + 谨慎结论”。建议把文档体系拆成以下几类，每类职责不同，不互相混用。

1. `Goal.md`：课题总控文档。

   作用：记录研究问题、贡献边界、数据集版本、实验状态、可信度审计结论、下一步行动计划。这个文档可以保留历史判断，但必须明确哪些结论已过期、哪些只是 pilot、哪些可进入论文。

2. `docs/research/erc_traceable_rag_report.md`：论文式主报告。

   作用：只写当前可被 artifact 支撑的研究叙述。报告必须分清：

   - DQE-generated gold dataset：题目来源、审计、source unit 修复、chunk 映射方法。
   - ERC live ablation：真实 live 实验结果。
   - Historical DQE system comparison：外部题库质量背景，不能当 ERC result。
   - Gold replay sanity：工程自检，只能放在附录或方法校验。
   - Build/replay digest：只按实际结果写，不能把 raw replay 和 online build 说成完全等价，除非 `online_vs_replay_match=True`。

3. `benchmark/erc_dqe_dataset_audit_<timestamp>/dataset_audit.md`：数据集审计记录。

   作用：回答“题目从哪里来，题型/难度/文档范围是否均衡，是否有重复题、空证据、不可答题、过泛化答案”。这是论文 dataset section 的证据来源。

4. `benchmark/erc_dqe_mapping_<timestamp>/mapping_audit.md`：证据映射记录。

   作用：回答“DQE source_unit_id 如何变成 ragent chunk_id，哪些修复发生过，page/source_ref/chunk_id 是否真实”。这是论文 provenance annotation section 的证据来源。

5. `benchmark/erc_full_eval_dqe_<timestamp>/summary.md`：新版 live ablation 结果摘要。

   作用：只在真实 live ablation 跑完之后生成。必须保留 results、judge_results、metrics、manifest、commands、env_snapshot、annotated_dataset、mapping_audit。这个目录才是后续论文主实验候选。

6. `docs/research/figures/`：论文图表导出目录。

   作用：只从可信 artifact 渲染图表。旧 20 题 pilot 图表应标记为 historical pilot 或不进入最终论文主图。

课题文档需要补齐的关键小节：

- Problem definition：专业 PDF RAG 的复杂问题为什么需要多证据覆盖和 provenance；不要把问题泛化为“所有 RAG 都更好”。
- ERC graph model：定义 Chunk、Entity、Relation、Evidence、SourceRef、SourceUnit、ChunkId、Page、SectionPath 的关系。
- Retrieval pipeline：定义 B0-B7-Full 每个组件真实开启/关闭的行为，而不只是表格命名。
- Dataset construction：明确 DQE current gold -> evidence source id audit -> source unit repair -> ragent chunk mapping -> balanced subset -> manual spot check 的流程。
- Annotation reliability：列出 source unit repair、table section matching、duplicate question、over-general answer 的处理规则。
- Metrics：区分 retrieval metrics、answer diagnostics、citation/provenance metrics、latency/cache metrics、build/replay metrics。
- Artifact protocol：每个实验必须写 run_manifest、commands、env_snapshot，并固定 dataset hash / project digest / code revision。
- Claims and limitations：只有 live ablation 支持主结论；gold replay、DQE old system score、historical pilot 都不能当主实验。

十四、下一步执行顺序

第一，做人工抽样复核。

优先抽查：

- 7 题 `dqe_mapped_complete_with_source_unit_repairs`。
- 使用 `doc_constrained_table_section_ngram` 的表格映射。
- 40 题中每个 question_type 至少 1 题。
- DQE audit 中被标记为 possibly over-general gold answer 的题。

复核输出应写入 mapping artifact 或单独 `manual_review.md`，每条给出 keep / revise / exclude / stress_set。

第二，跑新版 DQE-mapped live ablation。

输入 dataset：

`/Volumes/SSD1/ragent/benchmark/erc_evidence_questions_dqe_20260531_221654.jsonl`

建议输出目录：

`/Volumes/SSD1/ragent/benchmark/erc_full_eval_dqe_<timestamp>`

先跑 B0、B1、B2、B5、Full；稳定后补 B3、B4、B6、B7。必须保留：

- `results.jsonl`
- `judge_results.jsonl`
- `metrics.tsv`
- `summary.md`
- `latency_cache_summary.md`
- `run_manifest.json`
- `commands.md`
- `env_snapshot.txt`
- `annotated_dataset.jsonl`
- `mapping_audit.md`

第三，更新 `docs/research/erc_traceable_rag_report.md`。

更新原则：

- 不写“Full 一定优于 baseline”。
- 如果 Full 仍不优于 B0/B7，要如实报告，并分析 evidence selection 或 prompt assembly 的失败原因。
- 主结果优先报告 retrieval-layer evidence coverage、final evidence recall、required evidence coverage、citation recall、latency。
- answer correctness / faithfulness 作为 downstream diagnostic，除非 prompt assembly 和 judge 边界已充分固定。

第四，补全 build/replay/read-only 工程自检。

当前历史 live artifact 中 `readonly_snapshot_unchanged=True`，但 `online_vs_replay_match=False`。下一轮不能宣称 online build 与 offline replay 完全等价，除非新版 DQE live artifact 中 digest 对齐。若仍不对齐，应把它写成工程 limitation，并定位差异来自 graph、vector、doc status、chunk metadata 还是 cache。

第五，准备论文图表。

最终至少需要：

- Dataset table：DQE current gold、mapped 40 subset、manual-reviewed subset。
- Mapping audit table：source unit count、evidence item count、repair count、unmatched count、chunk coverage。
- Main live ablation table：B0-B7-Full retrieval metrics。
- Answer diagnostic table：correctness、faithfulness、unsupported claim rate。
- Latency/cache table：no cache、retrieval warm、answer warm、keyword candidate warm。
- Case figure：一个复杂问题从 query variants、chunk/entity/relation retrieval、graph expansion 到 final evidence chunks 的路径。

十五、进一步用 DQE 完善课题设计：把 DQE 从题库来源升级为算法收益测量控制层

当前 DQE-Bench 不应只被当作“多拿一些题”的来源。它更有价值的地方，是已经把问题类型、证据来源、文档范围、模态、gold reasoning、answer key points、系统分差和 replacement 决策组织成了可审计的评测控制变量。ERC 课题的核心目标是证明算法改进和框架改进带来收益，因此后续文档和实验应把 DQE 用作以下三层控制面：

1. Dataset control：保证问题不是手工挑出来有利于 ERC 的，而是来自 DQE 的 evidence-first gold catalog，并按题型、难度、文档范围和模态分层。
2. Component measurement：把每个 ERC 改进点绑定到对应 DQE 能力切片，测它在“应该起作用”的题上是否真的带来边际收益。
3. Error and iteration loop：用 DQE 的 keep / replace / focus_add 思路解释失败题，指导下一轮补题、剔题和算法修复，而不是只报告平均分。

### 15.1 DQE 可转化为 ERC 的控制变量

后续 `tools/import_dqe_bench_to_erc_dataset.py` 或配套分析脚本应从 DQE gold 样本和 mapping artifact 中稳定导出以下字段，并写入 dataset manifest 或 `dqe_capability_tags.jsonl`：

- `question_type`：8 类题型，用于分层报告收益。
- `difficulty`：easy / medium / hard，用于确认收益是否只来自简单题。
- `document_scope`：single_document / multi_document，用于衡量跨文档证据聚合。
- `modality`：text_document / multimodal_document，用于区分纯文本、表格、图片描述。
- `evidence_source_count`：原始 DQE required source unit 数量，用于构造多证据覆盖实验。
- `matched_evidence_count`：映射到真实 ragent chunk 后的 required evidence 数量，用于 live recall 分母。
- `source_doc_count`：gold evidence 跨多少个 source docs，用于跨文档压力分层。
- `source_type_mix`：paragraph / table / image_description，用于定位表格和多模态收益。
- `answer_key_point_count`：答案关键点数量，用于衡量复杂答案覆盖。
- `requires_calculation`：从 `question_type=aggregation_calculation` 及题目/gold reasoning 中派生。
- `source_unit_resolution_status`：verified / repaired_from_gold_evidence，用于人工复核和敏感性分析。
- `phase8_action`：keep / replace / no_decision，用于主集、stress set 和剔除策略。
- `dqe_historical_system_gap`：只能作为题目区分度背景，不能作为 ERC live result。

这些字段的目的不是让数据集更复杂，而是让每一个实验结论都能回答“收益发生在哪类题上，为什么这个组件应该有收益，以及失败是否集中在某类证据结构上”。

### 15.2 DQE 能力切片与 ERC 组件收益对应关系

后续主报告不应只给总体均分。应该按 DQE 切片报告每个算法组件的边际贡献：

| ERC 改进点 | DQE 目标切片 | 主要验证问题 | 主要指标 |
|---|---|---|---|
| Entity retrieval | entity-dense、answer_key_points 多、single/multi document text reasoning | 实体召回是否帮助定位相关 chunk | required_evidence_coverage、entity endpoint coverage、evidence_recall_at_k |
| Relation retrieval | comparison、condition_filtering、multi_document_text_reasoning | 关系/条件是否补足 chunk-only 漏掉的约束 | relation endpoint coverage、required_evidence_coverage、citation_recall |
| Graph expansion | multi_document、matched_evidence_count >= 2、跨章节证据题 | 图邻域是否带来 query 未显式包含但回答必需的证据 | new_required_hits_from_graph、source_doc_coverage、evidence_recall_at_k |
| Query variants | 多约束题、gold reasoning 多步骤题、source_doc_count >= 2 | query 改写是否覆盖多个子意图 | variant_unique_required_hits、per_variant_gold_hit_rate、candidate_recall_delta |
| Rerank | gold evidence 已在候选但 rank 靠后的题 | rerank 是否把真实证据提前 | gold_mrr、required_hit_rank_p50、evidence_recall_at_top_k |
| Evidence selection | matched_evidence_count >= 2、多 key point、多段 final answer 题 | final selection 是否保留足够证据而不是过度压缩 | final_evidence_recall、candidate_to_final_loss、citation_precision/recall |
| Provenance framework | 全部 mapped 题，特别是 repaired/table/multimodal 题 | page/source_ref/chunk_id 是否真实可追溯 | provenance_completeness、pseudo_ref_count、manual_review_pass_rate |
| Build/replay/read-only | 固定 DQE dataset + 固定 project/raw units | 工程闭环是否稳定复现 | online_vs_replay_match、readonly_snapshot_unchanged、digest_delta |
| Cache framework | 固定 DQE query set，重复运行 | 缓存是否提升真实查询延迟且不污染只读产物 | p50/p95 latency、cache hit stages、snapshot mutation count |

这张表应进入 `docs/research/erc_traceable_rag_report.md` 的实验设计部分，作为“为什么这些消融能测到算法收益”的核心说明。

### 15.3 建议新增 DQE-derived 子集

在 40 题 balanced subset 之外，建议用 DQE current gold 构造多个有明确用途的子集。每个子集都应该有独立 manifest、选题理由和排除理由。

1. `dqe_balanced_40`

   当前已生成。用途是 smoke + 首轮 live ablation，保证 8 类题型都有覆盖。

2. `dqe_main_80`

   每个 question_type 选 10 题。用途是论文主实验候选。优先选择 keep、hard/medium、多证据、multi_document、matched evidence >= 2 的题，同时保留少量 easy fact_lookup 作为 sanity。

3. `dqe_multi_evidence_stress`

   条件：matched_evidence_count >= 3 或 source_doc_count >= 2。用途是测 ERC 图、多证据覆盖和 query variants 的核心收益。这个集合应优先用于 RQ1/RQ2。

4. `dqe_table_multimodal_stress`

   条件：source_type_mix 包含 table 或 image_description，或 modality=multimodal_document。用途是测表格/图片描述 evidence 的真实 chunk 映射、召回和 final selection 稳定性。

5. `dqe_selection_stress`

   条件：B6/B7 候选召回高但 Full final recall 低的题。用途是专门诊断 evidence selection 是否丢证据。这个集合需要在首轮 live ablation 后生成。

6. `dqe_repair_review_set`

   条件：source_unit_resolution_status=repaired_from_gold_evidence。用途是人工复核 DQE source id 修复是否正确；未通过的题不能进入主实验，只能进入 stress 或 error analysis。

7. `dqe_replace_stress`

   条件：phase8_action=replace。用途不是主实验，而是作为“系统与题目质量边界”的压力集。若 ERC 在这些题上失败，不能直接算作算法退化；应分析是系统弱点还是题目 gold 不稳定。

### 15.4 用 DQE 做边际收益和归因分析

每次 live ablation 之后，应为每道题输出 component attribution，而不是只聚合均分。建议新增或扩展 artifact：

- `per_question_component_attribution.jsonl`
- `dqe_slice_metrics.tsv`
- `component_delta_by_slice.tsv`
- `failure_taxonomy.md`

每道题至少记录：

- B0/B1/B2/B3/B4/B5/B6/B7/Full 的 retrieved required hits。
- 哪些 required evidence 首次被哪个组件命中。
- query variant 命中了哪些 evidence。
- graph expansion 新增了哪些 evidence。
- rerank 前后 gold evidence rank 变化。
- final selection 丢掉了哪些 B6/B7 已召回 evidence。
- final answer 中哪些 answer key points 没有证据支持。
- 失败类型：retrieval_miss、graph_noise、rerank_demote、selection_drop、prompt_omission、judge_disagreement、gold_mapping_issue、answer_overgeneralization。

这样才能把“Full 没赢”拆开解释：是 ERC 图没有召回，还是召回了但 rerank 降级，还是 final selection 丢掉，还是 prompt assembly 没用上证据。这个归因比平均 correctness 更能支撑算法改进。

### 15.5 DQE 如何支撑三类论文主张

后续论文主张建议收敛成三类，每类都绑定 DQE evidence。

主张 A：ERC 异构证据图提升复杂题的多证据覆盖。

证据来源：

- `dqe_multi_evidence_stress`
- multi_document_text_reasoning
- multi_document_multimodal_reasoning
- matched_evidence_count >= 2/3 的题

应报告：

- B0 vs B3/B4/B5/B6/B7/Full 的 Evidence Recall@K。
- Required Evidence Coverage 的 per-slice delta。
- source_doc_coverage 是否提升。
- query variants 与 graph expansion 的 unique required hits。

主张 B：框架的 provenance-aware 设计提升可追溯性和可审计性。

证据来源：

- `source_unit_to_chunk_map.jsonl`
- `mapping_audit.md`
- manual review of repaired/table/multimodal evidence
- live `annotated_dataset.jsonl`

应报告：

- required evidence 中真实 chunk_id/source_ref/page_numbers 覆盖率。
- pseudo evidence 数量必须为 0。
- source unit repair 数量和人工通过率。
- citation recall 与 final evidence recall 的差距。

主张 C：build/replay/read-only/cache 路径支撑可复现实验和部署收益。

证据来源：

- 固定 DQE query set。
- fixed project digest。
- raw units replay artifact。
- read-only before/after snapshot。
- cache phase latency artifact。

应报告：

- online_vs_replay_match 是否为 True；若为 False，报告 digest 差异而不是宣称等价。
- readonly_snapshot_unchanged 是否为 True。
- no cache / retrieval warm / answer warm / keyword candidate warm 的 p50/p95。
- cache hit 是否改变 retrieval result；如果改变，必须标为 correctness risk。

### 15.6 DQE-informed 人工复核规则

人工复核不应随机看几题就结束。建议按 DQE 风险分层抽样：

- 全量复核 `dqe_repair_review_set`。
- 全量或高比例复核 `doc_constrained_table_section_ngram`。
- 每个 question_type 至少复核 2 题。
- 每个 source_doc 至少复核 2 条 evidence。
- 对 `possibly_over_general_gold_answer` 标记题做 key point coverage 检查。
- 对 phase8_action=replace 的题不进入主集，除非人工明确改为 keep 并写理由。

人工复核输出建议字段：

```json
{
  "question_id": "...",
  "evidence_index": 0,
  "review_status": "keep | revise | exclude | stress_set",
  "review_reason": "...",
  "gold_answer_fix": "",
  "evidence_fix": "",
  "reviewer": "manual",
  "reviewed_at": "..."
}
```

这些复核结果应被导入下一版 dataset，而不是只写在备注里。

### 15.7 DQE 对现有课题文档的具体改写要求

后续更新 `docs/research/erc_traceable_rag_report.md` 时，应新增或重写以下小节：

1. `DQE-Bench-derived Dataset Construction`

   说明 DQE SourceUnit、EvidenceBundle、Gold 样本如何转成 ERC live dataset。

2. `Evidence Mapping And Repair`

   说明 source unit 到 ragent chunk 的映射、38 条 stale source id 修复、表格证据匹配和人工复核规则。

3. `Capability Slices`

   用 DQE 字段定义 balanced、multi-evidence、table/multimodal、selection stress、repair review 等子集。

4. `Component Attribution`

   不只报告 config 平均分，还报告每个组件首次命中的 required evidence、rank 改变和 final selection loss。

5. `Claim Boundary`

   明确 DQE old system score 只是外部题库区分度背景；ERC 的收益只能来自本仓库 live ablation。

6. `Failure Taxonomy`

   将失败分为检索失败、图扩展噪声、rerank 降级、selection 丢证据、prompt 未使用证据、gold/mapping 问题、judge 分歧。

### 15.8 全量任务实验计划与执行路线

当前目标不是最小闭环，而是使用 DQE current gold 全量任务池来测算法改进和框架改进的收益。全量任务不是简单把 186 题混在一起算一个均分，而是“全量执行 + 分层归因 + stress analysis”：

1. 全量 mapped dataset：保留 186 道 DQE current gold 中所有能映射到真实 ragent chunk 的题。
2. phase8 keep/no_decision/replace 全部进入全量实验，但 replace 题默认只作为 stress/error-analysis 分层，不作为主 claim 的唯一依据。
3. 全量 B0-B7-Full live ablation 必须运行同一 dataset、同一 project、同一 judge mode、同一 env snapshot。
4. 全量结果必须按 DQE slice 拆开报告，不能只报告总体均分。
5. 需要为每道题生成 component attribution，解释每个算法组件贡献或失败的位置。

全量实验的产物应至少包含：

- `erc_evidence_questions_dqe_full_<timestamp>.jsonl`：全量 DQE-mapped ERC dataset。
- `dqe_capability_tags.jsonl`：每题的 DQE 控制变量和能力标签。
- `dqe_slice_manifest.json`：全量、keep、replace stress、多证据、跨文档、表格/多模态、repair review、calculation、hard、selection stress 等切片。
- `full_experiment_plan.md`：可直接复跑的 full gold replay 和 full live ablation 命令。
- `erc_full_eval_dqe_full_<timestamp>/`：全量 B0-B7-Full live ablation artifact。
- `per_question_component_attribution.jsonl`：逐题组件收益归因。
- `dqe_slice_metrics.tsv`：按 DQE slice 聚合的指标。
- `component_delta_by_slice.tsv`：按 slice 统计 B0->B3/B4/B5/B6/B7/Full 的边际收益。
- `failure_taxonomy.md`：失败题归因总结。

全量实验分为四个阶段执行。

第一阶段：全量数据集和分层产物生成。

执行：

```bash
python3 tools/import_dqe_bench_to_erc_dataset.py --selection-mode all --timestamp <timestamp>
```

预期输出：

- `benchmark/erc_evidence_questions_dqe_full_<timestamp>.jsonl`
- `benchmark/erc_dqe_dataset_audit_<timestamp>/`
- `benchmark/erc_dqe_mapping_<timestamp>/source_unit_to_chunk_map.jsonl`
- `benchmark/erc_dqe_mapping_<timestamp>/dqe_capability_tags.jsonl`
- `benchmark/erc_dqe_mapping_<timestamp>/dqe_slice_manifest.json`
- `benchmark/erc_dqe_mapping_<timestamp>/full_experiment_plan.md`

验收标准：

- 全量 dataset record_count 应接近 186；若少于 186，必须逐题说明 unmatched reason。
- 所有进入 live dataset 的题必须有真实 `required_chunk_ids` 和 `required_evidence`。
- `unmatched_evidence.jsonl` 必须存在；若非空，不能静默忽略。
- source unit repair、table section matching、phase8 replace 都必须进入 tags 和 slice manifest。

第二阶段：全量 harness sanity。

执行全量 gold replay 只用于检查评测 harness、dataset schema、artifact 输出和聚合逻辑，不作为系统收益：

```bash
uv run python tools/erc_full_eval.py \
  --dataset benchmark/erc_evidence_questions_dqe_full_<timestamp>.jsonl \
  --output-dir benchmark/erc_dqe_full_gold_replay_<timestamp> \
  --backend gold_replay \
  --configs B0 B1 B2 B3 B4 B5 B6 B7 Full \
  --skip-report
```

验收标准：

- 生成 `results.jsonl`、`metrics.tsv`、`summary.md`、`commands.md`、`env_snapshot.txt`。
- question_count 与 full dataset 一致。
- B0-B7-Full 均有结果。
- 报告中明确标记 gold replay 是 sanity，不得进入论文主表。

第三阶段：全量 live ablation。

执行：

```bash
uv run python tools/erc_full_eval.py \
  --dataset benchmark/erc_evidence_questions_dqe_full_<timestamp>.jsonl \
  --output-dir benchmark/erc_full_eval_dqe_full_<timestamp> \
  --backend live \
  --live-project-dir example/qwen4b_diet_kg \
  --skip-live-build \
  --configs B0 B1 B2 B3 B4 B5 B6 B7 Full \
  --judge-mode llm \
  --skip-report
```

必须保留：

- `results.jsonl`
- `judge_results.jsonl`
- `metrics.tsv`
- `summary.md`
- `latency_cache_summary.md`
- `run_manifest.json`
- `commands.md`
- `env_snapshot.txt`
- `annotated_dataset.jsonl`
- `build_inference_separation/separation_summary.json`

验收标准：

- 每个 config 的 question_count 与 full dataset 一致。
- LLM judge status 必须逐条记录；失败不能覆盖原始 retrieval metrics。
- live evidence matching 必须基于真实 chunk_id 或真实 content overlap。
- 若 Full 不优于 B0/B7，必须保留结果并进入 failure taxonomy，不能调题或只报有利子集。

第四阶段：全量归因分析和报告更新。

执行目标：

- 生成 `per_question_component_attribution.jsonl`。
- 生成 `dqe_slice_metrics.tsv`。
- 生成 `component_delta_by_slice.tsv`。
- 生成 `failure_taxonomy.md`。
- 更新 `docs/research/erc_traceable_rag_report.md`。

归因分析至少回答：

- B3 相对 B0 首次命中了哪些 entity-driven evidence。
- B4 相对 B3 首次命中了哪些 relation/condition evidence。
- B5 相对 B4 是否通过 graph expansion 增加跨章节或跨文档 evidence。
- B6 相对 B5 的 query variants 是否增加 required evidence hit。
- B7 相对 B6 是否改善 gold evidence rank。
- Full 相对 B7 是否保留或丢失 required evidence。
- 失败是否集中在 table/multimodal、source unit repair、phase8 replace、multi_document 或 hard 子集。

执行：

```bash
python3 tools/analyze_dqe_erc_results.py \
  --results-dir benchmark/erc_full_eval_dqe_full_<timestamp> \
  --capability-tags benchmark/erc_dqe_mapping_<timestamp>/dqe_capability_tags.jsonl \
  --slice-manifest benchmark/erc_dqe_mapping_<timestamp>/dqe_slice_manifest.json
```

最终目标是让 DQE 回答这三个问题：

- 题目是否足够可信，证据是否真实映射到 ragent chunk。
- 每个 ERC 算法组件在哪些 DQE 能力切片上带来可测收益。
- 当收益没有出现时，是算法组件失败、框架实现失败，还是题目/证据标注本身需要迭代。

### 15.9 DQE 全量任务执行记录

本轮已经把全量 DQE current gold 任务从计划推进到可复跑 artifact。当前已执行的是全量数据生成、全量 gold-replay harness sanity 和基于 full result schema 的 DQE slice/component attribution；这些结果用于验证评测框架和归因产物，不替代后续 full live ablation。

已生成的全量 artifact：

- 全量 dataset：`/Volumes/SSD1/ragent/benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl`
- 数据集审计：`/Volumes/SSD1/ragent/benchmark/erc_dqe_dataset_audit_20260601_000156`
- 映射审计：`/Volumes/SSD1/ragent/benchmark/erc_dqe_mapping_20260601_000156`
- 全量 gold-replay：`/Volumes/SSD1/ragent/benchmark/erc_dqe_full_gold_replay_20260601_000156`
- 分片指标：`/Volumes/SSD1/ragent/benchmark/erc_dqe_full_gold_replay_20260601_000156/dqe_slice_metrics.tsv`
- 组件增益：`/Volumes/SSD1/ragent/benchmark/erc_dqe_full_gold_replay_20260601_000156/component_delta_by_slice.tsv`
- 逐题归因：`/Volumes/SSD1/ragent/benchmark/erc_dqe_full_gold_replay_20260601_000156/per_question_component_attribution.jsonl`
- 失败归因：`/Volumes/SSD1/ragent/benchmark/erc_dqe_full_gold_replay_20260601_000156/failure_taxonomy.md`

全量 dataset 统计：

- record_count：186。
- question_type：fact_lookup 13、comparison 15、condition_filtering 16、aggregation_calculation 16、single_document_text_reasoning 29、single_document_multimodal_reasoning 34、multi_document_text_reasoning 35、multi_document_multimodal_reasoning 28。
- difficulty：easy 13、medium 53、hard 120。
- document_scope：single_document 123、multi_document 63。
- modality：text_document 124、multimodal_document 62。
- annotation_status：`dqe_mapped_complete` 171、`dqe_mapped_complete_with_source_unit_repairs` 15。
- `source_unit_to_chunk_map.jsonl`：331 条 evidence item 映射。
- `dqe_capability_tags.jsonl`：186 条。

全量 slice manifest 统计：

- `dqe_full_mapped`：186。
- `dqe_phase8_keep`：152。
- `dqe_phase8_replace_stress`：26。
- `dqe_multi_evidence_ge2`：97。
- `dqe_multi_evidence_ge3`：26。
- `dqe_multi_document`：63。
- `dqe_table_multimodal_stress`：128。
- `dqe_repair_review_set`：15。
- `dqe_calculation`：16。
- `dqe_hard`：120。
- `dqe_selection_stress_candidates`：72。

已执行命令：

```bash
python3 tools/import_dqe_bench_to_erc_dataset.py --selection-mode all
```

```bash
uv run python tools/erc_full_eval.py \
  --dataset benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl \
  --output-dir benchmark/erc_dqe_full_gold_replay_20260601_000156 \
  --backend gold_replay \
  --configs B0 B1 B2 B3 B4 B5 B6 B7 Full \
  --skip-report
```

```bash
python3 tools/analyze_dqe_erc_results.py \
  --results-dir benchmark/erc_dqe_full_gold_replay_20260601_000156 \
  --capability-tags benchmark/erc_dqe_mapping_20260601_000156/dqe_capability_tags.jsonl \
  --slice-manifest benchmark/erc_dqe_mapping_20260601_000156/dqe_slice_manifest.json
```

全量 gold-replay harness sanity 结果：

- `results.jsonl`：2232 行。
- full_no_cache 主实验行：1674 行，即 186 题乘以 B0、B1、B2、B3、B4、B5、B6、B7、Full。
- metrics rows：12 行，包含 9 个 full_no_cache config 和 Full 的 3 个 cache warm phase。
- B0：evidence_recall_at_k 0.8233，required_evidence_coverage 0.6545。
- B3：evidence_recall_at_k 0.9797，required_evidence_coverage 0.8798。
- B4：evidence_recall_at_k 0.9919，required_evidence_coverage 0.9560。
- B5：evidence_recall_at_k 1.0000，required_evidence_coverage 0.9837。
- B6：evidence_recall_at_k 1.0000，required_evidence_coverage 0.9889。
- B7：evidence_recall_at_k 1.0000，required_evidence_coverage 0.9987。
- Full：evidence_recall_at_k 1.0000，required_evidence_coverage 1.0000。

gold-replay slice/component sanity 观察：

- 总体 `B0 -> Full`：required_evidence_coverage +0.3455，correctness +0.2591。
- `dqe_multi_document` 的 `B0 -> Full`：required_evidence_coverage +0.4705，correctness +0.3529。
- `dqe_table_multimodal_stress` 的 `B0 -> Full`：required_evidence_coverage +0.3559，correctness +0.2669。
- `dqe_selection_stress_candidates` 的 `B0 -> Full`：required_evidence_coverage +0.4366，correctness +0.3274。
- `dqe_hard` 的 `B0 -> Full`：required_evidence_coverage +0.3738，correctness +0.2803。
- 当前 `failure_taxonomy.md` 在 gold-replay 层显示 `no_primary_failure: 186`。这只说明 harness 和归因 schema 闭环正常，不说明 live 系统没有失败。

2026-06-01 已完成 full live ablation。gold-replay 上面的数字仍只作为 harness sanity；论文主实验应使用下面的 full live artifact。

### 15.10 2026-06-01 DQE 全量 live ablation 执行结果（历史前一版）

> 本节保留 2026-06-01 `existing_project_copy` live run 的过程记录和当时判断，用于审计实验演进。它已被顶部“当前状态（2026-06-03）”和 `docs/research/erc_traceable_rag_total_results.md` 中的当前主线替代，不应再作为当前统一入口。

全量 live artifact：

- 主输出目录：`/Volumes/SSD1/ragent/benchmark/erc_full_eval_dqe_full_20260601_1233_retry1`
- 终端日志：`/Volumes/SSD1/ragent/benchmark/erc_full_eval_dqe_full_20260601_1233_retry1.terminal.log`
- 主指标：`/Volumes/SSD1/ragent/benchmark/erc_full_eval_dqe_full_20260601_1233_retry1/metrics.tsv`
- LLM judge：`/Volumes/SSD1/ragent/benchmark/erc_full_eval_dqe_full_20260601_1233_retry1/judge_results.jsonl`
- 分片指标：`/Volumes/SSD1/ragent/benchmark/erc_full_eval_dqe_full_20260601_1233_retry1/dqe_slice_metrics.tsv`
- 组件归因：`/Volumes/SSD1/ragent/benchmark/erc_full_eval_dqe_full_20260601_1233_retry1/component_delta_by_slice.tsv`
- 逐题归因：`/Volumes/SSD1/ragent/benchmark/erc_full_eval_dqe_full_20260601_1233_retry1/per_question_component_attribution.jsonl`
- 失败分类：`/Volumes/SSD1/ragent/benchmark/erc_full_eval_dqe_full_20260601_1233_retry1/failure_taxonomy.md`

最终执行命令：

```bash
OUT=benchmark/erc_full_eval_dqe_full_20260601_1233_retry1
uv run python tools/erc_full_eval.py \
  --dataset /Volumes/SSD1/ragent/benchmark/erc_evidence_questions_dqe_full_20260601_000156.jsonl \
  --output-dir "$OUT" \
  --backend live \
  --live-project-dir /Volumes/SSD1/ragent/example/qwen4b_diet_kg \
  --skip-live-build \
  --configs B0 B1 B2 B3 B4 B5 B6 B7 Full \
  --judge-mode llm \
  --skip-report \
  --resume-partial \
  --live-concurrency 4 \
  --live-max-attempts 5 \
  --live-retry-sleep 20 \
  --live-query-timeout 360 \
  --live-judge-timeout 180
```

为完成全量执行，评测 harness 已补齐以下工程能力：

- 增量写入 `results.jsonl` 和 `judge_results.jsonl`，避免长任务中断后丢失已完成查询。
- `--resume-partial` 支持按 config、cache phase、question id 续跑。
- live query 和 judge 均支持重试、sleep、timeout。
- `--live-concurrency 4` 按 config/cache phase 内并发执行，phase 边界仍保持顺序。
- LLM judge JSON parser 支持模型在 JSON 后追加文本的情况。
- 并发 judge 写入已改成任务局部聚合，避免共享列表重复写入。

最终 artifact 完整性：

- `results.jsonl`：2232 行，即 186 题乘以 9 个 full_no_cache config，再加 Full 的 3 个 cache warm phase。
- `judge_results.jsonl`：1674 行，覆盖全部 full_no_cache 主实验结果。
- judge status：`ok=1674`，失败 judge 已定点重跑并修复。
- `metrics.tsv`：13 行，包含 9 个 full_no_cache config 和 Full 的 4 个 cache phase。
- `dqe_slice_metrics.tsv`：100 行。
- `component_delta_by_slice.tsv`：78 行。
- `per_question_component_attribution.jsonl`：186 行。
- `failure_taxonomy.md`：保留全部失败类型，不做有利子集过滤。

主结果表如下。这里的 correctness、completeness、faithfulness 是 LLM judge 诊断指标；主张优先看 evidence recall、required coverage、unsupported claim rate 和 latency。

| config | correctness | completeness | faithfulness | evidence_recall@k | final_recall | required_coverage | unsupported_claim_rate | p50 latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 | 0.6788 | 0.7192 | 0.6616 | 0.3315 | 0.3315 | 0.4158 | 0.3176 | 9.6415 |
| B1 | 0.6944 | 0.7266 | 0.6523 | 0.3315 | 0.3315 | 0.4158 | 0.3173 | 17.3575 |
| B2 | 0.6878 | 0.7149 | 0.6346 | 0.4215 | 0.3141 | 0.5576 | 0.3252 | 18.4320 |
| B3 | 0.7084 | 0.7606 | 0.7030 | 0.3289 | 0.3289 | 0.5543 | 0.2647 | 16.3205 |
| B4 | 0.7355 | 0.7682 | 0.7341 | 0.3315 | 0.3315 | 0.5663 | 0.2429 | 21.5790 |
| B5 | 0.7228 | 0.7734 | 0.6997 | 0.4693 | 0.4117 | 0.6064 | 0.2808 | 21.4885 |
| B6 | 0.7303 | 0.7758 | 0.6732 | 0.4677 | 0.3692 | 0.5843 | 0.2998 | 21.6260 |
| B7 | 0.7370 | 0.7971 | 0.7199 | 0.4637 | 0.4261 | 0.6128 | 0.2683 | 26.2570 |
| Full | 0.7132 | 0.7604 | 0.6631 | 0.4664 | 0.2661 | 0.5328 | 0.3166 | 20.8090 |

相对 B0 的主要收益：

- B4：correctness +0.0567，required_coverage +0.1505，final_recall +0.0000，unsupported_claim_rate -0.0747。
- B5：correctness +0.0440，required_coverage +0.1906，final_recall +0.0802，unsupported_claim_rate -0.0368。
- B7：correctness +0.0582，required_coverage +0.1970，final_recall +0.0946，unsupported_claim_rate -0.0493。
- Full：correctness +0.0344，required_coverage +0.1170，final_recall -0.0654，unsupported_claim_rate -0.0010。

组件归因结论：

| component | comparison | delta_final_recall | delta_required_coverage | delta_correctness | delta_faithfulness |
|---|---|---:|---:|---:|---:|
| chunk_to_chunk_entity | B0 -> B3 | -0.0027 | +0.1385 | +0.0297 | +0.0414 |
| entity_to_relation | B3 -> B4 | +0.0027 | +0.0120 | +0.0271 | +0.0312 |
| relation_to_graph_expansion | B4 -> B5 | +0.0802 | +0.0401 | -0.0128 | -0.0344 |
| graph_to_query_variants | B5 -> B6 | -0.0426 | -0.0221 | +0.0075 | -0.0265 |
| query_variants_to_rerank | B6 -> B7 | +0.0569 | +0.0284 | +0.0067 | +0.0468 |
| rerank_to_evidence_selection | B7 -> Full | -0.1599 | -0.0800 | -0.0238 | -0.0569 |
| chunk_to_full | B0 -> Full | -0.0654 | +0.1170 | +0.0345 | +0.0015 |

解释：

- B7 是当前最强 end-to-end retrieval 配置：正确性、完整性、final evidence recall 和 required coverage 均为主配置最高，但 latency 也最高。
- B3/B4/B5 证明实体、关系和图扩展对 required coverage 有可测收益；B5 是 candidate recall 和 final recall 的关键跃升点。
- B6 的 query variants 单独看会降低 final recall 和 required coverage；它需要更严格的 query 过滤或候选合并约束。
- B7 的 rerank 能把 B6 的 final recall 损失拉回来，是当前保留 query variants 的主要理由。
- Full evidence selection 是负结果：相对 B7 丢失 final evidence recall 0.1599、required coverage 0.0800、correctness 0.0238。后续不能把 Full 写成最终成功版本，应把 evidence selection 作为下一轮算法修复目标。

DQE slice 观察：

| slice | n | B7 correctness | B7 final_recall | B7 required_coverage | B7 unsupported_claim_rate |
|---|---:|---:|---:|---:|---:|
| dqe_full_mapped | 186 | 0.7370 | 0.4261 | 0.6128 | 0.2683 |
| dqe_phase8_keep | 152 | 0.7732 | 0.4156 | 0.6082 | 0.2607 |
| dqe_phase8_replace_stress | 26 | 0.5788 | 0.4391 | 0.6150 | 0.2981 |
| dqe_multi_evidence_ge2 | 97 | 0.6617 | 0.3325 | 0.5633 | 0.3198 |
| dqe_multi_evidence_ge3 | 26 | 0.6589 | 0.2019 | 0.4850 | 0.3031 |
| dqe_multi_document | 63 | 0.6045 | 0.2659 | 0.5300 | 0.3400 |
| dqe_table_multimodal_stress | 128 | 0.6940 | 0.3535 | 0.5754 | 0.3055 |
| dqe_calculation | 16 | 0.8844 | 0.6250 | 0.6846 | 0.0956 |
| dqe_hard | 120 | 0.6832 | 0.3736 | 0.5839 | 0.2938 |

slice 层解释：

- calculation 切片最强，说明数值型问题在证据命中后可被当前回答链路较好利用。
- multi_document、multi_evidence_ge3、table/multimodal 仍是主短板，后续应优先优化跨文档 evidence assembly、表格 evidence 表达和最终 evidence selection。
- phase8_replace_stress 的 correctness 明显低于 keep 子集，应保留为 stress analysis，而不是从主表中剔除。

cache 结果：

| phase | p50 latency | p95 latency | mean latency | cache stages |
|---|---:|---:|---:|---|
| Full full_no_cache | 20.8090 | 36.4738 | 23.0588 | answer_cache_hit |
| Full retrieval_cache_warm | 8.9110 | 18.7730 | 9.4329 | answer_cache_hit,retrieval_cache_hit |
| Full answer_cache_warm | 0.0340 | 0.0902 | 0.0416 | answer_cache_hit |
| Full keyword_candidate_cache_warm | 23.9895 | 38.4075 | 25.1487 | answer_cache_hit,keyword_candidate_cache_hit |

cache 解释：

- retrieval cache 和 answer cache 有明确延迟收益。
- keyword candidate warm 在本次 run 中没有收益，反而慢于 full_no_cache；应作为框架改进问题保留，而不是包装成正结果。
- `full_no_cache` 仍记录到 `answer_cache_hit`，说明当前 runtime/cache 状态不是严格纯冷启动。论文最终 latency 表需要用隔离 cache DB 或清空 cache 的复跑来确认。

失败分类：

- `no_primary_failure`：73。
- `no_required_coverage_gain`：11。
- `retrieval_regression`：2。
- `selection_drop`：39。
- `unsupported_claim_risk`：61。

失败集中在 table/multimodal、hard、multi_evidence、multi_document 和 selection stress 相关标签上。这说明 DQE 的价值不是只扩大题量，而是把失败位置约束到了可解释的能力切片上。

本次 full live run 的可用性边界：

- 可以作为 DQE full mapped dataset 上的 retrieval/QA 主消融结果。
- 可以支撑“实体、关系、图扩展、后融合 rerank 对证据覆盖有收益”的主张。
- 不能支撑“Full evidence selection 已经优于 B7”的主张；当前结果相反。
- 不能支撑 fresh online build 与 raw replay 完全等价的工程主张；本 artifact 使用 `existing_project_copy`，build/replay 仍需单独做 fresh build audit。
- 第一次 full run 在 B7 阶段遇到 provider 空/非 JSON 响应而中断；最终 retry1 通过增量、续跑、重试、timeout 和并发 race 修复完成。该过程应写入 reproducibility note。

文档层后续动作（历史记录，当前已由 2026-06-02 统一入口替代）：

- `docs/research/erc_traceable_rag_report.md` 当时需要从 20 题 pilot 切换到 `erc_full_eval_dqe_full_20260601_1233_retry1`；当前已进一步切换到顶部列出的 2026-06-02 主 live artifact。
- 主表应优先使用 B7 作为当前 best retrieval setting，并把 Full evidence selection 写成负结果和下一轮修复目标。
- 附录应保留 gold-replay sanity、首次失败 run、judge reparse/rejudge 和 cache caveat。
