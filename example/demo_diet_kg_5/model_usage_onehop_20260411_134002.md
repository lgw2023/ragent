# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:39:40`
- Ended at: `2026-04-11T13:40:02`
- Metadata:
  - `query`: `根据《中国居民平衡膳食宝塔（2022）》这张图，下面哪种做法更符合“均衡膳食”的推荐？A. 晚餐只吃水果和蔬菜，不吃谷薯类和其他食物；B. 以谷薯类为基础，搭配蔬菜水果、动物性食物、奶及豆制品，并控制盐和油的摄入。`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4288 | 400 | 4688 | 0 |
| embedding | 13 | 160 | 0 | 160 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 4448 | 400 | 4848 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4288 | 400 | 4688 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 160 | 0 | 160 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:39:41` `embedding` / `text-embedding-v3` input=80 output=0 total=80 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:39:42` `chat` / `qwen3-32b` input=949 output=62 total=1011 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=28 output=0 total=28 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T13:39:43` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-11T13:39:44` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-11T13:40:02` `chat` / `qwen3-32b` input=3339 output=338 total=3677 source=`ragent.llm.openai.openai_complete_if_cache`
