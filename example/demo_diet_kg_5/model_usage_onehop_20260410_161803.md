# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-10T16:17:45`
- Ended at: `2026-04-10T16:18:03`
- Metadata:
  - `query`: `晚饭不吃或者是只吃水果和蔬菜，能不能减肥`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 1 | 3746 | 448 | 4194 | 0 |
| embedding | 9 | 45 | 0 | 45 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 3791 | 448 | 4239 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 1 | 3746 | 448 | 4194 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 45 | 0 | 45 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-10T16:17:45` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
2. `2026-04-10T16:17:45` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
3. `2026-04-10T16:17:45` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-10T16:17:45` `embedding` / `text-embedding-v3` input=8 output=0 total=8 source=`ragent.llm.openai.openai_embed`
5. `2026-04-10T16:17:45` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-10T16:17:46` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-10T16:17:46` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-10T16:17:46` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-10T16:17:46` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
10. `2026-04-10T16:17:46` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-10T16:18:02` `chat` / `qwen3-32b` input=3746 output=448 total=4194 source=`ragent.llm.openai.openai_complete_if_cache`
