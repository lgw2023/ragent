# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T12:40:27`
- Ended at: `2026-04-09T12:40:37`
- Metadata:
  - `query`: `如果你想按国标挑更完整、碎得没那么厉害的大米，在同一批试样里看到一粒米长度已经小于完整米粒平均长度的四分之三，但它还能留在直径 2.0 mm 的圆孔筛上，那么这粒米应归为“大碎米”还是普通“碎米”？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3288 | 266 | 3554 | 0 |
| embedding | 12 | 144 | 0 | 144 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 3432 | 266 | 3698 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3288 | 266 | 3554 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 144 | 0 | 144 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T12:40:27` `embedding` / `text-embedding-v3` input=76 output=0 total=76 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T12:40:29` `chat` / `qwen3-32b` input=944 output=57 total=1001 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=28 output=0 total=28 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T12:40:30` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T12:40:31` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-09T12:40:36` `chat` / `qwen3-32b` input=2344 output=209 total=2553 source=`ragent.llm.openai.openai_complete_if_cache`
