# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T22:48:18`
- Ended at: `2026-04-11T22:48:32`
- Metadata:
  - `query`: `如果我平时每天只想喝一份奶制品，下面哪种搭配更接近每天约300毫升液态奶的量：1盒200毫升纯牛奶再加1杯100毫升酸奶，还是1盒200毫升纯牛奶再加1片奶酪？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4179 | 356 | 4535 | 0 |
| embedding | 12 | 115 | 0 | 115 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4294 | 356 | 4650 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4179 | 356 | 4535 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 115 | 0 | 115 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T22:48:18` `embedding` / `text-embedding-v3` input=57 output=0 total=57 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T22:48:21` `chat` / `qwen3-32b` input=931 output=56 total=987 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T22:48:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T22:48:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T22:48:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T22:48:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T22:48:21` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T22:48:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T22:48:22` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T22:48:22` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T22:48:22` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T22:48:22` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T22:48:22` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T22:48:22` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-11T22:48:31` `chat` / `qwen3-32b` input=3248 output=300 total=3548 source=`ragent.llm.openai.openai_complete_if_cache`
