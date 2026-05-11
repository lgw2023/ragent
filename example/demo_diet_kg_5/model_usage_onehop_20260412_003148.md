# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:31:41`
- Ended at: `2026-04-12T00:31:48`
- Metadata:
  - `query`: `测垩白度时，通常要取多少克样品？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3198 | 132 | 3330 | 0 |
| embedding | 8 | 50 | 0 | 50 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 3248 | 132 | 3380 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3198 | 132 | 3330 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 8 | 50 | 0 | 50 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:31:42` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:31:43` `chat` / `qwen3-32b` input=884 output=37 total=921 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:31:44` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:31:44` `embedding` / `text-embedding-v3` input=8 output=0 total=8 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:31:44` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:31:44` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:31:44` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:31:44` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:31:44` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:31:45` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-12T00:31:48` `chat` / `qwen3-32b` input=2314 output=95 total=2409 source=`ragent.llm.openai.openai_complete_if_cache`
