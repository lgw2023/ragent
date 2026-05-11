# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-10T11:32:43`
- Ended at: `2026-04-10T11:33:05`
- Metadata:
  - `query`: `用碳水多少克蛋白质多少克脂肪多少克的方式来列出`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4292 | 643 | 4935 | 0 |
| embedding | 8 | 43 | 0 | 43 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 4335 | 643 | 4978 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4292 | 643 | 4935 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 8 | 43 | 0 | 43 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-10T11:32:44` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
2. `2026-04-10T11:32:45` `chat` / `qwen3-32b` input=885 output=33 total=918 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-10T11:32:45` `embedding` / `text-embedding-v3` input=9 output=0 total=9 source=`ragent.llm.openai.openai_embed`
4. `2026-04-10T11:32:45` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-10T11:32:46` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-10T11:32:46` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-10T11:32:46` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-10T11:32:46` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-10T11:32:46` `embedding` / `text-embedding-v3` input=8 output=0 total=8 source=`ragent.llm.openai.openai_embed`
10. `2026-04-10T11:32:47` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-10T11:33:04` `chat` / `qwen3-32b` input=3407 output=610 total=4017 source=`ragent.llm.openai.openai_complete_if_cache`
