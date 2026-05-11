# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:38:36`
- Ended at: `2026-04-11T13:38:58`
- Metadata:
  - `query`: `如果我想按《中国居民膳食指南（2022）》给自己配一顿晚餐，哪一种做法最符合“适量吃鱼、禽、蛋、瘦肉”这一准则：只喝鸡汤不吃鸡肉，还是既喝汤也吃肉？请说明应该怎么选。`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3949 | 537 | 4486 | 0 |
| embedding | 14 | 134 | 0 | 134 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 4083 | 537 | 4620 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3949 | 537 | 4486 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 134 | 0 | 134 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:38:37` `embedding` / `text-embedding-v3` input=62 output=0 total=62 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:38:38` `chat` / `qwen3-32b` input=929 output=61 total=990 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=27 output=0 total=27 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
15. `2026-04-11T13:38:39` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
16. `2026-04-11T13:38:40` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-11T13:38:58` `chat` / `qwen3-32b` input=3020 output=476 total=3496 source=`ragent.llm.openai.openai_complete_if_cache`
