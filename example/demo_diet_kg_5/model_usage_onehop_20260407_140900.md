# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T14:08:44`
- Ended at: `2026-04-07T14:09:00`
- Metadata:
  - `query`: `酱油16g+鸡精5g，再额外放2g盐，如果全摄入的话，这一天是不是已经超了？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5536 | 402 | 5938 | 0 |
| embedding | 4 | 86 | 0 | 86 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 5622 | 402 | 6024 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5536 | 402 | 5938 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 86 | 0 | 86 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T14:08:44` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T14:08:46` `chat` / `qwen3-32b` input=901 output=40 total=941 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T14:08:46` `embedding` / `text-embedding-v3` input=9 output=0 total=9 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T14:08:47` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T14:08:47` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T14:08:47` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T14:08:59` `chat` / `qwen3-32b` input=4635 output=362 total=4997 source=`ragent.llm.openai.openai_complete_if_cache`
