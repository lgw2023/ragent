# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T22:50:48`
- Ended at: `2026-04-11T22:51:06`
- Metadata:
  - `query`: `我最近在减脂，想喝一瓶甜味果蔬饮料，但每瓶大概有10克添加糖，虽然总热量只有140千卡，这种情况还适合偶尔喝吗？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4147 | 393 | 4540 | 0 |
| embedding | 10 | 91 | 0 | 91 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 4238 | 393 | 4631 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4147 | 393 | 4540 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 10 | 91 | 0 | 91 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T22:50:48` `embedding` / `text-embedding-v3` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T22:50:50` `chat` / `qwen3-32b` input=913 output=44 total=957 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T22:50:50` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T22:50:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T22:50:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T22:50:50` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T22:50:50` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T22:50:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T22:50:50` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T22:50:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T22:50:50` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T22:50:51` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-11T22:51:05` `chat` / `qwen3-32b` input=3234 output=349 total=3583 source=`ragent.llm.openai.openai_complete_if_cache`
