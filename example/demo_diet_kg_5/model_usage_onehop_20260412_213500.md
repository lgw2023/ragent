# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:34:39`
- Ended at: `2026-04-12T21:35:00`
- Metadata:
  - `query`: `我想把一日三餐吃得更合理，同时控制体重。按照这个建议，如果是一个 17 岁、身高 170 厘米、体重 80 公斤的女生，想减到更健康的体重，日常饮食里主食、蔬菜、肉蛋奶、油分别应该怎么安排？另外，类似这种食量偏大的饮食习惯，和现在常见的膳食结构相比，主要变化趋势是什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3994 | 639 | 4633 | 0 |
| embedding | 15 | 169 | 0 | 169 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 18 | 4163 | 639 | 4802 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3994 | 639 | 4633 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 15 | 169 | 0 | 169 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:34:40` `embedding` / `text-embedding-v3` input=85 output=0 total=85 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:34:42` `chat` / `qwen3-32b` input=965 output=75 total=1040 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:34:42` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:34:42` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:34:42` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:34:42` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:34:42` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:34:42` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:34:42` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:34:42` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:34:43` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:34:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:34:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:34:43` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:34:43` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:34:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T21:34:43` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
18. `2026-04-12T21:35:00` `chat` / `qwen3-32b` input=3029 output=564 total=3593 source=`ragent.llm.openai.openai_complete_if_cache`
