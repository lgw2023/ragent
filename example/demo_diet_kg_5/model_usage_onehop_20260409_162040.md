# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T16:20:24`
- Ended at: `2026-04-09T16:20:40`
- Metadata:
  - `query`: `酱油16g+鸡精5g，再额外放2g盐，如果全摄入的话，这一天是不是已经超了？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 1 | 2993 | 485 | 3478 | 0 |
| embedding | 9 | 74 | 0 | 74 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 3067 | 485 | 3552 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 1 | 2993 | 485 | 3478 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 74 | 0 | 74 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T16:20:24` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T16:20:24` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
3. `2026-04-09T16:20:25` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T16:20:25` `embedding` / `text-embedding-v3` input=9 output=0 total=9 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T16:20:25` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T16:20:25` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T16:20:25` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T16:20:25` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T16:20:25` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T16:20:26` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-09T16:20:39` `chat` / `qwen3-32b` input=2993 output=485 total=3478 source=`ragent.llm.openai.openai_complete_if_cache`
