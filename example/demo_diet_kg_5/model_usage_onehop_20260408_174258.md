# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-08T17:42:36`
- Ended at: `2026-04-08T17:42:58`
- Metadata:
  - `query`: `成人科学减重时，6 个月的理想减重目标和每月建议速度分别是什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 1 | 3596 | 166 | 3762 | 0 |
| embedding | 11 | 73 | 0 | 73 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 3669 | 166 | 3835 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 1 | 3596 | 166 | 3762 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 73 | 0 | 73 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-08T17:42:39` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
2. `2026-04-08T17:42:41` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
3. `2026-04-08T17:42:41` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-08T17:42:41` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
5. `2026-04-08T17:42:42` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-08T17:42:43` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
7. `2026-04-08T17:42:45` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-08T17:42:46` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-08T17:42:46` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-08T17:42:46` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-08T17:42:47` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
12. `2026-04-08T17:42:52` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-08T17:42:58` `chat` / `qwen3-32b` input=3596 output=166 total=3762 source=`ragent.llm.openai.openai_complete_if_cache`
