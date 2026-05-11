# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T09:51:32`
- Ended at: `2026-04-07T09:51:55`
- Metadata:
  - `query`: `酱油16g+鸡精5g，再额外放2g盐，如果全摄入的话，这一天是不是已经超了？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5005 | 581 | 5586 | 0 |
| embedding | 4 | 102 | 0 | 102 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 5107 | 581 | 5688 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5005 | 581 | 5586 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 102 | 0 | 102 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T09:51:32` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T09:51:32` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
3. `2026-04-07T09:51:33` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T09:51:33` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T09:51:33` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
6. `2026-04-07T09:51:46` `chat` / `qwen3-32b` input=4248 output=323 total=4571 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-04-07T09:51:54` `chat` / `qwen3-32b` input=757 output=258 total=1015 source=`ragent.llm.openai.openai_complete_if_cache`
