# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:25:09`
- Ended at: `2026-04-12T00:25:31`
- Metadata:
  - `query`: `日常饮食里，鸡蛋和鱼肉相比，哪个更适合作为优先选择的动物性食物？请列出两者的主要区别。`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4229 | 764 | 4993 | 0 |
| embedding | 11 | 81 | 0 | 81 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 4310 | 764 | 5074 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4229 | 764 | 4993 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 81 | 0 | 81 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:25:09` `embedding` / `text-embedding-v3` input=27 output=0 total=27 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:25:11` `chat` / `qwen3-32b` input=899 output=50 total=949 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:25:11` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:25:11` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:25:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:25:11` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:25:11` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:25:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:25:11` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:25:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:25:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T00:25:12` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T00:25:13` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T00:25:31` `chat` / `qwen3-32b` input=3330 output=714 total=4044 source=`ragent.llm.openai.openai_complete_if_cache`
