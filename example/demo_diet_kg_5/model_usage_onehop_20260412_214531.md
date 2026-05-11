# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:45:02`
- Ended at: `2026-04-12T21:45:31`
- Metadata:
  - `query`: `我在减重，平时饮食也比较规律，但最近双腿和脚踝都出现了水肿，还会有疼痛。除了先看医生排查病因外，如果想先从饮食上调整，哪些吃法更适合这种需要控制体重、又要注意血压和水肿的人？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4266 | 661 | 4927 | 0 |
| embedding | 14 | 139 | 0 | 139 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 4405 | 661 | 5066 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4266 | 661 | 4927 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 139 | 0 | 139 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:45:02` `embedding` / `text-embedding-v3` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:45:04` `chat` / `qwen3-32b` input=927 output=57 total=984 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:45:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:45:04` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:45:04` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:45:04` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:45:04` `embedding` / `text-embedding-v3` input=27 output=0 total=27 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:45:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:45:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:45:05` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:45:05` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:45:05` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:45:05` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:45:05` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:45:05` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:45:05` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-12T21:45:31` `chat` / `qwen3-32b` input=3339 output=604 total=3943 source=`ragent.llm.openai.openai_complete_if_cache`
