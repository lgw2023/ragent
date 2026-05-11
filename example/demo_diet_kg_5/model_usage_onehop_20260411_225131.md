# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T22:51:17`
- Ended at: `2026-04-11T22:51:31`
- Metadata:
  - `query`: `我想按均衡饮食来安排一天的饮食：如果我今天主要吃的是谷薯类食物，其他几类食物都吃得比较少，这样的搭配算不算合理？另外，水和油盐在日常饮食里大概应该控制到什么范围？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3615 | 413 | 4028 | 0 |
| embedding | 13 | 114 | 0 | 114 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 3729 | 413 | 4142 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3615 | 413 | 4028 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 114 | 0 | 114 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T22:51:17` `embedding` / `text-embedding-v3` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T22:51:19` `chat` / `qwen3-32b` input=925 output=53 total=978 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T22:51:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-11T22:51:20` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-11T22:51:30` `chat` / `qwen3-32b` input=2690 output=360 total=3050 source=`ragent.llm.openai.openai_complete_if_cache`
