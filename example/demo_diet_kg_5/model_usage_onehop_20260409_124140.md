# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T12:41:11`
- Ended at: `2026-04-09T12:41:40`
- Metadata:
  - `query`: `一位高血压患者晚餐想在“喝汤”和“补充蛋白质”之间做更稳妥的选择：如果在华东地区秋季食谱2的早餐里加一杯豆浆（大豆10g），并把正餐中的肉类主要营养获取方式理解为“只喝鸡汤、不吃鸡肉”，这种做法是否符合“既要喝汤，更要吃肉”的原则？请结合豆浆国家标准与鸡肉/鸡汤营养对比，判断更应优先保留哪一种来保证蛋白质摄入，并说明依据。`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5440 | 621 | 6061 | 0 |
| embedding | 15 | 217 | 0 | 217 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 18 | 5657 | 621 | 6278 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5440 | 621 | 6061 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 15 | 217 | 0 | 217 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T12:41:11` `embedding` / `text-embedding-v3` input=121 output=0 total=121 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T12:41:14` `chat` / `qwen3-32b` input=973 output=65 total=1038 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=32 output=0 total=32 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=26 output=0 total=26 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T12:41:14` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-09T12:41:15` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
16. `2026-04-09T12:41:15` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
17. `2026-04-09T12:41:15` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
18. `2026-04-09T12:41:39` `chat` / `qwen3-32b` input=4467 output=556 total=5023 source=`ragent.llm.openai.openai_complete_if_cache`
