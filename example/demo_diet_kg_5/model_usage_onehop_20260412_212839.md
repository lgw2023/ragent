# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:28:24`
- Ended at: `2026-04-12T21:28:39`
- Metadata:
  - `query`: `我家里想做一周减脂餐，目标是少吃油盐、控制热量，同时保证饮食多样。请帮我判断：如果按这个思路搭配，平均每天至少要吃多少类食物、每周至少要覆盖多少类食物；另外，常见主食里大米的质量指标里，哪一类粘米的碎米总量上限和水分含量上限最严格？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4250 | 388 | 4638 | 0 |
| embedding | 16 | 184 | 0 | 184 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 19 | 4434 | 388 | 4822 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4250 | 388 | 4638 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 16 | 184 | 0 | 184 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:28:24` `embedding` / `text-embedding-v3` input=81 output=0 total=81 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:28:28` `chat` / `qwen3-32b` input=948 output=81 total=1029 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:28:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:28:28` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:28:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:28:28` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:28:28` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:28:28` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:28:28` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:28:28` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:28:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:28:29` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:28:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:28:29` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:28:29` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:28:29` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T21:28:29` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
18. `2026-04-12T21:28:29` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
19. `2026-04-12T21:28:39` `chat` / `qwen3-32b` input=3302 output=307 total=3609 source=`ragent.llm.openai.openai_complete_if_cache`
