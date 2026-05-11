# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:08:40`
- Ended at: `2026-04-12T19:08:59`
- Metadata:
  - `query`: `我想减脂，晚上是不是最好少吃或者只吃水果、蔬菜？如果按健康饮食的原则，晚餐更适合怎么搭配？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4478 | 637 | 5115 | 0 |
| embedding | 9 | 56 | 0 | 56 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4534 | 637 | 5171 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4478 | 637 | 5115 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 56 | 0 | 56 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:08:41` `embedding` / `text-embedding-v3` input=28 output=0 total=28 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:08:42` `chat` / `qwen3-32b` input=898 output=36 total=934 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:08:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:08:43` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:08:43` `embedding` / `text-embedding-v3` input=8 output=0 total=8 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:08:43` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:08:43` `embedding` / `text-embedding-v3` input=10 output=0 total=10 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:08:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:08:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:08:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:08:44` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T19:08:59` `chat` / `qwen3-32b` input=3580 output=601 total=4181 source=`ragent.llm.openai.openai_complete_if_cache`
