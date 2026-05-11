# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:02:12`
- Ended at: `2026-04-12T19:02:31`
- Metadata:
  - `query`: `我想做一个更适合减重、同时又兼顾血压管理的日常饮食安排：如果把主食从精白米饭换成更常见的杂粮搭配，配上一天总油脂控制在较低水平的三餐，哪一种搭配更符合“食物多样、合理搭配”的思路，而且还能满足成人肥胖人群常见的能量控制目标？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4448 | 548 | 4996 | 0 |
| embedding | 15 | 155 | 0 | 155 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 18 | 4603 | 548 | 5151 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4448 | 548 | 4996 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 15 | 155 | 0 | 155 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:02:12` `embedding` / `text-embedding-v3` input=75 output=0 total=75 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:02:14` `chat` / `qwen3-32b` input=940 output=64 total=1004 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:02:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:02:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:02:14` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:02:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:02:14` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:02:14` `embedding` / `text-embedding-v3` input=26 output=0 total=26 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:02:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:02:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:02:15` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T19:02:15` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T19:02:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T19:02:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T19:02:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T19:02:15` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T19:02:15` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
18. `2026-04-12T19:02:30` `chat` / `qwen3-32b` input=3508 output=484 total=3992 source=`ragent.llm.openai.openai_complete_if_cache`
