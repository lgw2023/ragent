# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-10T14:24:36`
- Ended at: `2026-04-10T14:25:06`
- Metadata:
  - `query`: `16+8轻断食饮食方法怎么吃`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4274 | 944 | 5218 | 0 |
| embedding | 9 | 59 | 0 | 59 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4333 | 944 | 5277 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4274 | 944 | 5218 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 59 | 0 | 59 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-10T14:24:36` `embedding` / `text-embedding-v3` input=9 output=0 total=9 source=`ragent.llm.openai.openai_embed`
2. `2026-04-10T14:24:39` `chat` / `qwen3-32b` input=883 output=47 total=930 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-10T14:24:39` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
4. `2026-04-10T14:24:39` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-10T14:24:39` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-10T14:24:39` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
7. `2026-04-10T14:24:40` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
8. `2026-04-10T14:24:40` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-10T14:24:40` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-10T14:24:40` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
11. `2026-04-10T14:24:40` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-10T14:25:05` `chat` / `qwen3-32b` input=3391 output=897 total=4288 source=`ragent.llm.openai.openai_complete_if_cache`
