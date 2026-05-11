# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:07:36`
- Ended at: `2026-04-12T19:07:50`
- Metadata:
  - `query`: `我想按这个搭配来做代茶饮：山楂10克、荷叶30克、银花10克、菊花10克。它更适合想控制体重的人，还是更适合血压偏高的人？如果只能选一个方向，哪个更贴近它的主要作用？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4080 | 465 | 4545 | 0 |
| embedding | 10 | 105 | 0 | 105 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 4185 | 465 | 4650 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4080 | 465 | 4545 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 10 | 105 | 0 | 105 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:07:36` `embedding` / `text-embedding-v3` input=61 output=0 total=61 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:07:37` `chat` / `qwen3-32b` input=931 output=43 total=974 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:07:37` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:07:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:07:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:07:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:07:38` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:07:38` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:07:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:07:38` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:07:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T19:07:39` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-12T19:07:50` `chat` / `qwen3-32b` input=3149 output=422 total=3571 source=`ragent.llm.openai.openai_complete_if_cache`
