# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:26:47`
- Ended at: `2026-04-12T00:27:08`
- Metadata:
  - `query`: `如果要按日常饮食建议来对比，鱼虾蛋豆和谷薯类这两类食物，哪一类更应该作为每餐的主要组成，哪一类应该少一些？请用列表说明。`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4271 | 657 | 4928 | 0 |
| embedding | 12 | 109 | 0 | 109 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4380 | 657 | 5037 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4271 | 657 | 4928 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 109 | 0 | 109 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:26:47` `embedding` / `text-embedding-v3` input=43 output=0 total=43 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:26:49` `chat` / `qwen3-32b` input=912 output=55 total=967 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T00:26:50` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T00:26:51` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-12T00:27:08` `chat` / `qwen3-32b` input=3359 output=602 total=3961 source=`ragent.llm.openai.openai_complete_if_cache`
