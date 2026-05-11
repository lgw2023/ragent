# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:39:49`
- Ended at: `2026-04-12T21:39:57`
- Metadata:
  - `query`: `一名14岁、身体活动水平较高的女性，日常大概需要多少千卡能量？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4052 | 178 | 4230 | 0 |
| embedding | 9 | 55 | 0 | 55 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4107 | 178 | 4285 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4052 | 178 | 4230 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 55 | 0 | 55 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:39:49` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:39:51` `chat` / `qwen3-32b` input=890 output=40 total=930 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:39:51` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:39:51` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:39:51` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:39:51` `embedding` / `text-embedding-v3` input=10 output=0 total=10 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:39:52` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:39:52` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:39:52` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:39:52` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:39:52` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T21:39:57` `chat` / `qwen3-32b` input=3162 output=138 total=3300 source=`ragent.llm.openai.openai_complete_if_cache`
