# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:06:11`
- Ended at: `2026-04-12T19:06:29`
- Metadata:
  - `query`: `我现在体重偏高，又有高血压，平时已经吃得很少但体重还是不怎么下降，这种情况最可能是哪些因素在起作用？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4044 | 516 | 4560 | 0 |
| embedding | 12 | 93 | 0 | 93 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4137 | 516 | 4653 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4044 | 516 | 4560 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 93 | 0 | 93 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:06:12` `embedding` / `text-embedding-v3` input=31 output=0 total=31 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:06:13` `chat` / `qwen3-32b` input=900 output=50 total=950 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:06:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:06:14` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:06:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:06:14` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:06:14` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:06:14` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:06:14` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:06:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:06:14` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T19:06:15` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T19:06:15` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T19:06:16` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-12T19:06:29` `chat` / `qwen3-32b` input=3144 output=466 total=3610 source=`ragent.llm.openai.openai_complete_if_cache`
