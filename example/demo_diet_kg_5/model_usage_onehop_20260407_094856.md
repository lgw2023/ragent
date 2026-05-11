# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T09:48:19`
- Ended at: `2026-04-07T09:48:56`
- Metadata:
  - `query`: `35 岁男 170cm/86kg/腰围95，3 次血压 146/92、144/90、148/94，一天 2250 千卡减到 1750 够吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5022 | 909 | 5931 | 0 |
| embedding | 4 | 145 | 0 | 145 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 5167 | 909 | 6076 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5022 | 909 | 5931 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 145 | 0 | 145 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T09:48:19` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T09:48:20` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
3. `2026-04-07T09:48:20` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T09:48:20` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T09:48:21` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
6. `2026-04-07T09:48:43` `chat` / `qwen3-32b` input=4109 output=479 total=4588 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-04-07T09:48:55` `chat` / `qwen3-32b` input=913 output=430 total=1343 source=`ragent.llm.openai.openai_complete_if_cache`
