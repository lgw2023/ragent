# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T16:15:33`
- Ended at: `2026-04-07T16:15:41`
- Metadata:
  - `query`: `中速走 能量消耗`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3808 | 178 | 3986 | 0 |
| embedding | 3 | 20 | 0 | 20 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 6 | 3828 | 178 | 4006 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3808 | 178 | 3986 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 3 | 20 | 0 | 20 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T16:15:34` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T16:15:35` `chat` / `qwen3-32b` input=878 output=31 total=909 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T16:15:36` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T16:15:36` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T16:15:37` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
6. `2026-04-07T16:15:40` `chat` / `qwen3-32b` input=2930 output=147 total=3077 source=`ragent.llm.openai.openai_complete_if_cache`
