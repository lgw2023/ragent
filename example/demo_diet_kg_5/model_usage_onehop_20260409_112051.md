# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T11:20:37`
- Ended at: `2026-04-09T11:20:51`
- Metadata:
  - `query`: `高血压患者在外卖或现成餐选择时，若想同时兼顾补充优质蛋白和控制钠摄入，在“瓦罐鸡肉和汤”二选一以及“豆浆”作为搭配饮品的前提下，哪种组合更合适：A. 只喝鸡汤+任意豆浆；B. 吃鸡肉+外观均匀乳液状、质地细腻、允许少量沉淀和脂肪析出的豆浆；C. 只喝鸡汤+外观有少量沉淀的豆浆。请根据资料判断最佳选项，并说明关键依据。`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4138 | 469 | 4607 | 0 |
| embedding | 15 | 212 | 0 | 212 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 18 | 4350 | 469 | 4819 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4138 | 469 | 4607 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 15 | 212 | 0 | 212 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T11:20:37` `embedding` / `text-embedding-v3` input=130 output=0 total=130 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T11:20:39` `chat` / `qwen3-32b` input=979 output=60 total=1039 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T11:20:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T11:20:39` `embedding` / `text-embedding-v3` input=27 output=0 total=27 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T11:20:39` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T11:20:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T11:20:39` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T11:20:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T11:20:39` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T11:20:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T11:20:40` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T11:20:40` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T11:20:40` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T11:20:40` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
15. `2026-04-09T11:20:40` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
16. `2026-04-09T11:20:40` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
17. `2026-04-09T11:20:40` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
18. `2026-04-09T11:20:51` `chat` / `qwen3-32b` input=3159 output=409 total=3568 source=`ragent.llm.openai.openai_complete_if_cache`
