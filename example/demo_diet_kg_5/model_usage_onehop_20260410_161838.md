# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-10T16:18:14`
- Ended at: `2026-04-10T16:18:38`
- Metadata:
  - `query`: `减脂期可以吃什么水果`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4462 | 340 | 4802 | 0 |
| embedding | 8 | 39 | 0 | 39 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 4501 | 340 | 4841 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4462 | 340 | 4802 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 8 | 39 | 0 | 39 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-10T16:18:15` `embedding` / `text-embedding-v3` input=7 output=0 total=7 source=`ragent.llm.openai.openai_embed`
2. `2026-04-10T16:18:17` `chat` / `qwen3-32b` input=878 output=36 total=914 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-10T16:18:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-10T16:18:17` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
5. `2026-04-10T16:18:17` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-10T16:18:18` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
7. `2026-04-10T16:18:18` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-10T16:18:18` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-10T16:18:18` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-10T16:18:18` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-10T16:18:37` `chat` / `qwen3-32b` input=3584 output=304 total=3888 source=`ragent.llm.openai.openai_complete_if_cache`
