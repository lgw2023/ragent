# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-08T18:49:28`
- Ended at: `2026-04-08T18:50:08`
- Metadata:
  - `query`: `我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先中速步行 30 分钟，再爬楼多久能补回来？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4360 | 561 | 4921 | 0 |
| embedding | 9 | 77 | 0 | 77 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4437 | 561 | 4998 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4360 | 561 | 4921 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 77 | 0 | 77 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-08T18:49:32` `embedding` / `text-embedding-v3` input=37 output=0 total=37 source=`ragent.llm.openai.openai_embed`
2. `2026-04-08T18:49:34` `chat` / `qwen3-32b` input=913 output=42 total=955 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-08T18:49:38` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
4. `2026-04-08T18:49:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-08T18:49:39` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-08T18:49:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-08T18:49:41` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-08T18:49:42` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-08T18:49:43` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-08T18:49:44` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
11. `2026-04-08T18:49:48` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-08T18:50:07` `chat` / `qwen3-32b` input=3447 output=519 total=3966 source=`ragent.llm.openai.openai_complete_if_cache`
