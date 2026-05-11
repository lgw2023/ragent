# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-10T11:34:07`
- Ended at: `2026-04-10T11:34:20`
- Metadata:
  - `query`: `之前16+8瘦了4斤，但是月经量变少，恢复三餐后反弹8斤`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4066 | 440 | 4506 | 0 |
| embedding | 12 | 94 | 0 | 94 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4160 | 440 | 4600 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4066 | 440 | 4506 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 94 | 0 | 94 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-10T11:34:07` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
2. `2026-04-10T11:34:09` `chat` / `qwen3-32b` input=895 output=60 total=955 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
6. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
7. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
8. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
10. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-10T11:34:10` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
14. `2026-04-10T11:34:11` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-10T11:34:20` `chat` / `qwen3-32b` input=3171 output=380 total=3551 source=`ragent.llm.openai.openai_complete_if_cache`
