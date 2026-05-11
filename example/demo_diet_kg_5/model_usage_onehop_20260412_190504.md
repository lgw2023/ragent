# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:04:37`
- Ended at: `2026-04-12T19:05:04`
- Metadata:
  - `query`: `我今年17岁，身高170厘米，体重160斤，平时每天打排球2到3小时，另外每周还会做力量训练。按我的情况，首先应该怎么判断自己现在是不是超重或肥胖？如果想把体重降到130斤，饮食上更适合怎么调整主食结构，才能更有利于减脂又不至于吃得太单一？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3835 | 775 | 4610 | 0 |
| embedding | 14 | 147 | 0 | 147 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 3982 | 775 | 4757 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3835 | 775 | 4610 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 147 | 0 | 147 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:04:37` `embedding` / `text-embedding-v3` input=77 output=0 total=77 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:04:39` `chat` / `qwen3-32b` input=951 output=64 total=1015 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=26 output=0 total=26 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T19:04:40` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T19:04:41` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-12T19:05:04` `chat` / `qwen3-32b` input=2884 output=711 total=3595 source=`ragent.llm.openai.openai_complete_if_cache`
