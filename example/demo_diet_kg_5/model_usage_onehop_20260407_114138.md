# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T11:41:16`
- Ended at: `2026-04-07T11:41:38`
- Metadata:
  - `query`: `35 岁男 170cm/86kg/腰围95，3 次血压 146/92、144/90、148/94，一天 2250 千卡减到 1750 够吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 1 | 4144 | 572 | 4716 | 0 |
| embedding | 4 | 145 | 0 | 145 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 6 | 4289 | 572 | 4861 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 1 | 4144 | 572 | 4716 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 145 | 0 | 145 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T11:41:16` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T11:41:17` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
3. `2026-04-07T11:41:17` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T11:41:17` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T11:41:18` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
6. `2026-04-07T11:41:38` `chat` / `qwen3-32b` input=4144 output=572 total=4716 source=`ragent.llm.openai.openai_complete_if_cache`
