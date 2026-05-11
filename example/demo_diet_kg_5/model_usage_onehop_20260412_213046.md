# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:30:32`
- Ended at: `2026-04-12T21:30:46`
- Metadata:
  - `query`: `如果我想控制体重，日常水果该怎么选才更合适？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4209 | 519 | 4728 | 0 |
| embedding | 9 | 47 | 0 | 47 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4256 | 519 | 4775 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4209 | 519 | 4728 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 47 | 0 | 47 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:30:32` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:30:33` `chat` / `qwen3-32b` input=883 output=37 total=920 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:30:33` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:30:33` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:30:33` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:30:34` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:30:34` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:30:34` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:30:34` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:30:34` `embedding` / `text-embedding-v3` input=10 output=0 total=10 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:30:34` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T21:30:45` `chat` / `qwen3-32b` input=3326 output=482 total=3808 source=`ragent.llm.openai.openai_complete_if_cache`
