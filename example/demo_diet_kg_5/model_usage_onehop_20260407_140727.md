# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T14:07:03`
- Ended at: `2026-04-07T14:07:27`
- Metadata:
  - `query`: `今天油24g、盐4.8g、添加糖22g、酒精18g，先戒哪个？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5761 | 584 | 6345 | 0 |
| embedding | 4 | 74 | 0 | 74 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 5835 | 584 | 6419 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5761 | 584 | 6345 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 74 | 0 | 74 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T14:07:04` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T14:07:05` `chat` / `qwen3-32b` input=898 output=44 total=942 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T14:07:05` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T14:07:06` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T14:07:06` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T14:07:06` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T14:07:27` `chat` / `qwen3-32b` input=4863 output=540 total=5403 source=`ragent.llm.openai.openai_complete_if_cache`
