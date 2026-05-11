# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:29:25`
- Ended at: `2026-04-12T00:29:50`
- Metadata:
  - `query`: `我血压偏高，想通过饮食管理的话，日常应该多吃哪些食物、少吃哪些食物？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4481 | 608 | 5089 | 0 |
| embedding | 10 | 65 | 0 | 65 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 4546 | 608 | 5154 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4481 | 608 | 5089 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 10 | 65 | 0 | 65 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:29:26` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:29:27` `chat` / `qwen3-32b` input=892 output=40 total=932 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:29:27` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:29:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:29:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:29:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:29:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:29:28` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:29:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:29:28` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:29:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T00:29:30` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-12T00:29:50` `chat` / `qwen3-32b` input=3589 output=568 total=4157 source=`ragent.llm.openai.openai_complete_if_cache`
