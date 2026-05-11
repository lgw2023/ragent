# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T15:22:36`
- Ended at: `2026-04-12T15:22:49`
- Metadata:
  - `query`: `如果我有高血压，想把饮食安排得更适合控制血压，那么在“减钠增钾”和“合理膳食”这两种做法里，哪一种更直接体现为每天少放盐、同时多吃富钾食物？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3677 | 270 | 3947 | 0 |
| embedding | 11 | 111 | 0 | 111 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 3788 | 270 | 4058 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3677 | 270 | 3947 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 111 | 0 | 111 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T15:22:36` `embedding` / `text-embedding-v3` input=53 output=0 total=53 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T15:22:38` `chat` / `qwen3-32b` input=918 output=48 total=966 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T15:22:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T15:22:39` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T15:22:49` `chat` / `qwen3-32b` input=2759 output=222 total=2981 source=`ragent.llm.openai.openai_complete_if_cache`
