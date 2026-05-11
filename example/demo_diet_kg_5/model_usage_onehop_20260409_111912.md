# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T11:19:00`
- Ended at: `2026-04-09T11:19:12`
- Metadata:
  - `query`: `同样参考高血压食养指南的示例食谱，华东地区和西南地区在全天盐的建议上有什么共同点？哪一地区的部分食谱更明确使用了富钾盐而不是低钠盐？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4184 | 293 | 4477 | 0 |
| embedding | 12 | 125 | 0 | 125 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4309 | 293 | 4602 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4184 | 293 | 4477 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 125 | 0 | 125 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T11:19:00` `embedding` / `text-embedding-v3` input=49 output=0 total=49 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T11:19:04` `chat` / `qwen3-32b` input=917 output=57 total=974 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T11:19:04` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T11:19:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T11:19:04` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T11:19:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T11:19:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T11:19:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T11:19:05` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T11:19:05` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T11:19:05` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T11:19:05` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T11:19:05` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T11:19:05` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-09T11:19:11` `chat` / `qwen3-32b` input=3267 output=236 total=3503 source=`ragent.llm.openai.openai_complete_if_cache`
