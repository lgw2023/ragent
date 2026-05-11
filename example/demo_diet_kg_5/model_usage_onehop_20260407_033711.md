# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T03:36:59`
- Ended at: `2026-04-07T03:37:11`
- Metadata:
  - `query`: `今天油24g、盐4.8g、添加糖22g、酒精18g，先戒哪个？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 3 | 6312 | 1270 | 7582 | 0 |
| embedding | 4 | 85 | 0 | 85 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 8 | 6397 | 1270 | 7667 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3.5-flash | 3 | 6312 | 1270 | 7582 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 85 | 0 | 85 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T03:36:59` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T03:37:00` `chat` / `qwen3.5-flash` input=486 output=68 total=554 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T03:37:00` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T03:37:01` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T03:37:01` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T03:37:01` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T03:37:08` `chat` / `qwen3.5-flash` input=4660 output=720 total=5380 source=`ragent.llm.openai.openai_complete_if_cache`
8. `2026-04-07T03:37:11` `chat` / `qwen3.5-flash` input=1166 output=482 total=1648 source=`ragent.llm.openai.openai_complete_if_cache`
