# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:50:14`
- Ended at: `2026-04-12T21:50:46`
- Metadata:
  - `query`: `我想减脂又怕饿，能不能帮我搭一个一天两顿的吃法示例：早餐和晚餐各怎么安排更合适？最好能兼顾控制总能量、食物多样一点，而且晚餐里可以适当加一点坚果；如果我体重偏高，还要注意什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3957 | 1013 | 4970 | 0 |
| embedding | 13 | 119 | 0 | 119 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 4076 | 1013 | 5089 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3957 | 1013 | 4970 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 119 | 0 | 119 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:50:14` `embedding` / `text-embedding-v3` input=61 output=0 total=61 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:50:16` `chat` / `qwen3-32b` input=931 output=53 total=984 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:50:16` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:50:16` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:50:16` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:50:16` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:50:16` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:50:16` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:50:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:50:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:50:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:50:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:50:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:50:17` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:50:18` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-12T21:50:46` `chat` / `qwen3-32b` input=3026 output=960 total=3986 source=`ragent.llm.openai.openai_complete_if_cache`
