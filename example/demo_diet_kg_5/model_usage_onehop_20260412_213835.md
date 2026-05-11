# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:38:23`
- Ended at: `2026-04-12T21:38:35`
- Metadata:
  - `query`: `如果成年人每天总能量消耗里，基础代谢大约占60%到70%，身体活动只占15%到30%，食物热效应占5%到10%，那一个平时活动很少、总是久坐的人，即使吃得不多，体重还是很难下降，最可能是因为哪一部分消耗太少了？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4394 | 267 | 4661 | 0 |
| embedding | 11 | 118 | 0 | 118 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 4512 | 267 | 4779 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4394 | 267 | 4661 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 118 | 0 | 118 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:38:23` `embedding` / `text-embedding-v3` input=62 output=0 total=62 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:38:25` `chat` / `qwen3-32b` input=939 output=50 total=989 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:38:25` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:38:26` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T21:38:35` `chat` / `qwen3-32b` input=3455 output=217 total=3672 source=`ragent.llm.openai.openai_complete_if_cache`
