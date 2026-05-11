# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:26:27`
- Ended at: `2026-04-12T00:26:34`
- Metadata:
  - `query`: `如果想控制热量，早餐里一份中式搭配和一份西式搭配相比，哪一份能量更高一些？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4865 | 151 | 5016 | 0 |
| embedding | 9 | 64 | 0 | 64 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4929 | 151 | 5080 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4865 | 151 | 5016 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 64 | 0 | 64 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:26:27` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:26:28` `chat` / `qwen3-32b` input=893 output=39 total=932 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:26:29` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:26:29` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:26:29` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:26:29` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:26:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:26:29` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:26:29` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:26:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:26:31` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T00:26:34` `chat` / `qwen3-32b` input=3972 output=112 total=4084 source=`ragent.llm.openai.openai_complete_if_cache`
