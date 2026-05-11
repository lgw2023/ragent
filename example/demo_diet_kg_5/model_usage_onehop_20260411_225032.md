# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T22:50:07`
- Ended at: `2026-04-11T22:50:32`
- Metadata:
  - `query`: `我平时早餐常吃两片普通面包配2个鸡蛋，再喝一杯牛奶；午餐和晚餐也经常会吃鸡胸肉、鱼虾、瘦肉这类动物性食物。这样安排会不会把肉类吃得太多，长期下来不太符合健康饮食要求？如果想更合理一些，动物性食物应该怎么搭配才更合适？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5208 | 638 | 5846 | 0 |
| embedding | 14 | 152 | 0 | 152 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 5360 | 638 | 5998 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5208 | 638 | 5846 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 152 | 0 | 152 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T22:50:08` `embedding` / `text-embedding-v3` input=74 output=0 total=74 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T22:50:10` `chat` / `qwen3-32b` input=941 output=65 total=1006 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T22:50:10` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T22:50:10` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T22:50:10` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T22:50:10` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T22:50:10` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T22:50:10` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T22:50:10` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T22:50:10` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T22:50:11` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T22:50:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T22:50:11` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T22:50:11` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
15. `2026-04-11T22:50:11` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
16. `2026-04-11T22:50:11` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-11T22:50:31` `chat` / `qwen3-32b` input=4267 output=573 total=4840 source=`ragent.llm.openai.openai_complete_if_cache`
