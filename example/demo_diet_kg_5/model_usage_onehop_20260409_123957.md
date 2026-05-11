# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T12:39:44`
- Ended at: `2026-04-09T12:39:57`
- Metadata:
  - `query`: `成人肥胖患者如果想按指南选择一天食谱，应该优先在 1200kcal、1400kcal、1600kcal 这些示例能量水平中固定照搬，还是需要结合身高、体重和身体活动水平再做调整？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4603 | 321 | 4924 | 0 |
| embedding | 13 | 117 | 0 | 117 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 4720 | 321 | 5041 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4603 | 321 | 4924 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 117 | 0 | 117 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T12:39:45` `embedding` / `text-embedding-v3` input=51 output=0 total=51 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T12:39:47` `chat` / `qwen3-32b` input=933 output=68 total=1001 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T12:39:47` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T12:39:47` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T12:39:47` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T12:39:47` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T12:39:48` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T12:39:48` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T12:39:48` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T12:39:48` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T12:39:48` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T12:39:48` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T12:39:48` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T12:39:48` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-09T12:39:48` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-09T12:39:57` `chat` / `qwen3-32b` input=3670 output=253 total=3923 source=`ragent.llm.openai.openai_complete_if_cache`
