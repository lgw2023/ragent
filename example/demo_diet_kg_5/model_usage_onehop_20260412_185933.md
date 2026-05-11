# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T18:59:19`
- Ended at: `2026-04-12T18:59:33`
- Metadata:
  - `query`: `我想把主食和一部分肉类换得更健康一些，同时控制体重和血压。按常见成人饮食建议，平均每天至少要吃几类食物、每周至少要吃几类食物？另外如果选一款豆腐干，哪一类豆腐干应满足“颜色纯正、形状完整、大小薄厚均匀，孔状均匀、无霉点、组织松脆”这组要求？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3776 | 391 | 4167 | 0 |
| embedding | 15 | 178 | 0 | 178 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 18 | 3954 | 391 | 4345 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3776 | 391 | 4167 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 15 | 178 | 0 | 178 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T18:59:19` `embedding` / `text-embedding-v3` input=89 output=0 total=89 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T18:59:23` `chat` / `qwen3-32b` input=956 output=69 total=1025 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T18:59:23` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T18:59:23` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T18:59:23` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=35 output=0 total=35 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T18:59:24` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T18:59:25` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
18. `2026-04-12T18:59:33` `chat` / `qwen3-32b` input=2820 output=322 total=3142 source=`ragent.llm.openai.openai_complete_if_cache`
