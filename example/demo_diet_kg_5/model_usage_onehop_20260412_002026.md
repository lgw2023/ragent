# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:20:14`
- Ended at: `2026-04-12T00:20:26`
- Metadata:
  - `query`: `减脂期每天吃水果，建议控制在多少克比较合适？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4273 | 216 | 4489 | 0 |
| embedding | 8 | 49 | 0 | 49 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 4322 | 216 | 4538 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4273 | 216 | 4489 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 8 | 49 | 0 | 49 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:20:14` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:20:17` `chat` / `qwen3-32b` input=886 output=35 total=921 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:20:17` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:20:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:20:17` `embedding` / `text-embedding-v3` input=7 output=0 total=7 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:20:18` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:20:18` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:20:18` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:20:18` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:20:20` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-12T00:20:26` `chat` / `qwen3-32b` input=3387 output=181 total=3568 source=`ragent.llm.openai.openai_complete_if_cache`
