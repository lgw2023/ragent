# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:47:55`
- Ended at: `2026-04-12T21:48:30`
- Metadata:
  - `query`: `我想给有肥胖又有高血压的人安排一份日常食疗，手里有荷叶、山楂、茯苓、白扁豆和山药这几样，按常见的中医证型来看，哪些更适合肥胖的哪几类证型；同时如果是高血压日常饮食，还应该重点注意什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4819 | 658 | 5477 | 0 |
| embedding | 15 | 147 | 0 | 147 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 18 | 4966 | 658 | 5624 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4819 | 658 | 5477 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 15 | 147 | 0 | 147 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:47:55` `embedding` / `text-embedding-v3` input=69 output=0 total=69 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:48:00` `chat` / `qwen3-32b` input=934 output=63 total=997 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:48:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:48:00` `embedding` / `text-embedding-v3` input=28 output=0 total=28 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:48:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:48:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:48:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:48:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:48:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:48:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:48:00` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:48:01` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:48:01` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:48:01` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:48:01` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:48:01` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T21:48:01` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
18. `2026-04-12T21:48:29` `chat` / `qwen3-32b` input=3885 output=595 total=4480 source=`ragent.llm.openai.openai_complete_if_cache`
