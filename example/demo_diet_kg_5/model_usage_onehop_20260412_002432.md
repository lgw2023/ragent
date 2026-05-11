# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:23:57`
- Ended at: `2026-04-12T00:24:32`
- Metadata:
  - `query`: `和精制米饭相比，吃全谷物或杂豆类通常有什么区别？如果更关注控制热量和提高膳食质量，哪种更适合日常作为主食的一部分？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3634 | 798 | 4432 | 0 |
| embedding | 12 | 115 | 0 | 115 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 3749 | 798 | 4547 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3634 | 798 | 4432 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 115 | 0 | 115 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:23:57` `embedding` / `text-embedding-v3` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:23:59` `chat` / `qwen3-32b` input=906 output=62 total=968 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:23:59` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:23:59` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:23:59` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:23:59` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:23:59` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:24:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:24:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:24:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:24:00` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T00:24:00` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T00:24:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T00:24:04` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-12T00:24:32` `chat` / `qwen3-32b` input=2728 output=736 total=3464 source=`ragent.llm.openai.openai_complete_if_cache`
