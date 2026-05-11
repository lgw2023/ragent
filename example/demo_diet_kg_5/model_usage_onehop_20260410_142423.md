# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-10T14:24:06`
- Ended at: `2026-04-10T14:24:23`
- Metadata:
  - `query`: `晚饭不吃或者是只吃水果和蔬菜，能不能减肥`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4631 | 506 | 5137 | 0 |
| embedding | 9 | 45 | 0 | 45 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4676 | 506 | 5182 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4631 | 506 | 5137 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 45 | 0 | 45 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-10T14:24:06` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
2. `2026-04-10T14:24:08` `chat` / `qwen3-32b` input=885 output=36 total=921 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-10T14:24:08` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-10T14:24:08` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-10T14:24:08` `embedding` / `text-embedding-v3` input=8 output=0 total=8 source=`ragent.llm.openai.openai_embed`
6. `2026-04-10T14:24:08` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-10T14:24:08` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-10T14:24:08` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
9. `2026-04-10T14:24:08` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-10T14:24:08` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-10T14:24:09` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-10T14:24:22` `chat` / `qwen3-32b` input=3746 output=470 total=4216 source=`ragent.llm.openai.openai_complete_if_cache`
