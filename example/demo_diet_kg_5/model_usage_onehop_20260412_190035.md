# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:00:18`
- Ended at: `2026-04-12T19:00:35`
- Metadata:
  - `query`: `我想按减脂思路安排日常主食和早餐，家里常吃大米和豆腐。请问在这些选择里，嫩豆腐、老豆腐、冷冻豆腐、脱水豆腐中，哪一种每100克蛋白质含量最高？如果主食也想选一种更适合控制体重、同时常见又好搭配的米，粘米、粳米、灿糯米、粳糯米里哪一种的碎米总量上限最低？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3777 | 439 | 4216 | 0 |
| embedding | 14 | 185 | 0 | 185 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 3962 | 439 | 4401 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3777 | 439 | 4216 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 185 | 0 | 185 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:00:19` `embedding` / `text-embedding-v3` input=94 output=0 total=94 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:00:20` `chat` / `qwen3-32b` input=961 output=74 total=1035 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T19:00:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T19:00:22` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-12T19:00:35` `chat` / `qwen3-32b` input=2816 output=365 total=3181 source=`ragent.llm.openai.openai_complete_if_cache`
