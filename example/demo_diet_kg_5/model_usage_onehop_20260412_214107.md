# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:40:47`
- Ended at: `2026-04-12T21:41:07`
- Metadata:
  - `query`: `我最近想把晚餐里的主菜换一下：如果把50克即食鸡胸肉换成同样大致分量的鸡蛋，和鸡胸肉相比，哪一个更适合作为日常减脂饮食里的蛋白质来源？为什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4784 | 662 | 5446 | 0 |
| embedding | 9 | 87 | 0 | 87 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4871 | 662 | 5533 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4784 | 662 | 5446 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 87 | 0 | 87 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:40:47` `embedding` / `text-embedding-v3` input=49 output=0 total=49 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:40:48` `chat` / `qwen3-32b` input=921 output=40 total=961 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:40:49` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:40:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:40:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:40:49` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:40:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:40:49` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:40:49` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:40:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:40:49` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-12T21:41:07` `chat` / `qwen3-32b` input=3863 output=622 total=4485 source=`ragent.llm.openai.openai_complete_if_cache`
