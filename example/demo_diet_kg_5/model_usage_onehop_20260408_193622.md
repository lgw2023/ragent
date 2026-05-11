# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-08T19:35:49`
- Ended at: `2026-04-08T19:36:22`
- Metadata:
  - `query`: `早餐燕麦粥+牛奶+鸡蛋+西芹花生米，午餐杂粮饭+鸡翅根+土豆丝+菠菜+紫菜蛋汤，晚餐米饭+豆腐+香菇油菜+鲈鱼+苹果，每周都这样吃的话，食物种类够吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 1 | 3779 | 358 | 4137 | 0 |
| embedding | 14 | 170 | 0 | 170 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 3949 | 358 | 4307 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 1 | 3779 | 358 | 4137 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 170 | 0 | 170 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-08T19:35:51` `embedding` / `text-embedding-v3` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
2. `2026-04-08T19:35:53` `embedding` / `text-embedding-v3` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
3. `2026-04-08T19:35:54` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-08T19:35:54` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-08T19:35:54` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-08T19:35:54` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-08T19:35:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-08T19:35:56` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-08T19:36:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-08T19:36:02` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-08T19:36:03` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-08T19:36:03` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
13. `2026-04-08T19:36:05` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-08T19:36:08` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
15. `2026-04-08T19:36:10` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-08T19:36:22` `chat` / `qwen3-32b` input=3779 output=358 total=4137 source=`ragent.llm.openai.openai_complete_if_cache`
