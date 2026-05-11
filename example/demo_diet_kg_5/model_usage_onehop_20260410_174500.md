# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-10T17:44:37`
- Ended at: `2026-04-10T17:45:00`
- Metadata:
  - `query`: `我现在22岁，在学校想调整饮食结构，但有些东西买不到，比如橄榄油、核桃仁、燕麦等。仅根据这张《中国居民膳食指南》配图及其上下文，如果要做一个最容易执行的主食调整策略，应该优先调整哪一类食物，并朝什么方向替换？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4038 | 436 | 4474 | 0 |
| embedding | 12 | 137 | 0 | 137 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4175 | 436 | 4611 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4038 | 436 | 4474 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 137 | 0 | 137 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-10T17:44:37` `embedding` / `text-embedding-v3` input=73 output=0 total=73 source=`ragent.llm.openai.openai_embed`
2. `2026-04-10T17:44:41` `chat` / `qwen3-32b` input=938 output=53 total=991 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-10T17:44:41` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-10T17:44:41` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-10T17:44:41` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-10T17:44:41` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-10T17:44:41` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
8. `2026-04-10T17:44:41` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-10T17:44:42` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-10T17:44:42` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-10T17:44:42` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
12. `2026-04-10T17:44:42` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-10T17:44:42` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-10T17:44:43` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-10T17:44:59` `chat` / `qwen3-32b` input=3100 output=383 total=3483 source=`ragent.llm.openai.openai_complete_if_cache`
