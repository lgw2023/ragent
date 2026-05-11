# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:26:01`
- Ended at: `2026-04-12T21:26:22`
- Metadata:
  - `query`: `我在控制体重时，晚餐只吃一小碗清淡的饭菜，白天也没怎么吃高油高糖的东西，但连续一段时间体重还是几乎没变化。除了“吃得少”这个因素外，最可能还和什么饮食结构问题有关？另外，如果想把日常饮食调整得更有利于减重，一天大概要吃多少类食物才更合适？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4093 | 788 | 4881 | 0 |
| embedding | 12 | 147 | 0 | 147 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4240 | 788 | 5028 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4093 | 788 | 4881 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 147 | 0 | 147 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:26:01` `embedding` / `text-embedding-v3` input=81 output=0 total=81 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:26:03` `chat` / `qwen3-32b` input=949 output=54 total=1003 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:26:04` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:26:05` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-12T21:26:22` `chat` / `qwen3-32b` input=3144 output=734 total=3878 source=`ragent.llm.openai.openai_complete_if_cache`
