# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T03:36:34`
- Ended at: `2026-04-07T03:36:51`
- Metadata:
  - `query`: `35 岁男 170cm/86kg/腰围95，3 次血压 146/92、144/90、148/94，一天 2250 千卡减到 1750 够吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 3 | 5821 | 1740 | 7561 | 0 |
| embedding | 4 | 145 | 0 | 145 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 8 | 5966 | 1740 | 7706 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3.5-flash | 3 | 5821 | 1740 | 7561 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 145 | 0 | 145 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T03:36:34` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T03:36:35` `chat` / `qwen3.5-flash` input=525 output=97 total=622 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T03:36:36` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T03:36:37` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T03:36:37` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T03:36:38` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T03:36:46` `chat` / `qwen3.5-flash` input=3998 output=852 total=4850 source=`ragent.llm.openai.openai_complete_if_cache`
8. `2026-04-07T03:36:50` `chat` / `qwen3.5-flash` input=1298 output=791 total=2089 source=`ragent.llm.openai.openai_complete_if_cache`
