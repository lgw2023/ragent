# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:28:51`
- Ended at: `2026-04-12T21:29:02`
- Metadata:
  - `query`: `我最近打算戒烟、戒酒并调整饮食，但还是查出痛风了。按这种情况看，除了酒以外，平时摄入的哪一类食物也可能和痛风更相关，需要特别少吃？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3836 | 390 | 4226 | 0 |
| embedding | 12 | 109 | 0 | 109 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 3945 | 390 | 4335 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3836 | 390 | 4226 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 109 | 0 | 109 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:28:51` `embedding` / `text-embedding-v3` input=47 output=0 total=47 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:28:53` `chat` / `qwen3-32b` input=916 output=53 total=969 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:28:53` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:28:53` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:28:53` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:28:53` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:28:53` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:28:53` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:28:54` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:28:54` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:28:54` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:28:54` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:28:54` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:28:54` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-12T21:29:02` `chat` / `qwen3-32b` input=2920 output=337 total=3257 source=`ragent.llm.openai.openai_complete_if_cache`
