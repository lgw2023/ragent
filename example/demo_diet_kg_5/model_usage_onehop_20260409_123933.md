# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T12:39:25`
- Ended at: `2026-04-09T12:39:33`
- Metadata:
  - `query`: `如果你在控制体脂、想把饮食能量中脂肪占比控制得更合理，依据图中信息，2015—2017年我国居民平均脂肪供能比是多少？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5008 | 161 | 5169 | 0 |
| embedding | 10 | 90 | 0 | 90 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 5098 | 161 | 5259 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5008 | 161 | 5169 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 10 | 90 | 0 | 90 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T12:39:25` `embedding` / `text-embedding-v3` input=36 output=0 total=36 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T12:39:27` `chat` / `qwen3-32b` input=914 output=57 total=971 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T12:39:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T12:39:27` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T12:39:27` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T12:39:28` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T12:39:28` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T12:39:28` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T12:39:28` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T12:39:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T12:39:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T12:39:29` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-09T12:39:32` `chat` / `qwen3-32b` input=4094 output=104 total=4198 source=`ragent.llm.openai.openai_complete_if_cache`
