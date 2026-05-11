# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T16:03:22`
- Ended at: `2026-04-07T16:03:37`
- Metadata:
  - `query`: `下午多吃了 150 千卡点心，先 中速走 30 分钟，再爬楼多久能补回来？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 2752 | 328 | 3080 | 0 |
| embedding | 3 | 57 | 0 | 57 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 6 | 2809 | 328 | 3137 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 2752 | 328 | 3080 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 3 | 57 | 0 | 57 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T16:03:22` `embedding` / `text-embedding-v3` input=27 output=0 total=27 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T16:03:25` `chat` / `qwen3-32b` input=901 output=47 total=948 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T16:03:26` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T16:03:26` `embedding` / `text-embedding-v3` input=10 output=0 total=10 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T16:03:26` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
6. `2026-04-07T16:03:36` `chat` / `qwen3-32b` input=1851 output=281 total=2132 source=`ragent.llm.openai.openai_complete_if_cache`
