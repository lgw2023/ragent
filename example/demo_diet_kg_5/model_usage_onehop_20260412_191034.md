# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:10:19`
- Ended at: `2026-04-12T19:10:34`
- Metadata:
  - `query`: `我想给一个体重比较大、平时活动不多的人做减重饮食安排。除了控制总热量之外，为什么还要特别把每天的活动量提上去？如果按一天总消耗来算，活动这部分大概要占多少才比较合适？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3679 | 435 | 4114 | 0 |
| embedding | 11 | 106 | 0 | 106 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 3785 | 435 | 4220 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3679 | 435 | 4114 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 106 | 0 | 106 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:10:19` `embedding` / `text-embedding-v3` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:10:21` `chat` / `qwen3-32b` input=923 output=48 total=971 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:10:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:10:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:10:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:10:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:10:21` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:10:22` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:10:22` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:10:22` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:10:22` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T19:10:22` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T19:10:22` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T19:10:34` `chat` / `qwen3-32b` input=2756 output=387 total=3143 source=`ragent.llm.openai.openai_complete_if_cache`
