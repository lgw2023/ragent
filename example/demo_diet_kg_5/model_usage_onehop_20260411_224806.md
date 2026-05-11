# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T22:47:57`
- Ended at: `2026-04-11T22:48:06`
- Metadata:
  - `query`: `在比较碎米含量检验和品尝评分值检验这两种方法时，哪一种需要先把长度不小于完整米粒平均长度四分之三的米粒拣出来，哪一种则要使用参照样品来进行评分？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3612 | 182 | 3794 | 0 |
| embedding | 10 | 118 | 0 | 118 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 3730 | 182 | 3912 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3612 | 182 | 3794 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 10 | 118 | 0 | 118 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T22:47:58` `embedding` / `text-embedding-v3` input=56 output=0 total=56 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T22:47:59` `chat` / `qwen3-32b` input=917 output=50 total=967 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T22:47:59` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T22:47:59` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T22:47:59` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T22:48:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T22:48:00` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T22:48:00` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T22:48:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T22:48:00` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T22:48:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T22:48:00` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-11T22:48:06` `chat` / `qwen3-32b` input=2695 output=132 total=2827 source=`ragent.llm.openai.openai_complete_if_cache`
