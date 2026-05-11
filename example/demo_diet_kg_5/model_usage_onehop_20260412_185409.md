# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T18:53:53`
- Ended at: `2026-04-12T18:54:09`
- Metadata:
  - `query`: `我最近想靠运动减脂，但体重一直没什么变化。是不是说明只少吃还不够，还得配合像打网球这类日常身体活动，才能更好地控制体重？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4284 | 494 | 4778 | 0 |
| embedding | 12 | 90 | 0 | 90 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4374 | 494 | 4868 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4284 | 494 | 4778 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 90 | 0 | 90 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T18:53:53` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T18:53:55` `chat` / `qwen3-32b` input=906 output=49 total=955 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T18:53:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T18:53:55` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T18:53:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T18:53:55` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T18:53:55` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T18:53:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T18:53:56` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T18:53:56` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T18:53:56` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T18:53:56` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T18:53:56` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T18:53:56` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-12T18:54:08` `chat` / `qwen3-32b` input=3378 output=445 total=3823 source=`ragent.llm.openai.openai_complete_if_cache`
