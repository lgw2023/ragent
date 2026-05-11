# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:39:09`
- Ended at: `2026-04-11T13:39:27`
- Metadata:
  - `query`: `如果我想减脂，按《中国居民膳食指南（2022）》里的晚餐示例来安排，下面这个晚餐最符合推荐的是哪一个：A. 素三丁、炒苋菜、番茄蛋汤；B. 宫保鸡丁、油炸薯条、可乐；C. 红烧鸡翅、甜饮料、蛋糕；D. 火锅、啤酒、冰淇淋。`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4957 | 427 | 5384 | 0 |
| embedding | 14 | 185 | 0 | 185 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 5142 | 427 | 5569 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4957 | 427 | 5384 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 185 | 0 | 185 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:39:10` `embedding` / `text-embedding-v3` input=86 output=0 total=86 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:39:13` `chat` / `qwen3-32b` input=961 output=83 total=1044 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:39:13` `embedding` / `text-embedding-v3` input=52 output=0 total=52 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:39:13` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:39:13` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:39:13` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:39:13` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:39:14` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:39:14` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:39:14` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:39:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T13:39:14` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T13:39:14` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T13:39:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
15. `2026-04-11T13:39:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
16. `2026-04-11T13:39:14` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-11T13:39:27` `chat` / `qwen3-32b` input=3996 output=344 total=4340 source=`ragent.llm.openai.openai_complete_if_cache`
