# Ragent Strict Offline Replay

严格离线合并的目标不是合并已经 summary/压缩过的 finished KG，而是：

1. shard 阶段只做 chunk、embedding、entity/relation extraction，输出 raw merge units JSONL。
2. final 阶段按确定顺序 replay raw units，并复用 `ragent.operate.merge_nodes_and_edges` 生成最终 KG。

`tools/merge_kg_projects.py` 仍然是 finished KG fast/fallback merge。它适合语义可用的快速合并，但不能保证计算过程对应 online reference。

## Export

独立 markdown 导出：

```bash
python tools/export_raw_merge_units.py ./md_dir -o ./raw_units/shard-0001.jsonl --recursive
```

默认遇到单个文件失败会 fail fast。大批量 shard 如果希望跳过失败文件并继续：

```bash
python tools/export_raw_merge_units.py ./md_dir -o ./raw_units/shard-0001.jsonl --recursive --continue-on-error
```

失败文件会写到 `<output-stem>.failures.jsonl`，也可以用 `--failures-output` 指定路径。

长时间运行的 shard 建议同时开启断点续跑和旁路进度记录：

```bash
python tools/export_raw_merge_units.py ./md_dir \
  -o ./raw_units/shard-0001.jsonl \
  --recursive \
  --resume \
  --flush-each-unit \
  --continue-on-error \
  --progress-output ./progress/shard-0001.ndjson \
  --successes-output ./successes/shard-0001.ndjson \
  --failures-output ./failures/shard-0001.ndjson
```

`--resume` 会读取已有 output JSONL 中的 `doc_id` 并跳过这些文档，然后追加新结果。
如果已有 JSONL 存在坏行，命令会停止，避免在损坏文件后继续追加。

接入现有 PDF -> markdown 管线的导出：

```bash
python singlefile.py parse ./example.pdf ./mineru_out ./raw_units raw
```

`raw` stage 会复用已有最终 md；如果没有找到 md，会先执行增强 md 生成，再导出 raw units。单文件 `raw` stage 的第三个参数可以是 `.jsonl` 文件，也可以是目录；目录会写入 `<pdf-stem>.raw-units.jsonl`。目录批处理时第三个参数必须是输出目录。

通过现有 PDF -> markdown 管线或独立 markdown CLI 导出的 raw units 都会把 `model_usage_raw_export_*.md` 写到 raw JSONL 所在目录。

## Replay

默认 replay 是流式的：先扫描 JSONL 统计 group 数并校验顺序，再按 source group 一组一组读取和 merge。

```bash
python tools/replay_raw_merge_units_to_project.py ./raw_units -o ./final_project --overwrite
```

如果目标 project 已经存在，可用 `--resume` 继续写入；已有 `doc_status`
记录的文档会被跳过：

```bash
python tools/replay_raw_merge_units_to_project.py ./raw_units -o ./final_project --resume
```

小样本调试或历史非连续 group 输入可以使用 in-memory grouping：

```bash
python tools/replay_raw_merge_units_to_project.py ./raw_units -o ./final_project --overwrite --in-memory
```

如果某个 source group 失败，默认会回滚该 group 已写入的 `full_docs`、`text_chunks`、`chunks_vdb`，并尽量恢复 merge 触碰过的 graph/entity VDB/relation VDB 记录，同时把该 group 的 doc_status 标记为 FAILED。要继续处理后续 group：

```bash
python tools/replay_raw_merge_units_to_project.py ./raw_units -o ./final_project --overwrite --continue-on-error
```

`--no-rollback-on-error` 只用于故障分析，正常 strict replay 不建议使用。

Replay CLI 会把 `model_usage_raw_replay_*.md` 写到目标 project 目录。这个报告覆盖 replay merge summary 和最终 graph content embedding 等调用，不包含 shard raw extraction 阶段已经完成的 LLM 调用。

## Deterministic Ordering

确定性规则如下：

1. raw JSONL 文件顺序：CLI 显式传入的路径按参数顺序处理；目录输入中的 `*.jsonl` 按文件名排序。
2. unit 顺序：每个 JSONL 文件内按行号顺序处理。
3. `source_group_key`：独立 markdown export 使用源文件 stem；`singlefile.py parse ... raw` 使用在线入库的 `doc_name` stem，因此同一 PDF 的文本和图片描述会落到同一个 source group。
4. 同一 source group 内的 doc/chunk 顺序：继承 markdown insert plan 的 `sort_order`；parser 模式按 markdown 行号、图片描述优先级、chunk index 排序。
5. 流式 replay 要求同一个 `source_group_key` 在 JSONL 输入中只出现一个连续块。大规模 shard 建议一篇源文档一个 raw JSONL，或按 `source_group_key` 对 shard 输出做外部排序。

## Multi-Corpus Canonical Merge

多个语料各自 export 完成后，可以先合并成 canonical JSONL，再统一 replay：

```bash
python tools/merge_raw_units_canonical.py \
  pdf=./raw_units_pdf \
  otherdocs=./raw_units_otherdocs \
  -o ./raw_units_merged/all.raw-units.jsonl
```

默认会把 `source_group_key` 改写为 `<label>:<source_group_key>`，避免不同语料中同名
PDF、同名 markdown 或相同 stem 发生 group key 碰撞。需要跳过重复 `doc_id`
时加 `--dedupe-doc-ids`；需要保持原 key 时加 `--no-prefix-source-group-key`。

## Cache And Failure Semantics

Raw unit 包含 chunk、vector chunk、extraction result 和 chunk 记录中的 cache key 列表，但不把 shard 工作目录里的完整 LLM cache payload 内嵌进 JSONL。Replay 阶段会使用目标 project 的 `llm_response_cache` 处理 merge summary cache；如需逐次调用完全一致，需要固定 summary 阈值、LLM 模型、并发度和 cache 输入。

Shard export 默认 fail fast。`integrations.export_md_to_raw_merge_units(..., continue_on_error=True)` 或 CLI `--continue-on-error` 可把失败 unit 写入独立 `.failures.jsonl`。Replay 默认也 fail fast；建议 replay 到全新目标目录，失败后用 `--overwrite` 从 raw units 重放。虽然 replay 会尽力恢复 graph/vector 记录，跨后端图存储没有真正事务，生产 strict build 仍应把目标 project 目录当成一次性构建产物。

## Real Environment E2E

真实 `.env` 端到端测试默认跳过，避免 CI 或普通单测误触发外部模型调用。需要验证 example PDF 的 raw export、offline replay、online reference 基础一致性时显式开启：

```bash
RAGENT_RUN_REAL_ENV_E2E=1 python -m pytest tests/test_offline_replay_real_env_e2e.py -q
```

该测试会读取仓库根目录 `.env`，使用 `example/GB-31607-2021.pdf`，并检查 raw JSONL 非空、`model_usage_raw_export_*.md` 已持久化、offline replay 与 online reference 的 doc/chunk/VDB chunk ID 一致。真实 LLM 抽取具有非确定性，因此测试不要求 offline graph 与 online graph 完全同构。
