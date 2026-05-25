# Bulk KG Build Pipeline

大批量文档构建 KG 时，推荐把流程拆成业务编排层和 Ragent 通用层。
业务编排层负责目录扫描、分类、供应商分片和服务器环境变量；Ragent 通用层只保留
raw export、canonical merge、strict replay 和 finished KG merge。

## Recommended Flow

```text
PDF / Markdown corpus
        |
        v
MinerU enhanced markdown
        |
        v
raw export shards -> *.raw-units.jsonl
        |
        v
canonical raw-units merge
        |
        v
strict replay into final project
```

## Adopted Practices

1. **Export / Replay decoupling**: export 阶段完成 chunk、embedding、实体关系抽取，
   replay 阶段复用在线 `merge_nodes_and_edges` 语义构建最终 KG。
2. **Shard-level resumability**: standalone export 支持 `--resume`、
   `--flush-each-unit`、`--progress-output`、`--successes-output` 和
   `--failures-output`。
3. **Corpus collision avoidance**: 多语料合并时用
   `tools/merge_raw_units_canonical.py label=/path ...` 给 `source_group_key`
   加语料前缀。
4. **Replay into disposable targets**: 生产构建仍建议 replay 到新目录；确需续跑时用
   `tools/replay_raw_merge_units_to_project.py --resume`。
5. **Finished KG merge is separate**: `tools/merge_kg_projects.py` 用于快速合并已完成
   KG 项目，不等价于 raw replay 的在线语义。

## What Stays Outside Core

以下内容应保留在业务或服务器脚本中，不直接放入 Ragent 通用主线：

- 固定业务目录，例如 `/data/disk1/食品科学`。
- 食品科学 11 类分类规则、供应商权重和 shard 数。
- API key 加载脚本、代理地址和服务器绝对路径。
- 长跑任务 watch/retry 策略中依赖具体机器资源和供应商限流的参数。

这些脚本可以调用通用工具，但不应让主线工具默认绑定某个语料或内网环境。

## Commands

```bash
# Export one shard with resume and sidecar logs.
python tools/export_raw_merge_units.py ./md_shard \
  -o ./raw_units/shard-0001.raw-units.jsonl \
  --recursive \
  --resume \
  --flush-each-unit \
  --continue-on-error \
  --progress-output ./progress/shard-0001.ndjson \
  --successes-output ./successes/shard-0001.ndjson \
  --failures-output ./failures/shard-0001.ndjson

# Merge multiple corpora into one canonical stream.
python tools/merge_raw_units_canonical.py \
  pdf=./raw_units_pdf \
  otherdocs=./raw_units_otherdocs \
  -o ./raw_units_merged/all.raw-units.jsonl

# Replay into a final project.
python tools/replay_raw_merge_units_to_project.py \
  ./raw_units_merged/all.raw-units.jsonl \
  -o ./final_project \
  --overwrite
```
