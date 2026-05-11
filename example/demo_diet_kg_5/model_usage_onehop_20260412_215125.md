# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:50:59`
- Ended at: `2026-04-12T21:51:25`
- Metadata:
  - `query`: `我今年17岁，身高170厘米，体重80公斤，平时每天有2到3小时排球训练，每周还会加练力量训练。想在保证运动状态的前提下减到大约65公斤，日常总消耗里主动活动大概要占多少才更合适？如果按适合减脂的思路安排一天饮食，下面哪一档更接近合理：1200、1400、1600 还是更高？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4435 | 785 | 5220 | 0 |
| embedding | 15 | 162 | 0 | 162 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 18 | 4597 | 785 | 5382 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4435 | 785 | 5220 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 15 | 162 | 0 | 162 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:51:00` `embedding` / `text-embedding-v3` input=84 output=0 total=84 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:51:02` `chat` / `qwen3-32b` input=971 output=72 total=1043 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=35 output=0 total=35 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:51:02` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T21:51:03` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
18. `2026-04-12T21:51:24` `chat` / `qwen3-32b` input=3464 output=713 total=4177 source=`ragent.llm.openai.openai_complete_if_cache`
