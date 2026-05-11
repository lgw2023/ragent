# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-08T17:19:29`
- Ended at: `2026-04-08T17:19:51`
- Metadata:
  - `query`: `高血压患者每天食盐摄入量建议控制在多少？除了限盐，还强调了哪类食物摄入？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3968 | 204 | 4172 | 0 |
| embedding | 10 | 86 | 0 | 86 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 4054 | 204 | 4258 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3968 | 204 | 4172 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 10 | 86 | 0 | 86 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-08T17:19:33` `embedding` / `text-embedding-v3` input=28 output=0 total=28 source=`ragent.llm.openai.openai_embed`
2. `2026-04-08T17:19:36` `chat` / `qwen3-32b` input=896 output=45 total=941 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-08T17:19:38` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-08T17:19:38` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
5. `2026-04-08T17:19:40` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-08T17:19:40` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
7. `2026-04-08T17:19:42` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-08T17:19:42` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
9. `2026-04-08T17:19:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-08T17:19:43` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-08T17:19:43` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-08T17:19:45` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-08T17:19:51` `chat` / `qwen3-32b` input=3072 output=159 total=3231 source=`ragent.llm.openai.openai_complete_if_cache`
