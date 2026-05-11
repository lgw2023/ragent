# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T11:19:52`
- Ended at: `2026-04-09T11:20:02`
- Metadata:
  - `query`: `你在减脂期想从非发酵豆制品里选一个更适合直接当低负担加餐的豆腐干：如果你更在意“有韧性、掰对角 90°不断”这种耐嚼口感，同时希望外观上薄厚均匀、块形完整，那么按标准更符合你偏好的具体类型是哪一种？还需要满足哪两项对应的感官描述？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4485 | 225 | 4710 | 0 |
| embedding | 14 | 181 | 0 | 181 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 4666 | 225 | 4891 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4485 | 225 | 4710 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 181 | 0 | 181 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T11:19:53` `embedding` / `text-embedding-v3` input=83 output=0 total=83 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T11:19:55` `chat` / `qwen3-32b` input=950 output=72 total=1022 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T11:19:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T11:19:55` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T11:19:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T11:19:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T11:19:55` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T11:19:55` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T11:19:55` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T11:19:56` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T11:19:56` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T11:19:56` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T11:19:56` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T11:19:56` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
15. `2026-04-09T11:19:56` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
16. `2026-04-09T11:19:56` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-09T11:20:02` `chat` / `qwen3-32b` input=3535 output=153 total=3688 source=`ragent.llm.openai.openai_complete_if_cache`
