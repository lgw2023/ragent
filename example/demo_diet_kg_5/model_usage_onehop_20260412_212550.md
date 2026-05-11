# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:25:42`
- Ended at: `2026-04-12T21:25:50`
- Metadata:
  - `query`: `如果想通过日常饮食控制体重，水果每天大概吃多少比较合适？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4028 | 205 | 4233 | 0 |
| embedding | 8 | 45 | 0 | 45 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 4073 | 205 | 4278 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4028 | 205 | 4233 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 8 | 45 | 0 | 45 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:25:42` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:25:43` `chat` / `qwen3-32b` input=886 output=34 total=920 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:25:44` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:25:44` `embedding` / `text-embedding-v3` input=7 output=0 total=7 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:25:44` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:25:44` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:25:44` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:25:44` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:25:44` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:25:45` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-12T21:25:50` `chat` / `qwen3-32b` input=3142 output=171 total=3313 source=`ragent.llm.openai.openai_complete_if_cache`
