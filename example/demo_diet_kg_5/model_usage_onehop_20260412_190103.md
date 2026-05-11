# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T19:00:45`
- Ended at: `2026-04-12T19:01:03`
- Metadata:
  - `query`: `我最近在减重，平时吃得已经很少了，但体重还是不怎么下降，这通常说明什么问题？是不是和活动量太少、能量收支没平衡有关？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4116 | 581 | 4697 | 0 |
| embedding | 11 | 93 | 0 | 93 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 4209 | 581 | 4790 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4116 | 581 | 4697 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 93 | 0 | 93 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T19:00:45` `embedding` / `text-embedding-v3` input=39 output=0 total=39 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T19:00:47` `chat` / `qwen3-32b` input=908 output=48 total=956 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T19:00:47` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T19:00:47` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T19:00:47` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T19:00:47` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T19:00:47` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T19:00:48` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T19:00:48` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T19:00:48` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T19:00:48` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T19:00:48` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T19:00:48` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T19:01:03` `chat` / `qwen3-32b` input=3208 output=533 total=3741 source=`ragent.llm.openai.openai_complete_if_cache`
