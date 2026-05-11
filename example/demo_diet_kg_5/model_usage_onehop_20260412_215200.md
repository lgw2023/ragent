# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:51:36`
- Ended at: `2026-04-12T21:52:00`
- Metadata:
  - `query`: `我想控制体重，能不能帮我估算一下：一个31岁的男性，身高1.87米、体重130公斤，如果每天总共吃大约2200千卡，一般会更可能继续减重，还是大致维持不变？如果要把这2200千卡尽量分配到主食里，像米饭、馒头、面条、全谷物这些食物，大概分别相当于多少份？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4021 | 802 | 4823 | 0 |
| embedding | 14 | 157 | 0 | 157 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 4178 | 802 | 4980 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4021 | 802 | 4823 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 157 | 0 | 157 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:51:36` `embedding` / `text-embedding-v3` input=84 output=0 total=84 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:51:38` `chat` / `qwen3-32b` input=960 output=60 total=1020 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:51:38` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:51:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:51:38` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:51:38` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:51:38` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:51:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:51:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:51:38` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:51:39` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:51:39` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:51:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:51:39` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:51:39` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:51:39` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-12T21:52:00` `chat` / `qwen3-32b` input=3061 output=742 total=3803 source=`ragent.llm.openai.openai_complete_if_cache`
