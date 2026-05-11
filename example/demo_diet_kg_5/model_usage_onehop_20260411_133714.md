# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:37:04`
- Ended at: `2026-04-11T13:37:14`
- Metadata:
  - `query`: `根据《中华人民共和国国家标准》GB/T 1354-2018 中的检验方法，碎米含量检验和加工精度检验分别应按什么标准执行？这两项检验中，哪一项明确要求在称量前先把混入其中的长度不小于完整米粒平均长度四分之三的米粒拣出？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3837 | 213 | 4050 | 0 |
| embedding | 12 | 150 | 0 | 150 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 3987 | 213 | 4200 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3837 | 213 | 4050 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 150 | 0 | 150 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:37:04` `embedding` / `text-embedding-v3` input=70 output=0 total=70 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:37:07` `chat` / `qwen3-32b` input=946 output=70 total=1016 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:37:07` `embedding` / `text-embedding-v3` input=10 output=0 total=10 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:37:07` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:37:07` `embedding` / `text-embedding-v3` input=28 output=0 total=28 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:37:07` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:37:07` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:37:08` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:37:08` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:37:08` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:37:08` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T13:37:08` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T13:37:08` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T13:37:08` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-11T13:37:13` `chat` / `qwen3-32b` input=2891 output=143 total=3034 source=`ragent.llm.openai.openai_complete_if_cache`
