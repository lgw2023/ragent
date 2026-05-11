# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T14:07:38`
- Ended at: `2026-04-07T14:07:57`
- Metadata:
  - `query`: `谷类240g其中全谷杂豆60g、薯类80g、蔬菜360g里深色150g、水果250g，肥胖及高血压并症患者这样吃达标吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 6780 | 605 | 7385 | 0 |
| embedding | 4 | 140 | 0 | 140 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 6920 | 605 | 7525 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 6780 | 605 | 7385 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 140 | 0 | 140 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T14:07:39` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T14:07:41` `chat` / `qwen3-32b` input=923 output=63 total=986 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T14:07:41` `embedding` / `text-embedding-v3` input=31 output=0 total=31 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T14:07:42` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T14:07:42` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T14:07:42` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T14:07:57` `chat` / `qwen3-32b` input=5857 output=542 total=6399 source=`ragent.llm.openai.openai_complete_if_cache`
