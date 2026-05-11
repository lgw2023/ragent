# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T15:24:14`
- Ended at: `2026-04-12T15:24:22`
- Metadata:
  - `query`: `按照这种均衡膳食建议，一天里动物性食物推荐摄入量的范围是多少克？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4571 | 195 | 4766 | 0 |
| embedding | 8 | 61 | 0 | 61 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 4632 | 195 | 4827 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4571 | 195 | 4766 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 8 | 61 | 0 | 61 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T15:24:14` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T15:24:16` `chat` / `qwen3-32b` input=892 output=38 total=930 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T15:24:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T15:24:17` `embedding` / `text-embedding-v3` input=9 output=0 total=9 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T15:24:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T15:24:17` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T15:24:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T15:24:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T15:24:17` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T15:24:17` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-12T15:24:22` `chat` / `qwen3-32b` input=3679 output=157 total=3836 source=`ragent.llm.openai.openai_complete_if_cache`
