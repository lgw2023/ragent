# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:30:02`
- Ended at: `2026-04-12T00:30:14`
- Metadata:
  - `query`: `我在控制体重、想少吃高热量食物的时候，水果每天大概吃多少比较合适？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4478 | 324 | 4802 | 0 |
| embedding | 8 | 53 | 0 | 53 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 4531 | 324 | 4855 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4478 | 324 | 4802 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 8 | 53 | 0 | 53 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:30:02` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:30:03` `chat` / `qwen3-32b` input=891 output=34 total=925 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:30:04` `embedding` / `text-embedding-v3` input=7 output=0 total=7 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:30:04` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:30:04` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:30:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:30:04` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:30:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:30:04` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:30:06` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-12T00:30:13` `chat` / `qwen3-32b` input=3587 output=290 total=3877 source=`ragent.llm.openai.openai_complete_if_cache`
