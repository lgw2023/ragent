# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T11:19:24`
- Ended at: `2026-04-09T11:19:39`
- Metadata:
  - `query`: `成人肥胖患者在按指南安排日常饮食时，如果既想控制体重又经常饮酒，饮食管理上应优先满足哪些筛选条件：是选择高能量食物和酒类提神，还是应少吃高能量食物、饮食清淡并限制饮酒？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4138 | 552 | 4690 | 0 |
| embedding | 12 | 121 | 0 | 121 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4259 | 552 | 4811 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4138 | 552 | 4690 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 121 | 0 | 121 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T11:19:24` `embedding` / `text-embedding-v3` input=59 output=0 total=59 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T11:19:26` `chat` / `qwen3-32b` input=925 output=52 total=977 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T11:19:26` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T11:19:26` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T11:19:26` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T11:19:26` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T11:19:26` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T11:19:26` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T11:19:26` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T11:19:26` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T11:19:27` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T11:19:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T11:19:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T11:19:27` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-09T11:19:39` `chat` / `qwen3-32b` input=3213 output=500 total=3713 source=`ragent.llm.openai.openai_complete_if_cache`
