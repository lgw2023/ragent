# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T18:55:22`
- Ended at: `2026-04-12T18:55:50`
- Metadata:
  - `query`: `我想自己做一款无糖或少糖的豆浆饮品，按每100克算，蛋白质和脂肪至少要达到什么下限，才能算是纯豆浆或调味豆浆？另外，如果我再配一份适合高血压人群的冬季一日食谱，里面的山楂决明瘦肉汤和百合银耳雪梨羹这类搭配是否都属于适合控压、偏清淡的饮食思路？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5194 | 818 | 6012 | 0 |
| embedding | 16 | 238 | 0 | 238 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 19 | 5432 | 818 | 6250 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5194 | 818 | 6012 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 16 | 238 | 0 | 238 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T18:55:22` `embedding` / `text-embedding-v3` input=94 output=0 total=94 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T18:55:27` `chat` / `qwen3-32b` input=957 output=91 total=1048 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T18:55:27` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T18:55:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T18:55:27` `embedding` / `text-embedding-v3` input=7 output=0 total=7 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T18:55:27` `embedding` / `text-embedding-v3` input=50 output=0 total=50 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=7 output=0 total=7 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T18:55:28` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
18. `2026-04-12T18:55:29` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
19. `2026-04-12T18:55:49` `chat` / `qwen3-32b` input=4237 output=727 total=4964 source=`ragent.llm.openai.openai_complete_if_cache`
