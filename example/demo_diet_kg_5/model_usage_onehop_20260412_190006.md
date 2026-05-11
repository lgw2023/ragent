# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T18:59:44`
- Ended at: `2026-04-12T19:00:06`
- Metadata:
  - `query`: `我今年31岁，平时久坐，BMI大概24.5，想知道这种情况是不是已经偏胖了？如果想把体重和体脂控制下来，日常饮食上最该注意什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3814 | 662 | 4476 | 0 |
| embedding | 12 | 90 | 0 | 90 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 3904 | 662 | 4566 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3814 | 662 | 4476 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 90 | 0 | 90 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T18:59:44` `embedding` / `text-embedding-v3` input=40 output=0 total=40 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T18:59:46` `chat` / `qwen3-32b` input=914 output=55 total=969 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T18:59:46` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T18:59:46` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T18:59:46` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T18:59:46` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T18:59:46` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T18:59:46` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T18:59:46` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T18:59:47` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T18:59:47` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T18:59:47` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T18:59:47` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T18:59:47` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-12T19:00:06` `chat` / `qwen3-32b` input=2900 output=607 total=3507 source=`ragent.llm.openai.openai_complete_if_cache`
