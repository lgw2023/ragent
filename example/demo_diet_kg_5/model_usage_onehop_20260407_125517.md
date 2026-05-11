# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T12:55:01`
- Ended at: `2026-04-07T12:55:17`
- Metadata:
  - `query`: `谷类240g其中全谷杂豆60g、薯类80g、蔬菜360g里深色150g、水果250g，肥胖及高血压并症患者这样吃达标吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 1 | 5448 | 496 | 5944 | 0 |
| embedding | 4 | 157 | 0 | 157 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 6 | 5605 | 496 | 6101 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 1 | 5448 | 496 | 5944 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 157 | 0 | 157 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T12:55:01` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T12:55:02` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
3. `2026-04-07T12:55:02` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T12:55:02` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T12:55:03` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
6. `2026-04-07T12:55:16` `chat` / `qwen3-32b` input=5448 output=496 total=5944 source=`ragent.llm.openai.openai_complete_if_cache`
