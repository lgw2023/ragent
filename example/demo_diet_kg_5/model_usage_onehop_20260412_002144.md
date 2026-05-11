# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:21:17`
- Ended at: `2026-04-12T00:21:44`
- Metadata:
  - `query`: `想安全减重并保持健康体重，日常最关键的做法是什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3969 | 605 | 4574 | 0 |
| embedding | 9 | 55 | 0 | 55 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4024 | 605 | 4629 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3969 | 605 | 4574 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 55 | 0 | 55 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:21:17` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:21:19` `chat` / `qwen3-32b` input=886 output=41 total=927 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:21:19` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:21:19` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:21:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:21:19` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:21:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:21:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:21:20` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:21:20` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:21:23` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T00:21:43` `chat` / `qwen3-32b` input=3083 output=564 total=3647 source=`ragent.llm.openai.openai_complete_if_cache`
