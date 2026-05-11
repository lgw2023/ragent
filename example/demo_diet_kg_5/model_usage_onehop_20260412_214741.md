# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:47:36`
- Ended at: `2026-04-12T21:47:41`
- Metadata:
  - `query`: `我国居民每日谷类食物里，大米和面粉合计大约占总摄入量的百分之多少？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3884 | 92 | 3976 | 0 |
| embedding | 10 | 74 | 0 | 74 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 3958 | 92 | 4050 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3884 | 92 | 3976 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 10 | 74 | 0 | 74 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:47:36` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:47:38` `chat` / `qwen3-32b` input=893 output=44 total=937 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:47:38` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:47:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:47:38` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:47:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:47:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:47:38` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:47:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:47:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:47:38` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:47:39` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-12T21:47:41` `chat` / `qwen3-32b` input=2991 output=48 total=3039 source=`ragent.llm.openai.openai_complete_if_cache`
