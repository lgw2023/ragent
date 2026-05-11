# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-08T19:26:39`
- Ended at: `2026-04-08T19:27:06`
- Metadata:
  - `query`: `一个 90kg 的成年人，如果按指南把 6 个月减重目标先定在当前体重的 5%～10%，那第一阶段应该先减多少公斤、体重大约到多少？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3856 | 232 | 4088 | 0 |
| embedding | 11 | 85 | 0 | 85 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 3941 | 232 | 4173 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3856 | 232 | 4088 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 85 | 0 | 85 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-08T19:26:41` `embedding` / `text-embedding-v3` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
2. `2026-04-08T19:26:43` `chat` / `qwen3-32b` input=918 output=52 total=970 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-08T19:26:48` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-08T19:26:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-08T19:26:49` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-08T19:26:50` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
7. `2026-04-08T19:26:50` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-08T19:26:51` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-08T19:26:53` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
10. `2026-04-08T19:26:54` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-08T19:26:54` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-08T19:26:56` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-08T19:26:59` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-08T19:27:06` `chat` / `qwen3-32b` input=2938 output=180 total=3118 source=`ragent.llm.openai.openai_complete_if_cache`
