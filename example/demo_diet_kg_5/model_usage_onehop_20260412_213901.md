# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:38:46`
- Ended at: `2026-04-12T21:39:01`
- Metadata:
  - `query`: `我最近在控制体重，想自己安排饮食：如果按成人肥胖食养建议把全天能量控制在1600～2000千卡，同时参考高血压食养方案里那种“低钠盐、每天油约20～25g”的搭配思路，主食里把一部分普通大米换成脱水豆腐干，哪些食材的蛋白质含量更高、又更适合少油少盐的减重餐？在这几类里，能否直接判断出“脱水豆腐干”的蛋白质含量下限是否高于大米1级的蛋白质含量上限？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4576 | 390 | 4966 | 0 |
| embedding | 17 | 242 | 0 | 242 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 20 | 4818 | 390 | 5208 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4576 | 390 | 4966 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 17 | 242 | 0 | 242 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:38:46` `embedding` / `text-embedding-v3` input=124 output=0 total=124 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:38:49` `chat` / `qwen3-32b` input=992 output=82 total=1074 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:38:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:38:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:38:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:38:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:38:49` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:38:49` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:38:49` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:38:49` `embedding` / `text-embedding-v3` input=35 output=0 total=35 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:38:50` `embedding` / `text-embedding-v3` input=36 output=0 total=36 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:38:50` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:38:50` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:38:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:38:50` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:38:50` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T21:38:50` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
18. `2026-04-12T21:38:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
19. `2026-04-12T21:38:50` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
20. `2026-04-12T21:39:01` `chat` / `qwen3-32b` input=3584 output=308 total=3892 source=`ragent.llm.openai.openai_complete_if_cache`
