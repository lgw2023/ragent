# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:27:21`
- Ended at: `2026-04-12T00:27:36`
- Metadata:
  - `query`: `我正在减肥，想知道晚上那顿饭怎么搭配更合适：有没有一种比较均衡、适合晚餐的吃法，同时还能兼顾控制热量？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4859 | 521 | 5380 | 0 |
| embedding | 10 | 74 | 0 | 74 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 4933 | 521 | 5454 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4859 | 521 | 5380 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 10 | 74 | 0 | 74 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:27:22` `embedding` / `text-embedding-v3` input=32 output=0 total=32 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:27:23` `chat` / `qwen3-32b` input=902 output=41 total=943 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:27:23` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:27:23` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:27:23` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:27:23` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:27:24` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:27:24` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:27:24` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:27:24` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:27:24` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T00:27:26` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-12T00:27:36` `chat` / `qwen3-32b` input=3957 output=480 total=4437 source=`ragent.llm.openai.openai_complete_if_cache`
