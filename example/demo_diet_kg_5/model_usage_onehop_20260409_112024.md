# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T11:20:14`
- Ended at: `2026-04-09T11:20:24`
- Metadata:
  - `query`: `如果你现在想立刻准备一顿更符合这页指南倡导方式的家庭餐，依据图片内容，以下哪种做法最符合：A. 只点高油高盐外卖，不做任何处理；B. 家人一起用鸡蛋和彩椒、番茄、黄瓜等新鲜食材现做现吃；C. 用保健品代替一餐；D. 只吃一种食物以求简单？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3882 | 306 | 4188 | 0 |
| embedding | 14 | 162 | 0 | 162 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 4044 | 306 | 4350 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3882 | 306 | 4188 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 162 | 0 | 162 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T11:20:14` `embedding` / `text-embedding-v3` input=88 output=0 total=88 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T11:20:16` `chat` / `qwen3-32b` input=954 output=59 total=1013 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T11:20:16` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T11:20:16` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T11:20:16` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T11:20:16` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T11:20:16` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T11:20:16` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T11:20:16` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T11:20:16` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T11:20:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T11:20:17` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T11:20:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T11:20:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
15. `2026-04-09T11:20:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
16. `2026-04-09T11:20:17` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-09T11:20:24` `chat` / `qwen3-32b` input=2928 output=247 total=3175 source=`ragent.llm.openai.openai_complete_if_cache`
