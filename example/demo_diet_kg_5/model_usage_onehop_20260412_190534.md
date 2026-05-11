# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:05:15`
- Ended at: `2026-04-12T19:05:34`
- Metadata:
  - `query`: `我想把饮食调整得更利于减重和控制血压，平时应该优先少吃哪类食物、每天烹调油和盐大概要控制到什么量？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4209 | 558 | 4767 | 0 |
| embedding | 11 | 95 | 0 | 95 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 4304 | 558 | 4862 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4209 | 558 | 4767 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 95 | 0 | 95 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:05:15` `embedding` / `text-embedding-v3` input=37 output=0 total=37 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:05:17` `chat` / `qwen3-32b` input=906 output=48 total=954 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:05:17` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:05:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:05:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:05:17` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:05:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:05:18` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:05:18` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:05:18` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:05:18` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T19:05:18` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T19:05:18` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T19:05:33` `chat` / `qwen3-32b` input=3303 output=510 total=3813 source=`ragent.llm.openai.openai_complete_if_cache`
