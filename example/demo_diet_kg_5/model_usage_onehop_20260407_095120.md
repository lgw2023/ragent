# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T09:50:39`
- Ended at: `2026-04-07T09:51:20`
- Metadata:
  - `query`: `我有点胖，现在90kg， 想 6 个月减到 75kg，会不会太猛？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 6789 | 945 | 7734 | 0 |
| embedding | 4 | 68 | 0 | 68 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 6857 | 945 | 7802 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 6789 | 945 | 7734 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 68 | 0 | 68 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T09:50:40` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T09:50:40` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
3. `2026-04-07T09:50:40` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T09:50:41` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T09:50:41` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
6. `2026-04-07T09:51:05` `chat` / `qwen3-32b` input=5872 output=483 total=6355 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-04-07T09:51:19` `chat` / `qwen3-32b` input=917 output=462 total=1379 source=`ragent.llm.openai.openai_complete_if_cache`
