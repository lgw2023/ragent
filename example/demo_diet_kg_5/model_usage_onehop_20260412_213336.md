# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:33:12`
- Ended at: `2026-04-12T21:33:36`
- Metadata:
  - `query`: `我想给一位既有高血压又偏胖的成年人安排日常饮食，下面两种做法里，哪一种更适合长期吃：A. 一日三餐按东北地区 1200kcal 的减重食谱来吃；B. 参考西南地区里那个包含山楂 10g、草决明 10g 的瘦肉汤搭配的饮食方案？如果只能选一种更合适的，你建议选哪种，为什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5547 | 659 | 6206 | 0 |
| embedding | 15 | 187 | 0 | 187 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 18 | 5734 | 659 | 6393 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5547 | 659 | 6206 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 15 | 187 | 0 | 187 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:33:12` `embedding` / `text-embedding-v3` input=93 output=0 total=93 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:33:15` `chat` / `qwen3-32b` input=968 output=76 total=1044 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:33:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:33:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:33:15` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:33:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:33:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:33:15` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:33:15` `embedding` / `text-embedding-v3` input=36 output=0 total=36 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:33:15` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:33:16` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:33:16` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:33:16` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:33:16` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:33:16` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:33:16` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T21:33:16` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
18. `2026-04-12T21:33:35` `chat` / `qwen3-32b` input=4579 output=583 total=5162 source=`ragent.llm.openai.openai_complete_if_cache`
