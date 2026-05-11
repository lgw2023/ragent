# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T14:08:08`
- Ended at: `2026-04-07T14:08:32`
- Metadata:
  - `query`: `我有点胖，现在90kg， 想 6 个月减到 75kg，会不会太猛？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 6641 | 461 | 7102 | 0 |
| embedding | 4 | 61 | 0 | 61 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 6702 | 461 | 7163 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 6641 | 461 | 7102 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 61 | 0 | 61 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T14:08:08` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T14:08:10` `chat` / `qwen3-32b` input=898 output=37 total=935 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T14:08:10` `embedding` / `text-embedding-v3` input=7 output=0 total=7 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T14:08:10` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T14:08:11` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T14:08:11` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T14:08:32` `chat` / `qwen3-32b` input=5743 output=424 total=6167 source=`ragent.llm.openai.openai_complete_if_cache`
