# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:37:04`
- Ended at: `2026-04-12T21:37:13`
- Metadata:
  - `query`: `减脂期如果想把豆腐干当作补充蛋白质的零食，哪一种豆腐干的蛋白质含量最高？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3895 | 225 | 4120 | 0 |
| embedding | 9 | 66 | 0 | 66 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 3961 | 225 | 4186 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3895 | 225 | 4120 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 66 | 0 | 66 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:37:05` `embedding` / `text-embedding-v3` input=26 output=0 total=26 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:37:06` `chat` / `qwen3-32b` input=894 output=39 total=933 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:37:06` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:37:07` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:37:07` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:37:07` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:37:07` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:37:07` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:37:07` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:37:07` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:37:07` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T21:37:12` `chat` / `qwen3-32b` input=3001 output=186 total=3187 source=`ragent.llm.openai.openai_complete_if_cache`
