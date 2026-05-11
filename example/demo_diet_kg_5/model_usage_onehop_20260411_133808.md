# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:38:01`
- Ended at: `2026-04-11T13:38:08`
- Metadata:
  - `query`: `按照表2里豆浆类产品的理化指标，纯豆浆和调味豆浆的蛋白质最低限值分别是多少 g/100g？两者的最低限值一共是多少？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3891 | 119 | 4010 | 0 |
| embedding | 11 | 102 | 0 | 102 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 3993 | 119 | 4112 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3891 | 119 | 4010 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 102 | 0 | 102 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:38:02` `embedding` / `text-embedding-v3` input=42 output=0 total=42 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:38:03` `chat` / `qwen3-32b` input=911 output=49 total=960 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T13:38:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T13:38:05` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-11T13:38:07` `chat` / `qwen3-32b` input=2980 output=70 total=3050 source=`ragent.llm.openai.openai_complete_if_cache`
