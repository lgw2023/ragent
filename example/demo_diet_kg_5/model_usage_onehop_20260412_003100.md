# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:30:47`
- Ended at: `2026-04-12T00:31:00`
- Metadata:
  - `query`: `一名成年人身高1.60米、体重51.5千克，BMI是多少？属于体重过低、体重正常还是超重？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4362 | 332 | 4694 | 0 |
| embedding | 11 | 72 | 0 | 72 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 4434 | 332 | 4766 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4362 | 332 | 4694 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 72 | 0 | 72 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:30:47` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:30:48` `chat` / `qwen3-32b` input=901 output=45 total=946 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T00:30:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T00:30:50` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T00:31:00` `chat` / `qwen3-32b` input=3461 output=287 total=3748 source=`ragent.llm.openai.openai_complete_if_cache`
