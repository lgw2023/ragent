# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T22:47:26`
- Ended at: `2026-04-11T22:47:45`
- Metadata:
  - `query`: `如果一个成人想把血压控制得更稳，日常饮食上最核心的五个方面，哪一项最突出“少盐多钾”，哪一项最突出“合理搭配食物”，哪一项最突出“控制体重”，哪一项最突出“戒烟限酒”，哪一项最突出“定期监测并自我管理”？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4154 | 516 | 4670 | 0 |
| embedding | 17 | 160 | 0 | 160 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 20 | 4314 | 516 | 4830 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4154 | 516 | 4670 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 17 | 160 | 0 | 160 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T22:47:26` `embedding` / `text-embedding-v3` input=68 output=0 total=68 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T22:47:29` `chat` / `qwen3-32b` input=939 output=76 total=1015 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=26 output=0 total=26 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
15. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
16. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
17. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=36 output=0 total=36 source=`ragent.llm.openai.openai_embed`
18. `2026-04-11T22:47:29` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
19. `2026-04-11T22:47:30` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
20. `2026-04-11T22:47:44` `chat` / `qwen3-32b` input=3215 output=440 total=3655 source=`ragent.llm.openai.openai_complete_if_cache`
