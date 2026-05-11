# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T15:25:02`
- Ended at: `2026-04-12T15:25:20`
- Metadata:
  - `query`: `如果我把午餐里的肉类主要换成瘦猪肉、鸡肉、鱼和鸡蛋，哪些更适合减重期间经常吃，哪些要少吃？请按脂肪和胆固醇的高低来判断。`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4346 | 515 | 4861 | 0 |
| embedding | 13 | 118 | 0 | 118 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 4464 | 515 | 4979 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4346 | 515 | 4861 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 118 | 0 | 118 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T15:25:03` `embedding` / `text-embedding-v3` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T15:25:04` `chat` / `qwen3-32b` input=908 output=54 total=962 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T15:25:05` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T15:25:06` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-12T15:25:19` `chat` / `qwen3-32b` input=3438 output=461 total=3899 source=`ragent.llm.openai.openai_complete_if_cache`
