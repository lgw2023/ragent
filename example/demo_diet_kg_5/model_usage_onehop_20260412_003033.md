# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:30:27`
- Ended at: `2026-04-12T00:30:33`
- Metadata:
  - `query`: `如果买的是预包装的非发酵豆制品，哪一类一般不需要低温贮存，但其他这类产品通常最好放在较低温度下销售？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3262 | 93 | 3355 | 0 |
| embedding | 9 | 83 | 0 | 83 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 3345 | 93 | 3438 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3262 | 93 | 3355 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 83 | 0 | 83 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:30:27` `embedding` / `text-embedding-v3` input=33 output=0 total=33 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:30:29` `chat` / `qwen3-32b` input=901 output=45 total=946 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:30:29` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:30:29` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:30:29` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:30:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:30:30` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:30:30` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:30:30` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:30:30` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:30:32` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T00:30:33` `chat` / `qwen3-32b` input=2361 output=48 total=2409 source=`ragent.llm.openai.openai_complete_if_cache`
