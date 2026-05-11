# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:01:40`
- Ended at: `2026-04-12T19:02:02`
- Metadata:
  - `query`: `我有点担心血压偏高，但平时也想把饮食吃得更均衡一些。日常安排主食时，哪些类型的谷薯杂豆类更适合作为主要选择，能更好地提供碳水化合物、蛋白质以及B族维生素、钙、铁、锌、镁、钾等营养素？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4628 | 557 | 5185 | 0 |
| embedding | 17 | 150 | 0 | 150 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 20 | 4778 | 557 | 5335 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4628 | 557 | 5185 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 17 | 150 | 0 | 150 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:01:40` `embedding` / `text-embedding-v3` input=66 output=0 total=66 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:01:43` `chat` / `qwen3-32b` input=934 output=69 total=1003 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:01:43` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:01:43` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:01:43` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:01:43` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:01:43` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:01:43` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:01:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:01:43` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:01:43` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T19:01:44` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T19:01:44` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T19:01:44` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T19:01:44` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T19:01:44` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T19:01:44` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
18. `2026-04-12T19:01:44` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
19. `2026-04-12T19:01:44` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
20. `2026-04-12T19:02:01` `chat` / `qwen3-32b` input=3694 output=488 total=4182 source=`ragent.llm.openai.openai_complete_if_cache`
