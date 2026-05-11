# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T15:29:02`
- Ended at: `2026-04-12T15:29:14`
- Metadata:
  - `query`: `我想挑那种更容易在买米时辨认、也更容易把米分级说清楚的术语：一批米里，长度不到同批完整米粒平均长度的四分之三，而且留在直径2.0毫米圆孔筛上的不完整米粒，应该叫哪一类？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 2981 | 242 | 3223 | 0 |
| embedding | 11 | 139 | 0 | 139 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 3120 | 242 | 3362 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 2981 | 242 | 3223 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 139 | 0 | 139 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T15:29:03` `embedding` / `text-embedding-v3` input=65 output=0 total=65 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T15:29:05` `chat` / `qwen3-32b` input=933 output=61 total=994 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=28 output=0 total=28 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T15:29:06` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T15:29:07` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T15:29:14` `chat` / `qwen3-32b` input=2048 output=181 total=2229 source=`ragent.llm.openai.openai_complete_if_cache`
