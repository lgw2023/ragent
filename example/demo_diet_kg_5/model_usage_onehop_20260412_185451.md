# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T18:54:18`
- Ended at: `2026-04-12T18:54:51`
- Metadata:
  - `query`: `我想做减脂期饮食搭配，日常怎么安排更合适，尤其是每天大概需要吃几类食物、每周各类食物至少要吃几种？另外，哪些食物更适合少吃、哪些更适合多吃？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4614 | 1011 | 5625 | 0 |
| embedding | 14 | 132 | 0 | 132 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 4746 | 1011 | 5757 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4614 | 1011 | 5625 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 132 | 0 | 132 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T18:54:19` `embedding` / `text-embedding-v3` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T18:54:20` `chat` / `qwen3-32b` input=914 output=66 total=980 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T18:54:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T18:54:22` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-12T18:54:51` `chat` / `qwen3-32b` input=3700 output=945 total=4645 source=`ragent.llm.openai.openai_complete_if_cache`
