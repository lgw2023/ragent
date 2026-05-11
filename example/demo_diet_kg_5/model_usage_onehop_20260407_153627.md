# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T15:36:05`
- Ended at: `2026-04-07T15:36:27`
- Metadata:
  - `query`: `35 岁男 170cm/86kg/腰围95，3 次血压 146/92、144/90、148/94，一天 2250 千卡减到 1750 够吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 1 | 4577 | 647 | 5224 | 0 |
| embedding | 3 | 76 | 0 | 76 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 5 | 4653 | 647 | 5300 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 1 | 4577 | 647 | 5224 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 3 | 76 | 0 | 76 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T15:36:05` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T15:36:05` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
3. `2026-04-07T15:36:06` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T15:36:06` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
5. `2026-04-07T15:36:26` `chat` / `qwen3-32b` input=4577 output=647 total=5224 source=`ragent.llm.openai.openai_complete_if_cache`
