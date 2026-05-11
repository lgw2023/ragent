# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:01:14`
- Ended at: `2026-04-12T19:01:30`
- Metadata:
  - `query`: `我想在控制体重的时候，晚上吃点东西，什么样的蔬果更适合当作加餐？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5317 | 337 | 5654 | 0 |
| embedding | 9 | 56 | 0 | 56 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 5373 | 337 | 5710 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5317 | 337 | 5654 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 56 | 0 | 56 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:01:14` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:01:15` `chat` / `qwen3-32b` input=891 output=40 total=931 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:01:16` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:01:16` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:01:16` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:01:16` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:01:16` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:01:16` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:01:16` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:01:16` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:01:17` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T19:01:30` `chat` / `qwen3-32b` input=4426 output=297 total=4723 source=`ragent.llm.openai.openai_complete_if_cache`
