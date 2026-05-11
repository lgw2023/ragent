# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T14:09:11`
- Ended at: `2026-04-07T14:09:33`
- Metadata:
  - `query`: `早餐燕麦粥+牛奶+鸡蛋+西芹花生米，午餐杂粮饭+鸡翅根+土豆丝+菠菜+紫菜蛋汤，晚餐米饭+豆腐+香菇油菜+鲈鱼+苹果，每周都这样吃的话，食物种类够吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4793 | 407 | 5200 | 0 |
| embedding | 4 | 206 | 0 | 206 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 4999 | 407 | 5406 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4793 | 407 | 5200 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 206 | 0 | 206 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T14:09:12` `embedding` / `text-embedding-v3` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T14:09:16` `chat` / `qwen3-32b` input=930 output=92 total=1022 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T14:09:16` `embedding` / `text-embedding-v3` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T14:09:16` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T14:09:17` `embedding` / `text-embedding-v3` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T14:09:17` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T14:09:32` `chat` / `qwen3-32b` input=3863 output=315 total=4178 source=`ragent.llm.openai.openai_complete_if_cache`
