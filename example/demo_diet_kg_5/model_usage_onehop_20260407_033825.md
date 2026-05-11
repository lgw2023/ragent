# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T03:38:09`
- Ended at: `2026-04-07T03:38:25`
- Metadata:
  - `query`: `酱油16g+鸡精5g，再额外放2g盐，如果全摄入的话，这一天是不是已经超了？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 3 | 5615 | 1086 | 6701 | 0 |
| embedding | 4 | 102 | 0 | 102 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 8 | 5717 | 1086 | 6803 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3.5-flash | 3 | 5615 | 1086 | 6701 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 102 | 0 | 102 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T03:38:09` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T03:38:11` `chat` / `qwen3.5-flash` input=486 output=60 total=546 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T03:38:11` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T03:38:12` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T03:38:12` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T03:38:12` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T03:38:19` `chat` / `qwen3.5-flash` input=4024 output=659 total=4683 source=`ragent.llm.openai.openai_complete_if_cache`
8. `2026-04-07T03:38:25` `chat` / `qwen3.5-flash` input=1105 output=367 total=1472 source=`ragent.llm.openai.openai_complete_if_cache`
