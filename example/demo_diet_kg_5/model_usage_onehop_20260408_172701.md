# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-08T17:26:40`
- Ended at: `2026-04-08T17:27:01`
- Metadata:
  - `query`: `喝浓茶能解酒吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3998 | 191 | 4189 | 0 |
| embedding | 8 | 38 | 0 | 38 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 4036 | 191 | 4227 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3998 | 191 | 4189 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 8 | 38 | 0 | 38 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-08T17:26:43` `embedding` / `text-embedding-v3` input=8 output=0 total=8 source=`ragent.llm.openai.openai_embed`
2. `2026-04-08T17:26:46` `chat` / `qwen3-32b` input=880 output=34 total=914 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-08T17:26:48` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
4. `2026-04-08T17:26:49` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-08T17:26:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-08T17:26:51` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-08T17:26:51` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-08T17:26:51` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-08T17:26:52` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
10. `2026-04-08T17:26:55` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-08T17:27:01` `chat` / `qwen3-32b` input=3118 output=157 total=3275 source=`ragent.llm.openai.openai_complete_if_cache`
