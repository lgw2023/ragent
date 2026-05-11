# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T00:47:53`
- Ended at: `2026-04-11T00:48:06`
- Metadata:
  - `query`: `根据《成人肥胖食养指南（2024年版）》，如果一个人每天制造 500 千卡的热量缺口，按一个月（约 30 天）计算，大概可以减重多少千克？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4362 | 233 | 4595 | 0 |
| embedding | 9 | 93 | 0 | 93 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4455 | 233 | 4688 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4362 | 233 | 4595 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 93 | 0 | 93 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T00:47:54` `embedding` / `text-embedding-v3` input=45 output=0 total=45 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T00:47:56` `chat` / `qwen3-32b` input=922 output=42 total=964 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T00:47:56` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T00:47:56` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T00:47:56` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T00:47:56` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T00:47:56` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T00:47:56` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T00:47:56` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T00:47:56` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T00:47:57` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-11T00:48:06` `chat` / `qwen3-32b` input=3440 output=191 total=3631 source=`ragent.llm.openai.openai_complete_if_cache`
