# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:37:25`
- Ended at: `2026-04-11T13:37:31`
- Metadata:
  - `query`: `根据《中国居民膳食指南（2022）》中“准则一 食物多样，合理搭配”的建议，水果每天推荐摄入量是多少？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4062 | 122 | 4184 | 0 |
| embedding | 9 | 85 | 0 | 85 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4147 | 122 | 4269 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4062 | 122 | 4184 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 85 | 0 | 85 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:37:25` `embedding` / `text-embedding-v3` input=33 output=0 total=33 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:37:27` `chat` / `qwen3-32b` input=907 output=49 total=956 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:37:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:37:27` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:37:27` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:37:27` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:37:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:37:28` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:37:28` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:37:28` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:37:28` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-11T13:37:31` `chat` / `qwen3-32b` input=3155 output=73 total=3228 source=`ragent.llm.openai.openai_complete_if_cache`
