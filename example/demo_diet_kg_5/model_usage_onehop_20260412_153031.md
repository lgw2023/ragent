# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T15:30:21`
- Ended at: `2026-04-12T15:30:31`
- Metadata:
  - `query`: `我有点肥胖，还合并高血压，平时想靠饮食调理控制体重和血压。像这种情况，能不能直接用食养来辅助管理？如果本身还有其他慢性病或并发症，是不是就不能照搬普通建议了，需要更个性化地安排？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4176 | 307 | 4483 | 0 |
| embedding | 12 | 122 | 0 | 122 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4298 | 307 | 4605 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4176 | 307 | 4483 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 122 | 0 | 122 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T15:30:21` `embedding` / `text-embedding-v3` input=60 output=0 total=60 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T15:30:22` `chat` / `qwen3-32b` input=924 output=49 total=973 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T15:30:23` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T15:30:24` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-12T15:30:31` `chat` / `qwen3-32b` input=3252 output=258 total=3510 source=`ragent.llm.openai.openai_complete_if_cache`
