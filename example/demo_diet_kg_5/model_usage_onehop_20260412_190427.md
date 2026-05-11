# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:04:20`
- Ended at: `2026-04-12T19:04:27`
- Metadata:
  - `query`: `如果做一款非发酵豆制品，原料里提到的大豆和生产用水分别要满足什么要求？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4175 | 190 | 4365 | 0 |
| embedding | 9 | 58 | 0 | 58 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4233 | 190 | 4423 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4175 | 190 | 4365 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 58 | 0 | 58 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:04:20` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:04:22` `chat` / `qwen3-32b` input=892 output=39 total=931 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:04:22` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:04:22` `embedding` / `text-embedding-v3` input=10 output=0 total=10 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:04:22` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:04:22` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:04:22` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:04:22` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:04:23` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:04:23` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:04:23` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T19:04:27` `chat` / `qwen3-32b` input=3283 output=151 total=3434 source=`ragent.llm.openai.openai_complete_if_cache`
