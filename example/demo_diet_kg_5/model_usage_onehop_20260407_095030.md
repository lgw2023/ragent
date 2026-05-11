# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T09:49:48`
- Ended at: `2026-04-07T09:50:30`
- Metadata:
  - `query`: `谷类240g其中全谷杂豆60g、薯类80g、蔬菜360g里深色150g、水果250g，肥胖及高血压并症患者这样吃达标吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 6872 | 1210 | 8082 | 0 |
| embedding | 4 | 157 | 0 | 157 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 7029 | 1210 | 8239 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 6872 | 1210 | 8082 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 157 | 0 | 157 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T09:49:48` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T09:49:48` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
3. `2026-04-07T09:49:49` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T09:49:49` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T09:49:50` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
6. `2026-04-07T09:50:12` `chat` / `qwen3-32b` input=5721 output=718 total=6439 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-04-07T09:50:29` `chat` / `qwen3-32b` input=1151 output=492 total=1643 source=`ragent.llm.openai.openai_complete_if_cache`
